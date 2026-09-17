# ================================================================
# config/schedule_templates.py
# 各職業的時間表範本
#
# 用途：
#   睡眠濃縮時模型生成隔天時間表的「底稿」。
#   模型可大幅修改範本，但要通過規則檢查（必要時段必須存在）。
#
# 流程：
#   1. agent/scheduler.py 取出該角色職業的範本
#   2. 組 prompt（個性 + LTM 摘要 + 今日事件 + 範本）
#   3. 模型生成新時間表
#   4. 規則檢查 REQUIRED_SLOTS
#   5. 通過 → 寫入；失敗 → 補必要時段或 fallback 範本
#
# 時間表格式：
#   {time, action, location, type, completed}
#   type:      "fixed"（範本來的）/ "dynamic"（模型動態插入的）
#   completed: 執行時更新
#
# 注意：
#   範本裡的「起床」與「睡覺」時段，會同步影響角色的 sleep_pattern。
#   對話不在範本中，由 Markov 路徑在同地點時自然觸發。
#
# 對應 ARCHITECTURE.md §6.1.5
# ================================================================


# ================================================================
# A. 完整職業範本（現有 5 個角色對應的職業）
# ================================================================

# ── 咖啡師（Amy）────────────────────────────────────────────────
# 早起，工作日穩定，傍晚收工，作息規律
COFFEE_BARISTA_TEMPLATE = [
    {"time": "06:00", "action": "起床",     "location": "公寓三樓",
     "type": "fixed", "completed": False},
    {"time": "07:00", "action": "前往",     "location": "咖啡廳",
     "type": "fixed", "completed": False},
    {"time": "07:30", "action": "整理店面", "location": "咖啡廳",
     "type": "fixed", "completed": False},
    {"time": "08:30", "action": "賣咖啡",   "location": "咖啡廳",
     "type": "fixed", "completed": False},
    {"time": "12:00", "action": "吃飯",     "location": "咖啡廳後場",
     "type": "fixed", "completed": False},
    {"time": "13:00", "action": "賣咖啡",   "location": "咖啡廳",
     "type": "fixed", "completed": False},
    {"time": "18:00", "action": "打烊",     "location": "咖啡廳",
     "type": "fixed", "completed": False},
    {"time": "19:00", "action": "回家",     "location": "公寓三樓",
     "type": "fixed", "completed": False},
    {"time": "22:30", "action": "睡覺",     "location": "公寓三樓",
     "type": "fixed", "completed": False},
]


# ── 超市員工（Ben）──────────────────────────────────────────────
# 標準上班族作息，輪班型工作
SUPERMARKET_TEMPLATE = [
    {"time": "07:00", "action": "起床",   "location": "公寓二樓",
     "type": "fixed", "completed": False},
    {"time": "08:30", "action": "前往",   "location": "超市",
     "type": "fixed", "completed": False},
    {"time": "09:00", "action": "補貨",   "location": "超市",
     "type": "fixed", "completed": False},
    {"time": "11:00", "action": "收銀",   "location": "超市",
     "type": "fixed", "completed": False},
    {"time": "12:30", "action": "吃飯",   "location": "超市附近",
     "type": "fixed", "completed": False},
    {"time": "14:00", "action": "收銀",   "location": "超市",
     "type": "fixed", "completed": False},
    {"time": "17:00", "action": "補貨",   "location": "超市",
     "type": "fixed", "completed": False},
    {"time": "19:00", "action": "回家",   "location": "公寓二樓",
     "type": "fixed", "completed": False},
    {"time": "23:00", "action": "睡覺",   "location": "公寓二樓",
     "type": "fixed", "completed": False},
]


# ── 辦公室員工（Claire）─────────────────────────────────────────
# 標準白領作息，朝九晚六
OFFICE_WORKER_TEMPLATE = [
    {"time": "07:30", "action": "起床",     "location": "公寓一樓",
     "type": "fixed", "completed": False},
    {"time": "08:30", "action": "前往",     "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "09:00", "action": "工作",     "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "12:00", "action": "吃飯",     "location": "公司附近",
     "type": "fixed", "completed": False},
    {"time": "13:00", "action": "工作",     "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "18:00", "action": "回家",     "location": "公寓一樓",
     "type": "fixed", "completed": False},
    {"time": "19:00", "action": "整理家裡", "location": "公寓一樓",
     "type": "fixed", "completed": False},
    {"time": "23:30", "action": "睡覺",     "location": "公寓一樓",
     "type": "fixed", "completed": False},
]


# ── 公司老闆（David）────────────────────────────────────────────
# 工時較長，習慣早上去咖啡廳買咖啡
COMPANY_BOSS_TEMPLATE = [
    {"time": "08:00", "action": "起床",   "location": "獨棟房子",
     "type": "fixed", "completed": False},
    {"time": "08:30", "action": "前往",   "location": "咖啡廳",
     "type": "fixed", "completed": False},
    {"time": "09:00", "action": "前往",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "09:30", "action": "工作",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "13:00", "action": "吃飯",   "location": "公司附近",
     "type": "fixed", "completed": False},
    {"time": "14:00", "action": "工作",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "20:00", "action": "回家",   "location": "獨棟房子",
     "type": "fixed", "completed": False},
    {"time": "00:30", "action": "睡覺",   "location": "獨棟房子",
     "type": "fixed", "completed": False},
]


# ── 廚師（Emma）─────────────────────────────────────────────────
# 餐廳廚師作息，晚起晚睡，午晚兩個用餐高峰
CHEF_TEMPLATE = [
    {"time": "09:00", "action": "起床",   "location": "獨棟房子 2",
     "type": "fixed", "completed": False},
    {"time": "10:30", "action": "前往",   "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "11:00", "action": "備料",   "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "12:00", "action": "煮飯",   "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "14:00", "action": "休息",   "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "15:00", "action": "吃飯",   "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "17:00", "action": "備料",   "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "18:00", "action": "煮飯",   "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "22:00", "action": "回家",   "location": "獨棟房子 2",
     "type": "fixed", "completed": False},
    {"time": "01:00", "action": "睡覺",   "location": "獨棟房子 2",
     "type": "fixed", "completed": False},
]


# ── 餐廳員工（外場服務生）────────────────────────────────────────
RESTAURANT_STAFF_TEMPLATE = [
    {"time": "09:30", "action": "起床",     "location": "公寓",
     "type": "fixed", "completed": False},
    {"time": "10:30", "action": "前往",     "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "11:00", "action": "整理店面", "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "12:00", "action": "服務客人", "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "14:00", "action": "吃飯",     "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "15:00", "action": "休息",     "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "17:30", "action": "服務客人", "location": "餐廳",
     "type": "fixed", "completed": False},
    {"time": "22:00", "action": "回家",     "location": "公寓",
     "type": "fixed", "completed": False},
    {"time": "00:30", "action": "睡覺",     "location": "公寓",
     "type": "fixed", "completed": False},
]


# ================================================================
# B. 預留職業範本（基本款，後續可細調）
# ================================================================

# ── 律師 ─────────────────────────────────────────────────────────
LAWYER_TEMPLATE = [
    {"time": "07:00", "action": "起床",   "location": "公寓",
     "type": "fixed", "completed": False},
    {"time": "08:30", "action": "前往",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "09:00", "action": "工作",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "12:30", "action": "吃飯",   "location": "公司附近",
     "type": "fixed", "completed": False},
    {"time": "14:00", "action": "工作",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "20:00", "action": "回家",   "location": "公寓",
     "type": "fixed", "completed": False},
    {"time": "23:30", "action": "睡覺",   "location": "公寓",
     "type": "fixed", "completed": False},
]


# ── 工程師 ───────────────────────────────────────────────────────
ENGINEER_TEMPLATE = [
    {"time": "08:30", "action": "起床",   "location": "公寓",
     "type": "fixed", "completed": False},
    {"time": "09:30", "action": "前往",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "10:00", "action": "工作",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "13:00", "action": "吃飯",   "location": "公司附近",
     "type": "fixed", "completed": False},
    {"time": "14:00", "action": "工作",   "location": "辦公室",
     "type": "fixed", "completed": False},
    {"time": "20:00", "action": "回家",   "location": "公寓",
     "type": "fixed", "completed": False},
    {"time": "00:30", "action": "睡覺",   "location": "公寓",
     "type": "fixed", "completed": False},
]


# ================================================================
# C. 職業 → 範本對照表
# ================================================================

SCHEDULE_TEMPLATES = {
    "咖啡師":     COFFEE_BARISTA_TEMPLATE,
    "超市員工":   SUPERMARKET_TEMPLATE,
    "辦公室員工": OFFICE_WORKER_TEMPLATE,
    "公司老闆":   COMPANY_BOSS_TEMPLATE,
    "廚師":       CHEF_TEMPLATE,
    "餐廳員工":   RESTAURANT_STAFF_TEMPLATE,
    "律師":       LAWYER_TEMPLATE,
    "工程師":     ENGINEER_TEMPLATE,
}


# ================================================================
# D. 必要時段檢查（規則檢查）
#
# 模型生成的時間表必須包含這些 action（不限定時間或地點）。
# 缺少則由 scheduler 補上，或 fallback 用範本。
# ================================================================

REQUIRED_SLOTS = {
    "咖啡師":     ["起床", "賣咖啡", "睡覺"],
    "超市員工":   ["起床", "收銀", "睡覺"],
    "辦公室員工": ["起床", "工作", "睡覺"],
    "公司老闆":   ["起床", "工作", "睡覺"],
    "廚師":       ["起床", "煮飯", "睡覺"],
    "餐廳員工":   ["起床", "服務客人", "睡覺"],
    "律師":       ["起床", "工作", "睡覺"],
    "工程師":     ["起床", "工作", "睡覺"],
}


# ================================================================
# E. 工具函式
# ================================================================

def get_template(role: str) -> list:
    """
    取得指定職業的時間表範本（深拷貝，避免外部修改原始資料）。
    找不到對應職業時回傳辦公室員工範本作 fallback。
    """
    import copy
    template = SCHEDULE_TEMPLATES.get(role, OFFICE_WORKER_TEMPLATE)
    return copy.deepcopy(template)


def get_required_slots(role: str) -> list:
    """
    取得指定職業的必要時段清單。
    找不到對應職業時回傳通用必要時段。
    """
    return REQUIRED_SLOTS.get(role, ["起床", "睡覺"])


def validate_schedule(schedule: list, role: str) -> tuple:
    """
    檢查時間表是否包含所有必要時段。

    回傳 (is_valid, missing_actions)：
      is_valid       : True / False
      missing_actions: 缺少的行動列表
    """
    actions_in_schedule = {slot["action"] for slot in schedule}
    required = get_required_slots(role)
    missing = [a for a in required if a not in actions_in_schedule]
    return (len(missing) == 0, missing)
