# ================================================================
# tests/test_full_flow.py
# 無 LLM 全流程模擬測試
#
# 使用 FakeLoader + eval_confusion monkeypatch，跑完整 3 天模擬
# 並生成 docs/full_flow_report.md
# ================================================================

import sys
import io
import os
import unittest
import collections

# 設定 UTF-8 輸出（避免 Windows 中文亂碼）
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── 把專案根目錄加入 sys.path ─────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ================================================================
# FakeLoader：完全不呼叫真實 LLM
# ================================================================

class FakeLoader:
    """
    讓 Agent._call_model 走進 'loader is None 或未載入' 分支，回傳 ''。
    同時實作 consolidation 需要的 make_model_fn。
    """

    def is_loaded(self):
        return False

    def load(self):
        pass

    # consolidation 用的函式 factory
    def make_consolidation_fn(self, step: str):
        defaults = {
            "ham_extract": lambda text: [],
            "select":      lambda props, summary: props[:3] if props else [],
            "summary":     lambda stm_text: "（模擬日誌）",
            "relation":    lambda ltm_text: [],
            "emotion":     lambda ctx: "平靜",
            "schedule":    lambda ctx: [],
        }
        return defaults.get(step, lambda *a, **kw: None)

    def make_model_fn(self, **kw):
        return lambda prompt: ""

    def make_deliberate_fn(self):
        return lambda prompt: ""

    def make_dialogue_fn(self):
        return lambda prompt: ""


# ================================================================
# Monkeypatch 準備（延遲到 setUpClass 執行，tearDownClass 還原）
# ================================================================

import agent.agent as _agent_module
_ORIGINAL_EVAL_CONFUSION = _agent_module.eval_confusion
_FAKE_EVAL_CONFUSION = lambda **kw: {
    "mode": "intuitive",
    "C": 0.1,
    "U": 0.1,
    "K": 0.1,
    "S": 0.1,
}


# ================================================================
# 輔助：run_n_days
# ================================================================

def run_n_days(manager, n_days: int = 3) -> list:
    """
    執行 n 天完整模擬。
    優先嘗試 run_autonomous_days，若不存在則自行迴圈。
    """
    if hasattr(manager, "run_autonomous_days"):
        result = manager.run_autonomous_days(n_days)
        # run_autonomous_days 回傳 {"days": [...], "total_ticks": int}
        return result["days"] if isinstance(result, dict) else result

    all_days = []
    for _day in range(n_days):
        day_data = manager.run_one_day()
        all_days.append(day_data)
        if manager.all_sleeping_today():
            manager.clock.advance_day()
            manager._sleeping_today.clear()
    return all_days


# ================================================================
# 輔助：生成報告
# ================================================================

def _safe_get(d, *keys, default=""):
    """安全取 nested dict 值。"""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d


def generate_report(all_days: list, manager, output_path: str):
    """從 all_days 資料生成 Markdown 報告。"""

    lines = []
    lines.append("# AI-Town 全流程模擬報告（無 LLM 模式）\n")
    lines.append(f"模擬天數：{len(all_days)} 天\n")

    # ── 摘要表 ───────────────────────────────────────────────────
    lines.append("## 1. 摘要表\n")
    lines.append("| 角色 | 天數 | 總 Tick 數 | 行動次數 | 最常見行動 |")
    lines.append("|------|------|-----------|---------|-----------|")

    codes = manager.all_codes()

    for code in codes:
        char_name = manager.get_character(code).name
        for day_data in all_days:
            day_n = day_data.get("day", "?")
            ticks = day_data.get("ticks", [])
            total_ticks = len(ticks)

            # 收集行動（從 execute 結果取）
            action_counter = collections.Counter()
            for tick in ticks:
                exec_r = tick.get("execute", {}).get(code, {})
                act = exec_r.get("action", "")
                if act and act not in ("起床", "睡覺"):
                    action_counter[act] += 1

            action_count = sum(action_counter.values())
            most_common = action_counter.most_common(1)
            top_action = most_common[0][0] if most_common else "—"

            lines.append(
                f"| {char_name}({code}) | 第{day_n}天 | {total_ticks} "
                f"| {action_count} | {top_action} |"
            )

    lines.append("")

    # ── 每天每角色行動序列 ────────────────────────────────────────
    lines.append("## 2. 行動序列（每天每角色）\n")

    for day_data in all_days:
        day_n = day_data.get("day", "?")
        ticks = day_data.get("ticks", [])
        lines.append(f"### 第 {day_n} 天\n")

        for code in codes:
            char_name = manager.get_character(code).name
            lines.append(f"#### {char_name}（{code}）\n")
            lines.append("| 時間 | 行動 | 位置 | 模式 |")
            lines.append("|------|------|------|------|")

            for tick in ticks:
                time_str = tick.get("time", "??:??")
                exec_r   = tick.get("execute", {}).get(code, {})
                decide_r = tick.get("decide",  {}).get(code, {})

                action   = exec_r.get("action", "—")
                location = ""
                # 嘗試從 execute target 取位置（前往行動）
                if exec_r.get("action") == "前往":
                    location = exec_r.get("target", "")
                # 若沒有則從角色當前位置取（決策後）
                if not location:
                    try:
                        location = manager.get_character(code).current_location
                    except Exception:
                        location = "—"

                mode = decide_r.get("mode", "—")
                lines.append(f"| {time_str} | {action} | {location} | {mode} |")

            lines.append("")

    # ── 對話記錄 ─────────────────────────────────────────────────
    lines.append("## 3. 對話記錄\n")

    any_dialogue = False
    for day_data in all_days:
        day_n = day_data.get("day", "?")
        ticks = day_data.get("ticks", [])
        for tick in ticks:
            time_str = tick.get("time", "??:??")
            dialogues = tick.get("dialogues", [])
            if not dialogues:
                continue
            any_dialogue = True
            for dlg in dialogues:
                init_code = dlg.get("initiator", "?")
                resp_code = dlg.get("responder", "?")
                accepted  = dlg.get("accepted", False)
                n_turns   = len(dlg.get("turns", []))
                status    = "接受" if accepted else "拒絕"

                try:
                    init_name = manager.get_character(init_code).name
                    resp_name = manager.get_character(resp_code).name
                except Exception:
                    init_name = init_code
                    resp_name = resp_code

                lines.append(
                    f"- 第{day_n}天 {time_str}：**{init_name}** 發起對話 → "
                    f"**{resp_name}** {status}（{n_turns} 句話）"
                )

    if not any_dialogue:
        lines.append("（本次模擬中未發生對話）\n")
    else:
        lines.append("")

    # ── 睡眠時間統計 ─────────────────────────────────────────────
    lines.append("## 4. 睡眠時間統計\n")
    lines.append("| 角色 | 天數 | 最後 Tick 時間 |")
    lines.append("|------|------|--------------|")

    for day_data in all_days:
        day_n = day_data.get("day", "?")
        ticks = day_data.get("ticks", [])
        sleep_time = "—"
        if ticks:
            last_tick = ticks[-1]
            sleep_time = last_tick.get("time", "—")
        # 所有已睡角色都記錄同一個最後 tick 時間（因為是整天結束時）
        sleeping = day_data.get("ticks", [{}])[-1].get("sleeping_today", []) if ticks else []
        for code in codes:
            char_name = manager.get_character(code).name
            lines.append(f"| {char_name}({code}) | 第{day_n}天 | {sleep_time} |")

    lines.append("")
    lines.append("---\n")
    lines.append("*本報告由 `tests/test_full_flow.py` 自動生成（無 LLM 模式）。*\n")

    # ── 寫入檔案 ─────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


# ================================================================
# 主測試類別
# ================================================================

class TestFullFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """在所有測試前執行：patch eval_confusion、建立 manager 並跑 3 天模擬。"""
        # 啟用 monkeypatch（限定本測試類別範圍）
        _agent_module.eval_confusion = _FAKE_EVAL_CONFUSION

        from world.world_clock import WorldClock
        from agent.manager import AgentManager

        fake_loader = FakeLoader()
        clock       = WorldClock(start_hour=7)   # 從 07:00 開始
        cls.manager = AgentManager(loader=fake_loader, clock=clock)
        cls.all_days = run_n_days(cls.manager, n_days=3)

    @classmethod
    def tearDownClass(cls):
        """測試結束後還原 eval_confusion，避免污染其他測試。"""
        _agent_module.eval_confusion = _ORIGINAL_EVAL_CONFUSION

    # ────────────────────────────────────────────────────────────

    def test_1_three_days_completed(self):
        """應完成 3 天模擬，每天都有 ticks。"""
        self.assertEqual(len(self.all_days), 3,
                         f"應有 3 天資料，實際：{len(self.all_days)}")
        for i, day_data in enumerate(self.all_days):
            ticks = day_data.get("ticks", [])
            self.assertGreater(len(ticks), 0,
                               f"第 {i+1} 天 ticks 不能為空")

    def test_2_all_characters_have_actions(self):
        """每個角色在每天至少應有 1 次行動。"""
        codes = self.manager.all_codes()
        for day_data in self.all_days:
            day_n = day_data.get("day")
            for code in codes:
                has_action = False
                for tick in day_data.get("ticks", []):
                    exec_r = tick.get("execute", {}).get(code, {})
                    if exec_r.get("action"):
                        has_action = True
                        break
                self.assertTrue(
                    has_action,
                    f"角色 {code} 在第 {day_n} 天沒有任何行動記錄"
                )

    def test_3_all_characters_slept(self):
        """每天結束時所有角色應已入睡（透過 sleep_reports 確認）。"""
        codes = set(self.manager.all_codes())
        for day_data in self.all_days:
            day_n = day_data.get("day")
            # sleep_reports 包含每個角色的濃縮報告，代表已睡
            sleep_reports = set(day_data.get("sleep_reports", {}).keys())
            self.assertTrue(
                sleep_reports >= codes,
                f"第 {day_n} 天結束時未所有角色有睡眠報告：reports={sleep_reports}"
            )

    def test_4_sleep_reports_exist(self):
        """每天應有睡眠濃縮報告。"""
        for day_data in self.all_days:
            day_n = day_data.get("day")
            sleep_reports = day_data.get("sleep_reports", {})
            self.assertGreater(
                len(sleep_reports), 0,
                f"第 {day_n} 天沒有睡眠報告"
            )

    def test_5_decide_results_have_action(self):
        """decide 結果應有 action 欄位。"""
        codes = self.manager.all_codes()
        for day_data in self.all_days:
            for tick in day_data.get("ticks", []):
                for code in codes:
                    decide_r = tick.get("decide", {}).get(code, {})
                    # 允許 error 欄位（decide 失敗時）或有 action 欄位
                    if decide_r and "error" not in decide_r:
                        self.assertIn(
                            "action", decide_r,
                            f"decide 結果缺少 action 欄位：{decide_r}"
                        )

    def test_6_report_generated(self):
        """應成功生成 docs/full_flow_report.md。"""
        report_path = os.path.join(
            _PROJECT_ROOT, "docs", "full_flow_report.md"
        )
        result_path = generate_report(self.all_days, self.manager, report_path)
        self.assertTrue(
            os.path.exists(result_path),
            f"報告檔案未生成：{result_path}"
        )
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("AI-Town", content)
        self.assertIn("行動序列", content)
        print(f"\n[報告已寫入] {result_path}")

    def test_7_print_day1_action_sequences(self):
        """印出 Day1 各角色行動序列（包含時間和地點）。"""
        codes = self.manager.all_codes()
        day1 = self.all_days[0] if self.all_days else {}
        day_n = day1.get("day", 1)
        ticks = day1.get("ticks", [])

        print(f"\n===== 第 {day_n} 天 行動序列 =====")
        for code in codes:
            char = self.manager.get_character(code)
            print(f"\n--- {char.name}（{code}）---")
            print(f"{'時間':6s} | {'行動':10s} | {'位置':12s} | {'模式':10s}")
            print("-" * 50)
            for tick in ticks:
                time_str = tick.get("time", "??:??")
                exec_r   = tick.get("execute", {}).get(code, {})
                decide_r = tick.get("decide",  {}).get(code, {})

                action   = exec_r.get("action", "—")
                target   = exec_r.get("target", "")
                location = target if exec_r.get("action") == "前往" else ""
                if not location:
                    try:
                        location = char.current_location
                    except Exception:
                        location = "—"

                mode = decide_r.get("mode", "—")
                print(f"{time_str:6s} | {action:10s} | {location:12s} | {mode}")

        # 這個 test 永遠通過（只是印出資訊）
        self.assertTrue(True)


# ================================================================
# 執行入口
# ================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
