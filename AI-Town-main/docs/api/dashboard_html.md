# dashboard_html — HTML 模擬報告生成器

> **路徑**: `observe/dashboard_html.py`  
> **職責**: 將模擬資料轉換為完整的七分頁互動 HTML 報告

---

## 功能概覽

`dashboard_html` 模組是 AI-Town 觀察層的核心輸出元件，負責將整個模擬過程的資料轉換成一份自含式（standalone）的 HTML 儀表板。報告包含七個互動分頁，涵蓋角色總覽、每日決策日誌、時間表、LTM 記憶圖譜、困惑度曲線、對話記錄、睡眠濃縮報告。

HTML 報告引用 CDN 上的 vis.js（用於記憶圖譜的互動節點圖）和 chart.js（用於困惑度折線圖），不需要任何本地端 JavaScript 打包。所有模擬資料以 JSON 格式嵌入 HTML `<script>` 標籤，因此產出的單一 HTML 檔案可以離線開啟、分享，無需後端伺服器。

模組內部依職責拆分為多個私有函式（前綴 `_`）：B 區負責從 `sim_data` 提取並建構各分頁所需資料、E 區各自渲染一個分頁的 HTML 片段、G 區提供 CSS、H 區提供 JavaScript。公開 API 只有 `generate_report` 和 `ltm_to_vis_graph_from_data` 兩個函式。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | 讀取 `REPORT_DIR`（輸出目錄）和 `CHARACTER_NAMES`（代號→名字） |
| 依賴 | `observe.dialogue_log` | 呼叫 `format_dialogue_history` 格式化對話記錄 |
| 依賴 | `json`、`os`、`datetime` | 標準函式庫 |
| 被依賴 | `simulate.py` | 呼叫 `generate_report(manager, sim_data)` 產生報告 |
| 前端依賴 | vis.js（CDN） | 互動式 LTM 記憶節點圖 |
| 前端依賴 | chart.js 4.4.0（CDN） | 困惑度折線圖 |

---

## 主要類別 / 函式

### `generate_report(manager, simulation_data: dict, output_path: str = None) -> str`
**功能**: 生成完整的 HTML 儀表板並寫入磁碟，這是本模組唯一的主要公開入口。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `manager` | `AgentManager` | 模擬管理器，用於取得最終 LTM / 狀態（呼叫 `get_observation_data()`） |
| `simulation_data` | `dict` | `manager.run_autonomous_days()` 的回傳值，包含所有 ticks 的歷史資料 |
| `output_path` | `str \| None` | 自訂輸出路徑；`None` 時自動命名為 `reports/simulation_YYYYMMDD_HHMMSS.html` |

**回傳**: `str` — 實際寫入的檔案路徑  
**範例**:
```python
from observe.dashboard_html import generate_report

# sim_data 來自 manager.run_autonomous_days(3)
report_path = generate_report(manager, sim_data)
print(f"報告已生成：{report_path}")
# 報告已生成：reports/simulation_20260519_143022.html

# 自訂路徑
report_path = generate_report(manager, sim_data, "output/my_report.html")
```

---

### `ltm_to_vis_graph_from_data(nodes: list, edges: list) -> dict`
**功能**: 公開的相容性別名，將原始 LTM 節點和邊列表轉換為 vis.js 格式。這是 `_ltm_to_vis` 的公開版本，保留向後相容。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `nodes` | `list` | LTM 節點 list，每筆含 `id`、`label`、`type`、`value` |
| `edges` | `list` | LTM 邊 list，每筆含 `from`、`to`、`label`、`strength` |

**回傳**: `dict` — `{"nodes": [...], "edges": [...]}` 的 vis.js 格式

---

### 內部資料建構函式（B 區）

#### `_build_char_tick_log(sim_data) -> dict`
從 `sim_data` 提取每個角色的每 tick 決策記錄，包含行動、困惑度 C/K、Markov 機率分布（前 6）、是否為重大事件。回傳 `{code: [tick_dict, ...]}` 格式。

#### `_build_char_confusion(sim_data) -> dict`
從 `sim_data` 提取每個角色的困惑度時序資料（U/K/S/C/閾值/模式），供 chart.js 折線圖使用。回傳 `{code: {labels, U, K, S, C, modes, thresholds}}` 格式。

#### `_build_dialogue_list(sim_data) -> list`
攤平所有天、所有 tick 的對話記錄，加上 `day` 和 `time` 欄位，並呼叫 `format_dialogue_history` 格式化。

#### `_build_sleep_reports(sim_data) -> list`
收集所有天的睡眠濃縮報告，加上 `day` 和 `code` 欄位。

#### `_compute_stats(sim_data, final_state, dialogue_list) -> dict`
計算整體統計數字：總天數、總 ticks、模型呼叫次數（深思模式）、對話嘗試次數、對話接受次數。

---

### 分頁渲染函式（E 區）

| 函式 | 分頁 | 說明 |
|------|------|------|
| `_render_overview(final_state, stats)` | 總覽 | 角色最終狀態表格 + 統計卡片 |
| `_render_daily_log(final_state, char_tick_log, codes)` | 每日日誌 | 每 tick 決策卡片（含 Markov 機率條）|
| `_render_tick_entry(tick)` | — | 單一 tick 卡片 HTML 片段 |
| `_render_schedule(final_state, sleep_reports, codes)` | 時間表 | 每角色時間表表格 |
| `_render_ltm(final_state, codes)` | LTM 圖譜 | vis.js 容器 div |
| `_render_confusion(final_state, codes)` | 困惑度曲線 | chart.js canvas |
| `_render_dialogue(dialogue_list)` | 對話記錄 | 接受/拒絕對話卡片清單 |
| `_render_sleep(sleep_reports, final_state)` | 睡眠濃縮 | 睡眠報告卡片（含 HAM/LTM 統計徽章） |

---

## 模擬使用情境

### 情境一: 模擬 3 天後生成報告

```python
from world.world_clock import WorldClock
from agent.manager import AgentManager
from observe.dashboard_html import generate_report
from simulate import FakeLoader

loader  = FakeLoader()
clock   = WorldClock()
manager = AgentManager(loader, clock)

sim_data    = manager.run_autonomous_days(3)
report_path = generate_report(manager, sim_data)
print(f"報告路徑：{report_path}")
# 在瀏覽器開啟 report_path 即可看到七分頁儀表板
```

### 情境二: 只重新生成報告（不重跑模擬）

```python
from observe.dashboard_html import generate_report

# 空的 sim_data，只用 final_state
sim_data = {"days": [], "total_ticks": 0}
report_path = generate_report(manager, sim_data, output_path="reports/quick_check.html")
# 報告只有總覽分頁有資料，其他分頁顯示「無記錄」
```

---

## HTML 報告結構

```
AI-Town 模擬報告
├── 分頁 1：📊 總覽         — 角色最終狀態表 + 統計數字
├── 分頁 2：📅 每日日誌      — 每 tick 決策（直覺機率條 / 深思模型輸出）
├── 分頁 3：🗓 時間表        — 每角色作息計畫（睡眠後更新）
├── 分頁 4：🕸 LTM 圖譜      — vis.js 互動節點圖（可拖移、縮放、懸停查詳情）
├── 分頁 5：📈 困惑度曲線    — chart.js 折線（U/K/S/C + 閾值）
├── 分頁 6：💬 對話記錄      — 按接受/拒絕分組的對話卡片
└── 分頁 7：🌙 睡眠濃縮      — HAM 抽取量、LTM 變化、情緒轉換、隔天計畫
```

---

## 注意事項

- 報告為純 HTML 單一檔案，引用外部 CDN 資源（vis.js、chart.js），**離線環境**需要確保可存取 `https://unpkg.com` 和 `https://cdn.jsdelivr.net`。
- LTM 圖譜（vis.js）採用**延遲初始化**：只有在使用者切換到「LTM 圖譜」分頁時才執行渲染，避免頁面載入時全部初始化導致卡頓。
- 困惑度圖表（chart.js）在 `DOMContentLoaded` 時**立即初始化**，因為 canvas 已有明確的 `width/height` 屬性，不依賴容器可見性。
- `_render_tick_entry` 對深思模式（deliberate）和直覺模式（intuitive）渲染不同的 UI：直覺模式顯示 Markov 機率條，深思模式顯示模型思考（thought）和對話內容（content）。
- 多角色切換是純 JavaScript 的 CSS class 切換，不需要後端請求。
