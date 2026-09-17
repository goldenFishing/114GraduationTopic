# ================================================================
# tests/test_world_clock.py
# world/world_clock.py 單元測試
#
# 涵蓋：
#   1. 初始化與時間屬性
#   2. tick() 時間推進與跨午夜繞回
#   3. advance_day() 日期推進
#   4. scene_prefix() 輸出格式
#   5. is_forced_sleep_time() 判斷
#   6. should_trigger_slot() 時間表查詢
#   7. _format_time / _parse_time 工具函式
# ================================================================

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from world.world_clock import WorldClock, _format_time, _parse_time


class TestWorldClockInit(unittest.TestCase):
    """測試 WorldClock 初始化。"""

    def test_default_start_hour(self):
        """預設從 DAY_START_HOUR（06:00）開始。"""
        clock = WorldClock(start_hour=6)
        self.assertEqual(clock.time_str, "06:00")

    def test_day_starts_at_1(self):
        """初始日期為第 1 天。"""
        clock = WorldClock(start_hour=6)
        self.assertEqual(clock.day, 1)

    def test_ticks_today_starts_at_0(self):
        """初始 ticks_today 為 0。"""
        clock = WorldClock(start_hour=6)
        self.assertEqual(clock.ticks_today, 0)

    def test_time_minutes_property(self):
        """time_minutes 等於 start_hour * 60。"""
        clock = WorldClock(start_hour=8)
        self.assertEqual(clock.time_minutes, 8 * 60)

    def test_custom_start_hour(self):
        """自訂起始小時。"""
        clock = WorldClock(start_hour=10)
        self.assertEqual(clock.time_str, "10:00")

    def test_custom_minutes_per_tick(self):
        """自訂每 tick 分鐘數。"""
        clock = WorldClock(start_hour=6, minutes_per_tick=30)
        clock.tick()
        self.assertEqual(clock.time_minutes, 6 * 60 + 30)


class TestWorldClockTick(unittest.TestCase):
    """測試 tick() 時間推進。"""

    def setUp(self):
        self.clock = WorldClock(start_hour=6, minutes_per_tick=60)

    def test_single_tick_advances_one_hour(self):
        """一次 tick 推進 60 分鐘 (07:00)。"""
        self.clock.tick()
        self.assertEqual(self.clock.time_str, "07:00")

    def test_multiple_ticks(self):
        """多次 tick 累計推進。"""
        for _ in range(4):
            self.clock.tick()
        self.assertEqual(self.clock.time_str, "10:00")

    def test_ticks_today_increments(self):
        """每次 tick 後 ticks_today 加 1。"""
        self.clock.tick()
        self.assertEqual(self.clock.ticks_today, 1)
        self.clock.tick()
        self.assertEqual(self.clock.ticks_today, 2)

    def test_tick_midnight_wraps(self):
        """跨午夜時間繞回（23:00 + 60min → 00:00）。"""
        clock = WorldClock(start_hour=23, minutes_per_tick=60)
        clock.tick()
        self.assertEqual(clock.time_str, "00:00")

    def test_tick_past_midnight_wraps(self):
        """22:00 + 3 ticks → 01:00（跨午夜後 01:00）。"""
        clock = WorldClock(start_hour=22, minutes_per_tick=60)
        for _ in range(3):
            clock.tick()
        self.assertEqual(clock.time_str, "01:00")

    def test_tick_does_not_advance_day(self):
        """tick() 不自動增加日數。"""
        initial_day = self.clock.day
        for _ in range(25):
            self.clock.tick()
        self.assertEqual(self.clock.day, initial_day)

    def test_20_ticks_from_6am(self):
        """從 06:00 tick 20 次 → 02:00（隔天凌晨）。"""
        for _ in range(20):
            self.clock.tick()
        self.assertEqual(self.clock.time_str, "02:00")


class TestWorldClockAdvanceDay(unittest.TestCase):
    """測試 advance_day() 日期推進與重置。"""

    def setUp(self):
        self.clock = WorldClock(start_hour=6, minutes_per_tick=60)

    def test_advance_day_increments_day(self):
        """advance_day() 使日期 +1。"""
        self.clock.advance_day()
        self.assertEqual(self.clock.day, 2)

    def test_advance_day_resets_time_to_start(self):
        """advance_day() 重置時間為 DAY_START_HOUR。"""
        for _ in range(5):
            self.clock.tick()
        self.clock.advance_day()
        self.assertEqual(self.clock.time_str, "06:00")

    def test_advance_day_resets_ticks_today(self):
        """advance_day() 重置 ticks_today 為 0。"""
        for _ in range(5):
            self.clock.tick()
        self.clock.advance_day()
        self.assertEqual(self.clock.ticks_today, 0)

    def test_multiple_advance_days(self):
        """多次 advance_day() 累計天數。"""
        for _ in range(3):
            self.clock.advance_day()
        self.assertEqual(self.clock.day, 4)


class TestWorldClockScenePrefix(unittest.TestCase):
    """測試 scene_prefix() 格式。"""

    def test_scene_prefix_format(self):
        """scene_prefix 格式為 '第N天 HH:MM'。"""
        clock = WorldClock(start_hour=8)
        prefix = clock.scene_prefix()
        self.assertEqual(prefix, "第1天 08:00")

    def test_scene_prefix_after_advance(self):
        """第 3 天 10:00 的 scene_prefix。"""
        clock = WorldClock(start_hour=6, minutes_per_tick=60)
        clock.advance_day()
        clock.advance_day()
        for _ in range(4):
            clock.tick()
        self.assertEqual(clock.scene_prefix(), "第3天 10:00")

    def test_scene_prefix_midnight(self):
        """午夜後 scene_prefix 含 '00:00'。"""
        clock = WorldClock(start_hour=23, minutes_per_tick=60)
        clock.tick()
        self.assertIn("00:00", clock.scene_prefix())


class TestWorldClockIsForcedSleepTime(unittest.TestCase):
    """測試 is_forced_sleep_time() 判斷。"""

    def test_not_forced_sleep_at_start(self):
        """剛初始化時不在強制睡眠時間。"""
        clock = WorldClock(start_hour=6, minutes_per_tick=60)
        self.assertFalse(clock.is_forced_sleep_time())

    def test_forced_sleep_after_max_ticks(self):
        """達到 MAX_TICKS_PER_DAY 後 is_forced_sleep_time() 為 True。"""
        from config.world_config import MAX_TICKS_PER_DAY
        clock = WorldClock(start_hour=6, minutes_per_tick=60)
        for _ in range(MAX_TICKS_PER_DAY):
            clock.tick()
        self.assertTrue(clock.is_forced_sleep_time())

    def test_just_before_max_ticks(self):
        """未達 MAX_TICKS_PER_DAY 時為 False。"""
        from config.world_config import MAX_TICKS_PER_DAY
        clock = WorldClock(start_hour=6, minutes_per_tick=60)
        for _ in range(MAX_TICKS_PER_DAY - 1):
            clock.tick()
        self.assertFalse(clock.is_forced_sleep_time())

    def test_forced_sleep_resets_after_advance_day(self):
        """advance_day() 後 is_forced_sleep_time() 重置為 False。"""
        from config.world_config import MAX_TICKS_PER_DAY
        clock = WorldClock(start_hour=6, minutes_per_tick=60)
        for _ in range(MAX_TICKS_PER_DAY):
            clock.tick()
        clock.advance_day()
        self.assertFalse(clock.is_forced_sleep_time())


class TestWorldClockShouldTriggerSlot(unittest.TestCase):
    """測試 should_trigger_slot() 時間表觸發判斷。"""

    def setUp(self):
        self.clock = WorldClock(start_hour=8, minutes_per_tick=60)

    def test_slot_at_current_time_triggers(self):
        """時間表時段等於當前時間 → 觸發。"""
        slot = {"time": "08:00", "action": "工作"}
        self.assertTrue(self.clock.should_trigger_slot(slot))

    def test_slot_before_current_time_triggers(self):
        """時間表時段早於當前時間 → 觸發。"""
        slot = {"time": "07:00", "action": "起床"}
        self.assertTrue(self.clock.should_trigger_slot(slot))

    def test_slot_after_current_time_not_triggered(self):
        """時間表時段晚於當前時間 → 不觸發。"""
        slot = {"time": "09:00", "action": "上班"}
        self.assertFalse(self.clock.should_trigger_slot(slot))

    def test_slot_without_time_defaults_safely(self):
        """缺少 time 欄位的時間表時段不崩潰。"""
        slot = {"action": "休息"}
        # 無論結果為何，不應拋出例外
        result = self.clock.should_trigger_slot(slot)
        self.assertIsInstance(result, bool)


class TestFormatTime(unittest.TestCase):
    """測試 _format_time() 工具函式。"""

    def test_zero_minutes(self):
        self.assertEqual(_format_time(0), "00:00")

    def test_six_am(self):
        self.assertEqual(_format_time(360), "06:00")

    def test_noon(self):
        self.assertEqual(_format_time(720), "12:00")

    def test_midnight(self):
        self.assertEqual(_format_time(1440), "00:00")

    def test_one_am(self):
        self.assertEqual(_format_time(60), "01:00")

    def test_two_am(self):
        self.assertEqual(_format_time(120), "02:00")

    def test_with_minutes(self):
        self.assertEqual(_format_time(630), "10:30")


class TestParseTime(unittest.TestCase):
    """測試 _parse_time() 工具函式。"""

    def test_parse_six_am(self):
        self.assertEqual(_parse_time("06:00"), 360)

    def test_parse_midnight(self):
        self.assertEqual(_parse_time("00:00"), 0)

    def test_parse_noon(self):
        self.assertEqual(_parse_time("12:00"), 720)

    def test_parse_two_am(self):
        self.assertEqual(_parse_time("02:00"), 120)

    def test_parse_with_minutes(self):
        self.assertEqual(_parse_time("10:30"), 630)

    def test_parse_invalid_returns_default(self):
        """無法解析的時間字串回傳預設值（不崩潰）。"""
        result = _parse_time("not_a_time")
        self.assertIsInstance(result, int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
