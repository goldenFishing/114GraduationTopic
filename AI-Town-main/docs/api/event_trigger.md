# event_trigger — 感知層事件觸發器

> **路徑**: `perception/event_trigger.py`  
> **職責**: 將 YOLO 偵測差異轉換為結構化中斷事件並推入 AgentManager

---

## 功能概覽

`event_trigger` 模組是 AI-Town 感知層（Perception Layer）的事件驅動核心，負責將連續的視覺偵測資料流（YOLO 逐幀偵測）轉換成離散的中斷事件，並依場景變化的嚴重程度分級為 `weak`、`medium`、`strong` 三個等級。

**目前狀態**：本模組為 **stub（骨架）實作**，公開介面和分級邏輯已完整定義，但 `PerceptionWatcher` 的 async 監聽迴圈尚未實作（留有詳細設計注釋說明未來的實作方向）。現有可用功能為：`classify_event_strength`（分級邏輯）、`diff_detections`（逐幀差異計算）、`PerceptionWatcher.push_frame_sync`（同步推送單幀）。

`PerceptionWatcher` 維護每個角色的前一幀偵測結果（`_prev_detections`），每次收到新幀時計算差異（diff），若有物件出現或消失則生成中斷事件並呼叫 `manager.push_interrupt`，實現了「場景靜止時不觸發、場景改變時才推入事件」的設計目標。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `AgentManager`（執行期依賴） | 呼叫 `push_interrupt(code, event)` 推入中斷事件 |
| 依賴 | `YoloHandler`（執行期依賴） | 呼叫 `detect(image)` 取得偵測結果 |
| 被依賴 | `server.ws_server` | WSServer 收到 UE5 圖片後呼叫 `push_frame_sync` |

---

## 主要類別 / 函式

### `classify_event_strength(diff: dict) -> str`
**功能**: 依 YOLO 偵測差異（前後幀的物件集合變化）判斷事件強度等級。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `diff` | `dict` | `diff_detections` 的回傳值，包含 `objects_added`、`objects_removed`、`new_person` |

**回傳**: `str` — `"weak"` / `"medium"` / `"strong"`

**分級規則**:

| 條件 | 強度 |
|------|------|
| `diff["new_person"]` 有值 | `"strong"` |
| `"person"` 在 `objects_added` 中 | `"medium"` |
| 有任何物件新增或移除 | `"weak"` |
| 無任何變化 | `"weak"` |

**範例**:
```python
from perception.event_trigger import classify_event_strength

# 場景中出現已知人物（由 UE 提供身分）
diff = {"objects_added": [], "objects_removed": [], "new_person": "David"}
print(classify_event_strength(diff))  # "strong"

# 場景中出現一個新的未知人物
diff = {"objects_added": ["person"], "objects_removed": [], "new_person": None}
print(classify_event_strength(diff))  # "medium"

# 場景中出現一本書
diff = {"objects_added": ["book"], "objects_removed": [], "new_person": None}
print(classify_event_strength(diff))  # "weak"
```

---

### `diff_detections(prev: list, curr: list) -> dict`
**功能**: 比較兩次 YOLO 偵測結果，計算物件類別層面的差異（出現 / 消失的類別集合）。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `prev` | `list` | 上一幀的偵測結果（`YoloHandler.detect()` 的回傳值） |
| `curr` | `list` | 當前幀的偵測結果 |

**回傳**: `dict`:
```python
{
    "objects_added":   ["person", "cup"],  # 新出現的類別
    "objects_removed": ["laptop"],         # 消失的類別
    "new_person":      None                # 此欄位由 UE 連接後才填入身分
}
```

**注意**: `diff_detections` 在集合層面比較（每個類別只出現一次），不計算數量變化。  
**範例**:
```python
from perception.event_trigger import diff_detections

prev = [{"class": "laptop", "confidence": 0.9, "bbox": [...]},
        {"class": "chair",  "confidence": 0.8, "bbox": [...]}]

curr = [{"class": "person", "confidence": 0.95, "bbox": [...]},
        {"class": "chair",  "confidence": 0.82, "bbox": [...]},
        {"class": "cup",    "confidence": 0.75, "bbox": [...]}]

diff = diff_detections(prev, curr)
# {"objects_added": ["person", "cup"], "objects_removed": ["laptop"], "new_person": None}
```

---

### `class PerceptionWatcher`

持續監聽各角色的視覺輸入，偵測場景變化後觸發中斷事件。目前 async 監聽迴圈為 stub，只有 `push_frame_sync` 可使用。

#### `__init__(self, manager, yolo_handler)`
**功能**: 初始化監聽器，注入 AgentManager 和 YoloHandler 依賴。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `manager` | `AgentManager` | 用於推入中斷事件 |
| `yolo_handler` | `YoloHandler` | 用於偵測每幀圖片 |

---

#### `push_frame_sync(self, code: str, image) -> dict | None`
**功能**: 同步處理單一角色的一幀圖片。若場景有變化，生成並推入中斷事件；若無變化或偵測出錯，回傳 `None`。這是在尚未啟用 async loop 時的可用介面。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `code` | `str` | 角色代號（如 `"A"`） |
| `image` | `PIL.Image.Image \| None` | 當前幀圖片，`None` 時直接回傳 `None` |

**回傳**: `dict | None` — 若有場景變化，回傳生成的中斷事件 dict；否則回傳 `None`

**中斷事件格式**:
```python
{
    "type":      "yolo_change",
    "strength":  "medium",       # "weak" / "medium" / "strong"
    "data":      {               # diff_detections 的回傳值
        "objects_added":   ["person"],
        "objects_removed": [],
        "new_person":      None
    },
    "timestamp": "D1T10:30"     # manager.clock.time_str
}
```

**範例**:
```python
from PIL import Image
from perception.event_trigger import PerceptionWatcher
from perception.yolo_handler import YoloHandler

yolo    = YoloHandler()
watcher = PerceptionWatcher(manager=manager, yolo_handler=yolo)

# ws_server 收到 UE5 傳來的圖片後
img   = Image.open("frame_B.png")
event = watcher.push_frame_sync("B", img)
if event:
    print(f"Ben 觸發中斷：{event['strength']} ({event['data']['objects_added']})")
    # Ben 觸發中斷：medium (['person'])
```

---

## 未來 async 監聽迴圈設計（參考）

以下是模組注釋中記載的未來實作方向（尚未實作）：

```python
# 未來實作示意（非現有程式碼）
async def watch_loop(self):
    self._running = True
    while self._running:
        for code in active_characters:
            frame = await get_frame_from_ue(code)
            detections = self.yolo.detect(frame)
            diff = diff_detections(self._prev_detections.get(code, []), detections)
            if diff["objects_added"] or diff["objects_removed"]:
                strength = classify_event_strength(diff)
                self.manager.push_interrupt(code, {
                    "type":      "yolo_change",
                    "strength":  strength,
                    "data":      diff,
                    "timestamp": self.manager.clock.time_str
                })
            self._prev_detections[code] = detections
        await asyncio.sleep(1.0)
```

---

## 模擬使用情境

### 情境一: 手動測試分級邏輯（不需要 YOLO）

```python
from perception.event_trigger import diff_detections, classify_event_strength

# 模擬 Emma 走進辦公室場景
prev_frame = [{"class": "chair", "confidence": 0.8, "bbox": [0, 0, 100, 200]}]
curr_frame = [
    {"class": "chair",  "confidence": 0.8,  "bbox": [0, 0, 100, 200]},
    {"class": "person", "confidence": 0.95, "bbox": [200, 0, 400, 600]}
]

diff     = diff_detections(prev_frame, curr_frame)
strength = classify_event_strength(diff)
print(f"強度：{strength}, 新增：{diff['objects_added']}")
# 強度：medium, 新增：['person']
```

### 情境二: ws_server 整合，同步推送各角色的畫面

```python
from PIL import Image
from perception.event_trigger import PerceptionWatcher
from perception.yolo_handler import YoloHandler

yolo    = YoloHandler()
watcher = PerceptionWatcher(manager=manager, yolo_handler=yolo)

# 逐一處理各角色的畫面（由 UE WebSocket 觸發）
for code, frame_bytes in received_frames.items():
    import io
    img   = Image.open(io.BytesIO(frame_bytes))
    event = watcher.push_frame_sync(code, img)
    if event and event["strength"] == "strong":
        print(f"[{code}] 重大場景變化！")
```

---

## 注意事項

- `diff_detections` 的比較是**集合層面**的（每個類別只出現一次），不支援計數差異（例如「人從 1 個增加到 3 個」不會被偵測到）。
- `new_person` 欄位目前永遠為 `None`，設計為與 UE 整合後由 UE 端提供已知角色的身分識別，再填入此欄位。
- `push_frame_sync` 使用 `try/except` 捕獲偵測例外，任何 YOLO 錯誤都會靜默回傳 `None`，不會導致中斷事件觸發失敗影響主流程。
- 當 `image` 為 `None` 時，`push_frame_sync` 會直接回傳 `None`（早期返回），不會嘗試偵測。
- `_prev_detections` 是每個角色獨立維護的狀態，第一次呼叫某角色時，前一幀預設為空 list，因此第一幀的所有偵測結果都會被視為「新增」。
