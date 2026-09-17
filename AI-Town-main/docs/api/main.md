# main — 程式主入口（UE5 對接）

> **路徑**: `main.py`  
> **職責**: 啟動 WebSocket 伺服器或執行離線快速 demo

---

## 功能概覽

`main.py` 是 AI-Town 與 Unreal Engine 5（UE5）整合的主要入口點，提供兩種執行模式：WebSocket 伺服器模式（與 UE5 即時連接）和離線快速 demo 模式（無需 UE5，跑少量 ticks 驗證系統）。

伺服器模式（預設）呼叫 `run_server`，建立完整的系統元件（ModelLoader、WorldClock、AgentManager、YoloHandler）後啟動 `WSServer`，等待 UE5 連線傳入感知資料，並將決策行動 ID 回傳給 UE5。WebSocket 的具體實作委派給 `server.ws_server.WSServer`。

Demo 模式（`--demo`）呼叫 `run_demo`，跑指定輪次的 `manager.run_tick()`，在終端機直接印出每輪各角色的決策結果，適合快速驗證系統基本運作。Demo 模式使用真實 `ModelLoader`（非 FakeLoader），因此仍需 GPU；若要無 GPU 驗證，請改用 `simulate.py --no-model`。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `model.model_loader.ModelLoader` | 載入 AI 模型（必須） |
| 依賴 | `world.world_clock.WorldClock` | 建立模擬世界時鐘 |
| 依賴 | `agent.manager.AgentManager` | 管理所有角色的自主模擬 |
| 依賴 | `utils.logger.get_logger` | 取得 `"main"` logger |
| 依賴（伺服器模式） | `perception.yolo_handler.YoloHandler` | 場景視覺偵測 |
| 依賴（伺服器模式） | `server.ws_server.WSServer` | WebSocket 伺服器（具體實作） |

---

## 主要類別 / 函式

### `build_system() -> tuple`
**功能**: 初始化所有核心系統元件，回傳三元組 `(loader, clock, manager)`。是 `run_server` 和 `run_demo` 的共用初始化函式。  
**參數**: 無  
**回傳**: `tuple` — `(ModelLoader, WorldClock, AgentManager)`  
**副作用**: 
- 記錄啟動日誌
- 呼叫 `loader.load()` 載入模型
- 建立 `AgentManager` 並載入所有角色 JSON

**範例**:
```python
from main import build_system

loader, clock, manager = build_system()
print(f"已載入角色：{list(manager.characters.keys())}")
# 已載入角色：['A', 'B', 'C', 'D', 'E']
```

---

### `run_server(host: str = "localhost", port: int = 8765)`
**功能**: 啟動 WebSocket 伺服器，建立完整系統後等待 UE5 連線。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `host` | `str` | WebSocket 伺服器綁定的主機，預設 `"localhost"` |
| `port` | `int` | 監聽埠號，預設 `8765` |

**回傳**: `None`（阻塞，直到伺服器停止）  
**建立元件**: `ModelLoader` + `WorldClock` + `AgentManager` + `YoloHandler` + `WSServer`  
**範例**:
```python
# 等同於執行：python main.py
from main import run_server

run_server()  # 阻塞，等待 UE5 連線

# 自訂網路設定
run_server(host="0.0.0.0", port=9000)  # 允許外部連線
```

---

### `run_demo(rounds: int = 3)`
**功能**: 執行指定輪次的離線 demo，每輪印出所有角色的決策結果到終端機。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `rounds` | `int` | 要執行的 tick 輪數，預設 `3` |

**回傳**: `None`  
**範例**:
```python
from main import run_demo

# 執行 5 輪 demo
run_demo(rounds=5)

# 輸出格式（每輪）：
# --- Tick 1 (D1T06:00) ---
# [Amy] 工作
# [Ben] 吃早餐
# [Claire] 閱讀
# [David] 運動
# [Emma] 準備出門
```

---

## 命令列用法

```bash
# 啟動 WebSocket 伺服器（預設 localhost:8765）
python main.py

# 指定伺服器位址和埠
python main.py --host 0.0.0.0 --port 9000

# 快速 demo 模式（3 個 ticks）
python main.py --demo

# 快速 demo 模式（自訂 ticks 數）
python main.py --demo --rounds 5
```

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `--demo` | 旗標 | `False` | 啟用 demo 模式 |
| `--rounds` | `int` | `3` | demo 模式執行的 tick 數（僅 demo 模式有效） |
| `--host` | `str` | `"localhost"` | WebSocket 伺服器 host（僅伺服器模式有效） |
| `--port` | `int` | `8765` | WebSocket 伺服器埠號（僅伺服器模式有效） |

---

## 模擬使用情境

### 情境一: 執行快速 Demo，驗證五位角色的決策輸出

```bash
python main.py --demo --rounds 3
```

預期輸出：
```
=== AI 角色自主生活模擬系統 啟動 ===
=== 開始 demo，跑 3 個 ticks ===

--- Tick 1 (D1T06:00) ---
[Amy] 工作
[Ben] 吃早餐
[Claire] 閱讀
[David] 運動 
[Emma] 準備出門

--- Tick 2 (D1T07:00) ---
...

=== demo 結束 ===
```

### 情境二: 在程式中整合，直接呼叫 build_system 後執行自訂邏輯

```python
from main import build_system

loader, clock, manager = build_system()

# 直接執行一個 tick
result = manager.run_tick()
print(f"時間：{result['time']}")
for code, dec in result.get("decide", {}).items():
    char = manager.get_character(code)
    action  = dec.get("action", "")
    target  = dec.get("target", "")
    mode    = dec.get("mode", "intuitive")
    print(f"  {char.name}（{mode}）: {action} {target}")
```

### 情境三: 伺服器模式，與 UE5 連線

```bash
# Python 端啟動伺服器
python main.py --host localhost --port 8765

# UE5 端設定 WebSocket 連線到 ws://localhost:8765
# UE5 傳送感知資料，Python 端回傳 ActionID
```

---

## 兩種執行模式比較

| 特性 | WebSocket 伺服器模式 | Demo 模式 |
|------|---------------------|-----------|
| 命令 | `python main.py` | `python main.py --demo` |
| UE5 連線 | 必須 | 不需要 |
| 真實模型 | 是 | 是 |
| 可設定 ticks | 由 UE5 控制 | `--rounds N` |
| 阻塞執行 | 是 | 否 |
| 適用場景 | 完整整合測試 | 快速功能驗證 |

若要**無 GPU** 執行，請改用 `simulate.py --no-model`（FakeLoader 模式）。

---

## 注意事項

- `run_server` 和 `run_demo` 都使用真實 `ModelLoader`，需要 GPU 和已下載的模型權重。若要無 GPU 執行，請改用 `simulate.py --no-model`。
- `main.py` 中的 `run_server` 引用 `server.ws_server.WSServer`（不是 `UEDataReceiver`/`UEActionSender`），此類別在 `ws_server.py` 的公開文件中尚未定義，可能存放在其他版本或尚未實作。
- `run_demo` 呼叫的是 `manager.run_tick()`（單 tick），而非 `run_autonomous_days()`（多天），因此 demo 結束後不會生成 HTML 報告。若需要報告，請使用 `simulate.py`。
- `get_character(code)` 在 demo 輸出中用於取得角色名字（`char.name`），若 `manager` 不暴露此方法，需要改用 `manager.characters[code]["name"]`。
- `--rounds` 參數在伺服器模式下無效，只對 `--demo` 有效。
