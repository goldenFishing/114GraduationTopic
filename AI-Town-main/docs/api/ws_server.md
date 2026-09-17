# ws_server — UE5 資料輸入輸出介面

> **路徑**: `server/ws_server.py`  
> **職責**: 定義 Python 端與 UE5 之間的感知資料與行動指令介面

---

## 功能概覽

`ws_server` 模組定義了 AI-Town Python 端與 Unreal Engine 5（UE5）之間的資料通訊介面。模組以兩個職責分離的類別組成：`UEDataReceiver` 負責接收 UE5 傳來的感知資料（位置、視覺描述、場景文字），`UEActionSender` 負責將 Python 端的決策結果（ActionID）回傳給 UE5。

**目前狀態**：兩個類別均為 **stub（骨架）實作**，WebSocket 的實際連線建立、訊息解析、網路傳輸等邏輯尚未實作，標記為「後期整合時補充」。現有程式碼定義了清晰的資料流向和介面合約，使其他模組可以基於這些介面開發，不受 WebSocket 實作進度影響。

`UEDataReceiver` 採用**回呼函式（callback）模式**，各角色可以各自註冊一個感知資料處理器（`register_handler`），當 UE5 傳來該角色的感知資料時，對應的回呼函式會被觸發。`UEActionSender` 採用**暫存佇列（pending queue）模式**，行動結果先暫存在 `_pending` dict 中，後期 WebSocket 傳送邏輯完成後再讀取發送。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 被依賴 | `main.py` | `run_server` 函式建立 `WSServer` 實例（注意：`main.py` 引用的是 `WSServer`，而非本模組的 `UEDataReceiver`/`UEActionSender`，可能存在版本差異）|
| 被依賴 | `agent.manager` | 後期整合時，manager 的感知更新函式會被設為 `UEDataReceiver` 的 handler |

---

## 主要類別 / 函式

### `class UEDataReceiver`

接收 UE5 傳來的感知資料的 stub 實作。

#### `__init__(self)`
**功能**: 初始化空的 handler 字典 `{char_code: Callable}`。

---

#### `register_handler(self, char_code: str, handler: Callable)`
**功能**: 為特定角色註冊感知資料處理回呼函式。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `char_code` | `str` | 角色代號（如 `"A"`） |
| `handler` | `Callable` | 回呼函式，簽章為 `handler(perception: dict) -> None` |

**感知資料格式**:
```python
{
    "location":   "辦公室",         # 角色目前所在地點
    "yolo_desc":  "辦公室裡有人、筆電。",  # YOLO 視覺描述
    "scene_text": "下午，辦公室有些嘈雜。" # 場景文字說明
}
```

**範例**:
```python
from server.ws_server import UEDataReceiver

receiver = UEDataReceiver()

def handle_amy_perception(perception: dict):
    print(f"Amy 的位置：{perception['location']}")
    manager.update_perception("A", perception)

receiver.register_handler("A", handle_amy_perception)
```

---

#### `receive_perception(self, char_code: str, perception: dict) -> bool`
**功能**: 接收來自 UE5 的感知資料，轉發給已註冊的 handler；若無對應 handler，資料被忽略。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `char_code` | `str` | 角色代號 |
| `perception` | `dict` | 感知資料 dict（格式見上方） |

**回傳**: `bool` — `True` 若有 handler 處理；`False` 若無 handler（資料被忽略）  
**範例**:
```python
# 模擬 UE5 傳來 Ben 的感知資料
perception_data = {
    "location":   "咖啡館",
    "yolo_desc":  "咖啡館裡有2個人、杯子。",
    "scene_text": "午後，陽光灑入咖啡館。"
}
handled = receiver.receive_perception("B", perception_data)
print(handled)  # True（若 B 有已註冊的 handler）
```

---

### `class UEActionSender`

將 Python 決策結果（ActionID）回傳給 UE5 的 stub 實作。

#### `__init__(self)`
**功能**: 初始化空的待發送佇列 `{char_code: action_id}`。

---

#### `send_action(self, char_code: str, action_id: int) -> None`
**功能**: 發送 ActionID 給 UE5（目前暫存於 `_pending`，實際發送邏輯後期補充）。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `char_code` | `str` | 角色代號 |
| `action_id` | `int` | 行動 ID，對應 UE5 中的動畫或行為 |

**回傳**: `None`  
**範例**:
```python
from server.ws_server import UEActionSender

sender = UEActionSender()

# Claire 決定行動 ID 為 5（代表「閱讀」）
sender.send_action("C", 5)

# Emma 決定行動 ID 為 9（代表「對話」）
sender.send_action("E", 9)
```

---

#### `get_pending(self) -> dict`
**功能**: 取出所有待發送的 action，回傳 `{char_code: action_id}` 的副本（供測試或 polling 模式使用）。  
**回傳**: `dict` — `_pending` 的複製品（不清空原 queue）  
**範例**:
```python
pending = sender.get_pending()
print(pending)
# {"C": 5, "E": 9}
```

---

#### `clear_pending(self) -> None`
**功能**: 清空待發送 queue（發送完畢後呼叫）。  
**範例**:
```python
# 實際發送後清空
pending = sender.get_pending()
for code, action_id in pending.items():
    websocket.send(f"{code}:{action_id}")  # 後期實作
sender.clear_pending()
```

---

## 模擬使用情境

### 情境一: 完整的感知→決策→發送流程（前期測試用）

```python
from server.ws_server import UEDataReceiver, UEActionSender

receiver = UEDataReceiver()
sender   = UEActionSender()

# 為所有角色註冊感知 handler
for code in ["A", "B", "C", "D", "E"]:
    def make_handler(c):
        def handler(perception):
            # 更新角色感知後執行決策
            manager.update_perception(c, perception)
            result  = manager.run_tick_for(c)
            action_id = result.get("action_id", 0)
            sender.send_action(c, action_id)
        return handler
    receiver.register_handler(code, make_handler(code))

# 模擬 UE5 傳來 David 的感知資料
perception = {
    "location":   "圖書館",
    "yolo_desc":  "圖書館裡有人、書。",
    "scene_text": "安靜的圖書館下午。"
}
receiver.receive_perception("D", perception)

# 查看 pending actions
print(sender.get_pending())
# {"D": 3}  # 3 = 閱讀

sender.clear_pending()
```

### 情境二: 測試無 handler 的角色被靜默忽略

```python
from server.ws_server import UEDataReceiver

receiver = UEDataReceiver()
# 只為 Amy 和 Ben 註冊 handler
receiver.register_handler("A", lambda p: print(f"Amy: {p['location']}"))
receiver.register_handler("B", lambda p: print(f"Ben: {p['location']}"))

# Claire 未註冊，資料被忽略
result = receiver.receive_perception("C", {"location": "咖啡館", "yolo_desc": "", "scene_text": ""})
print(result)  # False
```

---

## 注意事項

- 本模組是純粹的 stub 實作，目前**不會實際建立 WebSocket 連線**。在 `main.py` 的 `run_server` 函式中引用的是 `WSServer`（不是本模組的類別），可能是一個尚未在本模組實作的類別，或存放在另一個未包含於此文件的檔案中。
- `send_action` 目前只是把 action_id 放入 `_pending` dict，後來覆蓋相同角色的 action（後呼叫的會覆蓋先前的），在一個 tick 中多次呼叫 `send_action("A", ...)` 只有最後一次有效。
- `get_pending` 回傳的是 `dict(self._pending)` 的**淺複製**，不是 `_pending` 本身，修改回傳值不影響內部狀態。
- WebSocket 真正的連線建立、訊息編解碼（JSON / binary）、心跳機制、斷線重連等功能，都標記為後期整合補充。
