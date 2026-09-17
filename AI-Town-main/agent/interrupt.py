# ================================================================
# agent/interrupt.py
# 中斷處理器
#
# 對應 ARCHITECTURE.md §6.3.4 + §9.5
#
# 中斷流程：
#   YOLO 偵測到變化 → 寫入該角色的 interrupt_queue
#   下一 tick 開始 → Manager 檢查 queue
#   有事件 → InterruptHandler.process_interrupt()
#     ├ 比較事件強度 vs 當前行動鎖
#     ├ 不可中斷 → 繼續原行動，但記錄事件到 STM
#     └ 可中斷 → Markov 重算 → 可能改變行動
#
# 行動鎖等級（config/world_config.INTERRUPT_LOCK_LEVELS）：
#   0：容易中斷（散步、移動、休閒）
#   1：重要才中斷（工作類）
#   2：不可中斷（對話、睡覺）
#
# YOLO 事件強度：
#   弱：物件變化 → 可中斷 lock=0
#   中：新人出現 → 可中斷 lock≤1
#   強：緊急/未預期 → 可中斷 lock≤2，但對話例外
#
# 誰會調用：
#   agent/manager.py — 每 tick 開始時檢查中斷
# ================================================================

from collections import defaultdict

from config.world_config import INTERRUPT_LOCK_LEVELS


# ================================================================
# 中斷事件資料結構
# ================================================================
#
# {
#   "type":      "yolo_change" | "external_input",
#   "strength":  "weak" | "medium" | "strong",
#   "data":      {...},
#   "timestamp": "HH:MM"
# }


# 強度 → 最大可中斷的鎖等級
_STRENGTH_TO_MAX_LOCK = {
    "weak":    0,
    "medium":  1,
    "strong":  2,
}


# ================================================================
# InterruptHandler
# ================================================================

class InterruptHandler:
    """
    中斷佇列管理 + 中斷決策邏輯。
    所有角色共用一個 handler 實例（manager 持有）。
    """

    def __init__(self):
        # {code: list[event]} 每個角色獨立佇列
        self._queues = defaultdict(list)

    # ────────────────────────────────────────────────────────────
    # A. 佇列操作（YOLO 寫入、tick 消費）
    # ────────────────────────────────────────────────────────────

    def push(self, code: str, event: dict):
        """YOLO / 感知層寫入中斷事件。"""
        self._queues[code].append(event)

    def pop_all(self, code: str) -> list:
        """取出該角色所有累積事件並清空。"""
        events = self._queues[code]
        self._queues[code] = []
        return events

    def has_events(self, code: str) -> bool:
        return len(self._queues[code]) > 0

    def clear_all(self):
        """清空所有佇列（例如所有角色入睡後）。"""
        self._queues.clear()

    # ────────────────────────────────────────────────────────────
    # B. 決策邏輯
    # ────────────────────────────────────────────────────────────

    def should_interrupt(self, current_action: str, event: dict) -> bool:
        """
        判斷事件能否中斷當前行動。

        current_action : 角色當前正在做的事
        event          : 中斷事件 dict

        規則：
          1. 對話中（lock=2）+ 強事件 → 不可中斷（對話例外）
          2. 否則：事件強度可中斷的最大 lock ≥ current_lock → 可中斷
        """
        current_lock  = INTERRUPT_LOCK_LEVELS.get(current_action, 0)
        strength      = event.get("strength", "weak")
        max_lock      = _STRENGTH_TO_MAX_LOCK.get(strength, 0)

        # 對話例外：對話中即使強事件也不中斷
        if current_action == "對話":
            return False

        # 睡覺中只有強事件才能中斷（例如緊急）
        if current_action == "睡覺":
            return strength == "strong"

        return max_lock >= current_lock

    # ────────────────────────────────────────────────────────────
    # C. 完整中斷處理
    # ────────────────────────────────────────────────────────────

    def process_interrupts(self, code: str, current_action: str) -> dict:
        """
        處理該角色所有累積的中斷事件，決定整體影響。

        參數：
          code          : 角色代號
          current_action: 當前行動

        回傳：
          {
            "should_interrupt": bool,    # 是否應該中斷重新決策
            "triggered_event":  dict,    # 觸發中斷的那個事件（最強的）
            "all_events":       list,    # 全部累積事件（不論是否中斷都記到 STM）
          }
        """
        events = self.pop_all(code)
        if not events:
            return {
                "should_interrupt": False,
                "triggered_event":  None,
                "all_events":       [],
            }

        # 找出強度最高的事件
        strongest = max(events,
                         key=lambda e: _STRENGTH_TO_MAX_LOCK.get(
                             e.get("strength", "weak"), 0))

        should_break = self.should_interrupt(current_action, strongest)

        return {
            "should_interrupt": should_break,
            "triggered_event":  strongest,
            "all_events":       events,
        }
