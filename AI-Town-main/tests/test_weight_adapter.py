# ================================================================
# tests/test_weight_adapter.py
# WeightAdapter 單元測試（使用 Python 內建 unittest）
# ================================================================

import sys
import os
import json
import unittest

# 將專案根目錄加入 sys.path，確保可以 import core 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.weight_adapter import WeightAdapter


class TestWeightAdapter(unittest.TestCase):

    # ----------------------------------------------------------------
    # 情境 1：預設初始化，權重總和 ≈ 1.0
    # ----------------------------------------------------------------
    def test_case1_default_weights_sum_to_one(self):
        adapter = WeightAdapter()
        w = adapter.get_weights()
        total = w["alpha"] + w["beta"] + w["gamma"]
        self.assertAlmostEqual(total, 1.0, delta=0.001,
            msg=f"預設權重總和應≈1.0，實際={total}")

    # ----------------------------------------------------------------
    # 情境 2：record_tick + update_weights 正常執行
    # ----------------------------------------------------------------
    def test_case2_record_and_update(self):
        adapter = WeightAdapter()
        breakdown = {
            "schedule":  {"吃飯": 0.8},
            "inertia":   {"吃飯": 0.3},
            "situation": {"吃飯": 0.2},
        }
        adapter.record_tick("吃飯", reward=0.5, breakdown=breakdown)
        adapter.update_weights()
        w = adapter.get_weights()

        # 總和 ≈ 1.0
        total = w["alpha"] + w["beta"] + w["gamma"]
        self.assertAlmostEqual(total, 1.0, delta=0.001,
            msg=f"update 後權重總和應≈1.0，實際={total}")

        # 每個值在 [MIN_WEIGHT, MAX_WEIGHT] 之間
        for key, val in w.items():
            self.assertGreaterEqual(val, WeightAdapter.MIN_WEIGHT,
                msg=f"{key}={val} 低於 MIN_WEIGHT={WeightAdapter.MIN_WEIGHT}")
            self.assertLessEqual(val, WeightAdapter.MAX_WEIGHT,
                msg=f"{key}={val} 高於 MAX_WEIGHT={WeightAdapter.MAX_WEIGHT}")

    # ----------------------------------------------------------------
    # 情境 3：負 reward 時所有 weights 仍在合法範圍內
    # ----------------------------------------------------------------
    def test_case3_negative_reward_clipping(self):
        adapter = WeightAdapter()
        breakdown = {
            "schedule":  {"工作": 0.9},
            "inertia":   {"工作": 0.1},
            "situation": {"工作": 0.0},
        }
        adapter.record_tick("工作", reward=-0.5, breakdown=breakdown)
        adapter.update_weights()
        w = adapter.get_weights()

        for key, val in w.items():
            self.assertGreaterEqual(val, WeightAdapter.MIN_WEIGHT,
                msg=f"負reward後 {key}={val} 低於 MIN_WEIGHT")
            self.assertLessEqual(val, WeightAdapter.MAX_WEIGHT,
                msg=f"負reward後 {key}={val} 高於 MAX_WEIGHT")

    # ----------------------------------------------------------------
    # 情境 4：to_dict / from_dict 往返序列化
    # ----------------------------------------------------------------
    def test_case4_serialization_roundtrip(self):
        adapter = WeightAdapter({"alpha": 0.5, "beta": 0.25, "gamma": 0.25})
        d = adapter.to_dict()
        adapter2 = WeightAdapter.from_dict(d)
        self.assertEqual(adapter2.get_weights(), adapter.get_weights(),
            msg="from_dict 還原後 get_weights() 應與原始相同")

    # ----------------------------------------------------------------
    # 情境 5：AI_Data/A_init.json 含 markov_weights 欄位
    # ----------------------------------------------------------------
    def test_case5_json_has_markov_weights(self):
        json_path = os.path.join(
            os.path.dirname(__file__), "..", "AI_Data", "A_init.json"
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("markov_weights", data,
            msg="A_init.json 應有 'markov_weights' key")

        mw = data["markov_weights"]
        for key in ("alpha", "beta", "gamma"):
            self.assertIn(key, mw,
                msg=f"markov_weights 應有 '{key}' key")
            self.assertIsInstance(mw[key], (int, float),
                msg=f"markov_weights['{key}'] 應為數值")


if __name__ == "__main__":
    unittest.main()
