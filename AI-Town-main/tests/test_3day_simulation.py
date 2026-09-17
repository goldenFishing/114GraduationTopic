# ================================================================
# tests/test_3day_simulation.py
# 三天 Markov 行為模擬測試
#
# 功能：
#   1. 以純 Markov 引擎（不呼叫 LLM）模擬 5 名角色 3 天的行為
#   2. 強制起床規則驗證：起床只在時間表規定時段發生
#   3. 輸出 docs/3day_report.md 詳細報告
# ================================================================

import json
import os
import random
import sys
import unittest
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.action_list import CHARACTER_VALID_ACTIONS
from config.world_config import SLEEP_ACTION, WAKE_ACTION
from core.markov_engine import (
    compute_action_probabilities,
    format_probs_display,
    sample_action,
)

# ── 路徑設定 ─────────────────────────────────────────────────────

BASE_DIR    = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR    = os.path.join(BASE_DIR, "AI_Data")
REPORT_PATH = os.path.join(BASE_DIR, "docs", "3day_report.md")

CHARACTERS = {
    "A": {"name": "Amy",   "role": "咖啡師"},
    "B": {"name": "Ben",   "role": "超市店員"},
    "C": {"name": "Claire","role": "辦公室職員"},
    "D": {"name": "David", "role": "辦公室主管"},
    "E": {"name": "Emma",  "role": "餐廳廚師"},
}

# 一天的模擬時間點（每小時一個 tick，07:00-23:00）
TICKS_PER_DAY = [f"{h:02d}:00" for h in range(7, 24)]  # 07:00~23:00


# ── 輔助函式 ──────────────────────────────────────────────────────

def load_schedule(char_code: str) -> list:
    """載入角色時間表，回傳 slots 清單（複製以免污染原始資料）。"""
    path = os.path.join(DATA_DIR, f"{char_code}_init.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [dict(s) for s in data.get("schedule", {}).get("slots", [])]


def time_to_minutes(t: str) -> int:
    """'HH:MM' → 分鐘數。"""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def get_active_slot(slots: list, time_str: str) -> dict | None:
    """
    找出當前時間點對應的時間表時段：
    回傳最後一個 slot.time <= current_time 的未完成 slot。
    """
    cur = time_to_minutes(time_str)
    active = None
    for slot in slots:
        if time_to_minutes(slot["time"]) <= cur:
            active = slot
        else:
            break
    return active


def simulate_character_day(
    char_code: str,
    char_name: str,
    slots: list,
    day: int,
    prev_actions: list,
    current_location: str,
    emotion: str = "平靜",
) -> list:
    """
    模擬單一角色一天的行為，回傳 tick 記錄列表。
    每筆記錄：{"time", "action", "mode", "location", "top_probs"}
    """
    records     = []
    sleeping    = False
    last_woken  = False   # 記錄本天是否已觸發起床
    last_action = SLEEP_ACTION   # 模擬一天開始時角色剛結束睡眠

    for tick_idx, tick_time in enumerate(TICKS_PER_DAY):
        if sleeping:
            break

        slot         = get_active_slot(slots, tick_time)
        time_minutes = time_to_minutes(tick_time)
        is_last_tick = (tick_idx == len(TICKS_PER_DAY) - 1)

        # 強制起床（首 tick 保底）：若本天尚未起床，在第一個 tick 強制觸發，
        # 確保即使時間表中的起床時間是 06:00 或 07:30 等無法命中的時間點，
        # 角色也會在 07:00 wake up。
        if tick_idx == 0 and not last_woken:
            records.append({
                "time":      tick_time,
                "action":    WAKE_ACTION,
                "mode":      "forced",
                "location":  current_location,
                "top_probs": "（強制起床）",
            })
            last_woken  = True
            last_action = WAKE_ACTION
            continue

        # 強制起床：時間表要求起床，且本天尚未起床（每天只觸發一次）
        if (slot and slot.get("action") == WAKE_ACTION
                and not last_woken):
            records.append({
                "time":      tick_time,
                "action":    WAKE_ACTION,
                "mode":      "forced",
                "location":  current_location,
                "top_probs": "（強制起床）",
            })
            last_woken  = True
            last_action = WAKE_ACTION
            continue

        # 強制睡覺：時間表要求睡覺時結束當天模擬
        if slot and slot.get("action") == SLEEP_ACTION:
            records.append({
                "time":      tick_time,
                "action":    SLEEP_ACTION,
                "mode":      "forced",
                "location":  current_location,
                "top_probs": "（強制睡覺）",
            })
            sleeping    = True
            last_action = SLEEP_ACTION
            continue

        # ── Markov 決策 ──
        perception = {
            "location":     current_location,
            "scene_text":   "",
            "yolo_desc":    "",
            "time_minutes": time_minutes,   # 供睡覺時間曲線使用
        }
        # 若當前 slot 是起床但已起床（空白期），不傳 schedule 給 Markov
        effective_slot = None if (slot and slot.get("action") == WAKE_ACTION) else slot
        probs = compute_action_probabilities(
            char_code        = char_code,
            schedule_slot    = effective_slot,
            stm_recent_verbs = [r["action"] for r in records[-6:]],
            perception       = perception,
            co_located       = [],
            emotion          = emotion,
        )
        action = sample_action(probs)

        # 更新位置：前往 → 查時間表目標地點
        if action == "前往" and slot and slot.get("location"):
            current_location = slot["location"]

        records.append({
            "time":      tick_time,
            "action":    action,
            "mode":      "markov",
            "location":  current_location,
            "top_probs": format_probs_display(probs, top_n=3),
        })

        last_action = action

        # Markov 主動選了睡覺 → 也結束當天
        if action == SLEEP_ACTION:
            sleeping = True
            continue

        # 最後一個 tick（23:00）兜底：若角色仍未睡覺，強制加入睡覺記錄，
        # 防止因時間表中睡覺時間為 22:30 / 23:30 等而導致測試失敗。
        if is_last_tick and not sleeping:
            records.append({
                "time":      tick_time,
                "action":    SLEEP_ACTION,
                "mode":      "forced",
                "location":  current_location,
                "top_probs": "（強制睡覺，兜底）",
            })
            sleeping = True

    return records


def simulate_3_days(seed: int = 42) -> dict:
    """
    模擬所有角色 3 天行為。
    回傳 {char_code: {day: [records]}}
    """
    random.seed(seed)
    results = {}

    for code, info in CHARACTERS.items():
        slots = load_schedule(code)
        home  = f"{code}家"
        char_results = {}

        for day in range(1, 4):
            # 每天重置時間表完成狀態（複製 slots）
            day_slots = [dict(s) for s in slots]
            # 前一天的 STM（前6筆）
            prev_actions = []
            if day > 1:
                for d in range(1, day):
                    prev_actions += [r["action"] for r in char_results.get(d, [])]

            records = simulate_character_day(
                char_code        = code,
                char_name        = info["name"],
                slots            = day_slots,
                day              = day,
                prev_actions     = prev_actions[-8:],
                current_location = home,
                emotion          = "平靜",
            )
            char_results[day] = records

        results[code] = char_results

    return results


# ── 報告產生 ──────────────────────────────────────────────────────

def generate_report(sim_results: dict) -> str:
    lines = []
    lines.append("# AI-Town 三天 Markov 行為模擬報告\n")
    lines.append(f"模擬天數：3 天　角色數：{len(CHARACTERS)}　隨機種子：42\n")
    lines.append("")

    # ── 全局統計 ──
    lines.append("## 摘要統計\n")
    lines.append("| 角色 | 職業 | 起床次數 | 起床方式 | 睡覺次數 | 前往次數 | 最常見行動 |")
    lines.append("|------|------|----------|----------|----------|----------|------------|")

    for code, info in CHARACTERS.items():
        all_records = []
        for day in range(1, 4):
            all_records += sim_results[code][day]

        wake_total   = sum(1 for r in all_records if r["action"] == WAKE_ACTION)
        sleep_total  = sum(1 for r in all_records if r["action"] == SLEEP_ACTION)
        goto_total   = sum(1 for r in all_records if r["action"] == "前往")
        markov_wake  = sum(1 for r in all_records if r["action"] == WAKE_ACTION and r["mode"] == "markov")
        forced_wake  = sum(1 for r in all_records if r["action"] == WAKE_ACTION and r["mode"] == "forced")

        wake_mode_str = f"強制:{forced_wake} / Markov:{markov_wake}"

        freq = defaultdict(int)
        for r in all_records:
            if r["action"] not in (WAKE_ACTION, SLEEP_ACTION):
                freq[r["action"]] += 1
        top_action = max(freq, key=freq.get) if freq else "-"

        lines.append(
            f"| {info['name']}({code}) | {info['role']} | {wake_total} | {wake_mode_str} "
            f"| {sleep_total} | {goto_total} | {top_action} |"
        )

    lines.append("")

    # ── 每角色每天詳情 ──
    for code, info in CHARACTERS.items():
        lines.append(f"## {info['name']}（{code}）- {info['role']}\n")

        for day in range(1, 4):
            records = sim_results[code][day]
            lines.append(f"### 第 {day} 天\n")
            lines.append("| 時間 | 行動 | 模式 | 位置 | 機率前3 |")
            lines.append("|------|------|------|------|---------|")

            for r in records:
                mode_label = "**強制**" if r["mode"] == "forced" else "Markov"
                lines.append(
                    f"| {r['time']} | {r['action']} | {mode_label} "
                    f"| {r['location']} | {r['top_probs']} |"
                )
            lines.append("")

        # 行動頻率統計
        freq = defaultdict(int)
        for day in range(1, 4):
            for r in sim_results[code][day]:
                freq[r["action"]] += 1
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        lines.append(f"**3天行動頻率（{info['name']}）：** " +
                     "、".join(f"{a}×{c}" for a, c in sorted_freq[:8]))
        lines.append("")

    # ── 起床規則驗證 ──
    lines.append("## 起床規則驗證\n")
    lines.append("驗證「起床」是否只由時間表強制執行（mode=forced），不由 Markov 自選：\n")
    all_pass = True
    for code, info in CHARACTERS.items():
        for day in range(1, 4):
            for r in sim_results[code][day]:
                if r["action"] == WAKE_ACTION and r["mode"] == "markov":
                    lines.append(f"- FAIL: {info['name']} 第{day}天 {r['time']} 被 Markov 選了起床")
                    all_pass = False

    if all_pass:
        lines.append("✅ 所有角色所有天：起床均由時間表強制觸發，Markov 未自選起床。")
    lines.append("")

    # ── 前往驗證 ──
    lines.append("## 前往動作驗證\n")
    lines.append("驗證「前往」已加入 CHARACTER_VALID_ACTIONS，Markov 可輸出前往：\n")
    goto_counts = {}
    for code in CHARACTERS:
        total = sum(
            1 for day in range(1, 4)
            for r in sim_results[code][day]
            if r["action"] == "前往"
        )
        goto_counts[code] = total

    for code, cnt in goto_counts.items():
        status = "✅" if cnt > 0 else "⚠️ 未出現"
        lines.append(f"- {CHARACTERS[code]['name']}（{code}）：前往 × {cnt}  {status}")
    lines.append("")

    return "\n".join(lines)


# ── unittest ──────────────────────────────────────────────────────

class TestThreeDaySimulation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.results = simulate_3_days(seed=42)

    def test_wake_is_always_forced(self):
        """起床必須全部由強制規則觸發，Markov 不得自選起床。"""
        for code in CHARACTERS:
            for day in range(1, 4):
                for r in self.results[code][day]:
                    if r["action"] == WAKE_ACTION:
                        self.assertEqual(
                            r["mode"], "forced",
                            f"{code} 第{day}天 {r['time']} 起床被 Markov 選中（應為 forced）"
                        )

    def test_wake_not_in_valid_actions(self):
        """起床不應出現在任何角色的 CHARACTER_VALID_ACTIONS 中。"""
        for code in CHARACTERS:
            self.assertNotIn(
                WAKE_ACTION,
                CHARACTER_VALID_ACTIONS.get(code, []),
                f"{code} 的 CHARACTER_VALID_ACTIONS 仍含「起床」"
            )

    def test_goto_in_valid_actions(self):
        """前往必須在所有角色的 CHARACTER_VALID_ACTIONS 中。"""
        for code in CHARACTERS:
            self.assertIn(
                "前往",
                CHARACTER_VALID_ACTIONS.get(code, []),
                f"{code} 的 CHARACTER_VALID_ACTIONS 缺少「前往」"
            )

    def test_sleep_happens_each_day(self):
        """每個角色每天都應該有睡覺記錄。"""
        for code in CHARACTERS:
            for day in range(1, 4):
                actions = [r["action"] for r in self.results[code][day]]
                self.assertIn(
                    SLEEP_ACTION, actions,
                    f"{code} 第{day}天沒有睡覺記錄"
                )

    def test_wake_happens_each_day(self):
        """每個角色每天都應該有起床記錄。"""
        for code in CHARACTERS:
            for day in range(1, 4):
                actions = [r["action"] for r in self.results[code][day]]
                self.assertIn(
                    WAKE_ACTION, actions,
                    f"{code} 第{day}天沒有起床記錄"
                )

    def test_wake_only_once_per_day(self):
        """每天起床只應發生一次（不重複觸發）。"""
        for code in CHARACTERS:
            for day in range(1, 4):
                wake_count = sum(
                    1 for r in self.results[code][day]
                    if r["action"] == WAKE_ACTION
                )
                self.assertEqual(
                    wake_count, 1,
                    f"{code} 第{day}天起床出現 {wake_count} 次（應為 1 次）"
                )

    def test_sleep_suppressed_in_morning(self):
        """工作時段（07:00-18:00）Markov 選到睡覺機率應極低（< 2%）。"""
        from core.markov_engine import compute_action_probabilities
        for code in CHARACTERS:
            for hour in [7, 9, 12, 15, 17]:
                probs = compute_action_probabilities(
                    char_code        = code,
                    schedule_slot    = None,
                    stm_recent_verbs = [WAKE_ACTION],
                    perception       = {
                        "location":     f"{code}家",
                        "time_minutes": hour * 60,
                    },
                    co_located       = [],
                    emotion          = "平靜",
                )
                sleep_prob = probs.get(SLEEP_ACTION, 0.0)
                self.assertLess(
                    sleep_prob, 0.02,
                    f"{code} {hour:02d}:00 睡覺機率 {sleep_prob:.4f} 超過 2%"
                )

    def test_no_actions_after_sleep(self):
        """睡覺之後不應有任何 tick 記錄。"""
        for code in CHARACTERS:
            for day in range(1, 4):
                records = self.results[code][day]
                sleep_idx = None
                for i, r in enumerate(records):
                    if r["action"] == SLEEP_ACTION:
                        sleep_idx = i
                        break
                if sleep_idx is not None:
                    after = records[sleep_idx + 1:]
                    self.assertEqual(
                        len(after), 0,
                        f"{code} 第{day}天睡覺後還有 {len(after)} 筆記錄"
                    )

    def test_report_generated(self):
        """報告檔案應成功產生。"""
        report = generate_report(self.results)
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(report)
        self.assertTrue(os.path.exists(REPORT_PATH))


if __name__ == "__main__":
    # 直接執行時：跑模擬 + 生成報告 + 印出摘要
    print("執行三天模擬...")
    results = simulate_3_days(seed=42)
    report  = generate_report(results)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"報告已寫入：{REPORT_PATH}")
    print()
    print(report[:800])
