# schedule_templates — 各職業作息範本與時間表驗證

> **路徑**: `config/schedule_templates.py`  
> **職責**: 提供職業範本、必要時段定義，並驗證模型生成的時間表

---

## 功能概覽

`schedule_templates.py` 定義了 AI-Town 中各職業角色的標準作息時間表範本，以及確保時間表品質的規則驗證機制。這些範本在睡眠濃縮流程中作為「底稿」，由 `agent/scheduler.py` 傳給 Phi-3.5 模型，讓模型在不偏離職業特性的前提下根據當天事件動態調整隔天計畫。

範本的設計貼近現實：Amy（咖啡師）06:00 起床、07:30 整理店面、18:00 打烊；Emma（廚師）09:00 晚起、橫跨午晚兩個用餐高峰、01:00 才入睡；David（公司老闆）習慣早上先去咖啡店買咖啡再前往辦公室，加班到 20:00，00:30 才睡。這些細節讓模型生成的時間表具備職業真實感。

驗證機制（`REQUIRED_SLOTS` + `validate_schedule()`）作為最後一道安全網：即使模型生成的時間表與範本差異很大，至少必須包含「起床」、核心工作行動、「睡覺」三個錨點。缺少時由 scheduler 補上或 fallback 回範本，確保模擬不會因為模型輸出異常而崩潰。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `copy`（標準函式庫） | `get_template()` 內部使用 `copy.deepcopy()` 防止外部修改原始範本 |
| 被依賴 | `agent/scheduler.py` | import `get_template()`、`get_required_slots()`、`validate_schedule()` 用於時間表生成與驗證 |
| 被依賴 | `config/prompts.py` | `prompt_generate_schedule()` 的 `template_text` 參數由 `get_template()` 取得後序列化 |

---

## 主要常數 / 資料結構

### `COFFEE_BARISTA_TEMPLATE`（Amy，咖啡師）
**型別**: `list[dict]`  
**說明**: Amy 的標準作息範本，早起早睡，工作日作息穩定。

| 時間 | 行動 | 地點 |
|------|------|------|
| 06:00 | 起床 | A家 |
| 07:00 | 前往 | 咖啡店 |
| 07:30 | 整理店面 | 咖啡店 |
| 08:30 | 賣咖啡 | 咖啡店 |
| 12:00 | 吃飯 | 咖啡店後場 |
| 13:00 | 賣咖啡 | 咖啡店 |
| 18:00 | 打烊 | 咖啡店 |
| 19:00 | 回家 | A家 |
| 22:30 | 睡覺 | A家 |

---

### `SUPERMARKET_TEMPLATE`（Ben，超市員工）
**型別**: `list[dict]`  
**說明**: Ben 的標準作息範本，輪班型工作，上午補貨、下午收銀。

| 時間 | 行動 | 地點 |
|------|------|------|
| 07:00 | 起床 | B家 |
| 08:30 | 前往 | 超市 |
| 09:00 | 補貨 | 超市 |
| 11:00 | 收銀 | 超市 |
| 12:30 | 吃飯 | 超市附近 |
| 14:00 | 收銀 | 超市 |
| 17:00 | 補貨 | 超市 |
| 19:00 | 回家 | B家 |
| 23:00 | 睡覺 | B家 |

---

### `OFFICE_WORKER_TEMPLATE`（Claire，辦公室員工）
**型別**: `list[dict]`  
**說明**: Claire 的標準作息範本，標準白領朝九晚六，回家後整理家裡。

| 時間 | 行動 | 地點 |
|------|------|------|
| 07:30 | 起床 | C家 |
| 08:30 | 前往 | 辦公室 |
| 09:00 | 工作 | 辦公室 |
| 12:00 | 吃飯 | 公司附近 |
| 13:00 | 工作 | 辦公室 |
| 18:00 | 回家 | C家 |
| 19:00 | 整理家裡 | C家 |
| 23:30 | 睡覺 | C家 |

---

### `COMPANY_BOSS_TEMPLATE`（David，公司老闆）
**型別**: `list[dict]`  
**說明**: David 的標準作息範本，工時較長，每天早上固定先繞去咖啡店買咖啡再到辦公室，加班到 20:00，00:30 才入睡。

| 時間 | 行動 | 地點 |
|------|------|------|
| 08:00 | 起床 | D家 |
| 08:30 | 前往 | 咖啡店 |
| 09:00 | 前往 | 辦公室 |
| 09:30 | 工作 | 辦公室 |
| 13:00 | 吃飯 | 公司附近 |
| 14:00 | 工作 | 辦公室 |
| 20:00 | 回家 | D家 |
| 00:30 | 睡覺 | D家 |

---

### `CHEF_TEMPLATE`（Emma，廚師）
**型別**: `list[dict]`  
**說明**: Emma 的標準作息範本，晚起晚睡的廚師作息，橫跨午餐（12:00）與晚餐（18:00）兩個高峰，中間有短暫休息與用餐時段。

| 時間 | 行動 | 地點 |
|------|------|------|
| 09:00 | 起床 | E家 |
| 10:30 | 前往 | 餐廳 |
| 11:00 | 備料 | 餐廳 |
| 12:00 | 煮飯 | 餐廳 |
| 14:00 | 休息 | 餐廳 |
| 15:00 | 吃飯 | 餐廳 |
| 17:00 | 備料 | 餐廳 |
| 18:00 | 煮飯 | 餐廳 |
| 22:00 | 回家 | E家 |
| 01:00 | 睡覺 | E家 |

---

### `RESTAURANT_STAFF_TEMPLATE`（餐廳外場員工）
**型別**: `list[dict]`  
**說明**: 預留的餐廳外場員工範本（服務生角色）。與廚師類似的作息，但工作行動為「服務客人」而非「煮飯」。`location` 起點使用「公寓大廳」，適用於住在公寓的角色。

---

### `LAWYER_TEMPLATE`（律師）
**型別**: `list[dict]`  
**說明**: 預留的律師職業範本，07:00 起床，加班到 20:00，標準知識工作者作息。未來新增律師角色時可直接使用。

---

### `ENGINEER_TEMPLATE`（工程師）
**型別**: `list[dict]`  
**說明**: 預留的工程師職業範本，08:30 較晚起床（工程師習慣），加班到 20:00，00:30 入睡。未來新增工程師角色時可直接使用。

---

### `SCHEDULE_TEMPLATES`
**型別**: `dict[str, list[dict]]`  
**說明**: 職業名稱到範本的對照表，是 `get_template()` 的查詢來源。

```python
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
```

---

### `REQUIRED_SLOTS`
**型別**: `dict[str, list[str]]`  
**說明**: 各職業的必要行動清單。模型生成的時間表若缺少這些行動，由 `scheduler` 補上或 fallback 回範本。

| 職業 | 必要行動 |
|------|---------|
| 咖啡師 | 起床、賣咖啡、睡覺 |
| 超市員工 | 起床、收銀、睡覺 |
| 辦公室員工 | 起床、工作、睡覺 |
| 公司老闆 | 起床、工作、睡覺 |
| 廚師 | 起床、煮飯、睡覺 |
| 餐廳員工 | 起床、服務客人、睡覺 |
| 律師 | 起床、工作、睡覺 |
| 工程師 | 起床、工作、睡覺 |

---

## 時間表條目格式

每個時間表條目（slot）是一個 dict，包含以下欄位：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `time` | `str` | 時間字串，格式 `"HH:MM"`（24 小時制） |
| `action` | `str` | 行動名稱，必須在 `VALID_ACTIONS` 中 |
| `location` | `str` | 地點名稱，必須在 `VALID_LOCATIONS` 中 |
| `type` | `str` | `"fixed"`（來自範本）或 `"dynamic"`（模型動態插入）|
| `completed` | `bool` | 初始為 `False`，執行後由模擬引擎更新為 `True` |

---

## 主要函式

### `get_template(role: str) -> list`

**功能**: 取得指定職業的時間表範本深拷貝，避免外部修改影響原始資料。找不到對應職業時 fallback 回辦公室員工範本。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `role` | `str` | 職業名稱，例如 `"咖啡師"`、`"廚師"` |

**回傳**: `list` — 時間表條目列表的深拷貝（修改不影響原始範本）

**範例**:
```python
from config.schedule_templates import get_template

# 取得 Amy（咖啡師）的範本
amy_template = get_template("咖啡師")
print(amy_template[0])
# {'time': '06:00', 'action': '起床', 'location': 'A家', 'type': 'fixed', 'completed': False}

# 修改拷貝不影響原始
amy_template[0]["completed"] = True
original = get_template("咖啡師")
print(original[0]["completed"])  # False（原始未被修改）

# 未知職業 → fallback 到辦公室員工範本
mystery_template = get_template("魔法師")
print(mystery_template[0])
# {'time': '07:30', 'action': '起床', 'location': 'C家', ...}
```

---

### `get_required_slots(role: str) -> list`

**功能**: 取得指定職業的必要時段行動清單。找不到對應職業時回傳通用必要時段 `["起床", "睡覺"]`。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `role` | `str` | 職業名稱 |

**回傳**: `list[str]` — 必要行動名稱列表

**範例**:
```python
from config.schedule_templates import get_required_slots

required = get_required_slots("廚師")
print(required)  # ['起床', '煮飯', '睡覺']

required = get_required_slots("魔法師")  # 未知職業
print(required)  # ['起床', '睡覺']（通用 fallback）
```

---

### `validate_schedule(schedule: list, role: str) -> tuple`

**功能**: 檢查時間表（通常是模型生成的）是否包含該職業的所有必要行動。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `schedule` | `list` | 時間表條目列表，每筆需含 `"action"` 欄位 |
| `role` | `str` | 職業名稱，用於查詢 `REQUIRED_SLOTS` |

**回傳**: `tuple[bool, list[str]]`
- `is_valid`：`True` 表示通過驗證；`False` 表示有缺失
- `missing_actions`：缺少的行動名稱列表（通過時為空列表 `[]`）

**範例**:
```python
from config.schedule_templates import validate_schedule

# Emma 的模型生成時間表（缺少「煮飯」）
model_schedule = [
    {"time": "09:00", "action": "起床",   "location": "E家"},
    {"time": "10:30", "action": "前往",   "location": "餐廳"},
    {"time": "11:00", "action": "備料",   "location": "餐廳"},
    {"time": "22:00", "action": "回家",   "location": "E家"},
    # 漏掉了「煮飯」和「睡覺」
]

is_valid, missing = validate_schedule(model_schedule, "廚師")
print(is_valid)   # False
print(missing)    # ['煮飯', '睡覺']

# Scheduler 收到 missing 後補上缺失時段或 fallback 至範本
```

---

## 模擬使用情境

### 情境一：Amy 睡覺時生成隔天時間表的完整流程

```python
from config.schedule_templates import get_template, validate_schedule

# Step 1：Scheduler 取得範本
template = get_template("咖啡師")

# Step 2：序列化為文字供 prompt 使用
template_text = "\n".join(
    f"{slot['time']} {slot['action']} @ {slot['location']}"
    for slot in template
)
# "06:00 起床 @ A家\n07:00 前往 @ 咖啡店\n..."

# Step 3：模型根據今日事件（Amy 今天很累）生成新時間表
# 假設模型提早了睡覺時間
model_output_schedule = [
    {"time": "06:00", "action": "起床",     "location": "A家"},
    {"time": "07:00", "action": "前往",     "location": "咖啡店"},
    {"time": "07:30", "action": "整理店面", "location": "咖啡店"},
    {"time": "08:30", "action": "賣咖啡",   "location": "咖啡店"},
    {"time": "15:00", "action": "打烊",     "location": "咖啡店"},  # 提早打烊
    {"time": "16:00", "action": "回家",     "location": "A家"},
    {"time": "21:00", "action": "睡覺",     "location": "A家"},   # 提早睡覺
]

# Step 4：驗證
is_valid, missing = validate_schedule(model_output_schedule, "咖啡師")
print(f"通過驗證：{is_valid}, 缺少：{missing}")
# 通過驗證：True, 缺少：[]

# Step 5：寫入 Amy 的角色資料
```

### 情境二：David 的時間表展現老闆特性

```python
from config.schedule_templates import get_template, REQUIRED_SLOTS

david_template = get_template("公司老闆")

# 驗證 David 每天早上必去咖啡店的習慣
morning_sequence = [s for s in david_template if s["time"] <= "09:30"]
for slot in morning_sequence:
    print(f"{slot['time']}: {slot['action']} → {slot['location']}")
# 08:00: 起床 → D家
# 08:30: 前往 → 咖啡店   ← David 每天必去 Amy 的咖啡店
# 09:00: 前往 → 辦公室

# 驗證必要時段（老闆版本和員工版本相同）
print(REQUIRED_SLOTS["公司老闆"])   # ['起床', '工作', '睡覺']
print(REQUIRED_SLOTS["辦公室員工"])  # ['起床', '工作', '睡覺']
```

### 情境三：新增角色職業並使用 fallback 機制

```python
from config.schedule_templates import get_template, get_required_slots, validate_schedule

# 假設加入一個「醫生」角色，暫時無對應範本
doctor_template = get_template("醫生")  # fallback 到辦公室員工範本
print(doctor_template[0]["time"])  # "07:30"（辦公室員工的起床時間）

# 模型生成的醫生時間表
doctor_schedule = [
    {"time": "07:30", "action": "起床", "location": "公寓大廳"},
    {"time": "08:30", "action": "工作", "location": "辦公室"},
    {"time": "22:00", "action": "睡覺", "location": "公寓大廳"},
]

# 使用通用必要時段驗證
is_valid, missing = validate_schedule(doctor_schedule, "醫生")
print(is_valid, missing)  # True []（通用 fallback 只要求起床+睡覺）
```

---

## 注意事項

- `get_template()` 使用 `copy.deepcopy()`，回傳的是完整的深層拷貝。修改回傳值（包括內部 dict 的欄位）不會影響 `SCHEDULE_TEMPLATES` 中的原始資料，可放心修改 `completed` 欄位標記執行狀態。
- 時間表中的 `time` 欄位格式為 `"HH:MM"` 24 小時制，凌晨時段（如 `"00:30"`、`"01:00"`）跨越午夜，是正常設計（對應 `world_config.DAY_END_HOUR=2`）。解析時間時需特別處理跨午夜的排序比較。
- 範本中的所有條目 `type` 均為 `"fixed"`。模型動態插入的時段在 `scheduler` 組裝最終時間表時標記為 `"dynamic"`。觀察工具可據此區分哪些行動是預定的、哪些是當天臨時決定的。
- `REQUIRED_SLOTS` 只要求行動存在，不要求特定時間或地點，給模型最大彈性。例如廚師的「煮飯」可以出現在任何時間，只要出現就通過驗證。
- David（公司老闆）的範本中有兩個連續「前往」時段（08:30 前往咖啡店、09:00 前往辦公室），這是刻意設計的，用於模擬先買咖啡再上班的行為。模擬引擎需能正確處理連續移動行動。
- 新增職業範本時，需同時在 `SCHEDULE_TEMPLATES` 和 `REQUIRED_SLOTS` 中各加一筆對應條目，否則 `validate_schedule()` 會使用通用 fallback `["起床", "睡覺"]`，導致職業核心行動不被強制要求。
