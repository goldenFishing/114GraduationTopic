# AgentManager — 多角色協調器

> **路徑**: `agent/manager.py`  
> **職責**: 協調所有角色的 tick 執行、對話配對、中斷分派、睡眠管理

---

## 功能概覽

`AgentManager` 是整個模擬的指揮中心。它在初始化時載入所有角色的 `Character`、`STM`、`LTM`、`MemoryGraph` 與 `Agent` 物件，並持有唯一的 `ModelLoader` 和 `InterruptHandler`，供所有角色共用。

每個 tick 透過 `run_tick()` 完成，內部分為兩個 Phase：**Phase 1（執行）** 執行上一個 tick 決定的 `pending_action`，**Phase 2（決策）** 為下一個 tick 決定新的行動。對話在 Phase 1 中以配對方式處理，確保雙方在同一個 tick 完成完整的對話循環（最多 `DIALOGUE_MAX_TURNS` 輪）。

多日自主模擬透過 `run_autonomous_days()` 進行：每天執行至所有角色入睡或達 `MAX_TICKS_PER_DAY` 上限，到達上限後強制剩餘角色入睡，推進到下一天。Manager 也提供 `push_interrupt()` 供外部（YOLO 感知層）注入中斷事件，以及 `get_observation_data()` 供 dashboard 查詢完整狀態。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `agent.agent.Agent` | 各角色的推論代理人 |
| 依賴 | `agent.interrupt.InterruptHandler` | 中斷佇列管理 |
| 依賴 | `core.character.Character` | 角色狀態物件 |
| 依賴 | `core.memory_stm.STM` | 短期記憶 |
| 依賴 | `core.memory_ltm.LTM` | 長期記憶 |
| 依賴 | `core.memory_graph.MemoryGraph` | 記憶圖譜 |
| 依賴 | `core.markov_engine.format_probs_display` | 日誌顯示用 |
| 依賴 | `model.prompt_io.PromptBuilder` | Prompt 組裝 |
| 依賴 | `world.world_clock.WorldClock` | 時鐘（tick 推進、時間查詢） |
| 依賴 | `utils.file_io` | 角色載入與存檔 |
| 依賴 | `utils.logger` | 結構化日誌 |
| 依賴 | `config.world_config` | 角色代號/名稱、對話常數、睡眠動作等 |
| 被依賴 | `simulate.py` | 呼叫 `run_autonomous_days()` |
| 被依賴 | `main.py` | 呼叫 `run_tick()`（接 UE 引擎） |
| 被依賴 | `ws_server.py` | 呼叫 `push_interrupt()` |

---

## 主要類別 / 函式

### `AgentManager`

**功能**: 多角色協調器，所有角色共用同一個 `ModelLoader` 與 `InterruptHandler`。

#### `__init__(self, loader, clock)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `loader` | `ModelLoader` | 已初始化（可未 loaded）的模型載入器 |
| `clock` | `WorldClock` | 世界時鐘實例 |

初始化時從檔案系統讀取所有角色資料，為每位角色建立完整的物件樹（`Character → STM → LTM → MemoryGraph → PromptBuilder → Agent`）。

---

#### `run_tick(self, perception_input, external_input) -> dict`

**功能**: 執行一個完整 tick 的七步流程。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `perception_input` | `dict` \| `None` | `{code: {"location", "yolo_desc", "scene_text"}}`；`None` 則自動補預設 perception |
| `external_input` | `dict` \| `None` | `{code: "input_text"}`；`None` 則無外部訊息 |

**七步流程**:

1. 所有角色重置 slot state
2. 強制起床/睡覺時間檢查（`_check_force_wake_sleep()`）
3. 補齊缺少的 perception（使用角色當前位置 + 時鐘場景前綴）
4. 中斷處理（`_handle_interrupts()`）
5. **Phase 1**：執行 pending_action（`_execute_phase()`）
6. **Phase 2**：決策下一 tick 行動（`_decide_phase()`）
7. STM 安全閥檢查 → 推進時鐘 → 收集對話歷史

**回傳**: tick 報告 dict

```python
{
    "tick":           int,        # 今天的第幾個 tick
    "time":           "HH:MM",
    "day":            int,
    "execute":        {code: {...}},  # Phase 1 結果
    "decide":         {code: {...}},  # Phase 2 結果
    "interrupts":     {code: {...}},
    "dialogues":      list,           # 對話歷史
    "sleeping_today": list,           # 已入睡角色代號
}
```

**範例**:

```python
# 第1天 09:00，Amy 在咖啡店，Ben 在辦公室
tick_result = manager.run_tick(
    perception_input = {
        "amy": {"location": "咖啡店",  "yolo_desc": "顧客排隊", "scene_text": "早晨"},
        "ben": {"location": "辦公室",  "yolo_desc": "",         "scene_text": "安靜"},
    },
    external_input = None,
)
print(tick_result["time"])             # "09:00"
print(tick_result["execute"]["amy"])   # {"action": "工作", "target": "", "completed": True}
```

---

#### `run_autonomous_days(self, n_days: int) -> dict`

**功能**: 執行 n 天自主模擬，每天呼叫 `run_one_day()`，所有角色入睡後推進日期。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `n_days` | `int` | 要模擬的天數 |

**回傳**: `{"days": list[day_data], "total_ticks": int}`

**範例**:

```python
# 模擬 3 天自主行為
result = manager.run_autonomous_days(3)
print(f"總 ticks: {result['total_ticks']}")
for day_data in result["days"]:
    print(f"第 {day_data['day']} 天：{len(day_data['ticks'])} 個 ticks")
```

---

#### `run_one_day(self) -> dict`

**功能**: 執行一天（直到所有角色入睡或達 `MAX_TICKS_PER_DAY` 上限）。達上限後強制所有未睡角色入睡。

**回傳**: `{"day": int, "ticks": list, "sleep_reports": dict}`

---

#### `_execute_phase(self, perception_input) -> dict`

**功能**: Phase 1 — 執行所有角色的 `pending_action`。

- 對話行動：先找配對（`_find_conversation_pairs()`），配對成功才進入對話循環
- 睡覺行動：檢查時間是否到達 `default_sleep_time`，未到則改為「休息」
- 前往行動：更新角色的 `current_location`
- 一般行動：更新 `current_action` 並記錄到 `today_actions`

---

#### `_decide_phase(self, perception_input, external_input) -> dict`

**功能**: Phase 2 — 所有角色呼叫 `agent.decide()` 決策下一 tick 行動。若決策為睡覺且時間已到，觸發 `_do_sleep()`。

---

#### `_handle_dialogue(self, initiator_code, responder_code, perception_input) -> dict`

**功能**: 處理一對對話的完整流程：鎖定雙方 → 邀請 → 接受/拒絕 → 對話循環 → 解鎖。

**對話循環邏輯**:
- 最多 `DIALOGUE_MAX_TURNS` 輪
- 每輪：responder 生成回應 → 若 `action != "對話"` 結束 → initiator 生成回應 → 若 `action != "對話"` 結束
- 使用最近 6 行作為對話歷史（`recent_dialogue_lines[-6:]`）

**拒絕時**：雙方都寫 STM，`is_locked` 解除，對話歷史記錄 `accepted: False`。

**範例**:

```python
# Amy（initiator）與 Claire（responder）在超市，Amy 想對話
result = manager._handle_dialogue("amy", "claire", perception_input)
print(result["initiator_result"]["accepted"])  # True 或 False
print(result["initiator_result"]["rounds"])    # 實際對話輪數
```

---

#### `_find_conversation_pairs(self) -> dict`

**功能**: 找出 `pending_action == "對話"` 且同地點的角色配對。優先配對雙方都想對話的組合。

**回傳**: `{code_a: code_b, code_b: code_a}` 雙向字典

---

#### `_handle_interrupts(self, perception_input) -> dict`

**功能**: 遍歷所有角色的中斷佇列，呼叫 `InterruptHandler.process_interrupts()`，若應中斷則呼叫 `agent.re_evaluate_on_interrupt()`。

---

#### `push_interrupt(self, code: str, event: dict)`

**功能**: 外部（YOLO 感知層或 ws_server）寫入中斷事件。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `code` | `str` | 角色代號，例如 `"ben"` |
| `event` | `dict` | 中斷事件，含 `type`、`strength`、`data`、`timestamp` |

**範例**:

```python
# YOLO 偵測到 David 附近出現陌生人
manager.push_interrupt("david", {
    "type":      "yolo_change",
    "strength":  "medium",
    "data":      {"detected": "陌生人"},
    "timestamp": "14:00",
})
```

---

#### `_do_sleep(self, code: str) -> dict`

**功能**: 觸發角色睡眠濃縮 + 存檔。先快照 `process_log`，再呼叫 `agent.sleep()`，補充結果後存入 `_sleep_reports_buffer`，並將代號加入 `_sleeping_today`。

---

#### `_check_safety_limit(self)`

**功能**: 檢查各角色的 STM 是否超過安全閥（`stm.is_over_safety_limit()`）。超過時強制觸發中途睡眠濃縮，防止記憶無限增長。

---

#### `get_observation_data(self) -> dict`

**功能**: 收集所有角色的完整狀態資料，供 dashboard 或觀察工具使用。

**回傳結構（每個 code）**:

```python
{
    "name":               str,
    "current_location":   str,
    "current_action":     str,
    "emotion":            str,
    "day":                int,
    "stm":                list,       # STM 所有記憶
    "ltm_nodes":          list,
    "ltm_edges":          list,
    "ltm_summary":        str,
    "process_log":        list,
    "schedule":           list,
    "sleep_pattern":      dict,
    "is_sleeping":        bool,
}
```

---

#### 公開查詢介面

| 方法 | 說明 |
|------|------|
| `get_character(code)` | 回傳指定角色的 `Character` 物件 |
| `get_agent(code)` | 回傳指定角色的 `Agent` 物件 |
| `all_codes()` | 回傳所有角色代號列表 |
| `pop_dialogue_history()` | 取出並清空本 tick 的對話歷史 |
| `all_sleeping_today()` | 是否所有角色都已入睡 |
| `get_process_log(code)` | 回傳指定角色的 `process_log` |

---

## 模擬使用情境

### 情境一: 啟動模擬器並執行 3 天

```python
from model.model_loader import ModelLoader
from world.world_clock import WorldClock
from agent.manager import AgentManager

loader = ModelLoader()
loader.load()  # 載入 Phi-3.5-Vision

clock   = WorldClock()           # 從 06:00 開始
manager = AgentManager(loader, clock)

result = manager.run_autonomous_days(3)
print(f"3 天共執行 {result['total_ticks']} 個 ticks")
```

### 情境二: 手動逐 tick 執行（接 UE 引擎）

```python
# main.py 逐 tick 接收 UE 推送的 perception
perception_from_ue = {
    "amy": {"location": "咖啡店", "yolo_desc": "顧客走近", "scene_text": "早晨"},
    "ben": {"location": "辦公室", "yolo_desc": "",          "scene_text": ""},
}

tick_result = manager.run_tick(perception_input=perception_from_ue)
print(tick_result["decide"]["amy"]["action"])  # Amy 決定的下一步行動
```

### 情境三: 外部事件注入 + 觀察狀態

```python
# ws_server 接收到緊急訊號，注入 Emma 的中斷事件
manager.push_interrupt("emma", {
    "type":      "external_input",
    "strength":  "strong",
    "data":      {"msg": "火災警報"},
    "timestamp": "15:30",
})

# 下一個 tick 自動處理中斷
tick = manager.run_tick()
print(tick["interrupts"]["emma"]["interrupted"])  # True

# 觀察所有角色當前狀態
obs = manager.get_observation_data()
print(obs["emma"]["current_action"])  # 可能已改為"前往"
```

---

## 注意事項

- **兩段式 Phase 設計**：Phase 1 執行的是「上一個 tick 決定的行動」，Phase 2 決策的是「下一個 tick 要做的行動」，兩個 Phase 在同一個 `run_tick()` 中完成，避免 agent 間的執行順序問題。
- **對話鎖定**：進入對話循環時，雙方 `is_locked = True`，防止其他邏輯同時修改狀態；循環結束（無論接受或拒絕）一定會解鎖。
- **睡覺時間保護**：`_decide_phase()` 和 `_execute_phase()` 都有「時間還早不能睡」的保護，Markov 抽到「睡覺」但時間未到時，自動改為「休息」。
- **時間計算跨午夜**：`_time_reached()` 使用 `day_start=06:00` 作為相對起點，正確處理 `23:00 → 02:00` 的跨午夜順序。
- **STM 安全閥**：`_check_safety_limit()` 在每 tick 結束前觸發，防止 STM 無限增長導致 OOM，觸發時強制中途睡眠。
- **`_sleeping_today` 集合**：角色入睡後不再參與任何 tick 邏輯，包括 perception 補齊、中斷處理、Phase 1/2 執行。
