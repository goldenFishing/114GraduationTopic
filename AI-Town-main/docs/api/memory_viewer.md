# memory_viewer — 記憶資料視覺化準備工具

> **路徑**: `observe/memory_viewer.py`  
> **職責**: 將 LTM/STM/過程日誌轉換為前端視覺化格式

---

## 功能概覽

`memory_viewer` 模組負責將 AI-Town 內部的記憶資料結構轉換成前端視覺化函式庫（vis.js、chart.js）所需的資料格式。本模組不直接依賴任何前端技術，只負責資料的轉換與整理，確保關注點分離。

三個主要函式各自對應一種視覺化場景：`ltm_to_vis_graph` 將 MemoryGraph 轉為互動式節點圖格式；`stm_to_timeline` 將短期記憶（STM）的 turn list 轉為時間軸可讀格式；`process_log_to_curves` 將每 tick 的困惑度指標序列化為折線圖所需的多維度數值陣列。

節點的大小（`value`）代表該概念在記憶中的平均強度，邊的粗細（`value`）反映命題強度（`strength * 5`，最小值為 1），視覺上直觀呈現記憶的重要程度。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `MemoryGraph`（執行期依賴） | 呼叫其 `get_all_nodes()` / `get_all_edges()` 方法 |
| 被依賴 | `observe.dashboard_html` | 使用本模組轉換後的資料渲染 vis.js 圖和 chart.js 折線圖 |
| 被依賴 | 前端 vis.js | 使用 `ltm_to_vis_graph` 的回傳格式 |
| 被依賴 | 前端 chart.js | 使用 `process_log_to_curves` 的回傳格式 |

---

## 主要類別 / 函式

### `ltm_to_vis_graph(memory_graph) -> dict`
**功能**: 將 MemoryGraph 物件轉換為 vis.js / cytoscape.js 相容的節點與邊格式，含中文 tooltip 說明。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `memory_graph` | `MemoryGraph` | 角色的長期記憶圖物件，需實作 `get_all_nodes()` 和 `get_all_edges()` |

**回傳**: `dict` — 包含 `"nodes"` 和 `"edges"` 兩個 list 的字典

節點格式（每筆）:
```python
{
    "id":    "node_001",
    "label": "Amy",
    "group": "person",    # person / location / concept
    "value": 0.8,         # 決定節點大小，= 平均 strength
    "title": "Amy\n類型：person\n涉及命題：5 筆\n平均強度：0.8"
}
```

邊格式（每筆）:
```python
{
    "from":   "node_001",
    "to":     "node_002",
    "label":  "喜歡",
    "value":  4,          # 線粗 1~5，= int(strength * 5)
    "title":  "Amy → 喜歡 → 閱讀\n地點：圖書館\n時間：下午\n強度：0.8\nID：p001",
    "arrows": "to"
}
```

**範例**:
```python
from observe.memory_viewer import ltm_to_vis_graph

# amy_agent.memory_graph 是 Amy 的 MemoryGraph 實例
vis_data = ltm_to_vis_graph(amy_agent.memory_graph)
print(f"節點數：{len(vis_data['nodes'])}")
print(f"邊數：{len(vis_data['edges'])}")
# 可直接傳給 vis.js：
# new vis.Network(container, {nodes: vis_data.nodes, edges: vis_data.edges}, options)
```

---

### `stm_to_timeline(stm_turns: list) -> list`
**功能**: 將角色的 STM turn 清單攤平成時間軸可讀的資料，提取感知、事件、內心狀態等關鍵欄位。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `stm_turns` | `list` | 角色 STM 的原始 turn list，每筆包含 `turn_id`、`time`、`perception`、`event`、`inner` 等欄位 |

**回傳**: `list` — 每筆包含以下欄位的 dict 清單:

| 欄位 | 來源路徑 | 說明 |
|------|----------|------|
| `turn_id` | `turn["turn_id"]` | 回合識別碼 |
| `time` | `turn["time"]` | 模擬時間字串 |
| `location` | `turn["perception"]["location"]` | 角色所在地點 |
| `yolo_desc` | `turn["perception"]["yolo_desc"]` | YOLO 視覺描述 |
| `input` | `turn["event"]["input_text"]` | 外部輸入文字 |
| `action` | `turn["event"]["action"]` | 決策行動 |
| `target` | `turn["event"]["target"]` | 行動對象 |
| `content` | `turn["event"]["content"]` | 行動內容/對話 |
| `thought` | `turn["inner"]["thought"]` | 內心獨白 |
| `emotion` | `turn["inner"]["emotion"]` | 情緒狀態 |

**範例**:
```python
from observe.memory_viewer import stm_to_timeline

# ben_data["stm"] 是 Ben 的 STM turn list
timeline = stm_to_timeline(ben_data["stm"])
for entry in timeline:
    print(f"{entry['time']} [{entry['location']}] {entry['action']} → {entry['emotion']}")
# 08:00 [公寓] 起床 → 平靜
# 09:00 [辦公室] 工作 → 專注
```

---

### `process_log_to_curves(process_log: list) -> dict`
**功能**: 將 process_log 轉成 chart.js 折線圖所需的多維度數值序列，包含 U/K/S/C 四個困惑度指標和決策模式。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `process_log` | `list` | 每 tick 的過程日誌，每筆需含 `turn_id`、`confusion`（含 U/K/S/C）、`decision_mode` |

**回傳**: `dict` — 格式如下:
```python
{
    "labels":   ["D1T06:00", "D1T07:00", ...],  # X 軸標籤
    "U_values": [0.2, 0.35, ...],               # 不確定性
    "K_values": [0.1, 0.6, ...],                # 困惑度峰值
    "S_values": [0.3, 0.4, ...],                # 情境複雜度
    "C_values": [0.25, 0.5, ...],               # 最終 C 值
    "modes":    ["intuitive", "deliberate", ...]# 決策模式
}
```

**範例**:
```python
from observe.memory_viewer import process_log_to_curves

curves = process_log_to_curves(claire_process_log)
# 找出所有觸發深思模式的時間點
deliberate_times = [
    curves["labels"][i]
    for i, mode in enumerate(curves["modes"])
    if mode == "deliberate"
]
print(f"Claire 觸發深思 {len(deliberate_times)} 次：{deliberate_times}")
```

---

## 模擬使用情境

### 情境一: 取得 David 的 LTM 圖譜資料並檢查節點分組

```python
from observe.memory_viewer import ltm_to_vis_graph

# david_memory_graph 是 David 的 MemoryGraph 實例
vis_data = ltm_to_vis_graph(david_memory_graph)

# 分析各類型節點數量
from collections import Counter
group_counts = Counter(n["group"] for n in vis_data["nodes"])
print(group_counts)
# Counter({'person': 4, 'concept': 7, 'location': 3})

# 找強度最高的邊
strongest = max(vis_data["edges"], key=lambda e: e["value"])
print(f"最強記憶：{strongest['title']}")
```

### 情境二: 將 Amy 的 STM 時間軸轉換後找出情緒低落的時刻

```python
from observe.memory_viewer import stm_to_timeline

timeline = stm_to_timeline(amy_data["stm"])

# 找出情緒為「憂鬱」或「焦慮」的 tick
bad_moods = [
    entry for entry in timeline
    if entry["emotion"] in ["憂鬱", "焦慮", "沮喪"]
]
for entry in bad_moods:
    print(f"{entry['time']} - {entry['thought']}")
```

---

## 注意事項

- `ltm_to_vis_graph` 直接呼叫 `memory_graph.get_all_nodes()` 和 `memory_graph.get_all_edges()`，傳入物件必須實作這兩個方法，否則會拋出 `AttributeError`。
- `process_log_to_curves` 回傳的 dict 沒有 `"thresholds"` 欄位（雖然函式內部有此欄位的設計），閾值資料改由 `dashboard_html._build_char_confusion` 直接從 `sim_data` 提取。
- 邊的 `value` 計算公式為 `max(1, int(strength * 5))`，強度為 0 的邊線粗為 1，強度為 1.0 的邊線粗為 5。
- `stm_to_timeline` 使用 `.get()` 進行安全存取，任何欄位缺失都會回傳空字串，不會拋出 `KeyError`。
