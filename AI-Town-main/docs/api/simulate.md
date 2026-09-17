# simulate — 離線模擬進入點

> **路徑**: `simulate.py`  
> **職責**: 執行無需 UE5 的多天離線模擬並輸出 HTML 報告

---

## 功能概覽

`simulate.py` 是 AI-Town 的主要**離線執行入口**，設計給不需要 UE5 連線的場景使用，例如演算法驗證、記憶系統測試、報告生成。透過命令列參數控制模擬天數、是否使用真實 AI 模型，以及是否跳過模擬只重新產生報告。

模組的核心是 `FakeLoader` 類別，它實作了與真實 `ModelLoader` 完全相同的介面，但所有模型呼叫都由規則式的 `_fake_response` 函式處理，無需 GPU 即可完整執行模擬流程。`_fake_response` 根據 prompt 內容的關鍵字判斷要回傳哪種格式的假輸出，涵蓋情緒判斷、LTM 摘要、HAM 抽取、時間表生成、深思決策等所有場景。

`main` 函式是整個模擬的協調者：建立 clock 和 manager 後，呼叫 `manager.run_autonomous_days(N)` 執行 N 天的自主模擬，再將結果傳給 `generate_report` 輸出 HTML 報告。完整錯誤處理確保即使模擬中途失敗，仍能產生一份空白報告。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `world.world_clock.WorldClock` | 建立模擬世界時鐘 |
| 依賴 | `agent.manager.AgentManager` | 執行多天自主模擬 |
| 依賴 | `observe.dashboard_html.generate_report` | 生成 HTML 報告 |
| 依賴 | `utils.logger.get_logger` | 取得 `"simulate"` logger |
| 依賴 | `config.world_config.SIMULATION_DEFAULT_DAYS` | 預設模擬天數 |
| 選擇性依賴 | `model.model_loader.ModelLoader` | 真實模型（`--no-model` 時不載入） |

---

## 主要類別 / 函式

### `class FakeLoader`

假模型 loader，完全替代 `ModelLoader`，實作相同介面但所有模型呼叫回傳規則式輸出。適用於無 GPU 環境或快速功能驗證。

#### 屬性
| 屬性 | 型別 | 說明 |
|------|------|------|
| `_loaded` | `bool` | 永遠為 `True` |
| `vision` | `None` | 視覺模型（無）|
| `text` | `None` | 文字模型（無）|
| `fusion` | `None` | 融合模型（無）|

#### `load(self)`
無操作（no-op），介面相容。

#### `is_loaded(self) -> bool`
永遠回傳 `True`。

#### `make_model_fn(self, max_new_tokens=256, temperature=0.0) -> Callable`
**功能**: 回傳一個接受 prompt 字串並回傳假輸出的函式。  
**回傳**: `Callable[[str], str]`

#### `make_deliberate_fn(self) -> Callable`
深思決策模型的假版本，委派給 `make_model_fn()`。

#### `make_dialogue_fn(self) -> Callable`
對話模型的假版本，委派給 `make_model_fn()`。

#### `make_consolidation_fn(self, step: str) -> Callable`
睡眠濃縮各步驟模型的假版本，委派給 `make_model_fn()`。

---

### `_fake_response(prompt: str) -> str`
**功能**: 根據 prompt 中的關鍵字判斷場景並回傳對應的假輸出字串。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `prompt` | `str` | 傳給模型的完整 prompt |

**回傳**: `str` — 對應場景的假模型輸出

**關鍵字對應規則**:

| Prompt 關鍵字 | 回傳內容 |
|--------------|---------|
| `"目前的情緒是什麼"` | `"平靜"` |
| `"用 1-2 句話總結"` | 簡短的一天摘要 |
| `"關係摘要"` | 關係維持原狀的說明 |
| `"抽取"` + `"HAM"` | `"{名字} \| 工作 \| 平凡 \| 無 \| 今天"` |
| `"選出最值得"` | 空字串（不選）|
| `"規劃"` + `"時間表"` | 標準六時段 JSON 時間表 |
| 其他（深思/對話 fallback） | 休息行動 + HAM 格式輸出 |

**範例**:
```python
from simulate import _fake_response

# 測試各種 prompt 場景
print(_fake_response("請問 Amy 目前的情緒是什麼？"))
# "平靜"

print(_fake_response("請為 Ben 規劃明天的時間表..."))
# '[{"time": "07:00", "action": "起床", "location": "公寓"}, ...]'

print(_fake_response("請從以下內容抽取 HAM 命題，涉及 Claire..."))
# "Claire | 工作 | 平凡 | 無 | 今天"
```

---

### `main()`
**功能**: CLI 主入口，解析命令列參數後執行模擬並輸出報告。  
**命令列參數**:

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `--days` | `int` | `SIMULATION_DEFAULT_DAYS` | 模擬天數 |
| `--no-model` | 旗標 | `False` | 使用 FakeLoader，不需 GPU |
| `--report-only` | 旗標 | `False` | 只重新產生報告，不執行模擬 |

---

## 命令列用法

```bash
# 預設：跑 config 設定的天數，使用真實模型
python simulate.py

# 模擬 5 天
python simulate.py --days 5

# 無 GPU 模式，使用假模型（開發/測試用）
python simulate.py --no-model

# 無 GPU 模式 + 指定天數
python simulate.py --days 3 --no-model

# 只重新生成報告（不重跑模擬）
python simulate.py --report-only
```

---

## 模擬使用情境

### 情境一: 以假模型快速驗證 3 天模擬流程

```python
# 等同於執行：python simulate.py --days 3 --no-model
# 直接在程式中呼叫主要步驟：

import sys
sys.argv = ["simulate.py", "--days", "3", "--no-model"]

from simulate import main
main()

# 輸出：
# === AI-Town 離線模擬啟動 ===
# 使用 FakeLoader（無模型模式）
# ...
# === 完成 ===
# 報告：reports/simulation_20260519_143022.html
# 耗時：X.X 秒
# 總 tick：XX
```

### 情境二: 在程式碼中直接使用 FakeLoader 測試特定功能

```python
from simulate import FakeLoader
from world.world_clock import WorldClock
from agent.manager import AgentManager

loader  = FakeLoader()
clock   = WorldClock()
manager = AgentManager(loader, clock)

# 跑 2 天模擬
sim_data = manager.run_autonomous_days(2)

# 驗證結果
print(f"模擬天數：{len(sim_data['days'])}")
total_ticks = sum(len(d["ticks"]) for d in sim_data["days"])
print(f"總 ticks：{total_ticks}")

# 產生報告
from observe.dashboard_html import generate_report
report_path = generate_report(manager, sim_data)
```

---

## 執行流程圖

```
python simulate.py --days 3 --no-model
       │
       ├─ 解析 CLI 參數
       ├─ 建立 FakeLoader（或 ModelLoader）
       ├─ 建立 WorldClock
       ├─ 建立 AgentManager(loader, clock)
       │
       ├─ manager.run_autonomous_days(3)
       │    ├─ Day 1: 各時段 tick → 決策 → 中斷處理 → 對話
       │    ├─ Day 2: ...（同上）
       │    └─ Day 3: ...（同上）+ 睡眠濃縮
       │
       └─ generate_report(manager, sim_data)
            └─ 輸出 reports/simulation_YYYYMMDD_HHMMSS.html
```

---

## 注意事項

- 模組頂部有 Windows 主控台 UTF-8 修正邏輯（`sys.stdout.reconfigure`），確保中文字元在 Windows 環境下正確顯示。
- 若模擬因 `KeyboardInterrupt`（Ctrl+C）或未預期例外中止，`sim_data` 會被設為空結構，仍會嘗試生成一份空白報告，不會完全沒有輸出。
- `--report-only` 模式下，AgentManager 仍然會被初始化並呼叫 `get_observation_data()`，因此角色 JSON 需要存在且格式正確。
- `_fake_response` 使用字串包含（`in`）而非正規表達式做 prompt 分類，較脆弱；若 prompt 模板改變，可能需要更新關鍵字。
- `FakeLoader.make_consolidation_fn` 的 `step` 參數目前被忽略（各步驟回傳相同函式），若不同步驟需要不同輸出格式，需要更新此方法。
