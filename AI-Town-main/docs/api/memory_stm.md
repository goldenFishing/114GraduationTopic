# memory_stm — 短期記憶（情節敘述形式）管理

> **路徑**: `core/memory_stm.py`  
> **職責**: 以三層結構儲存並管理當日情節記憶

---

## 功能概覽

`memory_stm` 實作 AI-Town 角色的短期記憶（STM）系統，對應認知科學中 Tulving（1972）的情節記憶理論。每一筆記憶稱為「turn」，由感知（perception）、事件（event）、內在（inner）三層組成，以敘述化文字形式編碼，模擬人類自傳記憶的多層結構（Conway & Pleydell-Pearce 2000）。

模組設計刻意不包含 HAM（Human Associative Memory）命題——HAM 只有在睡眠濃縮（consolidation）階段才從敘述中抽取並轉存至長期記憶（LTM）。STM 本身沒有筆數上限，但設有安全閥（`SAFETY_LIMIT = 50`）以避免記憶無限膨脹。

睡眠後 STM 不會完全清空，而是縮減為一筆昨日摘要 turn 加上最近 N 筆原始記錄（預設保留 5 筆），忠實呈現 Diekelmann & Born（2010）「睡眠是記憶轉移與整合，而非清除」的實證結論。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | 讀取 `STM_SAFETY_LIMIT`、`STM_KEEP_AFTER_CONS` 常數 |
| 被依賴 | `agent/manager.py` | 建立 STM 物件、檢查安全閥 |
| 被依賴 | `agent/agent.py` | 寫入決策、執行、對話記錄 |
| 被依賴 | `model/prompt_builder.py` | 取敘述化文字 / 最近 N 筆給 LLM prompt |
| 被依賴 | `core/markov_engine.py` | 取最近行動動詞序列計算慣性 |
| 被依賴 | `core/consolidation.py` | 取全部敘述抽 HAM、縮減 STM |
| 被依賴 | `observe/dashboard_html.py` | 視覺化當日 STM |

---

## 主要類別 / 函式

### `STM`

**功能**: 短期記憶管理器，直接引用 `Character._data["stm"]`，修改 STM 等於修改角色資料的原始 dict，無需額外序列化。

#### `__init__(self, character_data: dict)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_data` | `dict` | 角色完整資料 dict（由 `file_io.load_character()` 讀取） |

初始化時會確保 `character_data["stm"]["turns"]` 結構存在，並捨棄舊版的 `capacity` 欄位。

**範例**:
```python
from core.memory_stm import STM

data = {"name": "Amy", "stm": {}}
stm = STM(data)
```

---

#### `add_turn(self, turn_id: str, time: str, perception: dict, event: dict, inner: dict) -> dict`

**功能**: 寫入一筆新的 STM 記錄，三層結構均會通過 normalize 函式確保欄位完整。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `turn_id` | `str` | 唯一識別碼，格式 `D{day:03d}_T{turn:03d}`，如 `D001_T003` |
| `time` | `str` | 該時段時間，格式 `"HH:MM"` |
| `perception` | `dict` | `{"location": str, "yolo_desc": str, "scene_text": str}` |
| `event` | `dict` | `{"input_text": str, "action": str, "target": str, "content": str}` |
| `inner` | `dict` | `{"thought": str, "emotion": str}` |

**回傳**: `dict` — 寫入的 turn 物件

**範例**:
```python
turn = stm.add_turn(
    turn_id    = "D001_T002",
    time       = "09:30",
    perception = {"location": "咖啡店", "yolo_desc": "2個人、1個杯子", "scene_text": "早晨的咖啡店"},
    event      = {"input_text": "Ben: 早安", "action": "對話", "target": "Ben", "content": "早安，今天想喝什麼？"},
    inner      = {"thought": "Ben 看起來心情不錯", "emotion": "平靜"},
)
```

---

#### `add_summary_turn(self, day: int, summary_text: str)`

**功能**: 在新一天起始時插入「昨日摘要」turn，`turn_id` 使用 `T000` 標示，永遠放在所有 turns 的最前面。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `day` | `int` | 新一天的天數編號 |
| `summary_text` | `str` | 模型生成的昨日摘要文字 |

**範例**:
```python
stm.add_summary_turn(day=2, summary_text="Amy 在咖啡店遇見 Ben，和 David 聊了工作的事。")
```

---

#### `get_all(self) -> list`

**功能**: 回傳所有 STM 記錄，包含摘要 turn。

**回傳**: `list` — 所有 turn dict 的列表

---

#### `get_recent(self, n: int) -> list`

**功能**: 回傳最近 n 筆記錄，排除摘要 turn（T000）。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `n` | `int` | 要取得的最新筆數 |

**回傳**: `list` — 最近 n 筆非摘要 turn

**範例**:
```python
recent = stm.get_recent(3)  # 取最近 3 筆
```

---

#### `get_today_narrative(self, max_chars: int = None) -> str`

**功能**: 將當日所有 STM 記錄組合成敘述化文字，供 LLM prompt 注入使用。若超過 `max_chars` 字元限制，自動截斷較舊的部分並保留最新片段。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `max_chars` | `int \| None` | 字元上限（`None` = 不限制） |

**回傳**: `str` — 敘述化文字，無記錄時回傳 `"（今天還沒有任何記憶）"`

**範例**:
```python
narrative = stm.get_today_narrative(max_chars=2000)
# [09:30]
# 在咖啡店，看到2個人、1個杯子。
# 對 Ben 說：「早安，今天想喝什麼」
# 內心想：Ben 看起來心情不錯。（情緒：平靜）
```

---

#### `get_recent_actions(self, n: int = 5) -> list`

**功能**: 回傳最近 n 筆的行動動詞序列，排除摘要 turn 和空行動，供 Markov Engine 計算行為慣性。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `n` | `int` | 行動數量（預設 5） |

**回傳**: `list[str]` — 行動動詞列表，如 `["對話", "工作", "休息", "對話", "工作"]`

---

#### `is_over_safety_limit(self) -> bool`

**功能**: 檢查 STM 是否超過安全閥（`STM_SAFETY_LIMIT = 50`），超過時觸發中途濃縮。

**回傳**: `bool`

---

#### `shrink_to_summary(self, summary_text: str, new_day: int, keep_recent: int = STM_KEEP_AFTER_CONS)`

**功能**: 睡眠濃縮後縮減 STM。清空所有記錄，插入昨日摘要 turn，再附上保留的最近 N 筆原始記錄。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `summary_text` | `str` | 模型生成的當天摘要 |
| `new_day` | `int` | 新一天的天數（摘要 turn 用） |
| `keep_recent` | `int` | 保留最近幾筆原始記錄（預設 `STM_KEEP_AFTER_CONS`） |

**範例**:
```python
stm.shrink_to_summary(
    summary_text="Amy 在咖啡店工作，與 David 討論新菜單。",
    new_day=2,
    keep_recent=5,
)
```

---

#### `next_turn_number(self, day: int) -> int`

**功能**: 計算下一個 turn 編號（每天從 1 開始，T000 保留給摘要 turn）。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `day` | `int` | 當前天數 |

**回傳**: `int` — 下一個可用的 turn 編號

---

### 模組級工具函式

#### `make_turn_id(day: int, turn_number: int) -> str`

**功能**: 產生標準格式的唯一 turn_id。

**回傳**: `str` — 如 `"D001_T003"`

---

#### `_turn_to_narrative(turn: dict) -> str`

**功能**: 將單筆 STM turn 轉為自然語言敘述文字。摘要 turn（T000）以 `[昨日摘要]` 標頭呈現。

**輸出範例**:
```
[08:00]
在咖啡店，看到 2個人、1個杯子。
聽到：Ben 說早安
對 Ben 說：「早安，今天想喝什麼」
內心想：Ben 看起來心情不錯。（情緒：平靜）
```

---

## 模擬使用情境

### 情境一：Amy 第一天在咖啡店與 Ben 對話

```python
from core.memory_stm import STM, make_turn_id

# 初始化角色資料
amy_data = {"name": "Amy", "role": "咖啡師"}
stm = STM(amy_data)

# Day 1, Turn 1：Amy 開始工作
stm.add_turn(
    turn_id    = make_turn_id(1, 1),
    time       = "08:00",
    perception = {"location": "咖啡店", "yolo_desc": "1個人（Ben）、咖啡機", "scene_text": "Ben 走進咖啡店"},
    event      = {"input_text": "Ben: 早安，Amy", "action": "對話", "target": "Ben", "content": "早安！要喝拿鐵嗎？"},
    inner      = {"thought": "Ben 今天來得很早", "emotion": "開心"},
)

# Day 1, Turn 2：Amy 繼續工作
stm.add_turn(
    turn_id    = make_turn_id(1, 2),
    time       = "09:00",
    perception = {"location": "咖啡店", "yolo_desc": "3個人", "scene_text": "早上人潮開始增加"},
    event      = {"input_text": "", "action": "工作", "target": "", "content": ""},
    inner      = {"thought": "今天生意不錯", "emotion": "平靜"},
)

# 取得敘述化文字供 prompt 使用
print(stm.get_today_narrative())
print(f"目前 STM 筆數：{stm.count()}")  # 2
```

### 情境二：第二天睡眠濃縮後縮減 STM

```python
# 睡眠濃縮結束，縮減 STM
stm.shrink_to_summary(
    summary_text = "Amy 今天在咖啡店遇見 Ben（第一位客人），全天生意不錯，心情開心。",
    new_day      = 2,
    keep_recent  = 5,
)

# 查看縮減後狀態
print(stm.count())           # 最多 1（摘要）+ 5（保留）= 6 筆
print(stm.get_recent(3))     # 最近 3 筆非摘要記錄
```

---

## 注意事項

- STM 直接引用 `character_data` 內部 dict，修改 STM 等同修改原始資料，無需額外同步。
- 正常睡眠濃縮應呼叫 `shrink_to_summary()`，而非 `clear()`；`clear()` 僅用於 reset 等特殊情況。
- `get_recent_actions()` 的 `n*2` 多取設計是為了確保排除摘要 turn 後仍能取到足夠的行動動詞。
- `turn_id` 中 `T000` 為保留格式，只用於摘要 turn，請勿在 `add_turn()` 中使用編號 0。
- `get_today_narrative()` 的截斷邏輯保留最新部分（`text[-max_chars:]`），確保 LLM 接收到最近發生的事。
