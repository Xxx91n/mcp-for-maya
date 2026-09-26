"""T-24b Maya-side contract tests: describe_node / list_nodes (D-094).

Runs against the stub-bound _mcp_scene injection unit (monolith +
introspection fragment assembled - maya_env.module). These are
CONTRACT tests: shapes and error codes must hold in real Maya, where
the fragment runs inside a live DG.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def env(maya_env):
    return maya_env


class TestDescribeNode:
    def test_transform_facet_shape(self, env):
        env.scene.add_mesh("GEO_box", t=(1, 2, 3))
        out = env.module.describe_node("GEO_box")
        assert out["node"] == "GEO_box"
        assert out["type"] == "transform"
        by_name = {a["name"]: a for a in out["attrs"]}
        tr = by_name["translate"]
        assert tr["attr_type"] == "double3"
        assert tr["keyable"] is True
        assert tr["children"] == ["translateX", "translateY", "translateZ"]
        assert tr["exists"] is True
        assert tr["writable"] is True
        assert tr["connectable"] is True
        assert tr["multi"] is False
        assert tr["locked"] is False
        assert "value" not in tr  # include_values default False

    def test_enum_and_range_facets(self, env):
        env.scene.add_mesh("GEO_a")
        out = env.module.describe_node("GEO_a", attrs=["rotateOrder"])
        ro = out["attrs"][0]
        assert ro["enum"] is True
        assert "xyz" in ro["enum_values"]
        sp = env.scene.add_light("L_spot")
        env.scene.resolve("L_spotShape")  # shape exists
        out2 = env.module.describe_node("L_spotShape", attrs=["coneAngle"])
        ca = out2["attrs"][0]
        assert ca["min"] == 0.5
        assert ca["max"] == 179.5
        assert sp.type == "transform"

    def test_missing_node_domain_error(self, env):
        out = env.module.describe_node("no_such_node")
        assert out["error"]["code"] == "node_not_found"

    def test_missing_attr_aborts_whole_call(self, env):
        env.scene.add_mesh("GEO_a")
        out = env.module.describe_node("GEO_a", attrs=["translate", "bogusAttr"])
        assert out["error"]["code"] == "attr_not_found"
        assert "bogusAttr" in out["error"]["message"]

    def test_include_values_reads_getattr(self, env):
        env.scene.add_mesh("GEO_a", t=(5, 6, 7))
        out = env.module.describe_node("GEO_a", attrs=["translate"], include_values=True)
        assert out["attrs"][0]["value"] == [[5, 6, 7]]
        assert "soft_min" in out["attrs"][0]

    def test_non_dag_node_describable(self, env):
        env.scene.add_material("MAT_a")
        out = env.module.describe_node("MAT_a", include_connections=False)
        assert out["type"] == "lambert"
        names = [a["name"] for a in out["attrs"]]
        assert "color" in names  # seeded material attr (dynamic spec)
        assert "connections" not in out

    def test_connections_direction_and_plugs(self, env):
        env.scene.add_mesh("GEO_a")
        env.scene.add_material("MAT_a", assign_to=["GEO_a"])
        # material feeds its shadingEngine: out-connection
        out = env.module.describe_node("MAT_a")
        conns = out["connections"]
        sg_conns = [c for c in conns if c["direction"] == "out"]
        assert any(
            c["src_plug"] == "MAT_a.outColor" and c["dst_plug"] == "MAT_aSG.surfaceShader"
            for c in sg_conns
        ), conns
        # shadingEngine receives: in-connection
        out_sg = env.module.describe_node("MAT_aSG")
        ins = [c for c in out_sg["connections"] if c["direction"] == "in"]
        assert any(c["src_plug"] == "MAT_a.outColor" for c in ins), ins
        # mesh shape receives dagSetMembers from SG: in-connection
        out_sh = env.module.describe_node("GEO_aShape")
        ins_sh = [c for c in out_sh["connections"] if c["direction"] == "in"]
        assert any(
            c["dst_plug"] == "GEO_aShape.instObjGroups[0]"
            and c["src_plug"] == "MAT_aSG.dagSetMembers[0]"
            for c in ins_sh
        ), ins_sh


class TestListNodes:
    def test_lists_non_dag_nodes(self, env):
        env.scene.add_mesh("GEO_a")
        env.scene.add_material("MAT_a")
        out = env.module.list_nodes()
        assert out["error"] if "error" in out else True
        assert "MAT_a" in out["nodes"]  # dependency node included
        assert out["total_count"] == out["count"] >= 3
        assert out["has_more"] is False
        assert out["next_cursor"] is None

    def test_dag_only_filter(self, env):
        env.scene.add_mesh("GEO_a")
        env.scene.add_material("MAT_a")
        out = env.module.list_nodes(dag_only=True)
        assert "MAT_a" not in out["nodes"]
        assert "|GEO_a" in out["nodes"]  # DAG members keep long names

    def test_type_filter_inherited_and_exact(self, env):
        env.scene.add_light("L1", ltype="spotLight")
        env.scene.add_mesh("GEO_a")
        inh = env.module.list_nodes(node_type="light", inherited=True)
        assert inh["total_count"] == 1 and inh["nodes"] == ["|L1|L1Shape"]
        ex = env.module.list_nodes(node_type="light", inherited=False)
        assert ex["total_count"] == 0  # no node whose exact type is 'light'
        ex2 = env.module.list_nodes(node_type="spotLight", inherited=False)
        assert ex2["total_count"] == 1

    def test_pattern_glob(self, env):
        env.scene.add_mesh("GEO_a")
        env.scene.add_mesh("PROP_b")
        out = env.module.list_nodes(pattern="GEO_*")
        assert out["total_count"] == 2  # transform + shape
        assert all("GEO_" in n for n in out["nodes"])

    def test_pagination_and_cursor(self, env):
        for i in range(5):
            env.scene.add_transform(f"T{i}")
        p1 = env.module.list_nodes(limit=2)
        assert p1["count"] == 2 and p1["has_more"] is True
        assert p1["next_cursor"] == "2"
        p2 = env.module.list_nodes(limit=2, cursor=p1["next_cursor"])
        assert p2["count"] == 2 and p2["nodes"] != p1["nodes"]
        p3 = env.module.list_nodes(limit=2, cursor=p2["next_cursor"])
        assert p3["count"] == 1 and p3["has_more"] is False
        assert p3["next_cursor"] is None
        assert p3["total_count"] == 5

    def test_invalid_cursor(self, env):
        env.scene.add_transform("T0")
        out = env.module.list_nodes(cursor="not-a-token")
        assert out["error"]["code"] == "invalid_cursor"
        out2 = env.module.list_nodes(cursor="999")
        assert out2["error"]["code"] == "invalid_cursor"

    def test_limit_hard_cap(self, env):
        for i in range(3):
            env.scene.add_transform(f"T{i}")
        out = env.module.list_nodes(limit=500)
        assert out["limit"] == 100
        assert out["count"] == 3

    def test_type_counts_cover_full_match(self, env):
        env.scene.add_mesh("GEO_a")
        env.scene.add_material("MAT_a")
        out = env.module.list_nodes(limit=1, include_type_counts=True)
        assert out["type_counts"]["transform"] >= 1
        assert out["type_counts"]["lambert"] == 1
        assert out["count"] == 1  # page still truncated, counts are global

    def test_empty_scene(self, env):
        out = env.module.list_nodes()
        assert out["total_count"] == 0 and out["nodes"] == []
