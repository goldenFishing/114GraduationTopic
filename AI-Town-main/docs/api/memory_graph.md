# memory_graph — HAM 圖譜遍歷與擴散激活

> **路徑**: `core/memory_graph.py`  
> **職責**: 在 LTM 命題上建圖並執行擴散激活查詢

---

## 功能概覽

`memory_graph` 在 LTM 的命題資料之上建立圖譜結構，實作 Anderson（1983）的擴散激活理論（Spreading Activation Theory）。LTM 負責純粹的資料儲存，而本模組負責「如何從記憶中智慧地檢索相關資訊」——這是 AI-Town 角色能夠在對話時想起遠端相關記憶的核心機制。

在圖譜中，每個命題的 subject 和 object 都是節點，命題本身是帶標籤的邊（有向邊）。擴散激活從一個或多個起始節點出發，沿著邊向外擴散，每跳乘以衰減係數（`HAM_ACTIVATION_DECAY = 0.4`）。根據實證研究：1 跳約 80% 活化（`0.4^0 = 1.0`）、2 跳約 40% 活化（`0.4^1 = 0.4`），超過閾值（`HAM_RETRIEVE_THRESHOLD = 0.3`）的命題才會被收集。

除了擴散激活，本模組還提供反向組句（命題列表 → 自然語言敘述）及視覺化資料介面（節點/邊資料供前端 vis.js / cytoscape.js 使用）。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `core/memory_ltm.py` | 取得所有命題執行圖譜遍歷 |
| 依賴 | `config.world_config` | 讀取圖譜遍歷常數（max_hops、decay、threshold） |
| 依賴 | `config.action_list` | 取得 `VALID_LOCATIONS` 供節點型別判斷 |
| 被依賴 | `model/prompt_builder.py` | 深思/對話組 prompt 時取相關記憶敘述 |
| 被依賴 | `core/consolidation.py` | 更新關係時取與某角色相關的命題 |
| 被依賴 | `observe/memory_viewer.py` | 視覺化 LTM 圖譜 |

---

## 圖譜結構說明

每條 HAM 命題即為一條有向邊：
```
Amy ──[遇見]──> Ben
        ↑
    location: 咖啡店
    time: 第3天 早上
    strength: 0.85
```

擴散激活從起始節點（如 `"Amy"`）出發，找到連接 Amy 的所有命題，再從另一端節點（如 `"Ben"`）繼續向外擴散，活化值每跳乘以 `0.4`。

---

## 主要類別 / 函式

### `MemoryGraph`

**功能**: 在 LTM 上建立圖譜結構，提供擴散激活查詢與反向組句功能。

#### `__init__(self, ltm)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `ltm` | `LTM` | `core.memory_ltm.LTM` 實例 |

**範例**:
```python
from core.memory_ltm import LTM
from core.memory_graph import MemoryGraph

ltm = LTM(amy_data)
graph = MemoryGraph(ltm)
```

---

#### `spreading_retrieve(self, query_nodes, max_hops=2, activation_decay=0.4, threshold=0.3, top_k=20, min_strength=None, update_access=True) -> list`

**功能**: 核心擴散激活方法。從起始節點集合出發，以 BFS 方式向外擴散，收集活化值超過閾值的命題，按活化值降序排列後回傳。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `query_nodes` | `list[str]` | 起始節點列表（如角色名、地點名） |
| `max_hops` | `int` | 最多跳幾跳（預設 `HAM_TRAVERSE_MAX_HOPS = 2`） |
| `activation_decay` | `float` | 每跳活化衰減係數（預設 `HAM_ACTIVATION_DECAY = 0.4`） |
| `threshold` | `float` | 活化值門檻（預設 `HAM_RETRIEVE_THRESHOLD = 0.3`） |
| `top_k` | `int` | 最多回傳筆數（預設 20） |
| `min_strength` | `float \| None` | 命題 strength 最低門檻（`None` = 不過濾） |
| `update_access` | `bool` | 命中時是否呼叫 `ltm.touch()`（真實提取設 True，觀察查詢設 False） |

**回傳**: `list[dict]` — 格式 `[{"prop": dict, "activation": float, "hops": int}, ...]`，按 activation 降序排列

**活化值計算範例**:
- 直接命中（hop=1）：`activation_decay^0 = 1.0`
- 1 跳後（hop=2）：`activation_decay^1 = 0.4`
- 低於 threshold（0.3）的命題不回傳

**範例**:
```python
# Amy 正在與 David 對話，查詢相關記憶
results = graph.spreading_retrieve(
    query_nodes   = ["Amy", "David", "咖啡店"],
    max_hops      = 2,
    top_k         = 10,
    update_access = True,  # 真實提取，更新 access_count
)

for r in results:
    p = r["prop"]
    print(f"[activation={r['activation']:.2f}, hop={r['hops']}] {p['subject']} {p['relation']} {p['object']}")
```

---

#### `get_related_to(self, node: str, max_hops: int = 2, update_access: bool = False) -> list`

**功能**: 便利方法，找出與單一節點直接相關的所有命題。回傳原始 prop dict 列表（非包裝格式）。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `node` | `str` | 查詢節點名稱 |
| `max_hops` | `int` | 最多跳幾跳 |
| `update_access` | `bool` | 預設 `False`（程式內部查詢，不計算提取次數） |

**回傳**: `list[dict]` — 原始命題 dict 列表

**範例**:
```python
ben_related = graph.get_related_to("Ben")
# 回傳所有包含 Ben 為 subject 或 object 的命題
```

---

#### `auto_query_nodes(self, character_name, partner_name="", co_located=None, recent_stm_turns=None, location="") -> list`

**功能**: 根據當前情境自動組成查詢節點集合，將角色自身、對話對象、同地點角色、當前位置、STM 最近 3 筆中出現的角色名字全部納入，去重後回傳。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 角色自身名字 |
| `partner_name` | `str` | 對話對象名字（可空） |
| `co_located` | `list[str] \| None` | 同地點的角色名字列表 |
| `recent_stm_turns` | `list[dict] \| None` | 最近 STM turns（只看後 3 筆） |
| `location` | `str` | 當前位置名稱 |

**回傳**: `list[str]` — 去重後的查詢節點列表

**範例**:
```python
nodes = graph.auto_query_nodes(
    character_name   = "Amy",
    partner_name     = "David",
    co_located       = ["Ben", "Emma"],
    location         = "咖啡店",
    recent_stm_turns = stm.get_recent(3),
)
# nodes 可能為 ["Amy", "David", "Ben", "Emma", "咖啡店"]
```

---

#### `propositions_to_narrative(self, items: list, character_name: str) -> str`

**功能**: 將命題列表轉為自然語言敘述，供 prompt 注入。主詞或受詞等於 `character_name` 時自動替換為「你」，增強 LLM 的代入感。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `items` | `list` | `spreading_retrieve` 回傳格式 或 原始 prop dict 列表（兩者皆可） |
| `character_name` | `str` | 角色名字（自我引用會被替換為「你」） |

**回傳**: `str` — 自然語言敘述，無記憶時回傳 `"（沒有相關記憶）"`

**輸出範例**:
```
你第3天早上在咖啡店遇見Ben。你認識Claire。Ben在超市工作。
```

---

#### `get_all_nodes(self) -> list`

**功能**: 回傳所有圖譜節點的視覺化資料，供前端 vis.js / cytoscape.js 使用。節點型別依啟發式規則判斷：人名（person）、地點（location）或概念（concept）。

**回傳**: `list[dict]` — 每個節點包含：
```python
{
    "id":         "Amy",
    "label":      "Amy",
    "type":       "person",    # "person" | "location" | "concept"
    "value":      0.85,        # 涉及此節點的命題平均 strength
    "prop_count": 12,          # 涉及此節點的命題數
}
```

---

#### `get_all_edges(self) -> list`

**功能**: 回傳所有圖譜邊（即 HAM 命題），供前端視覺化使用。

**回傳**: `list[dict]` — 每條邊包含：
```python
{
    "from":     "Amy",
    "to":       "Ben",
    "label":    "遇見",
    "strength": 0.8,
    "prop_id":  "L001",
    "location": "咖啡店",
    "time":     "早上",
}
```

---

## 模擬使用情境

### 情境一：Amy 與 David 對話，從記憶中提取相關命題

```python
from core.memory_ltm import LTM
from core.memory_graph import MemoryGraph

amy_data = {"name": "Amy"}
ltm = LTM(amy_data)

# 預設 Amy 已有若干記憶
ltm.encode_batch([
    {"subject": "Amy",   "relation": "認識", "object": "David",  "location": "咖啡店", "time": "第1天"},
    {"subject": "David", "relation": "工作", "object": "辦公室"},
    {"subject": "Amy",   "relation": "討論", "object": "新菜單", "location": "咖啡店"},
    {"subject": "Ben",   "relation": "喜歡", "object": "拿鐵",   "location": "咖啡店"},
], day=3)

graph = MemoryGraph(ltm)

# 查詢與 David 和咖啡店相關的記憶
results = graph.spreading_retrieve(
    query_nodes   = ["David", "咖啡店"],
    update_access = True,
)

# 轉為 prompt 可用的敘述
narrative = graph.propositions_to_narrative(results, character_name="Amy")
print(narrative)
# 你第1天在咖啡店認識David。David工作辦公室。你在咖啡店討論新菜單。
```

### 情境二：視覺化整個記憶圖譜

```python
nodes = graph.get_all_nodes()
edges = graph.get_all_edges()

# nodes 範例
# [{"id": "Amy", "type": "person", "value": 0.9, "prop_count": 5}, ...]
# edges 範例
# [{"from": "Amy", "to": "Ben", "label": "遇見", "strength": 0.8}, ...]

# 可直接傳入前端 vis.js Network
print(f"節點數：{len(nodes)}，邊數：{len(edges)}")
```

---

## 注意事項

- `spreading_retrieve()` 使用 BFS 而非遞迴，每次迭代都維護一個前沿節點集合（`current_frontier`），避免重複遍歷。
- 同一命題可能從多條路徑被命中，系統取最大活化值（`max`）而非累加，符合 ACT-R 的活化競爭機制。
- `update_access=True` 時，命中的命題 strength 會重置為 1.0（`ltm.touch()`），視覺化和 debug 查詢應使用 `update_access=False` 以避免污染記憶強度。
- `auto_query_nodes()` 掃描最近 3 筆 STM turns 中的角色名字，依賴 `config.world_config.CHARACTER_NAMES` 字典，需確保角色名配置正確。
- `get_all_nodes()` 的節點型別判斷依賴 `CHARACTER_NAMES` 和 `VALID_LOCATIONS`，位於這兩個集合外的節點一律歸類為 `"concept"`。
