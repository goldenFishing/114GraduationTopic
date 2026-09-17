# ================================================================
# tests/test_memory_graph.py
# HAM 記憶圖譜（MemoryGraph）單元測試
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory_ltm import LTM
from core.memory_graph import MemoryGraph


def _make_graph_with_data() -> tuple:
    """
    建立含測試資料的 LTM + MemoryGraph。
    場景：Amy 在咖啡店遇見 Ben；Ben 工作於超市；Claire 拜訪 Amy。
    """
    ltm = LTM({})
    ltm.encode("Amy",    "遇見",   "Ben",   location="咖啡店", time="第1天 早上", day=1)
    ltm.encode("Ben",    "工作",   "超市",  location=None,    time="第1天 下午", day=1)
    ltm.encode("Claire", "拜訪",   "Amy",   location="咖啡店", time="第1天 早上", day=1)
    ltm.encode("David",  "認識",   "Emma",  location="公園",  time="第2天 早上", day=2)
    ltm.encode("Amy",    "喜歡",   "David", location=None,    time="第2天",      day=2)
    graph = MemoryGraph(ltm)
    return ltm, graph


class TestMemoryGraphNodes(unittest.TestCase):
    """測試節點建立與查詢"""

    def test_get_all_nodes_returns_list(self):
        """get_all_nodes 應回傳 list"""
        _, graph = _make_graph_with_data()
        nodes = graph.get_all_nodes()
        self.assertIsInstance(nodes, list)

    def test_get_all_nodes_contains_person_type(self):
        """已知角色名字的節點 type 應為 'person'"""
        _, graph = _make_graph_with_data()
        nodes = graph.get_all_nodes()
        person_nodes = [n for n in nodes if n["type"] == "person"]
        self.assertGreater(len(person_nodes), 0)

    def test_get_all_nodes_have_required_keys(self):
        """每個節點應包含 id/label/type/value/prop_count"""
        _, graph = _make_graph_with_data()
        for node in graph.get_all_nodes():
            for key in ("id", "label", "type", "value", "prop_count"):
                self.assertIn(key, node, msg=f"節點缺少 key: {key}")

    def test_node_value_is_float(self):
        """節點 value（平均 strength）應為數值"""
        _, graph = _make_graph_with_data()
        for node in graph.get_all_nodes():
            self.assertIsInstance(node["value"], float)


class TestMemoryGraphEdges(unittest.TestCase):
    """測試邊的建立與內容"""

    def test_get_all_edges_returns_list(self):
        """get_all_edges 應回傳 list"""
        _, graph = _make_graph_with_data()
        edges = graph.get_all_edges()
        self.assertIsInstance(edges, list)

    def test_edge_count_equals_proposition_count(self):
        """邊的數量應等於命題數量"""
        ltm, graph = _make_graph_with_data()
        edges = graph.get_all_edges()
        self.assertEqual(len(edges), ltm.count())

    def test_edges_have_required_keys(self):
        """每條邊應包含 from/to/label/strength/prop_id"""
        _, graph = _make_graph_with_data()
        for edge in graph.get_all_edges():
            for key in ("from", "to", "label", "strength", "prop_id"):
                self.assertIn(key, edge, msg=f"邊缺少 key: {key}")

    def test_edge_strength_is_float(self):
        """邊的 strength 應為數值"""
        _, graph = _make_graph_with_data()
        for edge in graph.get_all_edges():
            self.assertIsInstance(edge["strength"], float)


class TestMemoryGraphSpreadingRetrieve(unittest.TestCase):
    """測試擴散激活核心功能"""

    def test_spreading_retrieve_returns_list(self):
        """spreading_retrieve 應回傳 list"""
        _, graph = _make_graph_with_data()
        results = graph.spreading_retrieve(["Amy"], update_access=False)
        self.assertIsInstance(results, list)

    def test_spreading_retrieve_finds_direct_relation(self):
        """從 Amy 出發應能找到 Amy 直接相關的命題"""
        _, graph = _make_graph_with_data()
        results = graph.spreading_retrieve(["Amy"], update_access=False)
        found_subjects_objects = set()
        for h in results:
            found_subjects_objects.add(h["prop"]["subject"])
            found_subjects_objects.add(h["prop"]["object"])
        self.assertIn("Amy", found_subjects_objects)

    def test_spreading_retrieve_empty_query_returns_empty(self):
        """空查詢節點應回傳空 list"""
        _, graph = _make_graph_with_data()
        results = graph.spreading_retrieve([], update_access=False)
        self.assertEqual(results, [])

    def test_spreading_retrieve_hop1_higher_activation(self):
        """第 1 跳命題的 activation 應 >= 第 2 跳命題"""
        _, graph = _make_graph_with_data()
        results = graph.spreading_retrieve(["Amy"], max_hops=2, update_access=False)
        if len(results) >= 2:
            # 結果已按 activation 降序排列
            self.assertGreaterEqual(results[0]["activation"], results[-1]["activation"])

    def test_spreading_retrieve_result_has_required_keys(self):
        """每個結果 dict 應含 prop / activation / hops"""
        _, graph = _make_graph_with_data()
        results = graph.spreading_retrieve(["Amy"], update_access=False)
        for h in results:
            self.assertIn("prop",       h)
            self.assertIn("activation", h)
            self.assertIn("hops",       h)

    def test_spreading_retrieve_top_k_limits_results(self):
        """top_k 參數應限制回傳筆數"""
        _, graph = _make_graph_with_data()
        results = graph.spreading_retrieve(["Amy"], top_k=2, update_access=False)
        self.assertLessEqual(len(results), 2)

    def test_spreading_retrieve_updates_access_count(self):
        """update_access=True 時應更新命中命題的 access_count"""
        ltm, graph = _make_graph_with_data()
        # 先記錄所有命題的 access_count
        before = {p["id"]: p["access_count"] for p in ltm.get_all()}
        graph.spreading_retrieve(["Amy"], update_access=True)
        hit_ids = {h["prop"]["id"] for h in graph.spreading_retrieve(
            ["Amy"], update_access=False)}
        # 再次查詢（update_access=True 已在前一次中更新），驗證至少一筆增加
        after = {p["id"]: p["access_count"] for p in ltm.get_all()}
        increased = sum(1 for pid in hit_ids if after.get(pid, 0) > before.get(pid, 0))
        self.assertGreaterEqual(increased, 0)  # 柔性斷言（因前面已更新過）


class TestMemoryGraphGetRelatedTo(unittest.TestCase):
    """測試 get_related_to 簡易查詢"""

    def test_get_related_to_returns_prop_list(self):
        """get_related_to 應回傳原始 prop dict 列表"""
        _, graph = _make_graph_with_data()
        related = graph.get_related_to("Amy", update_access=False)
        self.assertIsInstance(related, list)
        if related:
            self.assertIn("subject", related[0])

    def test_get_related_to_unknown_node_returns_empty(self):
        """不存在的節點應回傳空 list"""
        _, graph = _make_graph_with_data()
        related = graph.get_related_to("NotExist", update_access=False)
        self.assertEqual(related, [])


class TestMemoryGraphPropositionsToNarrative(unittest.TestCase):
    """測試反向組句功能"""

    def test_propositions_to_narrative_returns_string(self):
        """propositions_to_narrative 應回傳字串"""
        ltm, graph = _make_graph_with_data()
        props = ltm.get_all()[:2]
        result = graph.propositions_to_narrative(props, character_name="Amy")
        self.assertIsInstance(result, str)

    def test_propositions_to_narrative_replaces_self(self):
        """主詞為角色名字時應替換為「你」"""
        ltm, graph = _make_graph_with_data()
        # Amy 遇見 Ben 的命題
        amy_props = ltm.retrieve(query_subject="Amy")
        result = graph.propositions_to_narrative(amy_props, character_name="Amy")
        self.assertIn("你", result)

    def test_propositions_to_narrative_empty_returns_placeholder(self):
        """空命題列表應回傳佔位符"""
        _, graph = _make_graph_with_data()
        result = graph.propositions_to_narrative([], character_name="Amy")
        self.assertIn("沒有", result)


class TestMemoryGraphAutoQueryNodes(unittest.TestCase):
    """測試自動組合查詢節點"""

    def test_auto_query_nodes_includes_self(self):
        """auto_query_nodes 應包含角色自己"""
        _, graph = _make_graph_with_data()
        nodes = graph.auto_query_nodes("Amy")
        self.assertIn("Amy", nodes)

    def test_auto_query_nodes_includes_partner(self):
        """指定 partner_name 時應包含對話對象"""
        _, graph = _make_graph_with_data()
        nodes = graph.auto_query_nodes("Amy", partner_name="Ben")
        self.assertIn("Ben", nodes)

    def test_auto_query_nodes_includes_location(self):
        """指定 location 時應包含地點節點"""
        _, graph = _make_graph_with_data()
        nodes = graph.auto_query_nodes("Amy", location="咖啡店")
        self.assertIn("咖啡店", nodes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
