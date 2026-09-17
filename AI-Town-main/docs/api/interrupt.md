# InterruptHandler — 中斷處理器

> **路徑**: `agent/interrupt.py`  
> **職責**: 管理各角色中斷佇列，決定事件能否打斷當前行動

---

## 功能概覽

`InterruptHandler` 是 AI-Town 的感知→決策橋接模組。當 YOLO 物件偵測或外部輸入偵測到場景變化時，事件被推入對應角色的中斷佇列（`push()`）。在每個 tick 開始時，`AgentManager` 呼叫 `process_interrupts()` 取出所有佇列事件，選出強度最高的事件，判斷是否應中斷角色當前行動。

中斷能否成立取決於兩個維度：**事件強度**（`weak` / `medium` / `strong`）與**行動鎖等級**（`0~2`）。行動鎖等級由 `config/world_config.INTERRUPT_LOCK_LEVELS` 設定，例如散步為 0（容易被中斷），工作為 1（需重要事件才中斷），對話與睡覺為 2（最高優先）。對話是特例：即使是 `strong` 事件也不中斷，確保對話完整性。

所有角色共用同一個 `InterruptHandler` 實例，各角色以代號（`code`）隔離各自的佇列。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config.INTERRUPT_LOCK_LEVELS` | 各行動的鎖等級定義 |
| 被依賴 | `agent.manager.AgentManager` | 每 tick 呼叫 `process_interrupts()`；外部呼叫 `push()` |

---

## 中斷強度對照表

| 事件強度 | 可中斷的最大鎖等級 | 典型觸發場景 |
|---------|------------------|-------------|
| `"weak"` | 0 | 物件輕微變化（桌上多了一個杯子） |
| `"medium"` | 1 | 新人出現在視野中 |
| `"strong"` | 2 | 緊急/未預期事件（警報、意外） |

## 行動鎖等級說明

| 鎖等級 | 代表行動 | 說明 |
|--------|---------|------|
| 0 | 散步、移動、休閒 | 容易被任何強度中斷 |
| 1 | 工作類行動 | 需 medium 或 strong 才中斷 |
| 2 | 對話、睡覺 | 最難中斷；對話永不中斷，睡覺只有 strong 才中斷 |

---

## 主要類別 / 函式

### `InterruptHandler`

**功能**: 中斷佇列管理與中斷決策邏輯。所有角色共用一個實例（`AgentManager` 持有）。

#### `__init__(self)`

初始化一個 `defaultdict(list)` 作為各角色的獨立中斷佇列 `_queues`。

---

#### `push(self, code: str, event: dict)`

**功能**: YOLO 感知層或外部輸入將事件推入指定角色的佇列。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `code` | `str` | 角色代號，例如 `"amy"` |
| `event` | `dict` | 中斷事件，見下方事件格式說明 |

**事件格式**:

```python
{
    "type":      "yolo_change" | "external_input",
    "strength":  "weak" | "medium" | "strong",
    "data":      {...},          # 事件詳情
    "timestamp": "HH:MM"
}
```

**範例**:

```python
# YOLO 偵測到 Amy 附近出現新人
handler.push("amy", {
    "type":      "yolo_change",
    "strength":  "medium",
    "data":      {"detected": "Ben 走進咖啡店"},
    "timestamp": "10:30",
})
```

---

#### `pop_all(self, code: str) -> list`

**功能**: 取出該角色所有累積事件並**清空**佇列。每個 tick 消費時呼叫。

**範例**:

```python
events = handler.pop_all("amy")  # 取出 Amy 所有積壓事件
print(len(events))  # 例如 2（本 tick 有兩個事件）
print(handler.has_events("amy"))  # False（佇列已清空）
```

---

#### `has_events(self, code: str) -> bool`

**功能**: 快速檢查角色佇列是否有待處理事件，避免不必要的處理開銷。

**範例**:

```python
if handler.has_events("ben"):
    outcome = handler.process_interrupts("ben", "工作")
```

---

#### `clear_all(self)`

**功能**: 清空所有角色的佇列。通常在所有角色入睡後呼叫，確保隔天不殘留舊事件。

---

#### `should_interrupt(self, current_action: str, event: dict) -> bool`

**功能**: 判斷單一事件能否中斷當前行動。

**特殊規則**:
1. **對話例外**：`current_action == "對話"` → 永遠回傳 `False`（即使 strong 事件）
2. **睡覺例外**：`current_action == "睡覺"` → 只有 `strength == "strong"` 才回傳 `True`
3. **一般規則**：`_STRENGTH_TO_MAX_LOCK[strength] >= INTERRUPT_LOCK_LEVELS[current_action]`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `current_action` | `str` | 角色當前行動，例如 `"工作"` |
| `event` | `dict` | 中斷事件 dict（需含 `"strength"` 欄位） |

**回傳**: `bool`

**範例**:

```python
# Ben 正在工作（lock=1），medium 事件能否中斷？
can = handler.should_interrupt("工作", {"strength": "medium"})
print(can)  # True（medium 的 max_lock=1 >= 工作的 lock=1）

# Claire 正在對話（lock=2），strong 事件能否中斷？
can = handler.should_interrupt("對話", {"strength": "strong"})
print(can)  # False（對話永不中斷）

# David 正在散步（lock=0），weak 事件能否中斷？
can = handler.should_interrupt("散步", {"strength": "weak"})
print(can)  # True（weak 的 max_lock=0 >= 散步的 lock=0）
```

---

#### `process_interrupts(self, code: str, current_action: str) -> dict`

**功能**: 處理該角色所有累積的中斷事件，找出強度最高的事件，決定整體影響。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `code` | `str` | 角色代號 |
| `current_action` | `str` | 角色當前行動 |

**回傳**:

```python
{
    "should_interrupt": bool,    # 是否應中斷並重新決策
    "triggered_event":  dict,    # 觸發中斷的最強事件（可為 None）
    "all_events":       list,    # 全部累積事件（供 STM 記錄用）
}
```

**內部邏輯**:
1. `pop_all(code)` 取出所有事件
2. 以 `_STRENGTH_TO_MAX_LOCK` 為鍵找出強度最高的事件（`strongest`）
3. `should_interrupt(current_action, strongest)` 判斷是否中斷
4. 回傳結果（`all_events` 包含全部，供 STM 記錄）

**範例**:

```python
# Amy 佇列有兩個事件：weak（物件變化）+ strong（警報）
# Amy 當前行動：工作（lock=1）
outcome = handler.process_interrupts("amy", "工作")

print(outcome["should_interrupt"])  # True（strong 事件 max_lock=2 >= 1）
print(outcome["triggered_event"]["strength"])  # "strong"
print(len(outcome["all_events"]))   # 2（兩個事件都在）
```

---

## 模擬使用情境

### 情境一: YOLO 偵測到場景變化，Amy 的工作被中斷

```python
# YOLO 層偵測到 Amy 附近出現緊急狀況
manager.push_interrupt("amy", {
    "type":      "yolo_change",
    "strength":  "strong",
    "data":      {"detected": "顧客昏倒"},
    "timestamp": "10:45",
})

# 下一個 tick，manager 自動處理中斷
tick = manager.run_tick()
interrupted = tick["interrupts"]["amy"]["interrupted"]
print(interrupted)  # True
print(tick["interrupts"]["amy"]["new_action"])  # Amy 的新行動，例如 "前往"
```

### 情境二: Ben 正在對話，strong 事件不中斷

```python
handler.push("ben", {
    "type":      "external_input",
    "strength":  "strong",
    "data":      {"msg": "緊急通知"},
    "timestamp": "14:00",
})

# Ben 當前行動是"對話"（對話例外保護）
outcome = handler.process_interrupts("ben", "對話")
print(outcome["should_interrupt"])  # False（對話永不中斷）
print(len(outcome["all_events"]))   # 1（事件仍被記錄，供 STM 用）
```

### 情境三: 同一 tick 多個事件，以最強者決定

```python
# Claire 在休息，同 tick 積壓了 3 個事件
handler.push("claire", {"type": "yolo_change", "strength": "weak",   "data": {}, "timestamp": "11:00"})
handler.push("claire", {"type": "yolo_change", "strength": "medium", "data": {}, "timestamp": "11:00"})
handler.push("claire", {"type": "yolo_change", "strength": "weak",   "data": {}, "timestamp": "11:00"})

outcome = handler.process_interrupts("claire", "休息")
print(outcome["triggered_event"]["strength"])  # "medium"（最強者）
print(outcome["should_interrupt"])             # True（medium max_lock=1 >= 休息 lock=0）
```

---

## 注意事項

- **佇列在 `pop_all()` 後清空**：`process_interrupts()` 內部呼叫 `pop_all()`，因此每個 tick 只處理一次，不會重複觸發。
- **`all_events` 的用途**：即使 `should_interrupt == False`，`all_events` 仍包含所有事件，`AgentManager` 可將這些事件記入 STM，讓角色「知道但不行動」。
- **強度最高者決策**：當佇列有多個事件時，只取強度最高的一個判斷是否中斷，其他較弱的事件不單獨觸發中斷，但都在 `all_events` 中。
- **所有角色共用實例**：`InterruptHandler` 以 `code` 隔離各角色佇列，不同角色的事件不會互相干擾。
- **`clear_all()` 時機**：應在所有角色都入睡後呼叫，確保隔天不殘留前一天的事件。
