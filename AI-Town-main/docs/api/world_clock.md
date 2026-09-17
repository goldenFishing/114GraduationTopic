# WorldClock — 虛擬世界時鐘

> **路徑**: `world/world_clock.py`  
> **職責**: 管理模擬世界的虛擬時間推進、天數追蹤與時間表觸發

---

## 功能概覽

`WorldClock` 是 AI-Town 模擬世界的時間軸。它以**分鐘**為內部單位記錄當前時間，每次 `tick()` 推進 `MINUTES_PER_TICK`（= 60 分鐘，從 `config/world_config` 讀取），因此一天最多有 `MAX_TICKS_PER_DAY`（= 20）個 tick，從 `DAY_START_HOUR`（= 6，即 06:00）開始，到凌晨 02:00 結束。

**日期**不自動推進：必須在所有角色都入睡後，由 `AgentManager.run_autonomous_days()` 明確呼叫 `advance_day()` 才會推進到下一天並重置 tick 計數。`tick()` 處理跨午夜（23:00 → 00:00），但不遞增日期，確保日期語意由上層控制。

`is_forced_sleep_time()` 是安全閥：當 `ticks_today >= MAX_TICKS_PER_DAY`（20 個 tick）時，Manager 強制讓所有未睡角色入睡。`should_trigger_slot()` 則是時間表查詢介面：比較 slot 的設定時間與當前時間，判斷該時間段是否已到達。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config.DAY_START_HOUR` | 一天起始小時（預設 6） |
| 依賴 | `config.world_config.MINUTES_PER_TICK` | 每 tick 推進分鐘數（預設 60） |
| 依賴 | `config.world_config.MAX_TICKS_PER_DAY` | 每天最多 tick 數（預設 20） |
| 被依賴 | `agent.manager.AgentManager` | `run_tick()` 呼叫 `clock.tick()`；`run_one_day()` 呼叫 `is_forced_sleep_time()`；`run_autonomous_days()` 呼叫 `advance_day()` |
| 被依賴 | `core.character.Character` | 呼叫 `should_trigger_slot()` 決定時間表 |

---

## 時間軸示意

```
第 N 天（DAY_START_HOUR = 6，MINUTES_PER_TICK = 60，MAX_TICKS_PER_DAY = 20）

Tick  0: 06:00  ← 一天開始
Tick  1: 07:00
Tick  2: 08:00
...
Tick  6: 12:00
...
Tick 17: 23:00
Tick 18: 00:00  ← 跨午夜（_minutes 繞回）
Tick 19: 01:00
── is_forced_sleep_time() 在 tick 20 後為 True ──
（實際上 Manager 在 Tick 20 時檢查，強制入睡）
凌晨 02:00 對應 MAX_TICKS_PER_DAY 範圍末端
```

---

## 主要類別 / 函式

### `WorldClock`

**功能**: 虛擬世界時鐘，管理時間推進與天數。

#### `__init__(self, start_hour, minutes_per_tick)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `start_hour` | `int` | 一天起始小時（預設 `DAY_START_HOUR` = 6） |
| `minutes_per_tick` | `int` | 每 tick 推進分鐘數（預設 `MINUTES_PER_TICK` = 60） |

**初始狀態**:
- `_minutes = start_hour * 60`（例如 `6 * 60 = 360`，即 06:00）
- `_day = 1`
- `_ticks_this_day = 0`

**範例**:

```python
# 預設初始化（06:00，第 1 天）
clock = WorldClock()
print(clock.time_str)   # "06:00"
print(clock.day)        # 1
print(clock.ticks_today) # 0

# 自訂起始時間（從 08:00 開始）
clock2 = WorldClock(start_hour=8)
print(clock2.time_str)  # "08:00"
```

---

### Properties（屬性）

#### `time_str -> str`

**功能**: 當前時間的 `HH:MM` 格式字串。

**範例**:

```python
# 推進 3 個 tick 後（3 * 60 = 180 分鐘，從 06:00 起）
clock.tick(); clock.tick(); clock.tick()
print(clock.time_str)  # "09:00"
```

---

#### `time_minutes -> int`

**功能**: 當前時間的分鐘數（0–1439）。供 `AgentManager._current_minutes()` 直接使用。

**範例**:

```python
# 在 14:30
print(clock.time_minutes)  # 870  （14 * 60 + 30）
```

---

#### `day -> int`

**功能**: 當前天數，從 1 開始計數。只有 `advance_day()` 才會遞增。

---

#### `ticks_today -> int`

**功能**: 今天已推進的 tick 數。供 `is_forced_sleep_time()` 比較 `MAX_TICKS_PER_DAY`。

---

### 推進方法

#### `tick(self)`

**功能**: 推進一格（`MINUTES_PER_TICK` = 60 分鐘）。跨午夜（`_minutes >= 24 * 60 = 1440`）時自動繞回（`-= 1440`），**不自動遞增日期**。遞增 `_ticks_this_day`。

**範例**:

```python
clock = WorldClock()  # 06:00，第 1 天
for _ in range(18):
    clock.tick()
print(clock.time_str)    # "00:00"（跨午夜後繞回）
print(clock.ticks_today) # 18
print(clock.day)         # 1（日期未變）
```

---

#### `advance_day(self)`

**功能**: 所有角色入睡後呼叫。遞增 `_day`，將 `_minutes` 重置為 `DAY_START_HOUR * 60`（06:00），`_ticks_this_day` 重置為 0。

**範例**:

```python
# 第 1 天結束，所有角色入睡
clock.advance_day()
print(clock.day)         # 2
print(clock.time_str)    # "06:00"（重置）
print(clock.ticks_today) # 0（重置）
```

---

### 判斷方法

#### `is_forced_sleep_time(self) -> bool`

**功能**: 判斷是否已達每天 tick 上限（`MAX_TICKS_PER_DAY` = 20）。回傳 `True` 時，`AgentManager.run_one_day()` 強制讓所有未入睡角色呼叫 `_do_sleep()`。

**範例**:

```python
clock = WorldClock()
print(clock.is_forced_sleep_time())  # False（ticks_today = 0）

for _ in range(20):
    clock.tick()
print(clock.is_forced_sleep_time())  # True（ticks_today = 20 >= 20）
print(clock.time_str)                # "02:00"（06:00 + 20*60 分鐘，跨午夜後）
```

---

#### `should_trigger_slot(self, slot: dict) -> bool`

**功能**: 判斷時間表的時段是否已到達當前時間。比較 `slot["time"]` 與 `_minutes`，使用絕對分鐘數比較（`_minutes >= slot_minutes`）。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `slot` | `dict` | 時間表時段，需含 `"time"` 欄位（`HH:MM` 格式） |

**注意**: 此方法使用絕對時間比較，不考慮跨日序（午夜後的 00:00–05:59 會被視為「未到達 06:00 以後的時段」）。跨日序的正確比較由 `agent/manager.py` 中的 `_time_reached()` 函式處理。

**範例**:

```python
clock = WorldClock()  # 06:00

# 08:00 的時段
slot = {"time": "08:00", "action": "工作", "location": "辦公室"}
print(clock.should_trigger_slot(slot))  # False（06:00 < 08:00）

clock.tick(); clock.tick()  # 推進至 08:00
print(clock.should_trigger_slot(slot))  # True（08:00 >= 08:00）

# 已過時段
past_slot = {"time": "07:00", "action": "早餐"}
print(clock.should_trigger_slot(past_slot))  # True（08:00 >= 07:00）
```

---

### 場景前綴

#### `scene_prefix(self) -> str`

**功能**: 生成供 prompt 使用的場景時間前綴，格式為 `"第N天 HH:MM"`。

**範例**:

```python
clock = WorldClock()
clock.tick(); clock.tick()  # 推進至 08:00
print(clock.scene_prefix())  # "第1天 08:00"

clock.advance_day()
print(clock.scene_prefix())  # "第2天 06:00"
```

---

### 模組層工具函式

#### `_parse_time(time_str: str) -> int`

**功能**: 將 `HH:MM` 字串轉為分鐘數（0–1439）。解析失敗時回傳 `DAY_START_HOUR * 60`（= 360，即 06:00）。

**範例**:

```python
_parse_time("14:30")  # 870
_parse_time("00:00")  # 0
_parse_time("invalid") # 360（fallback）
```

---

#### `_format_time(minutes: int) -> str`

**功能**: 將分鐘數轉為 `HH:MM` 格式字串。

**範例**:

```python
_format_time(870)   # "14:30"
_format_time(0)     # "00:00"
_format_time(1439)  # "23:59"
```

---

## 模擬使用情境

### 情境一: 一天完整的 tick 推進

```python
from world.world_clock import WorldClock

clock = WorldClock()  # 06:00，第 1 天
print(f"開始：{clock.scene_prefix()}")  # "第1天 06:00"

tick_count = 0
while not clock.is_forced_sleep_time():
    clock.tick()
    tick_count += 1
    print(f"Tick {tick_count}: {clock.time_str}")

# 輸出：
# Tick 1: 07:00
# Tick 2: 08:00
# ...
# Tick 18: 00:00（跨午夜）
# Tick 19: 01:00
# Tick 20: 02:00  ← 此時 is_forced_sleep_time() 為 True，迴圈結束

print(clock.ticks_today)        # 20
print(clock.is_forced_sleep_time())  # True
```

### 情境二: 多天模擬（含日期推進）

```python
clock = WorldClock()

for day in range(1, 4):
    print(f"=== 第 {clock.day} 天開始，時間：{clock.time_str} ===")
    
    # 模擬一天（跑 MAX_TICKS_PER_DAY 個 tick）
    while not clock.is_forced_sleep_time():
        clock.tick()
    
    # 所有角色入睡後推進日期
    clock.advance_day()
    print(f"推進完成，現在是第 {clock.day} 天 {clock.time_str}")

# 輸出：
# === 第 1 天開始，時間：06:00 ===
# 推進完成，現在是第 2 天 06:00
# === 第 2 天開始，時間：06:00 ===
# 推進完成，現在是第 3 天 06:00
# === 第 3 天開始，時間：06:00 ===
```

### 情境三: 時間表觸發查詢（David 的工作時段）

```python
clock = WorldClock()  # 06:00

# David 的時間表
david_schedule = [
    {"time": "06:30", "action": "起床", "location": "家"},
    {"time": "08:00", "action": "工作", "location": "辦公室"},
    {"time": "12:00", "action": "休息", "location": "餐廳"},
    {"time": "22:00", "action": "睡覺", "location": "家"},
]

# 推進到 08:30（比 08:00 晚）
for _ in range(3):  # 06:00 + 3*60 = 09:00
    clock.tick()

# 檢查哪些時段已觸發
triggered = [s for s in david_schedule if clock.should_trigger_slot(s)]
print([s["action"] for s in triggered])  # ["起床", "工作"]
print(clock.time_str)  # "09:00"
```

---

## 注意事項

- **`tick()` 跨午夜不遞增日期**：`_minutes >= 1440` 時自動 `-= 1440` 繞回，但 `_day` 不變。日期推進完全由 `advance_day()` 控制，確保「一天」的語意由 `AgentManager` 決定。
- **`is_forced_sleep_time()` 是 tick 數量比較，不是時間比較**：20 個 tick（= 1200 分鐘 = 20 小時）從 06:00 累計到 02:00（隔天），Manager 的強制入睡是「tick 上限」而非「時間到了 02:00」。
- **`should_trigger_slot()` 的局限**：使用絕對分鐘數比較，午夜後的時段（00:00–05:59）與 06:00 以後的時段比較時可能有語意問題。精確的跨日序比較需使用 `manager.py` 中的 `_time_reached()` 函式。
- **`MINUTES_PER_TICK = 60`**：每 tick 等於 1 小時，模擬時間與現實時間解耦，一天 20 個虛擬小時對應任意現實執行時間。
- **`advance_day()` 重置時間到 `DAY_START_HOUR * 60`**：確保每天固定從 06:00 開始，不受前一天結束時間影響。
