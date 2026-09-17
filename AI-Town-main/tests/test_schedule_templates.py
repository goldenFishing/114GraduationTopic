# ================================================================
# tests/test_schedule_templates.py
# config/schedule_templates.py 模組的單元測試
# ================================================================

import sys
import os
import copy
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.schedule_templates import (
    COFFEE_BARISTA_TEMPLATE,
    SUPERMARKET_TEMPLATE,
    OFFICE_WORKER_TEMPLATE,
    COMPANY_BOSS_TEMPLATE,
    CHEF_TEMPLATE,
    RESTAURANT_STAFF_TEMPLATE,
    LAWYER_TEMPLATE,
    ENGINEER_TEMPLATE,
    SCHEDULE_TEMPLATES,
    REQUIRED_SLOTS,
    get_template,
    get_required_slots,
    validate_schedule,
)

# 合法的 action 集合（從 action_list 取得以確保一致性）
_REQUIRED_SLOT_KEYS = {"time", "action", "location", "type", "completed"}


def _check_slot_structure(test_case, slot, context=""):
    """驗證單一時段的資料結構正確性。"""
    test_case.assertIsInstance(slot, dict, f"{context} slot 應為 dict")
    for key in _REQUIRED_SLOT_KEYS:
        test_case.assertIn(key, slot, f"{context} slot 缺少欄位 '{key}'")
    test_case.assertIsInstance(slot["time"], str, f"{context} time 應為 str")
    test_case.assertIsInstance(slot["action"], str, f"{context} action 應為 str")
    test_case.assertIsInstance(slot["location"], str, f"{context} location 應為 str")
    test_case.assertEqual(slot["type"], "fixed", f"{context} type 應為 'fixed'")
    test_case.assertFalse(slot["completed"], f"{context} completed 預設應為 False")


def _has_action(template, action_name):
    return any(slot["action"] == action_name for slot in template)


class TestTemplateStructure(unittest.TestCase):
    """測試所有範本的結構完整性與欄位格式。"""

    def _test_template_structure(self, template, name):
        """通用結構驗證輔助方法。"""
        self.assertIsInstance(template, list, f"{name} 應為 list")
        self.assertGreater(len(template), 0, f"{name} 不應為空")
        for i, slot in enumerate(template):
            _check_slot_structure(self, slot, context=f"{name}[{i}]")

    def test_coffee_barista_structure(self):
        """COFFEE_BARISTA_TEMPLATE 的每個時段結構應正確。"""
        self._test_template_structure(COFFEE_BARISTA_TEMPLATE, "COFFEE_BARISTA_TEMPLATE")

    def test_supermarket_structure(self):
        """SUPERMARKET_TEMPLATE 的每個時段結構應正確。"""
        self._test_template_structure(SUPERMARKET_TEMPLATE, "SUPERMARKET_TEMPLATE")

    def test_office_worker_structure(self):
        """OFFICE_WORKER_TEMPLATE 的每個時段結構應正確。"""
        self._test_template_structure(OFFICE_WORKER_TEMPLATE, "OFFICE_WORKER_TEMPLATE")

    def test_company_boss_structure(self):
        """COMPANY_BOSS_TEMPLATE 的每個時段結構應正確。"""
        self._test_template_structure(COMPANY_BOSS_TEMPLATE, "COMPANY_BOSS_TEMPLATE")

    def test_chef_structure(self):
        """CHEF_TEMPLATE 的每個時段結構應正確。"""
        self._test_template_structure(CHEF_TEMPLATE, "CHEF_TEMPLATE")


class TestTemplateRequiredActions(unittest.TestCase):
    """測試每個職業範本是否包含必要的行動時段（起床與睡覺）。"""

    def _assert_has_sleep_and_wake(self, template, name):
        self.assertTrue(_has_action(template, "起床"),
                        f"{name} 應包含「起床」時段")
        self.assertTrue(_has_action(template, "睡覺"),
                        f"{name} 應包含「睡覺」時段")

    def test_barista_has_required_actions(self):
        """咖啡師範本應包含起床、賣咖啡、睡覺。"""
        self._assert_has_sleep_and_wake(COFFEE_BARISTA_TEMPLATE, "COFFEE_BARISTA_TEMPLATE")
        self.assertTrue(_has_action(COFFEE_BARISTA_TEMPLATE, "賣咖啡"),
                        "咖啡師範本應包含「賣咖啡」")

    def test_supermarket_has_required_actions(self):
        """超市員工範本應包含起床、收銀、睡覺。"""
        self._assert_has_sleep_and_wake(SUPERMARKET_TEMPLATE, "SUPERMARKET_TEMPLATE")
        self.assertTrue(_has_action(SUPERMARKET_TEMPLATE, "收銀"),
                        "超市員工範本應包含「收銀」")

    def test_office_worker_has_required_actions(self):
        """辦公室員工範本應包含起床、工作、睡覺。"""
        self._assert_has_sleep_and_wake(OFFICE_WORKER_TEMPLATE, "OFFICE_WORKER_TEMPLATE")
        self.assertTrue(_has_action(OFFICE_WORKER_TEMPLATE, "工作"),
                        "辦公室員工範本應包含「工作」")

    def test_chef_has_required_actions(self):
        """廚師範本應包含起床、煮飯、睡覺。"""
        self._assert_has_sleep_and_wake(CHEF_TEMPLATE, "CHEF_TEMPLATE")
        self.assertTrue(_has_action(CHEF_TEMPLATE, "煮飯"),
                        "廚師範本應包含「煮飯」")


class TestScheduleTemplatesDict(unittest.TestCase):
    """測試 SCHEDULE_TEMPLATES 字典的完整性。"""

    def test_schedule_templates_has_eight_roles(self):
        """SCHEDULE_TEMPLATES 應包含 8 個職業。"""
        self.assertEqual(len(SCHEDULE_TEMPLATES), 8)

    def test_schedule_templates_has_main_roles(self):
        """SCHEDULE_TEMPLATES 應包含 5 個主要角色的職業。"""
        for role in ["咖啡師", "超市員工", "辦公室員工", "公司老闆", "廚師"]:
            self.assertIn(role, SCHEDULE_TEMPLATES,
                          f"SCHEDULE_TEMPLATES 缺少職業：{role}")

    def test_all_templates_are_lists(self):
        """SCHEDULE_TEMPLATES 中的每個值應為 list。"""
        for role, template in SCHEDULE_TEMPLATES.items():
            self.assertIsInstance(template, list,
                                  f"SCHEDULE_TEMPLATES['{role}'] 應為 list")


class TestRequiredSlots(unittest.TestCase):
    """測試 REQUIRED_SLOTS 字典的正確性。"""

    def test_required_slots_keys_match_templates(self):
        """REQUIRED_SLOTS 的鍵應與 SCHEDULE_TEMPLATES 的鍵一致。"""
        self.assertSetEqual(set(REQUIRED_SLOTS.keys()), set(SCHEDULE_TEMPLATES.keys()))

    def test_all_required_slots_contain_sleep_wake(self):
        """每個職業的 REQUIRED_SLOTS 應包含「起床」與「睡覺」。"""
        for role, slots in REQUIRED_SLOTS.items():
            self.assertIn("起床", slots, f"{role} 的 REQUIRED_SLOTS 缺少「起床」")
            self.assertIn("睡覺", slots, f"{role} 的 REQUIRED_SLOTS 缺少「睡覺」")

    def test_barista_required_slots(self):
        """咖啡師的必要時段應包含「賣咖啡」。"""
        self.assertIn("賣咖啡", REQUIRED_SLOTS["咖啡師"])

    def test_chef_required_slots(self):
        """廚師的必要時段應包含「煮飯」。"""
        self.assertIn("煮飯", REQUIRED_SLOTS["廚師"])


class TestGetTemplate(unittest.TestCase):
    """測試 get_template() 工具函式。"""

    def test_get_known_template(self):
        """get_template('咖啡師') 應回傳與 COFFEE_BARISTA_TEMPLATE 相同內容。"""
        result = get_template("咖啡師")
        self.assertEqual(result, COFFEE_BARISTA_TEMPLATE)

    def test_get_template_returns_deep_copy(self):
        """get_template() 應回傳深拷貝，修改不影響原始資料。"""
        result = get_template("廚師")
        result[0]["action"] = "MODIFIED"
        original_first_action = CHEF_TEMPLATE[0]["action"]
        self.assertNotEqual(original_first_action, "MODIFIED",
                            "get_template 應回傳深拷貝，不應修改原始資料")

    def test_get_unknown_role_fallback(self):
        """get_template() 對未知職業應 fallback 回傳辦公室員工範本。"""
        result = get_template("不存在的職業")
        self.assertEqual(result, OFFICE_WORKER_TEMPLATE)

    def test_get_template_returns_list(self):
        """get_template() 應回傳 list。"""
        for role in SCHEDULE_TEMPLATES:
            result = get_template(role)
            self.assertIsInstance(result, list, f"get_template('{role}') 應回傳 list")


class TestGetRequiredSlots(unittest.TestCase):
    """測試 get_required_slots() 工具函式。"""

    def test_get_known_role_slots(self):
        """get_required_slots('廚師') 應回傳包含「煮飯」的清單。"""
        slots = get_required_slots("廚師")
        self.assertIn("煮飯", slots)

    def test_get_unknown_role_fallback(self):
        """get_required_slots() 對未知職業應 fallback 回傳含「起床」「睡覺」的清單。"""
        slots = get_required_slots("外星人")
        self.assertIn("起床", slots)
        self.assertIn("睡覺", slots)

    def test_returns_list(self):
        """get_required_slots() 應回傳 list。"""
        result = get_required_slots("律師")
        self.assertIsInstance(result, list)


class TestValidateSchedule(unittest.TestCase):
    """測試 validate_schedule() 工具函式。"""

    def test_valid_schedule_passes(self):
        """完整的時間表應通過驗證。"""
        schedule = copy.deepcopy(COFFEE_BARISTA_TEMPLATE)
        is_valid, missing = validate_schedule(schedule, "咖啡師")
        self.assertTrue(is_valid)
        self.assertEqual(missing, [])

    def test_missing_sleep_fails(self):
        """缺少「睡覺」時段的時間表應驗證失敗。"""
        schedule = [s for s in copy.deepcopy(OFFICE_WORKER_TEMPLATE)
                    if s["action"] != "睡覺"]
        is_valid, missing = validate_schedule(schedule, "辦公室員工")
        self.assertFalse(is_valid)
        self.assertIn("睡覺", missing)

    def test_missing_core_work_fails(self):
        """缺少核心工作時段的時間表應驗證失敗。"""
        schedule = [s for s in copy.deepcopy(SUPERMARKET_TEMPLATE)
                    if s["action"] != "收銀"]
        is_valid, missing = validate_schedule(schedule, "超市員工")
        self.assertFalse(is_valid)
        self.assertIn("收銀", missing)

    def test_unknown_role_uses_fallback_validation(self):
        """未知職業使用 fallback 驗證，含起床睡覺的時間表應通過。"""
        schedule = [
            {"time": "07:00", "action": "起床",   "location": "公寓大廳", "type": "fixed", "completed": False},
            {"time": "23:00", "action": "睡覺",   "location": "公寓大廳", "type": "fixed", "completed": False},
        ]
        is_valid, missing = validate_schedule(schedule, "未知職業")
        self.assertTrue(is_valid)
        self.assertEqual(missing, [])

    def test_returns_tuple(self):
        """validate_schedule() 應回傳 (bool, list) tuple。"""
        result = validate_schedule(CHEF_TEMPLATE, "廚師")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
