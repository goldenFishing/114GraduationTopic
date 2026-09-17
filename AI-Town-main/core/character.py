# ================================================================
# core/character.py
# 角色狀態的單一封裝
#
# 對應 ARCHITECTURE.md §6.2.1
#
# 設計原則：
#   1. 所有讀寫角色資料都透過這個類別，其他模組不直接碰 dict
#   2. 直接引用 dict 內部欄位（不複製），修改 Character 屬性等於修改原 dict
#   3. 第一次載入舊 JSON 時，自動補上新版欄位（sleep_pattern 等）
#
# 誰會調用：
#   agent/manager.py        — 初始化每個角色
#   agent/agent.py          — 讀寫個性/情緒/位置/關係
#   core/memory_stm.py      — 取 stm dict 引用
#   core/memory_ltm.py      — 取 ltm dict 引用
#   core/markov_engine.py   — 讀情緒、位置、時間表
#   core/consolidation.py   — 睡眠時更新各種狀態
#   model/prompt_builder.py — 取個性、習慣、關係組 prompt
#   agent/scheduler.py      — 寫回新時間表
#   agent/interrupt.py      — 取當前行動鎖等級
#   utils/file_io.py        — save_character 用 to_dict()
# ================================================================

from config.world_config import CHARACTER_NAMES, SLEEP_ACTION


# ================================================================
# 各職業的 sleep_pattern 預設值
# 第一次載入舊 JSON 時自動補上
# ================================================================

_DEFAULT_SLEEP_PATTERNS = {
    "咖啡師": {
        "default_wake_time":  "06:00",
        "force_wake_time":    "08:00",
        "default_sleep_time": "22:30",
        "force_sleep_time":   "01:00",
    },
    "超市員工": {
        "default_wake_time":  "07:00",
        "force_wake_time":    "09:00",
        "default_sleep_time": "23:00",
        "force_sleep_time":   "02:00",
    },
    "辦公室員工": {
        "default_wake_time":  "07:30",
        "force_wake_time":    "09:30",
        "default_sleep_time": "23:30",
        "force_sleep_time":   "02:00",
    },
    "公司老闆": {
        "default_wake_time":  "08:00",
        "force_wake_time":    "10:00",
        "default_sleep_time": "00:30",
        "force_sleep_time":   "02:00",
    },
    "廚師": {
        "default_wake_time":  "09:00",
        "force_wake_time":    "11:00",
        "default_sleep_time": "01:00",
        "force_sleep_time":   "02:00",
    },
    "餐廳員工": {
        "default_wake_time":  "09:30",
        "force_wake_time":    "11:00",
        "default_sleep_time": "00:30",
        "force_sleep_time":   "02:00",
    },
    "律師": {
        "default_wake_time":  "07:00",
        "force_wake_time":    "09:00",
        "default_sleep_time": "23:30",
        "force_sleep_time":   "02:00",
    },
    "工程師": {
        "default_wake_time":  "08:30",
        "force_wake_time":    "10:30",
        "default_sleep_time": "00:30",
        "force_sleep_time":   "02:00",
    },
}

_FALLBACK_SLEEP_PATTERN = {
    "default_wake_time":  "07:00",
    "force_wake_time":    "09:00",
    "default_sleep_time": "23:00",
    "force_sleep_time":   "02:00",
}


# ================================================================
# Character
# ================================================================

class Character:
    """
    單一角色的狀態管理。
    data : 從 file_io.load_character() 讀進來的 dict
    """

    def __init__(self, data: dict):
        self._data = data

        # 第一次載入舊 JSON 時自動補欄位
        self._ensure_sleep_pattern()
        self._ensure_state_fields()

        # ── 執行期暫存（不持久化到 JSON）────────────────────────
        # 每個 action 都是 1 tick 完成，中斷只影響「下一 tick」
        # 所以 pending_action 不需要 ticks_required / ticks_done
        self._pending_action: dict = {}    # {"action": str, "target": str}

        # 對話狀態（每 tick 重置）
        self.conversation_partner: str = ""
        self.conversation_turns_this_slot: int = 0
        self.is_locked: bool = False       # 對話中鎖定，不能被中斷

    # ── 第一次載入時補欄位 ──────────────────────────────────────

    def _ensure_sleep_pattern(self):
        """舊 JSON 沒有 sleep_pattern 時，依職業補預設值。"""
        if "sleep_pattern" not in self._data:
            role = self._data.get("role", "")
            self._data["sleep_pattern"] = dict(
                _DEFAULT_SLEEP_PATTERNS.get(role, _FALLBACK_SLEEP_PATTERN)
            )

    def _ensure_state_fields(self):
        """確保 state 必要欄位存在。"""
        state = self._data.setdefault("state", {})
        state.setdefault("day", 1)
        state.setdefault("current_location", self._data.get("residence", ""))
        state.setdefault("current_action", "")
        state.setdefault("today_actions", [])

    # ================================================================
    # A. 基本屬性
    # ================================================================

    @property
    def code(self) -> str:
        """角色代號（A B C D E），程式內部用。"""
        return self._data["name_code"]

    @property
    def name(self) -> str:
        """角色名字（Amy Ben ...），組 prompt 用。"""
        return self._data["name"]

    @property
    def role(self) -> str:
        return self._data["role"]

    @property
    def gender(self) -> str:
        return self._data.get("gender", "")

    @property
    def age(self) -> int:
        return self._data.get("age", 0)

    @property
    def residence(self) -> str:
        return self._data.get("residence", "")

    @property
    def emotion(self) -> str:
        return self._data["emotion"]

    @emotion.setter
    def emotion(self, value: str):
        self._data["emotion"] = value

    @property
    def day(self) -> int:
        return self._data["state"]["day"]

    @property
    def current_location(self) -> str:
        return self._data["state"]["current_location"]

    @current_location.setter
    def current_location(self, value: str):
        self._data["state"]["current_location"] = value

    @property
    def current_action(self) -> str:
        return self._data["state"]["current_action"]

    @current_action.setter
    def current_action(self, value: str):
        self._data["state"]["current_action"] = value

    # ================================================================
    # B. 個性與習慣
    # ================================================================

    def get_personality(self, short: bool = False) -> str:
        """
        short=True  → personality_short（一句話，直覺路徑備用）
        short=False → personality 完整版（思考路徑用）
        """
        key = "personality_short" if short else "personality"
        return self._data.get(key, "")

    def get_habit(self) -> str:
        return self._data.get("habit", "")

    # ================================================================
    # C. 關係
    # ================================================================

    def get_relationship(self, target_code: str) -> dict:
        """取得與 target_code 角色的關係 dict（initial + summary）。"""
        return self._data.get("relationships", {}).get(target_code, {})

    def get_relationship_text(self, target_code: str,
                               include_summary: bool = True) -> str:
        """
        回傳可直接注入 prompt 的關係描述文字。
        include_summary=True  → initial + summary（思考路徑）
        include_summary=False → 只有 initial
        """
        rel = self.get_relationship(target_code)
        if not rel:
            target_name = CHARACTER_NAMES.get(target_code, target_code)
            return f"{self.name} 與 {target_name} 不認識。"

        text = rel.get("initial", "")
        if include_summary and rel.get("summary"):
            text += f" 最近的狀況：{rel['summary']}"
        return text

    def update_relationship_summary(self, target_code: str, summary: str):
        """睡眠濃縮時更新關係摘要。"""
        rels = self._data.setdefault("relationships", {})
        if target_code in rels:
            rels[target_code]["summary"] = summary

    # ================================================================
    # D. 時間表
    # ================================================================

    def get_schedule(self) -> list:
        return self._data.get("schedule", {}).get("slots", [])

    def get_current_slot(self) -> dict | None:
        """回傳第一個尚未完成的時段；全部完成回 None。"""
        for slot in self.get_schedule():
            if not slot.get("completed", False):
                return slot
        return None

    def get_pending_slots(self, current_time_minutes: int) -> list:
        """
        回傳當前時間已到達但尚未完成的時段列表。
        current_time_minutes : 當前時間（從 00:00 起的分鐘數）
        """
        pending = []
        for slot in self.get_schedule():
            if slot.get("completed", False):
                continue
            slot_minutes = _parse_time_str(slot["time"])
            if current_time_minutes >= slot_minutes:
                pending.append(slot)
        return pending

    def mark_slot_completed(self, time_str: str):
        """將指定時間的時段標記為已完成。"""
        for slot in self.get_schedule():
            if slot["time"] == time_str:
                slot["completed"] = True
                break

    def insert_dynamic_slot(self, time_str: str, action: str,
                             location: str):
        """插入一個動態時段（執行中臨時加的）。"""
        slots = self._data.setdefault("schedule", {}).setdefault("slots", [])
        slots.append({
            "time": time_str,
            "action": action,
            "location": location,
            "type": "dynamic",
            "completed": False,
        })
        slots.sort(key=lambda s: s["time"])

    def replace_schedule(self, new_slots: list):
        """
        整批替換時間表（睡眠濃縮生成隔天時間表時呼叫）。
        new_slots 必須是符合格式的 list[dict]。
        """
        self._data.setdefault("schedule", {})["slots"] = list(new_slots)

    def reset_schedule(self):
        """新的一天開始，移除動態時段並重置 completed。"""
        slots = self.get_schedule()
        # 移除動態時段（隔天不繼承）
        slots = [s for s in slots if s.get("type") != "dynamic"]
        for slot in slots:
            slot["completed"] = False
        self._data["schedule"]["slots"] = slots

    def is_sleep_time(self, current_time_minutes: int = None) -> bool:
        """
        當前待完成的時段是否為睡覺。
        current_time_minutes 不為 None 時還會判斷時間是否已到。
        """
        slot = self.get_current_slot()
        if slot is None or slot["action"] != SLEEP_ACTION:
            return False
        if current_time_minutes is None:
            return True
        slot_minutes = _parse_time_str(slot["time"])
        return current_time_minutes >= slot_minutes

    # ================================================================
    # E. 睡眠模式
    # ================================================================

    def get_sleep_pattern(self) -> dict:
        return self._data["sleep_pattern"]

    def update_sleep_pattern(self, field: str, value: str):
        """field ∈ {default_wake_time, force_wake_time,
                    default_sleep_time, force_sleep_time}"""
        if field in self._data["sleep_pattern"]:
            self._data["sleep_pattern"][field] = value

    # ================================================================
    # F. 待辦行動（執行期暫存，不持久化）
    #
    # 每個 action 都是 1 tick 完成：
    #   Tick N: 決策 → 設定 pending
    #   Tick N+1: 執行 pending → 決策下一個 pending
    # 中斷只影響下一 tick 的決策。
    # ================================================================

    def set_pending_action(self, action: str, target: str = ""):
        """設定下一 tick 要執行的行動。"""
        self._pending_action = {"action": action, "target": target}

    def get_pending_action(self) -> dict:
        """回傳 {action, target}，沒有時回傳空 dict。"""
        return dict(self._pending_action)

    def has_pending_action(self) -> bool:
        return bool(self._pending_action.get("action"))

    def clear_pending_action(self):
        self._pending_action = {}

    # ================================================================
    # G. 困惑度
    # ================================================================

    def get_confusion_weights(self) -> dict:
        """回傳 {w1, w2, w3, threshold}。"""
        return self._data.get("confusion_weights",
                              {"w1": 0.4, "w2": 0.3, "w3": 0.3,
                               "threshold": 0.5})

    def get_confusion_threshold(self) -> float:
        """
        回傳「情緒調整後」的 threshold。
        實際調整邏輯在 core/confusion.adjust_threshold_by_emotion。
        """
        # 延遲匯入避免循環依賴
        from core.confusion import adjust_threshold_by_emotion
        base = self.get_confusion_weights().get("threshold", 0.5)
        return adjust_threshold_by_emotion(base, self.emotion)

    # ================================================================
    # H. 今日紀錄
    # ================================================================

    def add_today_action(self, action: str):
        self._data["state"]["today_actions"].append(action)

    def get_today_actions(self) -> list:
        return self._data["state"]["today_actions"]

    def clear_today_actions(self):
        self._data["state"]["today_actions"] = []

    # ================================================================
    # I. 跨日與重置
    # ================================================================

    def advance_day(self):
        """
        睡眠濃縮完成後呼叫：
          day +1、清空今日行動、重置時間表
        注意：emotion 與 schedule 的更新由 consolidation 處理，
              這裡只負責結構性重置。
        """
        self._data["state"]["day"] += 1
        self.clear_today_actions()
        self.reset_schedule()

    def reset_slot_state(self):
        """每個 tick 開始時呼叫，重置對話狀態。"""
        self.conversation_partner = ""
        self.conversation_turns_this_slot = 0
        self.is_locked = False

    # ================================================================
    # J. 序列化
    # ================================================================

    def to_dict(self) -> dict:
        """回傳原始 dict（供 file_io.save_character 寫回磁碟）。"""
        return self._data


# ================================================================
# 工具函式
# ================================================================

def _parse_time_str(time_str: str) -> int:
    """把 "HH:MM" 轉成從 00:00 起的分鐘數。"""
    try:
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return 0
