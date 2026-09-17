# ================================================================
# tests/test_memory_ltm.py
# 長期記憶（LTM）單元測試
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory_ltm import LTM


def _make_ltm() -> LTM:
    """建立空白 LTM 實例。"""
    return LTM({})


class TestLTMEncode(unittest.TestCase):
    """測試 encode / encode_batch 寫入功能"""

    def test_encode_single_proposition(self):
        """encode 後 count 應為 1"""
        ltm = _make_ltm()
        ltm.encode("Amy", "遇見", "Ben", location="咖啡店", time="第1天 早上", day=1)
        self.assertEqual(ltm.count(), 1)

    def test_encode_returns_dict_with_id(self):
        """encode 應回傳含 id 的命題 dict"""
        ltm = _make_ltm()
        prop = ltm.encode("Amy", "工作", "咖啡店", day=1)
        self.assertIsInstance(prop, dict)
        self.assertIn("id", prop)

    def test_encode_id_sequential(self):
        """連續 encode 的 id 應依序遞增"""
        ltm = _make_ltm()
        p1 = ltm.encode("Amy", "遇見", "Ben", day=1)
        p2 = ltm.encode("Ben", "工作", "超市", day=1)
        self.assertEqual(p1["id"], "L001")
        self.assertEqual(p2["id"], "L002")

    def test_encode_strength_initial_one(self):
        """剛寫入的命題 strength 應為 1.0"""
        ltm = _make_ltm()
        prop = ltm.encode("Claire", "喜歡", "咖啡", day=2)
        self.assertAlmostEqual(prop["strength"], 1.0)

    def test_encode_batch_multiple(self):
        """encode_batch 應一次寫入多筆命題"""
        ltm = _make_ltm()
        props = [
            {"subject": "David", "relation": "認識", "object": "Amy"},
            {"subject": "Emma", "relation": "好友", "object": "Amy", "location": "公園"},
        ]
        ltm.encode_batch(props, day=3)
        self.assertEqual(ltm.count(), 2)

    def test_id_not_duplicated_after_prune(self):
        """prune 後再 encode，id 不應重複"""
        ltm = _make_ltm()
        ltm.encode("Amy", "遇見", "Ben", day=1)
        ltm.encode("Ben", "喜歡", "Emma", day=1)
        # 強制讓第一筆衰減到 0
        ltm.get_all()[0]["strength"] = 0.0
        ltm.prune()
        new_prop = ltm.encode("Claire", "工作", "超市", day=2)
        # 新 ID 應比已存在的 L002 大
        new_n = int(new_prop["id"][1:])
        self.assertGreater(new_n, 2)


class TestLTMRetrieve(unittest.TestCase):
    """測試 retrieve 查詢功能"""

    def setUp(self):
        self.ltm = _make_ltm()
        self.ltm.encode("Amy", "遇見", "Ben", location="咖啡店", time="第1天 早上", day=1)
        self.ltm.encode("Amy", "工作", "咖啡店", day=1)
        self.ltm.encode("Ben", "工作", "超市", day=2)
        self.ltm.encode("Claire", "拜訪", "Amy", location="咖啡店", day=3)

    def test_retrieve_by_subject(self):
        """retrieve(query_subject='Amy') 應只回傳 Amy 為主詞的命題"""
        results = self.ltm.retrieve(query_subject="Amy")
        for p in results:
            self.assertEqual(p["subject"], "Amy")

    def test_retrieve_by_object(self):
        """retrieve(query_object='Amy') 應只回傳 Amy 為受詞的命題"""
        results = self.ltm.retrieve(query_object="Amy")
        for p in results:
            self.assertEqual(p["object"], "Amy")

    def test_retrieve_by_location(self):
        """retrieve(query_location='咖啡店') 應只回傳咖啡店命題"""
        results = self.ltm.retrieve(query_location="咖啡店")
        for p in results:
            self.assertEqual(p.get("location"), "咖啡店")

    def test_retrieve_no_match_returns_empty(self):
        """查詢不存在的 subject 應回傳空 list"""
        results = self.ltm.retrieve(query_subject="Emma")
        self.assertEqual(results, [])

    def test_retrieve_top_k_limit(self):
        """retrieve(top_k=2) 最多回傳 2 筆"""
        results = self.ltm.retrieve(top_k=2)
        self.assertLessEqual(len(results), 2)

    def test_retrieve_update_access_increments_count(self):
        """retrieve(update_access=True) 應讓 access_count 增加"""
        props = self.ltm.retrieve(query_subject="Amy", update_access=True)
        for p in props:
            self.assertGreaterEqual(p["access_count"], 1)


class TestLTMDecayAndPrune(unittest.TestCase):
    """測試衰減與修剪功能"""

    def test_apply_decay_reduces_strength(self):
        """apply_decay 後所有命題的 strength 應降低"""
        ltm = _make_ltm()
        ltm.encode("Amy", "遇見", "Ben", day=1)
        original = ltm.get_all()[0]["strength"]
        ltm.apply_decay()
        self.assertLess(ltm.get_all()[0]["strength"], original)

    def test_apply_decay_with_high_access_count_slower(self):
        """access_count 高的命題衰減應比 access_count=0 的慢"""
        ltm1 = _make_ltm()
        ltm2 = _make_ltm()
        ltm1.encode("Amy", "遇見", "Ben", day=1)
        ltm2.encode("Amy", "遇見", "Ben", day=1)
        # 設定 access_count
        ltm1.get_all()[0]["access_count"] = 0
        ltm2.get_all()[0]["access_count"] = 10
        ltm1.apply_decay()
        ltm2.apply_decay()
        self.assertGreater(ltm2.get_all()[0]["strength"], ltm1.get_all()[0]["strength"])

    def test_prune_removes_low_strength(self):
        """prune 後低 strength 的命題應被刪除"""
        ltm = _make_ltm()
        ltm.encode("Amy", "遇見", "Ben", day=1)
        ltm.get_all()[0]["strength"] = 0.01  # 低於 LTM_FORGET_THRESHOLD=0.2
        removed = ltm.prune()
        self.assertGreater(removed, 0)
        self.assertEqual(ltm.count(), 0)

    def test_prune_keeps_high_strength(self):
        """prune 應保留 strength 高的命題"""
        ltm = _make_ltm()
        ltm.encode("Amy", "遇見", "Ben", day=1)  # strength=1.0
        removed = ltm.prune()
        self.assertEqual(removed, 0)
        self.assertEqual(ltm.count(), 1)

    def test_delete_by_id(self):
        """delete 應能刪除指定 ID 的命題並回傳 True"""
        ltm = _make_ltm()
        prop = ltm.encode("David", "認識", "Emma", day=1)
        pid = prop["id"]
        success = ltm.delete(pid)
        self.assertTrue(success)
        self.assertIsNone(ltm.get_by_id(pid))


class TestLTMSummaryAndText(unittest.TestCase):
    """測試摘要與文字輸出功能"""

    def test_set_and_get_summary(self):
        """set_summary 後 get_summary 應回傳相同文字"""
        ltm = _make_ltm()
        summary = "Amy 在第一天認識了 Ben，並在咖啡店工作。"
        ltm.set_summary(summary)
        self.assertEqual(ltm.get_summary(), summary)

    def test_to_text_returns_pipe_format(self):
        """to_text 應回傳 pipe 分隔格式"""
        ltm = _make_ltm()
        ltm.encode("Amy", "遇見", "Ben", location="咖啡店", time="早上", day=1)
        text = ltm.to_text()
        self.assertIn("|", text)

    def test_to_text_empty_returns_placeholder(self):
        """無命題時 to_text 應回傳佔位符"""
        ltm = _make_ltm()
        text = ltm.to_text()
        self.assertIn("沒有", text)

    def test_to_readable_natural_language(self):
        """to_readable 應回傳自然語言格式"""
        ltm = _make_ltm()
        ltm.encode("Emma", "好友", "Amy", location="公園", day=1)
        readable = ltm.to_readable()
        self.assertIn("Emma", readable)
        self.assertIn("Amy", readable)

    def test_touch_resets_strength(self):
        """touch 後 strength 應重置為 1.0 且 access_count 增加"""
        ltm = _make_ltm()
        prop = ltm.encode("Amy", "工作", "咖啡店", day=1)
        prop["strength"] = 0.5
        ltm.touch(prop["id"])
        updated = ltm.get_by_id(prop["id"])
        self.assertAlmostEqual(updated["strength"], 1.0)
        self.assertEqual(updated["access_count"], 1)


class TestLTMIndex(unittest.TestCase):
    """測試 LTM 地點×人員頻率索引（ltm_index / update_index / get_combo_freq）。"""

    def setUp(self):
        self.ltm = _make_ltm()

    def test_ltm_index_initialized_empty(self):
        """初始化後 ltm_index 應為空 dict。"""
        self.assertIsInstance(self.ltm.ltm_index, dict)
        self.assertEqual(len(self.ltm.ltm_index), 0)

    def test_update_index_increments_count(self):
        """update_index 後該組合的 count 應增加。"""
        self.ltm.update_index("咖啡店", ["A", "B"])
        self.assertEqual(self.ltm.get_combo_freq("咖啡店", ["A", "B"]), 1)

    def test_update_index_multiple_times(self):
        """同一組合多次 update_index 應累加。"""
        for _ in range(3):
            self.ltm.update_index("超市", ["B"])
        self.assertEqual(self.ltm.get_combo_freq("超市", ["B"]), 3)

    def test_get_combo_freq_unknown_returns_zero(self):
        """未記錄的組合 get_combo_freq 應回傳 0。"""
        freq = self.ltm.get_combo_freq("廣場", ["A"])
        self.assertEqual(freq, 0)

    def test_people_set_order_independent(self):
        """update_index 傳入的 people_set 順序不同應視為同一組合。"""
        self.ltm.update_index("餐廳", ["C", "A"])
        # 順序不同但集合相同，應能取到
        freq = self.ltm.get_combo_freq("餐廳", ["A", "C"])
        self.assertEqual(freq, 1)

    def test_different_locations_different_keys(self):
        """不同地點的相同人員組合應分開計算。"""
        self.ltm.update_index("咖啡店", ["A"])
        self.ltm.update_index("超市", ["A"])
        self.assertEqual(self.ltm.get_combo_freq("咖啡店", ["A"]), 1)
        self.assertEqual(self.ltm.get_combo_freq("超市", ["A"]), 1)

    def test_empty_people_set(self):
        """空 people_set 也應能正確記錄。"""
        self.ltm.update_index("廣場", [])
        self.assertEqual(self.ltm.get_combo_freq("廣場", []), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
