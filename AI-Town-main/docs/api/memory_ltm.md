# memory_ltm — 長期記憶（HAM 命題網絡）管理

> **路徑**: `core/memory_ltm.py`  
> **職責**: 以 HAM 5 元組命題儲存並管理長期語意記憶

---

## 功能概覽

`memory_ltm` 實作 AI-Town 角色的長期記憶（LTM）系統，以 Anderson & Bower（1973）的 HAM（Human Associative Memory）5 元組命題網絡為儲存格式。每一筆記憶命題包含主詞（subject）、關係（relation）、受詞（object）、地點（location）、時間（time），以及強度（strength）和存取次數（access_count）等元數據。

本模組負責純粹的 CRUD 操作、衰減與修剪邏輯，刻意不包含圖譜遍歷（那是 `core/memory_graph.py` 的責任）。衰減公式採用 ACT-R 的「被提取越多、衰減越慢」原則：實際衰減率 = `LTM_DECAY_RATE / (1 + access_count × 0.5)`，確保常被想起的記憶（如與 Ben 的日常互動）比偶發事件（一次性遇到陌生人）更長久保留。

LTM 也維護一個壓縮摘要（`ltm_summary`），由睡眠濃縮的 Step 5 更新，供 Markov Engine 和 prompt 建構器快速取用整體記憶概況，無需每次都遍歷所有命題。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | 讀取 `LTM_DECAY_RATE`、`LTM_FORGET_THRESHOLD` |
| 被依賴 | `agent/manager.py` | 建立 LTM 物件 |
| 被依賴 | `core/consolidation.py` | 寫入命題、衰減、修剪、生成摘要 |
| 被依賴 | `core/memory_graph.py` | 取所有命題建立圖譜結構 |
| 被依賴 | `model/prompt_builder.py` | 條件查詢取相關記憶 |
| 被依賴 | `observe/memory_viewer.py` | 視覺化 LTM 命題 |

---

## 命題資料格式

```python
{
    "id":           "L001",          # 自動產生，格式 L{num:03d}
    "subject":      "Amy",           # 主詞
    "relation":     "遇見",           # 關係動詞
    "object":       "Ben",           # 受詞
    "location":     "咖啡店",         # 可為 None
    "time":         "第3天 早上",     # 可為 None
    "strength":     1.0,             # 記憶強度，0.0 ~ 1.0
    "access_count": 0,               # 被提取次數
    "encoded_day":  3                # 第幾天存入
}
```

---

## 主要類別 / 函式

### `LTM`

**功能**: 長期記憶管理器，直接操作 `Character._data["ltm"]`，提供 HAM 命題的完整 CRUD 及衰減邏輯。

#### `__init__(self, character_data: dict)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_data` | `dict` | 角色完整資料 dict |

初始化時確保 `character_data["ltm"]["ltm_summary"]` 和 `["propositions"]` 兩個子結構存在。

**範例**:
```python
from core.memory_ltm import LTM

amy_data = {"name": "Amy"}
ltm = LTM(amy_data)
```

---

#### `encode(self, subject, relation, obj, location=None, time=None, day=1) -> dict`

**功能**: 寫入單筆 HAM 命題，自動產生唯一 ID，初始 strength = 1.0，access_count = 0。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `subject` | `str` | 主詞（角色名、地點或概念） |
| `relation` | `str` | 關係動詞 |
| `obj` | `str` | 受詞 |
| `location` | `str \| None` | 發生地點（可省略） |
| `time` | `str \| None` | 發生時間（可省略） |
| `day` | `int` | 存入時的天數 |

**回傳**: `dict` — 寫入的命題物件

**範例**:
```python
prop = ltm.encode(
    subject  = "Amy",
    relation = "遇見",
    obj      = "David",
    location = "公園",
    time     = "第2天 下午",
    day      = 2,
)
# {"id": "L001", "subject": "Amy", "relation": "遇見", ...}
```

---

#### `encode_batch(self, propositions: list, day: int = 1)`

**功能**: 批次寫入命題列表，睡眠濃縮 Step 4 使用。每個元素須含 subject/relation/object，location 和 time 可省略。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `propositions` | `list[dict]` | HAM 命題列表 |
| `day` | `int` | 存入時的天數 |

**範例**:
```python
ltm.encode_batch([
    {"subject": "Amy", "relation": "喜歡", "object": "拿鐵"},
    {"subject": "Amy", "relation": "認識", "object": "Claire", "location": "餐廳"},
], day=3)
```

---

#### `retrieve(self, query_subject=None, query_relation=None, query_object=None, query_location=None, query_time=None, top_k=10, update_access=False) -> list`

**功能**: 條件查詢命題，所有非 None 的條件為 AND 關係。`update_access=True` 時命中命題的 access_count 加 1 且 strength 重置為 1.0。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `query_subject` | `str \| None` | 主詞過濾（精確匹配） |
| `query_relation` | `str \| None` | 關係過濾 |
| `query_object` | `str \| None` | 受詞過濾 |
| `query_location` | `str \| None` | 地點過濾 |
| `query_time` | `str \| None` | 時間過濾 |
| `top_k` | `int` | 最多回傳筆數（預設 10） |
| `update_access` | `bool` | 是否更新 access_count（真實「想起」時設 True） |

**回傳**: `list[dict]` — 符合條件的命題列表

**範例**:
```python
# 找 Amy 在咖啡店的所有記憶
results = ltm.retrieve(
    query_subject  = "Amy",
    query_location = "咖啡店",
    update_access  = True,  # 真的「想起來」了
)
```

---

#### `get_summary(self) -> str` / `set_summary(self, summary: str)`

**功能**: 讀取或更新 LTM 壓縮摘要文字，由濃縮 Step 5 呼叫 `set_summary()`。

**範例**:
```python
summary = ltm.get_summary()
# "Amy 認識 Ben（咖啡店常客）、David（同事）、Claire（餐廳老闆）..."

ltm.set_summary("Amy 在咖啡店工作已兩天，與 Ben 建立日常打招呼的習慣。")
```

---

#### `apply_decay(self)`

**功能**: 對所有命題套用衰減，在睡眠濃縮 Step 10 呼叫。

衰減公式（`LTM_DECAY_RATE` 預設 0.05）：
```
actual_decay = LTM_DECAY_RATE / (1 + access_count × 0.5)
strength = max(0.0, strength - actual_decay)
```

實際效果：
- `access_count = 0` → 每天衰減 0.05
- `access_count = 2` → 每天衰減 0.025
- `access_count = 10` → 每天衰減 ≈ 0.008

---

#### `prune(self) -> int`

**功能**: 刪除 strength 低於 `LTM_FORGET_THRESHOLD` 的命題（遺忘機制），回傳刪除筆數。

**回傳**: `int` — 被刪除的命題數

**範例**:
```python
deleted = ltm.prune()
print(f"遺忘了 {deleted} 筆記憶")
```

---

#### `touch(self, prop_id: str)`

**功能**: 標記命題為「剛被提取」，access_count + 1，strength 重置為 1.0。由 `memory_graph` 的擴散激活完成後批次呼叫。

---

#### `to_text(self, props: list = None) -> str`

**功能**: 命題列表轉為 pipe 分隔格式文字，與模型輸入/輸出格式一致。

**輸出範例**:
```
Amy | 遇見 | David | 咖啡店 | 早上
Ben | 工作 | 超市 | 無 | 無
```

---

#### `to_readable(self, props: list = None) -> str`

**功能**: 命題列表轉為自然語言（供觀察工具或 log 使用）。

**輸出範例**:
```
- Amy 在咖啡店 早上 遇見 David
- Ben 工作 超市
```

---

## 模擬使用情境

### 情境一：Amy 第一天結束後的 LTM 寫入

```python
from core.memory_ltm import LTM

amy_data = {"name": "Amy"}
ltm = LTM(amy_data)

# 睡眠濃縮 Step 4：批次寫入今日重要命題
ltm.encode_batch([
    {"subject": "Amy", "relation": "遇見",  "object": "Ben",   "location": "咖啡店", "time": "第1天 早上"},
    {"subject": "Amy", "relation": "服務",  "object": "Ben",   "location": "咖啡店"},
    {"subject": "Amy", "relation": "認識",  "object": "Claire", "location": "餐廳"},
], day=1)

# 睡眠濃縮 Step 5：設定 LTM 摘要
ltm.set_summary("Amy 在咖啡店遇見 Ben，並認識了餐廳老闆 Claire。")

print(f"LTM 共 {ltm.count()} 筆命題")
print(ltm.to_readable())
```

### 情境二：第 20 天後的記憶衰減與遺忘

```python
# 模擬 20 天的衰減
for day in range(20):
    ltm.apply_decay()

pruned = ltm.prune()
print(f"遺忘了 {pruned} 筆記憶（strength 低於閾值）")

# 查詢 Amy 還記得的與 Ben 相關的記憶
still_remember = ltm.retrieve(query_object="Ben", top_k=5)
for p in still_remember:
    print(f"  {p['subject']} {p['relation']} {p['object']}  強度={p['strength']:.3f}  存取={p['access_count']}次")
```

---

## 注意事項

- `_next_id()` 使用已有 ID 的最大值 + 1，確保 `prune()` 後不會產生重複 ID。
- `retrieve()` 的 `update_access` 預設為 `False`：觀察/debug 查詢不應計入提取次數，只有角色真正「想起來」時才傳 `True`。
- `touch()` 在 access_count 更新的同時會將 strength 重置為 1.0，模擬「提取強化記憶」效果。
- LTM 直接引用 `character_data` 內部 dict，不做資料複製，修改命題屬性會直接反映在原始資料上。
- `to_text()` 輸出格式與模型的 HAM 輸出格式相同（pipe 分隔），便於直接作為 prompt 輸入。
