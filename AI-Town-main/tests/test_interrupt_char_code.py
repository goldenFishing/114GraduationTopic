# ================================================================
# tests/test_interrupt_char_code.py
# 確認 compute_action_probabilities 的所有呼叫都包含 char_code 參數
#
# 情境 1：re_evaluate_on_interrupt 中的呼叫包含 char_code
# 情境 2：重大事件（is_major）路徑中的呼叫包含 char_code
# ================================================================

import sys
import os
import unittest
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _read_agent_source():
    """讀取 agent/agent.py 的原始碼。"""
    agent_path = os.path.join(os.path.dirname(__file__), "..", "agent", "agent.py")
    with open(agent_path, "r", encoding="utf-8") as f:
        return f.read()


class TestInterruptCharCode(unittest.TestCase):
    """確認 agent.py 中所有 compute_action_probabilities 呼叫都帶有 char_code。"""

    def setUp(self):
        self.source = _read_agent_source()

    # ------------------------------------------------------------------
    # 情境 1：re_evaluate_on_interrupt 方法中的 compute_action_probabilities
    # ------------------------------------------------------------------
    def test_re_evaluate_on_interrupt_has_char_code(self):
        """
        re_evaluate_on_interrupt 方法內的 compute_action_probabilities 呼叫
        必須包含 char_code 參數。
        """
        lines = self.source.splitlines()

        # 找到 re_evaluate_on_interrupt 方法的起始行
        method_start = None
        for i, line in enumerate(lines):
            if "def re_evaluate_on_interrupt" in line:
                method_start = i
                break

        self.assertIsNotNone(
            method_start,
            "找不到 re_evaluate_on_interrupt 方法定義"
        )

        # 從方法起始行往後掃，找到第一個 compute_action_probabilities 呼叫
        call_start = None
        for i in range(method_start, len(lines)):
            if "compute_action_probabilities(" in lines[i]:
                call_start = i
                break

        self.assertIsNotNone(
            call_start,
            "re_evaluate_on_interrupt 中找不到 compute_action_probabilities 呼叫"
        )

        # 取呼叫區塊（到關閉括號為止，最多掃 20 行）
        call_block = "\n".join(lines[call_start: call_start + 20])

        self.assertIn(
            "char_code",
            call_block,
            "re_evaluate_on_interrupt 中的 compute_action_probabilities 缺少 char_code 參數"
        )

    # ------------------------------------------------------------------
    # 情境 2：重大事件（is_major）路徑的 compute_action_probabilities
    # ------------------------------------------------------------------
    def test_is_major_block_has_char_code(self):
        """
        is_major 重算區塊中的 compute_action_probabilities 呼叫
        必須包含 char_code 參數。
        """
        lines = self.source.splitlines()

        # 找到 is_major 判斷區塊（if is_major:）
        major_block_start = None
        for i, line in enumerate(lines):
            # 只抓縮排後的 if is_major:，避免匹配到變數賦值
            stripped = line.strip()
            if stripped == "if is_major:":
                major_block_start = i
                break

        self.assertIsNotNone(
            major_block_start,
            "找不到 'if is_major:' 區塊"
        )

        # 往後掃找到該區塊內的 compute_action_probabilities 呼叫
        call_start = None
        for i in range(major_block_start, min(major_block_start + 30, len(lines))):
            if "compute_action_probabilities(" in lines[i]:
                call_start = i
                break

        self.assertIsNotNone(
            call_start,
            "is_major 區塊中找不到 compute_action_probabilities 呼叫"
        )

        # 取呼叫區塊（最多 20 行）
        call_block = "\n".join(lines[call_start: call_start + 20])

        self.assertIn(
            "char_code",
            call_block,
            "is_major 區塊的 compute_action_probabilities 缺少 char_code 參數"
        )

    # ------------------------------------------------------------------
    # 額外保障：確認全檔案所有 compute_action_probabilities 呼叫都有 char_code
    # ------------------------------------------------------------------
    def test_all_calls_have_char_code(self):
        """
        agent.py 中每一個 compute_action_probabilities(...) 呼叫區塊
        都必須包含 char_code。
        """
        lines = self.source.splitlines()
        call_indices = [
            i for i, line in enumerate(lines)
            if "compute_action_probabilities(" in line
            # 跳過 import 行
            and "import" not in line
        ]

        self.assertGreaterEqual(
            len(call_indices), 3,
            f"預期至少 3 個 compute_action_probabilities 呼叫，實際找到 {len(call_indices)} 個"
        )

        for idx in call_indices:
            call_block = "\n".join(lines[idx: idx + 20])
            self.assertIn(
                "char_code",
                call_block,
                f"第 {idx + 1} 行的 compute_action_probabilities 呼叫缺少 char_code 參數"
            )


if __name__ == "__main__":
    unittest.main()
