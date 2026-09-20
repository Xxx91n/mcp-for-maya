"""Maya client for communicating with Maya command ports."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from typing_extensions import Self

from maya_mcp_server.bootstrap import (
    get_bootstrap_code,
    get_helper_module_code,
)
from maya_mcp_server.maya_mcp_helper import (
    FRAME_HEADER_SIZE,
    MAX_FRAME_SIZE,
    encode_frame,
)
from maya_mcp_server.security import (
    InputValidationError,
    PipelineError,
    sanitize_error_message,
)
from maya_mcp_server.types import (
    COMMUNICATION_PORT_MAX,
    COMMUNICATION_PORT_MIN,
    CommandResponse,
    OutputBuffer,
    PortType,
    ResultType,
    SessionInfo,
)


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Buffer size limit to prevent unbounded memory growth (10MB)
MAX_BUFFER_SIZE = 10_485_760

# Connect retry schedule (D-013): exponential backoff 0.5s / 1s / 2s
CONNECT_RETRY_DELAYS = (0.5, 1.0, 2.0)

# Post-connect liveness gate: a Qt server in headless Maya can accept TCP
# while readyRead never fires; bound the probe so bootstrap fails fast.
QT_PROBE_TIMEOUT = 5.0  # seconds


class MayaUnavailableError(PipelineError):
    """Maya channel unreachable (host-side failure -> isError + code)."""

    code = "maya_unavailable"


# Backwards-compatible name: D-019 pins the code, existing code the class name.
MayaConnectionError = MayaUnavailableError


class MayaTimeoutError(MayaUnavailableError):
    """Timed out waiting on the Maya channel."""

    code = "maya_timeout"


class MayaExecutionError(PipelineError):
    """Error executing code in Maya (host-side failure -> isError + code)."""

    code = "maya_execution"


def _domain_error_text(error: Any) -> str:
    """Render a wire error as "code: message" (D-019).

    Wire errors are dual-schema: known domain errors carry {"code": ...}
    and exceptions carry {"type", "traceback"}. The code must survive into
    the exception text so both channels match native write_module's
    "code: message" format.
    """
    if isinstance(error, dict):
        code = error.get("code")
        msg = error.get("message", "Unknown error")
        if code:
            return f"{code}: {msg}"
        return str(msg)
    return str(error)


def raise_for_error(response: CommandResponse) -> None:
    """Raise MayaExecutionError if the response carries a Maya-side error.

    Single choke point so both server.execute_code and the scene-tool layer
    surface errors identically (message sanitized, code/type + traceback kept).
    """
    err = getattr(response, "error", None)
    if not err:
        return
    if isinstance(err, dict) and err.get("code"):
        detail = f"{err['code']}: {err.get('message', 'Unknown error')}"
        etb = err.get("traceback", "")
    else:
        etype = err.get("type", "Error") if isinstance(err, dict) else "Error"
        emsg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        etb = err.get("traceback", "") if isinstance(err, dict) else ""
        detail = f"Maya execution error ({etype}): {emsg}"
    if etb:
        detail += "\n" + etb
    raise MayaExecutionError(sanitize_error_message(detail))


@dataclass
class BaseMayaClient(ABC):
    """Abstract base class for Maya clients."""

    GET_SESSION_INFO: ClassVar[str]
    EXECUTE_TEMPLATE: ClassVar[str]
    CREATE_MODULE_TEMPLATE: ClassVar[str]
    INSTALL_STREAM_CAPTURE: ClassVar[str]
    UNINSTALL_STREAM_CAPTURE: ClassVar[str]
    GET_BUFFERED_OUTPUT: ClassVar[str]

    # True when the transport carries length-prefixed frames and can move
    # multi-MB payloads safely (D-013). False = native commandPort, whose
    # line protocol is bootstrap/headless-only and never promised large loads.
    framed_channel: ClassVar[bool] = False

    host: str = "127.0.0.1"
    port: int = 7001
    timeout: float = 30.0
    buffer_size: int = 65536

    def __post_init__(self) -> None:
        """
        Initialize a Maya client.

        Args:
            host: Maya host address
            port: Maya command port number
            timeout: Default timeout for operations in seconds
            buffer_size: Socket buffer size
        """
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        # Output buffers for stdout/stderr capture
        self._stdout_buffer: str = ""
        self._stderr_buffer: str = ""

    @property
    def key(self) -> str:
        """Unique key for the session."""
        return f"{self.host}:{self.port}"

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self) -> None:
        """
        Establish connection to Maya command port.

        Raises:
            MayaConnectionError: If connection fails
        """
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            logger.info(f"Connected to Maya at {self.host}:{self.port}")
        except asyncio.TimeoutError as e:
            raise MayaTimeoutError(f"Timeout connecting to Maya at {self.host}:{self.port}") from e
        except OSError as e:
            raise MayaConnectionError(
                f"Failed to connect to Maya at {self.host}:{self.port}: {e}"
            ) from e

    async def disconnect(self) -> None:
        """Close connection to Maya."""
        # FIXME: shut down the maya command port running in Maya
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Async context manager exit."""
        await self.disconnect()

    def append_output(self, stdout: str = "", stderr: str = "") -> None:
        """
        Append output to the client's buffers.

        This is called after execute_code to accumulate output.

        Args:
            stdout: Stdout content to append
            stderr: Stderr content to append
        """
        if stdout:
            self._stdout_buffer += stdout
            if len(self._stdout_buffer) > MAX_BUFFER_SIZE:
                excess = len(self._stdout_buffer) - MAX_BUFFER_SIZE
                self._stdout_buffer = self._stdout_buffer[excess:]
                logger.warning(
                    f"Stdout buffer exceeded {MAX_BUFFER_SIZE} bytes, "
                    f"trimmed {excess} bytes from the beginning"
                )
        if stderr:
            self._stderr_buffer += stderr
            if len(self._stderr_buffer) > MAX_BUFFER_SIZE:
                excess = len(self._stderr_buffer) - MAX_BUFFER_SIZE
                self._stderr_buffer = self._stderr_buffer[excess:]
                logger.warning(
                    f"Stderr buffer exceeded {MAX_BUFFER_SIZE} bytes, "
                    f"trimmed {excess} bytes from the beginning"
                )

    def get_accumulated_output(self, clear: bool = True) -> OutputBuffer:
        """
        Get accumulated stdout/stderr output.

        Args:
            clear: If True, clear the buffers after reading

        Returns:
            OutputBuffer with stdout and stderr fields
        """
        output = OutputBuffer(stdout=self._stdout_buffer, stderr=self._stderr_buffer)

        if clear:
            self._stdout_buffer = ""
            self._stderr_buffer = ""

        return output

    def clear_output(self) -> None:
        """Clear the accumulated output buffers."""
        self._stdout_buffer = ""
        self._stderr_buffer = ""

    async def install_stream_capture(self) -> None:
        """
        Install stream capture for stdout/stderr in Maya.

        This redirects stdout/stderr through custom writers that buffer
        output for retrieval via get_buffered_output().
        """
        await self._send_receive(self.INSTALL_STREAM_CAPTURE)
        logger.debug(f"Stream capture installed for {self.host}:{self.port}")

    async def uninstall_stream_capture(self) -> None:
        """
        Remove stream capture and restore original stdout/stderr in Maya.
        """
        await self._send_receive(self.UNINSTALL_STREAM_CAPTURE)
        logger.debug(f"Stream capture uninstalled for {self.host}:{self.port}")

    async def get_buffered_output(self) -> OutputBuffer:
        """
        Get buffered stdout/stderr content and clear the buffers.

        Returns:
            OutputBuffer with stdout and stderr fields containing captured output.
        """
        response = await self._send_receive(self.GET_BUFFERED_OUTPUT)
        result = response.result if response.result is not None else {}
        return OutputBuffer(
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
        )

    async def session_info(self) -> SessionInfo:
        """
        Get information about the connected Maya session.

        Returns:
            SessionInfo with pid, user, maya version, current scene, etc.
        """
        response = await self._send_receive(self.GET_SESSION_INFO)
        # get_session_info() returns a JSON string, parse it
        raw = response.result
        if isinstance(raw, str):
            try:
                info = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                info = {}
        elif isinstance(raw, dict):
            info = raw
        else:
            info = {}

        return SessionInfo(
            session_key=self.key,
            host=self.host,
            port=self.port,
            pid=info.get("pid", 0),
            user=info.get("user", ""),
            maya_version=info.get("maya_version", ""),
            scene_name=info.get("scene_name", ""),
            scene_path=info.get("scene_path", ""),
        )

    async def execute_code(
        self,
        code: str,
        result_type: ResultType | str = ResultType.NONE,
    ) -> CommandResponse:
        """
        Execute Python code in Maya and return the result.

        Args:
            code: Python code to execute
            result_type: How to handle the result (enum or plain string —
                both are normalized at this boundary)
                - NONE: Execute statements, don't capture result
                - JSON: Evaluate expression, JSON encode result
                - RAW: Evaluate expression, return string representation

        Returns:
            CommandResponse with result and error info.
            Note: stdout/stderr are delivered via MCP Resources, not returned here.
        """
        # Normalize at the boundary (D-046): enum members pass through,
        # plain strings like "JSON" are coerced. 0.1.1 crashed here on
        # result_type.value when str-typed callers (scene_tools,
        # visual_tools) reached this shared method.
        try:
            result_type = ResultType(result_type)
        except ValueError:
            raise InputValidationError(
                f"Invalid result_type {result_type!r}: must be NONE, JSON, or RAW"
            ) from None

        # Qt server JSON protocol over the framed channel. There is no
        # retry: execution errors are returned in the response (never
        # raised here) and surface to callers via the two-layer contract.
        response = await self._send_receive(
            self.EXECUTE_TEMPLATE,
            {"code": code, "result_type": result_type.value},
            raise_on_error=False,
        )

        # Decode JSON result if needed (same as commandPort path)
        if result_type == ResultType.JSON and response.result is not None:
            try:
                if isinstance(response.result, dict):
                    decoded_result = response.result
                elif isinstance(response.result, str):
                    decoded_result = json.loads(response.result)
                else:
                    decoded_result = response.result
                return CommandResponse(result=decoded_result, error=response.error)
            except json.JSONDecodeError:
                pass  # Keep as string if not valid JSON

        return response

    # Abstract methods that must be implemented by subclasses

    @abstractmethod
    async def _send_receive(
        self, method: str, params: dict[str, Any] | None = None, raise_on_error: bool = True
    ) -> CommandResponse:
        """
        Send command to Maya and receive response.

        Args:
            method: Command string or method name (may contain {param} placeholders)
            params: Parameters to format into the command or pass to the method
            raise_on_error: If True, raise exception on error.
                If False, return full response with error.

        Returns:
            CommandResponse with result and error attributes

        Raises:
            MayaConnectionError: If not connected
            MayaTimeoutError: If the response deadline is exceeded
            MayaExecutionError: If communication fails or raise_on_error is True and command errors
        """
        ...

    @abstractmethod
    async def write_module(self, name: str, code: str, overwrite: bool = False) -> str:
        """Create a virtual Python module in the Maya session."""
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """Check if the Maya session is still responsive."""
        ...


class MayaClient(BaseMayaClient):
    """Async client for communicating with a Maya command port."""

    # Access the helper via __import__ (works in single expressions)
    _MCP_HELPER = "__import__('maya_mcp')"

    # Command templates that use __import__ to access the persistent _mcp module
    GET_SESSION_INFO = f"{_MCP_HELPER}.get_session_info()"
    EXECUTE_TEMPLATE = f"{_MCP_HELPER}.execute({{code!r}}, {{result_type!r}})"
    CREATE_MODULE_TEMPLATE = f"{_MCP_HELPER}.create_module({{name!r}}, {{code!r}}, {{overwrite!r}})"
    INSTALL_STREAM_CAPTURE = f"{_MCP_HELPER}.install_stream_capture()"
    UNINSTALL_STREAM_CAPTURE = f"{_MCP_HELPER}.uninstall_stream_capture()"
    GET_BUFFERED_OUTPUT = f"{_MCP_HELPER}.get_buffered_output()"
    START_COMMAND_PORT = f"{_MCP_HELPER}.start_command_port({{port!r}})"

    # Qt server command templates
    START_QT_SERVER = f"{_MCP_HELPER}.start_qt_server({{port!r}})"
    STOP_QT_SERVER = f"{_MCP_HELPER}.stop_qt_server()"
    GET_QT_SERVER_PORT = f"{_MCP_HELPER}.get_qt_server_port()"

    # Check if bootstrap has been done
    CHECK_BOOTSTRAP = "'maya_mcp' in __import__('sys').modules"

    def __post_init__(self) -> None:
        super().__post_init__()
        self._port_type: PortType = PortType.UNKNOWN

    async def _send_receive(
        self, method: str, params: dict[str, Any] | None = None, raise_on_error: bool = True
    ) -> CommandResponse:
        """
        Send command to Maya commandPort and receive response.

        Args:
            method: Command template string (may contain {param} placeholders)
            params: Parameters to format into the template
            raise_on_error: If True, raise exception on error.
                If False, return full response with error.

        Returns:
            CommandResponse with result and error attributes

        Raises:
            MayaConnectionError: If not connected
            MayaUnavailableError: If the connection is lost mid-request
            MayaExecutionError: If communication fails or raise_on_error is True and command errors
        """
        if not self._writer or not self._reader:
            raise MayaConnectionError("Not connected to Maya")

        # Format the command template with params
        if params:
            command = method.format(**params)
        else:
            command = method

        async with self._lock:
            try:
                # Send command - commandPort executes on newline, so the
                # terminator is unconditional (D-041): without it the
                # command parks in the receive buffer until the next send
                # flushes it through (off-by-one).
                self._writer.write(command.encode("utf-8") + b"\n")
                await self._writer.drain()

                # Read response until null terminator
                response_bytes = b""
                while True:
                    chunk = await asyncio.wait_for(
                        self._reader.read(self.buffer_size),
                        timeout=self.timeout,
                    )
                    if not chunk:
                        raise MayaUnavailableError(
                            f"Connection closed on {self.host}:{self.port} "
                            "before response terminator"
                        )
                    response_bytes += chunk
                    # Maya terminates responses with \n\x00
                    if response_bytes.endswith(b"\x00"):
                        break

                # Decode and strip terminator
                response_str = response_bytes.decode("utf-8").rstrip("\x00").rstrip("\n")

                # Parse JSON response if the command returns JSON
                # Most helper functions return JSON with {"result": ..., "error": ...}
                try:
                    response = json.loads(response_str)
                    # Check if it's a structured response
                    if isinstance(response, dict) and ("result" in response or "error" in response):
                        if raise_on_error and response.get("error"):
                            error = response["error"]
                            if isinstance(error, dict):
                                raise MayaExecutionError(f"{error.get('message', 'Unknown error')}")
                            else:
                                raise MayaExecutionError(str(error))
                        return CommandResponse(
                            result=response.get("result"), error=response.get("error")
                        )
                    else:
                        # It's JSON but not our structured format, treat as raw result
                        return CommandResponse(result=response, error=None)
                except json.JSONDecodeError:
                    # Not JSON, treat as raw string result
                    return CommandResponse(result=response_str, error=None)

            except asyncio.TimeoutError as e:
                raise MayaTimeoutError("Timeout waiting for Maya response") from e
            except (ConnectionError, asyncio.IncompleteReadError) as e:
                raise MayaUnavailableError(
                    f"Connection lost on {self.host}:{self.port}: {e}"
                ) from e
            except (MayaExecutionError, MayaUnavailableError):
                raise
            except Exception as e:
                raise MayaExecutionError(f"Error communicating with Maya: {e}") from e

    async def _detect_port_type(self) -> PortType:
        """
        Detect whether the command port speaks MEL or Python.

        Returns:
            PortType indicating the port's language
        """
        if self._port_type != PortType.UNKNOWN:
            return self._port_type

        try:
            # Try a simple Python expression
            response = await self._send_receive("1+1")

            # If we get "2" back, it's Python
            result_str = str(response.result if response.result is not None else "").strip()
            if result_str == "2":
                self._port_type = PortType.PYTHON
            else:
                # Likely MEL - would return an error or different format
                self._port_type = PortType.MEL

        except Exception:
            self._port_type = PortType.UNKNOWN

        logger.info(f"Detected port type: {self._port_type.value}")
        return self._port_type

    async def _bootstrap(self, overwrite: bool = False) -> None:
        """
        Bootstrap the Maya session with helper functions.

        This creates the _mcp module in Maya's sys.modules,
        providing utilities for code execution with capture.
        """
        port_type = await self._detect_port_type()

        if port_type != PortType.PYTHON:
            # TODO: support bootstrapping from a MEL command port
            raise MayaConnectionError(
                f"Cannot bootstrap non-Python port (detected: {port_type.value})"
            )

        if not overwrite:
            # Check if already bootstrapped (e.g., from previous connection)
            check_result = await self._send_receive(self.CHECK_BOOTSTRAP)
            if (
                str(check_result.result if check_result.result is not None else "").strip()
                == "True"
            ):
                logger.info("Maya session already bootstrapped, updating module...")
                # Re-execute bootstrap code to get latest create_module function
                bootstrap_code = get_bootstrap_code()
                bootstrap_cmd = f"exec({bootstrap_code!r}, globals())"
                await self._send_receive(bootstrap_cmd)
                # Now use the fresh create_module to update the helper module
                helper_code = get_helper_module_code()
                cmd = "create_module({name!r}, {code!r}, {overwrite!r})"
                await self._send_receive(
                    cmd, {"name": "maya_mcp", "code": helper_code, "overwrite": True}
                )
                logger.info("Maya mcp module updated")
                return

        # Execute bootstrap code using exec() with globals() to persist definitions
        # Maya command port runs each command in isolated scope, so we must use
        # exec(..., globals()) to make the code affect the global namespace
        bootstrap_code = get_bootstrap_code()
        bootstrap_cmd = f"exec({bootstrap_code!r}, globals())"
        await self._send_receive(bootstrap_cmd)
        # We've now bootstrapped the create_module function, which we use to create
        # the helper module:
        helper_code = get_helper_module_code()
        # Remove the module name prefix since create_module doesn't exist yet
        cmd = "create_module({name!r}, {code!r}, {overwrite!r})"
        await self._send_receive(
            cmd, {"name": "maya_mcp", "code": helper_code, "overwrite": overwrite}
        )
        logger.info("Maya session bootstrapped")

    async def bootstrap(self, client_type: Literal["native", "qt"] = "native") -> BaseMayaClient:
        """
        Boostrap remote session and return a new client
        """
        await self._bootstrap()

        # Create a dedicated communication port for this client
        new_port = random.randint(COMMUNICATION_PORT_MIN, COMMUNICATION_PORT_MAX)
        new_client: BaseMayaClient

        if client_type == "native":
            logger.info(f"Creating dedicated commandPort on port {new_port}")
            result = await self._send_receive(self.START_COMMAND_PORT, {"port": new_port})
            logger.info(f"Dedicated commandPort created: {result}")

            # Wait a moment for the port to start listening
            await asyncio.sleep(0.5)

            logger.info(f"Connecting to dedicated port {new_port}...")
            new_client = MayaClient(
                host=self.host, port=new_port, timeout=self.timeout, buffer_size=self.buffer_size
            )
        elif client_type == "qt":
            # Unlike the commandPort, the qt server can handle multiple clients on the same port.
            # Therefore, the port returned by _send_receive might be different than requested.
            logger.info(f"Starting Qt server on port {new_port}")
            # raise_on_error=False: start_qt_server reports failures as a JSON
            # {"error": ...} payload on the wire, not an exception (F-1 fix).
            result = await self._send_receive(
                self.START_QT_SERVER, {"port": new_port}, raise_on_error=False
            )
            qt_error: Any = result.error
            qt_port = None
            # The native channel may wrap the JSON payload in result (dict or str)
            payload = result.result
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    payload = None
            if isinstance(payload, dict):
                qt_error = qt_error or payload.get("error")
                qt_port = payload.get("port")

            qt_client: MayaQtClient | None = None
            if not qt_error:
                if qt_port:
                    new_port = qt_port
                logger.info(f"Qt server started on port {new_port}")

                # Wait a moment for the port to start listening
                await asyncio.sleep(0.5)

                logger.info(f"Connecting to dedicated port {new_port}...")
                qt_client = MayaQtClient(
                    host=self.host,
                    port=new_port,
                    timeout=self.timeout,
                    buffer_size=self.buffer_size,
                )
                try:
                    await qt_client.connect()
                    # Liveness gate (D-013): in headless Maya a Qt listener can
                    # accept TCP while readyRead never fires - a zombie channel.
                    # Probe the framed protocol before registering the session.
                    alive = await asyncio.wait_for(qt_client.ping(), timeout=QT_PROBE_TIMEOUT)
                    if not alive:
                        raise MayaUnavailableError(
                            "Qt server accepted the connection but does not respond"
                        )
                except Exception as e:
                    logger.warning(f"Qt channel unusable ({e}); falling back")
                    qt_error = e
                    try:
                        await qt_client.disconnect()
                    except Exception:
                        pass
                    qt_client = None

            if qt_client is not None:
                new_client = qt_client
            else:
                # Headless Maya (mayapy) has no Qt event loop. Per D-013 the
                # native commandPort is the minimal fallback working channel
                # there - it never promises large payloads.
                logger.warning(
                    f"Qt server unavailable ({qt_error}); "
                    "falling back to a dedicated native commandPort"
                )
                result = await self._send_receive(self.START_COMMAND_PORT, {"port": new_port})
                logger.info(f"Dedicated commandPort created: {result}")
                await asyncio.sleep(0.5)
                new_client = MayaClient(
                    host=self.host,
                    port=new_port,
                    timeout=self.timeout,
                    buffer_size=self.buffer_size,
                )
        else:
            raise InputValidationError(f"Unknown client_type {client_type!r}")
        # Connect to the new dedicated port (the Qt branch already probed it)
        if not new_client.is_connected:
            await new_client.connect()
        logger.info(f"Connected to dedicated port {new_port}")
        return new_client

    async def write_module(
        self,
        name: str,
        code: str,
        overwrite: bool = False,
    ) -> str:
        """
        Create a virtual Python module in the Maya session.

        Args:
            name: Module name (can be dotted path like 'mypackage.mymodule')
            code: Python source code for the module
            overwrite: If True, replace existing module; else raise error

        Returns:
            Success message

        Raises:
            MayaExecutionError: If module creation fails
        """
        response = await self._send_receive(
            self.CREATE_MODULE_TEMPLATE,
            {"name": name, "code": code, "overwrite": overwrite},
        )
        raise_for_error(response)

        # The native commandPort wraps create_module()'s JSON in the raw result
        # payload: errors arrive inside result, not in response.error. Surface
        # them instead of reporting success on a dead response.
        result = response.result
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(result, dict):
            inner_error = result.get("error")
            if inner_error:
                if isinstance(inner_error, dict):
                    raise MayaExecutionError(
                        f"{inner_error.get('code', 'module_error')}: "
                        f"{inner_error.get('message', 'module creation failed')}"
                    )
                raise MayaExecutionError(str(inner_error))
            message = result.get("message")
            if message:
                return str(message)
        return f"Module '{name}' created"

    async def ping(self) -> bool:
        """
        Check if the Maya connection is alive.

        Returns:
            True if Maya responds, False otherwise
        """
        try:
            response = await self._send_receive("1+1")
            return str(response.result if response.result is not None else "").strip() == "2"
        except Exception:
            return False


class MayaQtClient(BaseMayaClient):
    """Async client for the custom Maya Qt command server (D-013/ADR-0010).

    Primary working channel: length-prefixed frames (16 MiB cap) over a
    localhost-only QTcpServer; per-connection FIFO queue Maya-side;
    requests here are serialized by self._lock and correlated by id.
    """

    framed_channel: ClassVar[bool] = True

    GET_SESSION_INFO = "get_session_info"
    EXECUTE_TEMPLATE = "execute"
    CREATE_MODULE_TEMPLATE = "create_module"
    INSTALL_STREAM_CAPTURE = "install_stream_capture"
    UNINSTALL_STREAM_CAPTURE = "uninstall_stream_capture"
    GET_BUFFERED_OUTPUT = "get_buffered_output"

    def __post_init__(self) -> None:
        super().__post_init__()
        self._request_counter: int = 0

    async def connect(self) -> None:
        """Connect to the Qt server, retrying on the 0.5/1/2s backoff schedule."""
        last_error: Exception | None = None
        attempts = len(CONNECT_RETRY_DELAYS) + 1

        for attempt in range(attempts):
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout,
                )
                logger.info(f"Connected to Qt server at {self.host}:{self.port}")
                return
            except (OSError, asyncio.TimeoutError) as e:
                last_error = e
                if attempt < attempts - 1:
                    delay = CONNECT_RETRY_DELAYS[attempt]
                    logger.warning(
                        f"Failed to connect to Qt server "
                        f"(attempt {attempt + 1}/{attempts}): {e}; retry in {delay}s"
                    )
                    await asyncio.sleep(delay)

        if isinstance(last_error, asyncio.TimeoutError):
            raise MayaTimeoutError(
                f"Timeout connecting to Qt server at {self.host}:{self.port} "
                f"after {attempts} attempts"
            ) from last_error
        raise MayaUnavailableError(
            f"Failed to connect to Qt server at {self.host}:{self.port} "
            f"after {attempts} attempts: {last_error}"
        ) from last_error

    async def write_module(
        self,
        name: str,
        code: str,
        overwrite: bool = False,
    ) -> str:
        """
        Create a virtual Python module in the Maya session.

        Args:
            name: Module name (can be dotted path like 'mypackage.mymodule')
            code: Python source code for the module
            overwrite: If True, replace existing module; else raise error

        Returns:
            Success message

        Raises:
            MayaExecutionError: If module creation fails
        """
        response = await self._send_receive(
            self.CREATE_MODULE_TEMPLATE, {"name": name, "code": code, "overwrite": overwrite}
        )
        result = response.result if response.result is not None else {}
        if isinstance(result, dict):
            return str(result.get("message", f"Module '{name}' created"))
        return f"Module '{name}' created"

    async def _send_receive(
        self, method: str, params: dict[str, Any] | None = None, raise_on_error: bool = True
    ) -> CommandResponse:
        """Send JSON request to Qt server and receive response.

        Args:
            method: Method name to call
            params: Parameters for the method
            raise_on_error: If True, raise exception on error.
                If False, return full response with error.

        Returns:
            CommandResponse with result and error attributes
        """
        if not self._writer or not self._reader:
            raise MayaUnavailableError("Not connected to Qt server")

        async with self._lock:
            # Generate request ID
            self._request_counter += 1
            request_id = f"req-{self._request_counter}"

            # Build + frame the request
            request = {"id": request_id, "method": method, "params": params or {}}
            payload = json.dumps(request).encode("utf-8")
            if len(payload) > MAX_FRAME_SIZE:
                raise InputValidationError(
                    f"request {len(payload)}B exceeds frame cap {MAX_FRAME_SIZE}B"
                )

            try:
                self._writer.write(encode_frame(payload))
                await self._writer.drain()

                # Read one length-prefixed response frame
                header = await asyncio.wait_for(
                    self._reader.readexactly(FRAME_HEADER_SIZE), timeout=self.timeout
                )
                frame_len = int.from_bytes(header, "big")
                if frame_len > MAX_FRAME_SIZE:
                    raise MayaExecutionError(
                        f"response frame {frame_len}B exceeds cap {MAX_FRAME_SIZE}B"
                    )
                body = await asyncio.wait_for(
                    self._reader.readexactly(frame_len), timeout=self.timeout
                )

                response = json.loads(body.decode("utf-8"))

                # Validate response ID
                if response.get("id") != request_id:
                    raise MayaExecutionError(
                        f"Response ID mismatch: expected {request_id}, got {response.get('id')}"
                    )

                # Check for error - keep the wire code in the message
                # ("code: message", same as the native write_module path, D-019)
                if raise_on_error and response.get("error"):
                    raise MayaExecutionError(_domain_error_text(response["error"]))

                # Return CommandResponse
                return CommandResponse(result=response.get("result"), error=response.get("error"))

            except asyncio.TimeoutError as e:
                raise MayaTimeoutError("Timeout waiting for Qt server response") from e
            except (MayaUnavailableError, MayaExecutionError):
                raise
            except (ConnectionError, asyncio.IncompleteReadError) as e:
                raise MayaUnavailableError("Connection closed by Qt server") from e
            except json.JSONDecodeError as e:
                raise MayaExecutionError(f"Invalid JSON response from Qt server: {e}") from e
            except Exception as e:
                raise MayaExecutionError(f"Error communicating with Qt server: {e}") from e

    async def ping(self) -> bool:
        """
        Check if the Maya connection is alive.

        Returns:
            True if Maya responds, False otherwise
        """
        try:
            response = await self._send_receive("ping")
            return bool(response.result == "pong")
        except Exception:
            return False

    async def health(self) -> dict[str, Any]:
        """Deeper health probe: server status, port, client count, uptime.

        Returns {"status": ...} even on a degraded channel.
        """
        try:
            response = await self._send_receive("health")
            if isinstance(response.result, dict):
                return response.result
        except Exception:
            pass
        return {"status": "unavailable"}
