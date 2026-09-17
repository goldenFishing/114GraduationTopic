# yolo_handler — YOLO 場景偵測與語意轉換

> **路徑**: `perception/yolo_handler.py`  
> **職責**: 偵測場景中的物件並轉換為自然語言描述

---

## 功能概覽

`yolo_handler` 模組封裝 YOLOv8（ultralytics）的物件偵測功能，將 Unreal Engine 傳來的場景截圖分析成結構化的偵測結果，並進一步判斷場景變化是否值得觸發角色的推論週期，最後將有意義的偵測結果轉換為中文自然語言描述，供注入角色的 STM `image_desc` 欄位。

**外部依賴**：`ultralytics`（YOLOv8 套件）和 `Pillow`（圖片處理）。YOLOv8 為可選依賴，若未安裝，`YoloHandler` 所有方法仍可正常呼叫，只是回傳空結果（fallback 模式），不會導致程式崩潰。這讓開發者在沒有 GPU 的環境中也能正常運行其他模組。

偵測篩選邏輯建立在 `_MEANINGFUL_CLASSES` 白名單上，只有在這個集合中的物件類別才會被視為「有意義的場景變化」。物件名稱從英文自動轉換為中文（透過 `_CLASS_ZH` 對照表），並以自然語言句型輸出，如「辦公室裡有2個人、椅子。」

---

## 外部依賴說明

| 依賴 | 套件名稱 | 用途 |
|------|----------|------|
| YOLOv8 | `ultralytics` | 物件偵測模型，偵測圖片中的物件類別、信心度和邊界框 |
| Pillow | `Pillow` (PIL) | 接受 `PIL.Image.Image` 格式作為偵測輸入 |

**如何安裝**:
```bash
pip install ultralytics Pillow
```

**如何在沒有 YOLOv8 的環境下使用（Mock 模式）**:
```python
# 直接實例化即可，不會報錯
handler = YoloHandler()
# detect() 回傳 []
# is_meaningful([]) 回傳 False
# to_description([]) 回傳 ""
# process(image) 回傳 (False, "")
```

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `ultralytics.YOLO`（可選） | YOLOv8 物件偵測 |
| 依賴 | `PIL.Image` | 圖片格式 |
| 被依賴 | `perception.event_trigger` | `PerceptionWatcher` 使用 `YoloHandler` 偵測每幀 |
| 被依賴 | `main.py` | `run_server` 建立 `YoloHandler` 實例傳給 `WSServer` |

---

## 主要類別 / 函式

### `class YoloHandler`

YOLO 偵測包裝器，提供統一介面讓其餘模組不需直接與 `ultralytics` 互動。

#### `__init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.4)`
**功能**: 初始化 YOLO 模型。若 `ultralytics` 未安裝或模型載入失敗，進入 fallback 模式（`self._model = None`）。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `model_path` | `str` | YOLO 模型權重路徑，預設使用 YOLOv8n（最小模型） |
| `confidence` | `float` | 偵測信心度閾值，低於此值的偵測結果會被過濾，預設 `0.4` |

**範例**:
```python
from perception.yolo_handler import YoloHandler

# 使用預設 YOLOv8n
handler = YoloHandler()

# 使用較大的 YOLOv8m，提高精度但速度較慢
handler = YoloHandler(model_path="yolov8m.pt", confidence=0.5)
```

---

#### `detect(self, image: Image.Image) -> list`
**功能**: 對 PIL 圖片執行 YOLO 物件偵測，回傳偵測結果清單。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 要分析的圖片 |

**回傳**: `list` — 每筆格式:
```python
{
    "class":      "person",         # YOLO 英文類別名
    "confidence": 0.87,             # 信心度 0.0~1.0
    "bbox":       [x1, y1, x2, y2] # 邊界框座標（float）
}
```
YOLO 未安裝時回傳 `[]`。  
**範例**:
```python
from PIL import Image
from perception.yolo_handler import YoloHandler

handler = YoloHandler()
img = Image.open("screenshots/office_scene.png")
detections = handler.detect(img)
# [{"class": "person", "confidence": 0.92, "bbox": [100.0, 50.0, 300.0, 400.0]},
#  {"class": "laptop", "confidence": 0.85, "bbox": [200.0, 300.0, 450.0, 450.0]}]
```

---

#### `is_meaningful(self, detections: list) -> bool`
**功能**: 判斷偵測結果是否包含值得觸發角色推論的物件類別。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `detections` | `list` | `detect()` 的回傳值 |

**回傳**: `bool` — `True` 若至少有一個偵測結果屬於 `_MEANINGFUL_CLASSES`  
**有意義的物件類別**: `person`、`chair`、`cup`、`laptop`、`bottle`、`handbag`、`book`、`cell phone`、`bench`、`dining table`  
**範例**:
```python
detections = [{"class": "person", "confidence": 0.9, "bbox": [...]},
              {"class": "car", "confidence": 0.8, "bbox": [...]}]
handler.is_meaningful(detections)  # True（有 person）

detections = [{"class": "car", "confidence": 0.8, "bbox": [...]}]
handler.is_meaningful(detections)  # False（car 不在有意義清單）
```

---

#### `to_description(self, detections: list, location: str = "") -> str`
**功能**: 將偵測結果中有意義的物件轉換為中文自然語言描述。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `detections` | `list` | `detect()` 的回傳值 |
| `location` | `str` | 當前場景地點（增加語境），如 `"辦公室"` |

**回傳**: `str` — 中文描述句，格式為 `"{location}裡有{物件}。"` 或 `"畫面中有{物件}。"`（無 location 時）  
**範例**:
```python
detections = [
    {"class": "person",  "confidence": 0.92, "bbox": [...]},
    {"class": "person",  "confidence": 0.88, "bbox": [...]},
    {"class": "laptop",  "confidence": 0.85, "bbox": [...]}
]
desc = handler.to_description(detections, location="辦公室")
# "辦公室裡有2個人、筆電。"

desc = handler.to_description(detections)
# "畫面中有2個人、筆電。"
```

---

#### `process(self, image: Image.Image, location: str = "") -> tuple`
**功能**: 一次完成偵測 → 判斷是否有意義 → 生成描述的完整流程。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `image` | `PIL.Image.Image` | 要分析的圖片 |
| `location` | `str` | 當前場景地點 |

**回傳**: `tuple` — `(should_trigger: bool, description: str)`  
**範例**:
```python
from PIL import Image

img = Image.open("screenshot.png")
should_trigger, desc = handler.process(img, location="咖啡館")
if should_trigger:
    print(f"觸發推論：{desc}")
    # 觸發推論：咖啡館裡有人、杯子。
```

---

## 模擬使用情境

### 情境一: Amy 在辦公室收到新畫面，觸發感知更新

```python
from PIL import Image
from perception.yolo_handler import YoloHandler

handler = YoloHandler()
img = Image.open("ue_screenshot_A_office.png")

should_trigger, yolo_desc = handler.process(img, location="辦公室")
if should_trigger:
    # 注入 Amy 的 STM 感知欄位
    perception = {
        "location":   "辦公室",
        "yolo_desc":  yolo_desc,  # "辦公室裡有3個人、筆電、椅子。"
        "scene_text": "早晨，辦公室開始有人陸續進來。"
    }
    manager.update_perception("A", perception)
```

### 情境二: 在無 GPU 的測試環境使用 Mock 模式

```python
from perception.yolo_handler import YoloHandler

# 即使沒安裝 ultralytics，也能正常實例化
handler = YoloHandler()
print(handler._model)  # None

# 所有方法正常回傳，不報錯
should_trigger, desc = handler.process(None)
# should_trigger = False, desc = ""

# 手動模擬 Mock 偵測
mock_detections = [{"class": "person", "confidence": 0.9, "bbox": [0, 0, 100, 200]}]
print(handler.is_meaningful(mock_detections))   # True
print(handler.to_description(mock_detections, "圖書館"))  # "圖書館裡有人。"
```

---

## 注意事項

- 模型第一次執行 `detect` 時 YOLOv8 會自動下載 `yolov8n.pt`（需要網路連線，約 6MB）。如果要離線使用，需要預先下載權重檔並指定完整路徑。
- `to_description` 中物件計數邏輯按中文名稱（而非英文類別）分組，因此如果 `_CLASS_ZH` 中有多個英文名對應到相同中文名，它們的計數會被合並。
- `_MEANINGFUL_CLASSES` 可依 UE 場景擴充，直接修改模組頂層的集合即可。
- `process` 方法中若 `is_meaningful` 為 `False`，**不會呼叫** `to_description`，直接回傳 `(False, "")`，節省計算。
- 若圖片為 `None` 且 YOLO 已安裝，`detect` 會因傳入 `None` 給模型而拋出例外；`process` 不對此做保護，請上層確保傳入有效圖片物件。
