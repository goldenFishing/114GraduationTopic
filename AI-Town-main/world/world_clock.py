# ================================================================
# world/world_clock.py
# 世界時鐘
#
# 對應 ARCHITECTURE.md §6.6.1
#
# 設計：
#   一天 20 ticks，從 06:00 開始到 02:00（凌晨）
#   每 tick 推進 60 分鐘
#   日期只在 advance_day() 時推進
#
# 主要修改：
#   1. MAX_TICKS_PER_DAY 22 → 20
#   2. 移除「凌晨 4 點強制全員睡」（改各角色 force_sleep_time）
#   3. DAY_START 從字串改為整數小時
# ================================================================

from config.world_config import (
    DAY_START_HOUR,
    MINUTES_PER_TICK,
    MAX_TICKS_PER_DAY,
)


class WorldClock:
    """虛擬世界時鐘。"""

    def __init__(self, start_hour: int = DAY_START_HOUR,
                 minutes_per_tick: int = MINUTES_PER_TICK):
        self._minutes          = start_hour * 60
        self._minutes_per_tick = minutes_per_tick
        self._day              = 1
        self._ticks_this_day   = 0

    # ────────────────────────────────────────────────────────────
    # 時間存取
    # ────────────────────────────────────────────────────────────

    @property
    def time_str(self) -> str:
        return _format_time(self._minutes)

    @property
    def time_minutes(self) -> int:
        return self._minutes

    @property
    def day(self) -> int:
        return self._day

    @property
    def ticks_today(self) -> int:
        return self._ticks_this_day

    # ────────────────────────────────────────────────────────────
    # 推進
    # ────────────────────────────────────────────────────────────

    def tick(self):
        """推進一格（60 分鐘），跨午夜時繞回，不自動增日。"""
        self._minutes += self._minutes_per_tick
        if self._minutes >= 24 * 60:
            self._minutes -= 24 * 60
        self._ticks_this_day += 1

    def advance_day(self):
        """所有角色入睡後呼叫：推進到下一天並重置 tick 計數。"""
        self._day            += 1
        self._minutes         = DAY_START_HOUR * 60
        self._ticks_this_day  = 0

    # ────────────────────────────────────────────────────────────
    # 場景前綴
    # ────────────────────────────────────────────────────────────

    def scene_prefix(self) -> str:
        """例如 "第3天 08:00"。"""
        return f"第{self._day}天 {self.time_str}"

    # ────────────────────────────────────────────────────────────
    # 判斷
    # ────────────────────────────────────────────────────────────

    def is_forced_sleep_time(self) -> bool:
        """
        是否已達 MAX_TICKS_PER_DAY 的 tick 上限。
        到此 manager 會強制讓所有未睡的角色入睡。
        """
        return self._ticks_this_day >= MAX_TICKS_PER_DAY

    # ────────────────────────────────────────────────────────────
    # 時間表查詢（為了 Character 用，相容舊版）
    # ────────────────────────────────────────────────────────────

    def should_trigger_slot(self, slot: dict) -> bool:
        """時間表時段是否已到達當前時間。"""
        slot_minutes = _parse_time(slot.get("time", "00:00"))
        return self._minutes >= slot_minutes


# ────────────────────────────────────────────────────────────────
# 工具
# ────────────────────────────────────────────────────────────────

def _parse_time(time_str: str) -> int:
    try:
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return DAY_START_HOUR * 60


def _format_time(minutes: int) -> str:
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"
