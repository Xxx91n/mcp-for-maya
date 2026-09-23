"""T-19a tests: polyhaven host-side client (D-074/D-075).

Network is faked at the urllib.request.urlopen seam - the tests still
exercise the real whitelist check, User-Agent header, size caps, md5
verification, cache manifest, and domain-error mapping.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from maya_mcp_server import polyhaven
from maya_mcp_server.polyhaven import AssetError


class FakeResp:
    """Minimal urlopen response: read(n) + headers.get() + geturl()."""

    def __init__(self, data: bytes, headers: dict | None = None, url: str = ""):
        self._data = data
        self.headers = headers or {}
        self._url = url

    def read(self, n: int = -1) -> bytes:
        return self._data if n is None or n < 0 else self._data[:n]

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(routes: dict, record: list | None = None):
    """routes: url -> bytes | (bytes, headers) | Exception instance."""

    def _open(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if record is not None:
            record.append(
                {
                    "url": url,
                    "ua": req.get_header("User-agent") if hasattr(req, "get_header") else None,
                }
            )
        v = routes.get(url)
        if v is None:
            raise urllib.error.URLError("no route: " + url)
        if isinstance(v, Exception):
            raise v
        if isinstance(v, tuple):
            data, headers = v
        else:
            data, headers = v, {}
        return FakeResp(data, headers, url=url)

    return _open


@pytest.fixture
def files_payload():
    """A Camera_01-shaped /files payload (2 parts, real PH key style)."""
    return {
        "fbx": {
            "1k": {
                "fbx": {
                    "url": "https://dl.polyhaven.org/x/Camera_01_1k.fbx",
                    "size": 5,
                    "md5": hashlib.md5(b"FBX!!").hexdigest(),
                }
            }
        },
        "body_diff": {
            "1k": {
                "jpg": {
                    "url": "https://dl.polyhaven.org/x/body_diff_1k.jpg",
                    "size": 4,
                    "md5": hashlib.md5(b"DIFF").hexdigest(),
                }
            }
        },
        "body_nor_gl": {
            "1k": {
                "jpg": {
                    "url": "https://dl.polyhaven.org/x/body_nor_gl_1k.jpg",
                    "size": 3,
                    "md5": hashlib.md5(b"NGL").hexdigest(),
                }
            }
        },
        "body_roughness": {
            "1k": {
                "jpg": {
                    "url": "https://dl.polyhaven.org/x/body_roughness_1k.jpg",
                    "size": 5,
                    "md5": hashlib.md5(b"ROUGH").hexdigest(),
                }
            }
        },
        "strap_metallic": {
            "1k": {
                "jpg": {
                    "url": "https://dl.polyhaven.org/x/strap_metallic_1k.jpg",
                    "size": 4,
                    "md5": hashlib.md5(b"METL").hexdigest(),
                }
            }
        },
    }


def files_routes(files_payload):
    routes = {"https://api.polyhaven.com/files/Camera_01": json.dumps(files_payload).encode()}
    contents = {
        "https://dl.polyhaven.org/x/Camera_01_1k.fbx": b"FBX!!",
        "https://dl.polyhaven.org/x/body_diff_1k.jpg": b"DIFF",
        "https://dl.polyhaven.org/x/body_nor_gl_1k.jpg": b"NGL",
        "https://dl.polyhaven.org/x/body_roughness_1k.jpg": b"ROUGH",
        "https://dl.polyhaven.org/x/strap_metallic_1k.jpg": b"METL",
    }
    routes.update(contents)
    return routes


# ------------------------------------------------------------------
# search
# ------------------------------------------------------------------


class TestSearch:
    def test_search_filters_and_limits(self, monkeypatch):
        assets = {
            f"asset_{i:02d}": {
                "name": f"Asset {i}",
                "categories": ["props"],
                "tags": ["vintage"] if i % 2 else ["modern"],
            }
            for i in range(30)
        }
        routes = {"https://api.polyhaven.com/assets?t=models": json.dumps(assets).encode()}
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes))
        out = polyhaven.search_assets(query="vintage", limit=20)
        assert len(out["results"]) == 15  # only vintage assets match
        assert out["total_count"] == 15
        assert out["limit"] == 20

    def test_search_caps_at_20_preserves_total(self, monkeypatch):
        assets = {
            f"asset_{i:02d}": {"name": f"Asset {i}", "categories": [], "tags": []}
            for i in range(50)
        }
        routes = {"https://api.polyhaven.com/assets?t=models": json.dumps(assets).encode()}
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes))
        out = polyhaven.search_assets(query="asset", limit=99)
        assert len(out["results"]) == 20  # hard cap
        assert out["total_count"] == 50

    def test_search_sends_user_agent(self, monkeypatch):
        record = []
        routes = {"https://api.polyhaven.com/assets?t=models": b"{}"}
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes, record))
        polyhaven.search_assets()
        assert record and "mcp-for-maya" in (record[0]["ua"] or "")


# ------------------------------------------------------------------
# guardrails
# ------------------------------------------------------------------


class TestGuards:
    def test_url_whitelist_rejects_foreign_host(self):
        with pytest.raises(AssetError) as ei:
            polyhaven._fetch("https://evil.example.com/x.fbx", timeout=1, max_bytes=10)
        assert ei.value.code == "url_not_allowed"

    def test_http_scheme_rejected(self):
        with pytest.raises(AssetError) as ei:
            polyhaven._fetch("http://dl.polyhaven.org/x.fbx", timeout=1, max_bytes=10)
        assert ei.value.code == "url_not_allowed"

    def test_redirect_to_foreign_host_rejected(self):
        # R1: a whitelisted entry URL may not 30x-bounce to an arbitrary
        # host - every redirect hop re-runs the whitelist check.
        h = polyhaven._WhitelistRedirectHandler()
        req = urllib.request.Request("https://api.polyhaven.com/files/x")
        with pytest.raises(AssetError) as ei:
            h.redirect_request(req, None, 302, "Found", {}, "http://evil.example.com/y")
        assert ei.value.code == "url_not_allowed"

    def test_redirect_within_whitelist_allowed(self):
        h = polyhaven._WhitelistRedirectHandler()
        req = urllib.request.Request("https://api.polyhaven.com/files/x")
        nxt = h.redirect_request(req, None, 302, "Found", {}, "https://dl.polyhaven.org/y.fbx")
        assert nxt is not None and "dl.polyhaven.org" in nxt.full_url

    def test_redirect_cap(self):
        assert polyhaven._WhitelistRedirectHandler.max_redirections == 3

    def test_network_unavailable_domain_error(self, monkeypatch):
        monkeypatch.setattr(
            polyhaven,
            "_urlopen",
            lambda req, timeout=None: (_ for _ in ()).throw(
                urllib.error.URLError("connection refused")
            ),
        )
        with pytest.raises(AssetError) as ei:
            polyhaven.search_assets()
        assert ei.value.code == "network_unavailable"
        assert ei.value.suggestion

    def test_404_maps_to_asset_not_found(self, monkeypatch):
        err = urllib.error.HTTPError("https://api.polyhaven.com/files/nope", 404, "nf", {}, None)
        monkeypatch.setattr(
            polyhaven,
            "_urlopen",
            lambda req, timeout=None: (_ for _ in ()).throw(err),
        )
        with pytest.raises(AssetError) as ei:
            polyhaven.get_asset_files("nope")
        assert ei.value.code == "asset_not_found"

    def test_size_cap_content_length(self, monkeypatch):
        routes = {
            "https://dl.polyhaven.org/big.fbx": (
                b"x" * 100,
                {"Content-Length": str(10 * 1024 * 1024)},
            )
        }
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes))
        with pytest.raises(AssetError) as ei:
            polyhaven._fetch(
                "https://dl.polyhaven.org/big.fbx",
                timeout=1,
                max_bytes=1024,
            )
        assert ei.value.code == "download_too_large"

    def test_size_cap_mid_read(self, monkeypatch):
        routes = {"https://dl.polyhaven.org/big.fbx": b"x" * 2048}
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes))
        with pytest.raises(AssetError) as ei:
            polyhaven._fetch(
                "https://dl.polyhaven.org/big.fbx",
                timeout=1,
                max_bytes=1024,
            )
        assert ei.value.code == "download_too_large"

    def test_invalid_asset_id_rejected(self):
        for bad in ("../escape", "a b", "", "x" * 200, None):
            with pytest.raises(AssetError) as ei:
                polyhaven.validate_asset_id(bad)
            assert ei.value.code == "invalid_asset_id"


# ------------------------------------------------------------------
# texture key splitting + file selection
# ------------------------------------------------------------------


class TestSelectFiles:
    def test_split_texture_key(self):
        assert polyhaven.split_texture_key("body_nor_gl") == ("body", "nor_gl")
        assert polyhaven.split_texture_key("strap_metallic") == (
            "strap",
            "metallic",
        )
        assert polyhaven.split_texture_key("body_roughness") == (
            "body",
            "roughness",
        )
        assert polyhaven.split_texture_key("fbx") is None
        assert polyhaven.split_texture_key("random_key") is None

    def test_select_files_groups_parts(self, files_payload):
        sel = polyhaven.select_files(files_payload, "1k")
        assert sel["fbx"]["url"].endswith("Camera_01_1k.fbx")
        assert set(sel["parts"]["body"]) == {"diff", "nor_gl", "roughness"}
        assert set(sel["parts"]["strap"]) == {"metallic"}

    def test_select_files_no_fbx(self):
        with pytest.raises(AssetError) as ei:
            polyhaven.select_files({"body_diff": {}}, "1k")
        assert ei.value.code == "not_a_model"


# ------------------------------------------------------------------
# download + cache
# ------------------------------------------------------------------


class TestDownload:
    def test_download_descriptor_shape(self, monkeypatch, tmp_path, files_payload):
        monkeypatch.setattr(
            polyhaven,
            "_urlopen",
            fake_urlopen(files_routes(files_payload)),
        )
        d = polyhaven.download_asset("Camera_01", cache_root=str(tmp_path))
        assert d["asset_id"] == "Camera_01"
        assert d["source"] == "download"
        assert Path(d["fbx_path"]).is_file()
        assert set(d["texture_parts"]["body"]) == {
            "diff",
            "nor_gl",
            "roughness",
        }
        assert d["license"] == "CC0-1.0"
        # every file hashed (sha256 audit + md5 verify)
        assert len(d["files_hash"]) == 5
        fbx_entry = d["files_hash"]["Camera_01_1k.fbx"]
        assert fbx_entry["md5"] == hashlib.md5(b"FBX!!").hexdigest()
        assert fbx_entry["sha256"] == hashlib.sha256(b"FBX!!").hexdigest()
        # manifest written into the cache dir
        manifest = json.loads((Path(d["cache_dir"]) / "manifest.json").read_text())
        assert manifest["asset_id"] == "Camera_01"
        assert len(manifest["files"]) == 5

    def test_second_call_is_cache_hit(self, monkeypatch, tmp_path, files_payload):
        record = []
        routes = files_routes(files_payload)
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes, record))
        polyhaven.download_asset("Camera_01", cache_root=str(tmp_path))
        file_urls_first = [r["url"] for r in record if "/x/" in r["url"]]
        assert len(file_urls_first) == 5

        record.clear()
        d = polyhaven.download_asset("Camera_01", cache_root=str(tmp_path))
        assert d["source"] == "cache"
        # metadata refetched, files NOT re-downloaded
        file_urls_second = [r["url"] for r in record if "/x/" in r["url"]]
        assert file_urls_second == []
        assert any("/files/Camera_01" in r["url"] for r in record)

    def test_no_silent_stale_cache(self, monkeypatch, tmp_path, files_payload):
        # populate cache once
        monkeypatch.setattr(
            polyhaven,
            "_urlopen",
            fake_urlopen(files_routes(files_payload)),
        )
        polyhaven.download_asset("Camera_01", cache_root=str(tmp_path))
        # then the network dies: even with a complete cache the call
        # must surface network_unavailable, never serve stale bytes
        monkeypatch.setattr(
            polyhaven,
            "_urlopen",
            lambda req, timeout=None: (_ for _ in ()).throw(urllib.error.URLError("offline")),
        )
        with pytest.raises(AssetError) as ei:
            polyhaven.download_asset("Camera_01", cache_root=str(tmp_path))
        assert ei.value.code == "network_unavailable"

    def test_md5_mismatch_rejected(self, monkeypatch, tmp_path, files_payload):
        payload = dict(files_payload)
        payload["fbx"] = {
            "1k": {
                "fbx": {
                    "url": "https://dl.polyhaven.org/x/Camera_01_1k.fbx",
                    "size": 5,
                    "md5": "0" * 32,  # wrong hash
                }
            }
        }
        routes = files_routes(payload)
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes))
        with pytest.raises(AssetError) as ei:
            polyhaven.download_asset("Camera_01", cache_root=str(tmp_path))
        assert ei.value.code == "download_corrupt"

    def test_foreign_url_in_payload_rejected(self, monkeypatch, tmp_path):
        """A hostile /files payload pointing off-whitelist is refused."""
        payload = {
            "fbx": {
                "1k": {
                    "fbx": {
                        "url": "https://evil.example.com/x.fbx",
                        "size": 3,
                        "md5": None,
                    }
                }
            }
        }
        routes = {"https://api.polyhaven.com/files/bad": json.dumps(payload).encode()}
        monkeypatch.setattr(polyhaven, "_urlopen", fake_urlopen(routes))
        with pytest.raises(AssetError) as ei:
            polyhaven.download_asset("bad", cache_root=str(tmp_path))
        assert ei.value.code == "url_not_allowed"
