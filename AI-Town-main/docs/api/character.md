# character — 角色狀態的單一封裝

> **路徑**: `core/character.py`  
> **職責**: 統一管理角色所有屬性、時間表與執行期狀態

---

## 功能概覽

`character.py` 是 AI-Town 中所有角色資料的唯一存取入口，對應 ARCHITECTURE.md §6.2.1。所有其他模組若需要讀寫角色資料，都必須透過 `Character` 類別的屬性與方法，而不能直接操作底層 dict，確保資料一致性與易於追蹤。

`Character` 直接引用從磁碟讀取的角色 JSON dict（`_data`），修改屬性等同修改原始資料，不需要額外序列化步驟。第一次載入舊版 JSON 時，`_ensure_sleep_pattern()` 和 `_ensure_state_fields()` 會自動補齊缺少的欄位，保證向後相容性。

執行期暫存（`_pending_action`、`conversation_partner` 等）不會被持久化到 JSON，這些狀態只在記憶體中存在，每次重啟後重置，符合「每個 action 都是 1 tick 完成」的設計原則。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | `CHARACTER_NAMES`、`SLEEP_ACTION` 常數 |
| 依賴 | `core/weight_adapter.py` | `WeightAdapter.DEFAULT_WEIGHTS` 作為 Markov 權重預設值 |
| 被依賴 | `agent/manager.py` | 初始化每個角色的 Character 實例 |
| 被依賴 | `agent/agent.py` | 讀寫個性、情緒、位置、關係 |
| 被依賴 | `core/memory_stm.py` | 取 `_data["stm"]` dict 引用 |
| 被依賴 | `core/memory_ltm.py` | 取 `_data["ltm"]` dict 引用 |
| 被依賴 | `core/markov_engine.py` | 讀取情緒、位置、時間表 |
| 被依賴 | `core/consolidation.py` | 睡眠時更新情緒、時間表、關係 |
| 被依賴 | `model/prompt_builder.py` | 取個性、習慣、關係組 prompt |
| 被依賴 | `utils/file_io.py` | `save_character()` 呼叫 `to_dict()` |

---

## 職業睡眠時間預設值

| 職業 | 起床時間（預設/強制） | 睡覺時間（預設/強制） |
|------|----------------------|----------------------|
| 咖啡師 | 06:00 / 08:00 | 22:30 / 01:00 |
| 超市員工 | 07:00 / 09:00 | 23:00 / 02:00 |
| 辦公室員工 | 07:30 / 09:30 | 23:30 / 02:00 |
| 公司老闆 | 08:00 / 10:00 | 00:30 / 02:00 |
| 廚師 | 09:00 / 11:00 | 01:00 / 02:00 |
| 工程師 | 08:30 / 10:30 | 00:30 / 02:00 |

---

## 主要類別 / 函式

### `Character`

**功能**: 單一角色的完整狀態管理器，整合基本屬性、個性習慣、關係網絡、時間表管理、睡眠模式及 Markov 權重。

#### `__init__(self, data: dict)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `data` | `dict` | 由 `file_io.load_character()` 讀入的角色 JSON 資料 |

初始化時自動呼叫 `_ensure_sleep_pattern()` 補職業預設睡眠模式，以及 `_ensure_state_fields()` 確保 state 結構完整。

**範例**:
```python
from core.character import Character
from utils.file_io import load_character

data = load_character("A")  # 載入 Amy 的 JSON
amy = Character(data)
print(amy.name)   # "Amy"
print(amy.role)   # "咖啡師"
```

---

### A. 基本屬性（唯讀 property）

| 屬性 | 型別 | 說明 |
|------|------|------|
| `code` | `str` | 角色代號（A/B/C/D/E），程式內部識別用 |
| `name` | `str` | 角色名字（Amy/Ben/Claire/David/Emma） |
| `role` | `str` | 職業（咖啡師/工程師等） |
| `gender` | `str` | 性別 |
| `age` | `int` | 年齡 |
| `residence` | `str` | 居住地點 |
| `emotion` | `str` | 當前情緒（可讀寫） |
| `day` | `int` | 當前天數（唯讀） |
| `current_location` | `str` | 當前位置（可讀寫） |
| `current_action` | `str` | 當前行動（可讀寫） |

---

### B. 個性與習慣

#### `get_personality(self, short: bool = False) -> str`

**功能**: 取得角色個性描述。`short=True` 回傳一句話版本（直覺路徑），`short=False` 回傳完整版（思考路徑）。

**範例**:
```python
amy.get_personality(short=True)
# "Amy 是一個熱情開朗的咖啡師"

amy.get_personality(short=False)
# "Amy 是一個熱情開朗的咖啡師，喜歡和顧客聊天，對咖啡有獨到見解..."
```

---

### C. 關係管理

#### `get_relationship(self, target_code: str) -> dict`

**功能**: 取得與指定角色的關係 dict，包含 `initial`（初始描述）和 `summary`（更新摘要）。

#### `get_relationship_text(self, target_code: str, include_summary: bool = True) -> str`

**功能**: 回傳可直接注入 prompt 的關係文字。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `target_code` | `str` | 目標角色代號（如 `"B"`） |
| `include_summary` | `bool` | 是否包含最近動態摘要（思考路徑用 True） |

**範例**:
```python
amy.get_relationship_text("B", include_summary=True)
# "Amy 和 Ben 是朋友，常在咖啡店相遇。 最近的狀況：Amy 為 Ben 制作了新的特調咖啡。"
```

#### `update_relationship_summary(self, target_code: str, summary: str)`

**功能**: 睡眠濃縮 Step 6 更新關係摘要時呼叫。

---

### D. 時間表管理

#### `get_schedule(self) -> list`

**功能**: 回傳完整時間表 slots 列表。每個 slot 格式：
```python
{"time": "09:00", "action": "工作", "location": "咖啡店", "type": "fixed", "completed": False}
```

#### `get_current_slot(self) -> dict | None`

**功能**: 回傳第一個尚未完成的時段；全部完成時回傳 `None`。

#### `get_pending_slots(self, current_time_minutes: int) -> list`

**功能**: 回傳當前時間已到達但尚未完成的時段列表。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `current_time_minutes` | `int` | 當前時間（從 00:00 起的分鐘數，如 `9 * 60 = 540` 代表 09:00） |

#### `mark_slot_completed(self, time_str: str)`

**功能**: 將指定時間的時段標記為已完成。

#### `insert_dynamic_slot(self, time_str: str, action: str, location: str)`

**功能**: 在執行中臨時插入動態時段，插入後按時間重新排序。動態時段在新的一天開始時會被自動移除（不繼承到隔天）。

#### `replace_schedule(self, new_slots: list)`

**功能**: 整批替換時間表，睡眠濃縮生成隔天時間表後呼叫。

#### `is_sleep_time(self, current_time_minutes: int = None) -> bool`

**功能**: 當前待完成時段是否為睡覺行動（`SLEEP_ACTION`）。傳入時間時會額外確認時間是否已到。

---

### E. 睡眠模式

#### `get_sleep_pattern(self) -> dict`

**功能**: 回傳角色的睡眠模式設定。格式：
```python
{
    "default_wake_time":  "06:00",
    "force_wake_time":    "08:00",
    "default_sleep_time": "22:30",
    "force_sleep_time":   "01:00",
}
```

#### `update_sleep_pattern(self, field: str, value: str)`

**功能**: 更新睡眠模式特定欄位。`field` 必須是四個合法 key 之一。

---

### F. 待辦行動（執行期暫存）

設計原則：每個 action 都是 1 tick 完成。Tick N 決策 → 設定 pending；Tick N+1 執行 pending 並決策下一個。

#### `set_pending_action(self, action: str, target: str = "")`
#### `get_pending_action(self) -> dict`
#### `has_pending_action(self) -> bool`
#### `clear_pending_action(self)`

**範例**:
```python
amy.set_pending_action(action="對話", target="Ben")
if amy.has_pending_action():
    pa = amy.get_pending_action()  # {"action": "對話", "target": "Ben"}
    # 執行...
    amy.clear_pending_action()
```

---

### G. 困惑度

#### `get_confusion_weights(self) -> dict`

**功能**: 回傳 `{w1, w2, w3, threshold}`，預設值 `{"w1": 0.4, "w2": 0.3, "w3": 0.3, "threshold": 0.5}`。

#### `get_confusion_threshold(self) -> float`

**功能**: 回傳「情緒調整後」的困惑度閾值，呼叫 `core.mental_state.adjust_threshold_by_emotion()`。負面情緒時閾值較高（更難觸發 deliberate 模式）。

---

### I. 跨日重置

#### `advance_day(self)`

**功能**: 睡眠濃縮完成後呼叫，day + 1、清空今日行動、重置時間表 completed 狀態。

#### `reset_slot_state(self)`

**功能**: 每個 tick 開始時呼叫，重置對話狀態（`conversation_partner`、`conversation_turns_this_slot`、`is_locked`）。

---

### J. 序列化

#### `to_dict(self) -> dict`

**功能**: 回傳原始 `_data` dict，供 `file_io.save_character()` 寫回磁碟。

---

### K. 自適應 Markov 權重

#### `get_markov_weights(self) -> dict`

**功能**: 回傳此角色的 Markov 三源權重 `{alpha, beta, gamma}`，從 JSON 讀取；若尚未設定則回傳 `WeightAdapter.DEFAULT_WEIGHTS`。

#### `set_markov_weights(self, weights: dict)`

**功能**: 更新 Markov 權重，由睡眠濃縮 Step 12 呼叫。

---

## 模擬使用情境

### 情境一：Amy 第三天早上的工作流程

```python
from core.character import Character

amy = Character(load_character("A"))

# 查看當前狀態
print(f"第 {amy.day} 天  位置：{amy.current_location}  情緒：{amy.emotion}")

# 取得當前時段
slot = amy.get_current_slot()
if slot:
    print(f"預定行動：{slot['action']} @ {slot['location']}（{slot['time']}）")

# 執行對話後更新狀態
amy.current_action = "對話"
amy.add_today_action("對話")
amy.mark_slot_completed("09:00")

# 查看與 Ben 的關係文字（給 LLM prompt 用）
rel_text = amy.get_relationship_text("B", include_summary=True)
print(rel_text)
```

### 情境二：Claire（餐廳員工）的動態插入時段

```python
claire = Character(load_character("C"))

# 原時間表：工作 12:00，休息 15:00，睡覺 00:30
# 突發事件：David 14:30 臨時來訪
claire.insert_dynamic_slot("14:30", "對話", "餐廳")

# 查看新時間表
for slot in claire.get_schedule():
    status = "✓" if slot["completed"] else "○"
    print(f"  {status} {slot['time']}  {slot['action']}  {slot['location']}  [{slot['type']}]")
```

---

## 注意事項

- `_pending_action`、`conversation_partner` 等執行期暫存欄位**不會**被序列化到 JSON，程式重啟後會重置。
- `advance_day()` 只負責結構性重置，情緒更新和新時間表生成由 `consolidation.py` 負責。
- `get_confusion_threshold()` 使用延遲匯入（`from core.mental_state import adjust_threshold_by_emotion`）避免循環依賴。
- 動態時段（`type="dynamic"`）在 `reset_schedule()` 時會被移除，不會延續到隔天。
- 睡眠模式的 `force_sleep_time` / `force_wake_time` 是強制邊界，角色無論如何都不會在這個時間後繼續維持清醒或睡覺。
