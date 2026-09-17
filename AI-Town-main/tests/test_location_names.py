# ================================================================
# tests/test_location_names.py
# 驗證位置命名統一重構後所有地點名稱正確
# ================================================================

import json
import os
import sys
import unittest

# 確保可以 import 專案根目錄下的套件
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 舊地點名稱（不應再出現）
OLD_NAMES = {
    "公寓三樓", "公寓二樓", "公寓一樓",
    "獨棟房子 2", "獨棟房子",
    "咖啡廳後場", "咖啡廳",
    "公園", "附近街道",
    "辦公桌前", "辦公區前",
}

# 新地點名稱
NEW_NAMES = {
    "A家", "B家", "C家", "D家", "E家",
    "公寓大廳",
    "咖啡店", "咖啡店後場",
    "超市", "超市附近",
    "餐廳",
    "辦公室",
    "公司附近",
    "廣場", "街道",
}

AI_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "AI_Data"
)


# ================================================================
# 測試情境 1：VALID_LOCATIONS 使用新名稱
# ================================================================

class TestValidLocations(unittest.TestCase):
    """測試情境 1：VALID_LOCATIONS 使用新名稱"""

    def setUp(self):
        from config.action_list import VALID_LOCATIONS
        self.locs = VALID_LOCATIONS

    def test_contains_new_names(self):
        """VALID_LOCATIONS 應包含 A家、B家、咖啡店、廣場"""
        for name in ("A家", "B家", "咖啡店", "廣場"):
            self.assertIn(name, self.locs,
                          f"VALID_LOCATIONS 缺少新名稱: {name}")

    def test_not_contains_old_names(self):
        """VALID_LOCATIONS 不應包含舊地點名稱"""
        for old in OLD_NAMES:
            self.assertNotIn(old, self.locs,
                             f"VALID_LOCATIONS 仍含舊名稱: {old}")

    def test_all_expected_new_locations(self):
        """VALID_LOCATIONS 應為指定的 15 個新名稱"""
        expected = [
            "A家", "B家", "C家", "D家", "E家",
            "公寓大廳",
            "咖啡店", "咖啡店後場",
            "超市", "超市附近",
            "餐廳", "辦公室", "公司附近",
            "廣場", "街道",
        ]
        self.assertEqual(sorted(self.locs), sorted(expected))


# ================================================================
# 測試情境 2：ACTION_TABLE 中沒有舊辦公室名稱
# ================================================================

class TestActionTable(unittest.TestCase):
    """測試情境 2：ACTION_TABLE 中沒有舊辦公室名稱"""

    def setUp(self):
        from config.action_list import ACTION_TABLE
        self.locations = [entry["location"] for entry in ACTION_TABLE]

    def test_no_old_office_names(self):
        """ACTION_TABLE 不應含 '辦公桌前' 和 '辦公區前'"""
        for old in ("辦公桌前", "辦公區前"):
            self.assertNotIn(old, self.locations,
                             f"ACTION_TABLE 仍含舊辦公室名稱: {old}")

    def test_has_office(self):
        """ACTION_TABLE 中工作類行動應使用 '辦公室'"""
        office_entries = [
            e for e in self._get_action_table()
            if "工作" in e["name"]
        ]
        for e in office_entries:
            self.assertEqual(e["location"], "辦公室",
                             f"ACTION_TABLE id={e['id']} 的 location 應為辦公室")

    def _get_action_table(self):
        from config.action_list import ACTION_TABLE
        return ACTION_TABLE


# ================================================================
# 測試情境 3：CHARACTER_HOME_LOCATION 值都是新名稱
# ================================================================

class TestCharacterHomeLocation(unittest.TestCase):
    """測試情境 3：CHARACTER_HOME_LOCATION 值都是新名稱"""

    def setUp(self):
        from config.action_list import CHARACTER_HOME_LOCATION
        self.home = CHARACTER_HOME_LOCATION

    def test_all_values_are_new_names(self):
        """CHARACTER_HOME_LOCATION 的每個值應為 A家/B家/C家/D家/E家"""
        valid_homes = {"A家", "B家", "C家", "D家", "E家"}
        for char, loc in self.home.items():
            self.assertIn(loc, valid_homes,
                          f"角色 {char} 的家 '{loc}' 不在新名稱清單中")

    def test_no_old_names_in_values(self):
        """CHARACTER_HOME_LOCATION 的值不應含任何舊地點名稱"""
        for char, loc in self.home.items():
            self.assertNotIn(loc, OLD_NAMES,
                             f"角色 {char} 的家仍為舊名稱: {loc}")


# ================================================================
# 測試情境 4：schedule_templates 中無舊地點名稱
# ================================================================

class TestScheduleTemplates(unittest.TestCase):
    """測試情境 4：schedule_templates 中無舊地點名稱"""

    def _get_all_template_locations(self):
        from config.schedule_templates import SCHEDULE_TEMPLATES
        locs = []
        for role, template in SCHEDULE_TEMPLATES.items():
            for slot in template:
                locs.append((role, slot.get("location", "")))
        return locs

    def test_no_old_names_in_templates(self):
        """所有 SCHEDULE_TEMPLATES 中的 location 不應含舊地點名稱"""
        for role, loc in self._get_all_template_locations():
            self.assertNotIn(loc, OLD_NAMES,
                             f"SCHEDULE_TEMPLATES['{role}'] 仍含舊名稱: {loc}")

    def test_no_old_apartment_names(self):
        """範本不應含 公寓三樓/公寓二樓/公寓一樓/獨棟房子/獨棟房子 2"""
        old_apartment = {"公寓三樓", "公寓二樓", "公寓一樓", "獨棟房子", "獨棟房子 2"}
        for role, loc in self._get_all_template_locations():
            self.assertNotIn(loc, old_apartment,
                             f"SCHEDULE_TEMPLATES['{role}'] 仍含舊住宅名稱: {loc}")

    def test_no_old_cafe_names(self):
        """範本不應含 咖啡廳/咖啡廳後場"""
        old_cafe = {"咖啡廳", "咖啡廳後場"}
        for role, loc in self._get_all_template_locations():
            self.assertNotIn(loc, old_cafe,
                             f"SCHEDULE_TEMPLATES['{role}'] 仍含舊咖啡廳名稱: {loc}")


# ================================================================
# 測試情境 5：JSON 中 residence 欄位使用新名稱
# ================================================================

class TestJsonResidences(unittest.TestCase):
    """測試情境 5：JSON 中 residence 欄位使用新名稱"""

    def _load_all_init_jsons(self):
        data = {}
        for fname in ("A_init.json", "B_init.json", "C_init.json",
                      "D_init.json", "E_init.json"):
            fpath = os.path.join(AI_DATA_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data[fname] = json.load(f)
        return data

    def test_residence_uses_new_names(self):
        """所有 JSON 的 residence 欄位應使用新名稱"""
        valid_residences = {"A家", "B家", "C家", "D家", "E家"}
        for fname, obj in self._load_all_init_jsons().items():
            residence = obj.get("residence", "")
            self.assertIn(residence, valid_residences,
                          f"{fname} 的 residence='{residence}' 不是新名稱")

    def test_residence_not_old_names(self):
        """所有 JSON 的 residence 欄位不應含舊地點名稱"""
        for fname, obj in self._load_all_init_jsons().items():
            residence = obj.get("residence", "")
            self.assertNotIn(residence, OLD_NAMES,
                             f"{fname} 的 residence 仍為舊名稱: {residence}")

    def test_specific_residences(self):
        """驗證每個角色 JSON 的 residence 對應正確"""
        expected = {
            "A_init.json": "A家",
            "B_init.json": "B家",
            "C_init.json": "C家",
            "D_init.json": "D家",
            "E_init.json": "E家",
        }
        for fname, obj in self._load_all_init_jsons().items():
            self.assertEqual(obj["residence"], expected[fname],
                             f"{fname} 的 residence 應為 {expected[fname]}")

    def test_schedule_locations_in_jsons(self):
        """JSON schedule.slots 中的 location 不應含舊地點名稱"""
        for fname, obj in self._load_all_init_jsons().items():
            slots = obj.get("schedule", {}).get("slots", [])
            for slot in slots:
                loc = slot.get("location", "")
                self.assertNotIn(loc, OLD_NAMES,
                                 f"{fname} schedule slot location 仍含舊名稱: {loc}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
