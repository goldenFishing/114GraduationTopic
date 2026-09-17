# inference_engine — 圖文融合推論引擎

> **路徑**: `model/inference_engine.py`  
> **職責**: 封裝 Phi-3.5-Vision 的視覺編碼、文字 prompt 建構與圖文融合推論

---

## 功能概覽

`inference_engine.py` 將 Phi-3.5-Vision 模型的推論流程切分為三個獨立元件，對應模型架構的三個階段：`VisionEncoder`（圖片 → tensor）、`TextEncoder`（文字 → chat prompt）、`FusionDecoder`（融合推論 → 文字輸出）。三個元件由 `ModelLoader` 組裝，不直接單獨使用。

`GenerationConfig` 是推論參數的統一封裝，提供 `deliberate()` 和 `dialogue()` 兩個工廠方法，從 `config/model_config` 讀取對應的 `max_new_tokens` 與 `temperature`，確保各場景的生成行為一致。

最後，`batch_generate()` 函式提供 Batch 推論入口，根據 GPU VRAM 自動決定 batch size，適合批量處理多個角色的決策請求。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `PIL.Image` | 圖片載入與 RGB 轉換 |
| 依賴 | `torch` | GPU 推論、VRAM 查詢 |
| 依賴 | `config.model_config` | 各場景的 token 預算與 temperature |
| 被依賴 | `model.model_loader.ModelLoader` | 組裝三個元件，提供給 Agent 使用 |
| 被依賴 | `agent.agent.Agent` | 呼叫 `_call_model()` 時走 `fusion.generate()` |

---

## 資料型別

### `VisionBatch`

**功能**: 封裝 Phi-3.5-Vision image_processor 的輸出，方便傳遞圖片 tensor。

| 欄位 | 型別 | 說明 |
|------|------|------|
| `pixel_values` | `torch.Tensor` | 圖片像素值 tensor |
| `image_sizes` | `Any` \| `None` | 原始圖片尺寸（Phi-3.5 需要） |
| `num_img_tokens` | `Any` \| `None` | 每張圖佔用的 token 數 |

#### `to_dict(self) -> Dict[str, Any]`

將非 `None` 的欄位轉為 dict，供 `FusionDecoder.fuse_inputs()` 使用。只有 `image_sizes` 和 `num_img_tokens` 非 `None` 時才加入。

---

### `TextPrompt`

**功能**: 封裝建構好的 chat prompt 字串。

| 欄位 | 型別 | 說明 |
|------|------|------|
| `prompt` | `str` | 完整的 chat template 字串，含圖片佔位符 |

---

### `GenerationConfig`

**功能**: 推論參數封裝，避免每次呼叫都硬編碼參數。

| 欄位 | 預設值 | 說明 |
|------|--------|------|
| `max_new_tokens` | `256` | 最多生成幾個 token |
| `temperature` | `0.0` | 溫度（0.0 = 貪婪解碼） |
| `do_sample` | `False` | 是否啟用採樣 |

#### `GenerationConfig.deliberate() -> GenerationConfig`

從 `DELIBERATE_MAX_TOKENS`、`DELIBERATE_TEMPERATURE` 建構深思路徑的設定，`do_sample=False`（確定性輸出）。

#### `GenerationConfig.dialogue() -> GenerationConfig`

從 `DIALOGUE_MAX_TOKENS`、`DIALOGUE_TEMPERATURE` 建構對話路徑設定，若 `DIALOGUE_TEMPERATURE > 0` 則 `do_sample=True`（增加多樣性）。

**範例**:

```python
# 深思路徑設定（確定性）
cfg = GenerationConfig.deliberate()
print(cfg.max_new_tokens)  # 例如 512（從 model_config 讀取）
print(cfg.do_sample)       # False

# 對話路徑設定（帶溫度）
cfg = GenerationConfig.dialogue()
print(cfg.temperature)     # 例如 0.7
print(cfg.do_sample)       # True
```

---

## 主要類別 / 函式

### `VisionEncoder`

**功能**: 包裝 Phi-3.5-Vision 的 `image_processor`，將圖片列表轉為模型可接受的 tensor。

#### `__init__(self, processor)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `processor` | `AutoProcessor` | Phi-3.5-Vision 的 processor 物件 |

---

#### `encode(self, images, return_tensors) -> VisionBatch`

**功能**: 將一批圖片編碼為 tensor。自動處理 `str`（路徑）和 `PIL.Image` 兩種輸入，並強制轉為 RGB。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `images` | `Sequence[ImageLike]` | 圖片列表（路徑字串或 PIL.Image） |
| `return_tensors` | `str` | 輸出 tensor 格式，預設 `"pt"`（PyTorch） |

**回傳**: `VisionBatch`

**範例**:

```python
from PIL import Image
img = Image.open("scene_screenshot.png")
vision_batch = loader.vision.encode([img])
image_inputs = vision_batch.to_dict()
# image_inputs 含 pixel_values、image_sizes（若非 None）等
```

---

### `TextEncoder`

**功能**: 建立含圖片佔位符的 chat prompt，使用 processor 的 tokenizer apply_chat_template。

#### `build_prompt(self, user_text, num_images, system_text) -> TextPrompt`

**功能**: 組合完整的 chat prompt。每張圖插入一個 `<|image_N|>\n` 佔位符，放在 user 訊息的最前面。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `user_text` | `str` | 主要 prompt 文字（角色狀態、場景等） |
| `num_images` | `int` | 圖片數量（0 表示純文字） |
| `system_text` | `str` \| `None` | 可選的 system prompt |

**回傳**: `TextPrompt`

**佔位符範例**: 2 張圖時插入 `<|image_1|>\n<|image_2|>\n` 在 user 內容前。

**範例**:

```python
# 純文字 prompt（無圖片）
text_prompt = loader.text.build_prompt(
    user_text  = "Amy 是咖啡師，現在在咖啡店工作。請決定下一步行動。",
    num_images = 0,
)
print(text_prompt.prompt)  # 含 chat template 的完整字串

# 含 1 張圖片的 prompt
text_prompt = loader.text.build_prompt(
    user_text  = "根據場景截圖決定行動。",
    num_images = 1,
)
# prompt 開頭含 "<|image_1|>\n 根據場景截圖決定行動。"
```

---

### `FusionDecoder`

**功能**: 接受融合後的圖文輸入，呼叫 Phi-3.5-Vision 模型生成文字輸出。

#### `__init__(self, model, processor, device)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `model` | `AutoModelForCausalLM` | 已載入的 Phi-3.5-Vision 模型 |
| `processor` | `AutoProcessor` | 對應的 processor |
| `device` | `torch.device` | 推論裝置（`cuda:0`、`mps` 或 `cpu`） |

---

#### `fuse_inputs(self, text, image_inputs, return_tensors) -> Dict[str, Any]`

**功能**: 呼叫 processor 的 `_convert_images_texts_to_inputs()` 合併圖文輸入，生成模型可接受的 dict。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `text` | `str` | 已建構的 chat prompt 字串 |
| `image_inputs` | `dict` | `VisionBatch.to_dict()` 的輸出（可為空 dict） |
| `return_tensors` | `str` | 預設 `"pt"` |

**範例**:

```python
# 純文字（無圖片）
fused = loader.fusion.fuse_inputs(
    text         = text_prompt.prompt,
    image_inputs = {},
)

# 含圖片
fused = loader.fusion.fuse_inputs(
    text         = text_prompt.prompt,
    image_inputs = vision_batch.to_dict(),
)
```

---

#### `generate(self, fused_inputs, gen_cfg) -> str`

**功能**: 單筆推論（`@torch.inference_mode()`）。將所有 tensor 搬到目標裝置，呼叫 `model.generate()`，切除 prompt 部分只回傳新生成的文字。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `fused_inputs` | `Dict[str, Any]` | `fuse_inputs()` 的輸出 |
| `gen_cfg` | `GenerationConfig` \| `None` | 推論設定；`None` 時使用預設（256 tokens，溫度 0） |

**回傳**: `str`（已切除 prompt 部分的純輸出文字）

**範例**:

```python
raw_output = loader.fusion.generate(fused, GenerationConfig.deliberate())
# raw_output 例如：
# "[ACTION] 工作\n[TARGET] \n[CONTENT] \n[THOUGHT] 現在是上班時間..."
```

---

#### `generate_batch(self, fused_inputs_list, gen_cfg) -> List[str]`

**功能**: Batch 推論。由於 Phi-3.5-Vision 的輸入結構特殊（含 `image_sizes` 等欄位），目前以 sequential fallback 實作（逐個呼叫 `generate()`）。真正的 padding batch 由 `batch_generate()` 函式的分塊邏輯處理。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `fused_inputs_list` | `List[Dict]` | 多筆 fused inputs |
| `gen_cfg` | `GenerationConfig` \| `None` | 推論設定 |

**回傳**: `List[str]`（順序與輸入對應）

---

### 模組層函式

#### `detect_available_vram_mb() -> int`

**功能**: 偵測當前 GPU 可用顯存（MB）。非 CUDA 環境（CPU、MPS）回傳 `0`。

---

#### `decide_batch_size(num_prompts, vram_mb) -> int`

**功能**: 根據顯存決定 batch size 上限。

| VRAM 條件 | batch size 上限 |
|-----------|----------------|
| `>= VRAM_THRESHOLD_HIGH` | `BATCH_SIZE_MAX_HIGH_VRAM` |
| `>= VRAM_THRESHOLD_MID` | `BATCH_SIZE_MAX_MID_VRAM` |
| 否則（低顯存 / CPU） | `BATCH_SIZE_MAX_LOW_VRAM` |

實際回傳值為 `min(num_prompts, max_batch)`，不超過需求量。

**範例**:

```python
# 有 8GB VRAM（符合 VRAM_THRESHOLD_HIGH）
bs = decide_batch_size(10)
print(bs)  # 例如 4（BATCH_SIZE_MAX_HIGH_VRAM）

# CPU 環境（VRAM=0）
bs = decide_batch_size(10, vram_mb=0)
print(bs)  # 例如 1（BATCH_SIZE_MAX_LOW_VRAM）
```

---

#### `batch_generate(loader, prompts, images_list, gen_cfg) -> list`

**功能**: Batch 推論入口。自動計算 batch size，分塊處理，合併結果。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `loader` | `ModelLoader` | 含 `.vision`、`.text`、`.fusion` 的模型載入器 |
| `prompts` | `list[str]` | prompt 字串列表 |
| `images_list` | `list` \| `None` | 對應的圖片列表（`PIL.Image` 或 `None`）；`None` 表示全部純文字 |
| `gen_cfg` | `GenerationConfig` \| `None` | 推論設定 |

**回傳**: `list[str]`（結果順序與 prompts 對應）

**內部流程**:
1. `decide_batch_size()` 計算 batch size
2. 以 batch size 分塊
3. 每塊內對每個 (prompt, image) 配對做 `text.build_prompt()` + `vision.encode()` + `fusion.fuse_inputs()`
4. 呼叫 `fusion.generate_batch()` 推論
5. 合併所有結果

**範例**:

```python
from model.inference_engine import batch_generate, GenerationConfig

prompts = [
    "Amy 的決策 prompt...",
    "Ben 的決策 prompt...",
    "Claire 的決策 prompt...",
]
results = batch_generate(loader, prompts, images_list=None, gen_cfg=GenerationConfig.deliberate())
print(results[0])  # Amy 的模型輸出
print(results[1])  # Ben 的模型輸出
```

---

## 模擬使用情境

### 情境一: 完整圖文推論流程（含場景截圖）

```python
from PIL import Image
from model.inference_engine import GenerationConfig

scene_img = Image.open("scene_14_00.png")

# 1. 視覺編碼
vision_batch = loader.vision.encode([scene_img])

# 2. 文字 prompt 建構
text_prompt = loader.text.build_prompt(
    user_text  = "Ben 在辦公室，截圖顯示有同事走近。請決定 Ben 下一步行動。",
    num_images = 1,
)

# 3. 圖文融合
fused = loader.fusion.fuse_inputs(
    text         = text_prompt.prompt,
    image_inputs = vision_batch.to_dict(),
)

# 4. 推論
output = loader.fusion.generate(fused, GenerationConfig.deliberate())
print(output)  # "[ACTION] 對話\n[TARGET] 同事\n..."
```

### 情境二: 純文字 Batch 推論（多角色同步決策）

```python
from model.inference_engine import batch_generate, GenerationConfig

amy_prompt   = "..."  # Amy 的完整決策 prompt
ben_prompt   = "..."  # Ben 的完整決策 prompt
claire_prompt = "..." # Claire 的完整決策 prompt

outputs = batch_generate(
    loader      = loader,
    prompts     = [amy_prompt, ben_prompt, claire_prompt],
    images_list = None,  # 純文字，無截圖
    gen_cfg     = GenerationConfig.deliberate(),
)
print(outputs[0])  # Amy 的輸出
print(outputs[2])  # Claire 的輸出
```

---

## 注意事項

- **`FusionDecoder.generate()` 切除 prompt 部分**：使用 `ids[:, fused_inputs["input_ids"].shape[1]:]` 確保回傳的只有新生成的 token，不含原始 prompt。
- **`generate_batch()` 目前為 sequential fallback**：由於 Phi-3.5-Vision 的 `image_sizes` 等欄位難以 padding，目前的實作是逐一推論；真正的 batch 平行化留待後續優化。
- **VRAM 偵測失敗時回傳 0**：`detect_available_vram_mb()` 在任何例外下都回傳 0，確保降級至低 batch size 而不崩潰。
- **`do_sample` 自動設定**：`GenerationConfig.dialogue()` 中 `do_sample = (DIALOGUE_TEMPERATURE > 0)`，temperature=0 時自動關閉採樣（貪婪解碼），避免 temperature=0 + do_sample=True 的矛盾設定。
- **tensor 搬移**：`generate()` 內對所有有 `.to()` 方法的 tensor 做 `.to(self.device)`，確保 CPU 預處理的 tensor 在 GPU 模型上正常運行。
