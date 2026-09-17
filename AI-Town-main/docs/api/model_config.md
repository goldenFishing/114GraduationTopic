# model_config — Phi-3.5-Vision 推論參數集中管理

> **路徑**: `config/model_config.py`  
> **職責**: 定義模型載入、推論、批次與 Prompt 預算的所有數值參數

---

## 功能概覽

`model_config.py` 集中管理所有與 Phi-3.5-Vision-Instruct 模型互動相關的超參數。這些參數分為六大類：模型載入設定、深思路徑（deliberate，System 2 決策）的生成設定、對話生成設定、睡眠濃縮各步驟的 token 上限、prompt 注入預算，以及批次推論的批大小閾值。

此模組之所以獨立存在，是因為不同的推論場景對模型輸出有截然不同的需求——決策需要確定性（`temperature=0.0`），對話需要多樣性（`temperature=0.3`）；HAM 抽取需要較多 token，情緒推斷只需一個詞（10 tokens）。將這些分散設定集中於單一檔案，讓硬體調校（顯存）與行為調校（溫度、長度）都能在一處完成。

在硬體適應方面，此模組定義了 VRAM 判斷閾值（12 GB / 16 GB）與對應的批大小，讓 `model/batch_inference.py` 能在 RTX 3060、RTX 4090 等不同等級硬體上自動選擇最佳批次策略，無需手動修改推論邏輯。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | （無外部依賴） | 純常數定義，不 import 任何模組 |
| 被依賴 | `model/model_loader.py` | 使用 `MODEL_ID`、`MODEL_NUM_CROPS`、`MODEL_CACHE_DIR` 載入模型 |
| 被依賴 | `model/fusion_decoder.py` | 使用 `DELIBERATE_*`、`DIALOGUE_*` 作為 GenerationConfig 預設值 |
| 被依賴 | `model/prompt_builder.py` | 使用 `STM_TOKEN_BUDGET`、`LTM_TOKEN_BUDGET` 截斷 prompt 區塊 |
| 被依賴 | `model/batch_inference.py` | 使用 `BATCH_SIZE_MAX_*`、`VRAM_THRESHOLD_*` 決定批大小 |
| 被依賴 | `agent/scheduler.py` | 使用 `SCHEDULE_GEN_MAX_TOKENS` 限制時間表生成長度 |
| 被依賴 | `core/consolidation.py` | 使用 `CONSOLIDATE_*_MAX_TOKENS` 各步驟 token 上限 |

---

## 主要常數 / 資料結構

### `MODEL_ID`
**型別**: `str`  
**預設值**: `"microsoft/Phi-3.5-vision-instruct"`  
**說明**: HuggingFace Hub 上的模型識別碼。`model/model_loader.py` 在程式啟動時用此 ID 從 Hub 或本地快取載入模型。若要替換為其他模型，修改此值即可，無需改動載入邏輯。

---

### `MODEL_NUM_CROPS`
**型別**: `int`  
**預設值**: `4`  
**說明**: Phi-3.5-Vision 處理圖片時的切塊數量。切塊越多視覺細節越豐富，但顯存消耗和推論時間也相應增加。AI-Town 主要使用文字推論，此值設為 4 已足夠處理場景截圖中的物件偵測結果。

---

### `MODEL_CACHE_DIR`
**型別**: `str | None`  
**預設值**: `None`  
**說明**: 模型權重的本地快取目錄。`None` 表示使用 HuggingFace 預設快取路徑（通常是 `~/.cache/huggingface/`）。若硬碟空間有限或需要指定快取位置，可改為自訂路徑，例如 `"D:/models/phi35"`。

---

### `DELIBERATE_MAX_TOKENS`
**型別**: `int`  
**預設值**: `600`  
**說明**: 深思路徑（System 2 決策）的輸出 token 上限。預算分配：`[ACTION]+[TARGET]+[CONTENT]` 約 50 tokens、`[THOUGHT]` 約 130 tokens、`[HAM]` 5 條命題約 350 tokens、緩衝 70 tokens，合計 600 tokens。

---

### `DELIBERATE_TEMPERATURE`
**型別**: `float`  
**預設值**: `0.0`  
**說明**: 深思路徑的生成溫度。設為 0.0 表示確定性（greedy）輸出，在相同 prompt 下每次產生相同結果，確保決策可重現、易於除錯。

---

### `DIALOGUE_MAX_TOKENS`
**型別**: `int`  
**預設值**: `400`  
**說明**: 對話生成每輪的輸出 token 上限。對話回應不需要 HAM 命題那麼長，400 tokens 足以容納一句完整回應加上 `[THOUGHT]` 內心想法。

---

### `DIALOGUE_TEMPERATURE`
**型別**: `float`  
**預設值**: `0.3`  
**說明**: 對話生成的溫度。稍微提高至 0.3，讓不同角色的對話具有語言風格差異，避免 Amy 和 Emma 的說話方式一模一樣，同時不至於過於隨機而失去語意連貫性。

---

### `CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS`
**型別**: `int`  
**預設值**: `500`  
**說明**: 睡眠濃縮 Step 2 的 token 上限——從 STM 敘述中抽取 HAM 5 元組命題。需要輸出最多 10 筆命題（每筆約 30-50 tokens），故設為 500。

---

### `CONSOLIDATE_SELECT_MAX_TOKENS`
**型別**: `int`  
**預設值**: `200`  
**說明**: 睡眠濃縮 Step 3 的 token 上限——從候選 HAM 中篩選最重要的 5 筆。輸出量少於 Step 2，200 tokens 足夠。

---

### `CONSOLIDATE_SUMMARY_MAX_TOKENS`
**型別**: `int`  
**預設值**: `80`  
**說明**: 睡眠濃縮 Step 5 的 token 上限——生成 LTM 新摘要（1-2 句話）。短摘要任務，80 tokens 已綽綽有餘。

---

### `CONSOLIDATE_RELATION_MAX_TOKENS`
**型別**: `int`  
**預設值**: `80`  
**說明**: 睡眠濃縮 Step 6 的 token 上限——更新與某角色的關係摘要（1 句話）。與 `CONSOLIDATE_SUMMARY_MAX_TOKENS` 相同量級。

---

### `CONSOLIDATE_EMOTION_MAX_TOKENS`
**型別**: `int`  
**預設值**: `10`  
**說明**: 睡眠濃縮 Step 7 的 token 上限——推斷新情緒。只需回傳一個情緒詞（如「平靜」、「疲憊」），10 tokens 已遠超需求，極大節省推論成本。

---

### `SCHEDULE_GEN_MAX_TOKENS`
**型別**: `int`  
**預設值**: `500`  
**說明**: 睡眠濃縮 Step 8 的 token 上限——生成隔天時間表 JSON list。一份完整時間表約含 8-10 個時段，每個 JSON 物件約 40-50 tokens，合計約 400-500 tokens。

---

### `STM_TOKEN_BUDGET`
**型別**: `int`  
**預設值**: `1500`  
**說明**: `PromptBuilder` 在組裝 prompt 時，STM 敘述化文字區塊的最大 token 數。一天 30 筆 STM 敘述，每筆約 50 tokens，合計約 1500 tokens，剛好達到此上限。超出時截斷最早的記錄。

---

### `LTM_TOKEN_BUDGET`
**型別**: `int`  
**預設值**: `800`  
**說明**: prompt 中 LTM 命題反向組句後的最大 token 數。HAM 圖譜 2 跳擴散後命題量增加，此預算確保注入的長期記憶不會讓 prompt 超長而影響推論速度。

---

### `BATCH_SIZE_MAX_HIGH_VRAM`
**型別**: `int`  
**預設值**: `5`  
**說明**: 顯存 ≥ 16 GB（如 RTX 4090 24GB）時的最大批大小。5 個角色可在一次 forward pass 中同時處理，最大化 GPU 利用率。

---

### `BATCH_SIZE_MAX_MID_VRAM`
**型別**: `int`  
**預設值**: `3`  
**說明**: 顯存 ≥ 12 GB（如 RTX 3060 12GB）時的最大批大小。每批處理 3 個角色，避免 OOM（Out of Memory）錯誤。

---

### `BATCH_SIZE_MAX_LOW_VRAM`
**型別**: `int`  
**預設值**: `1`  
**說明**: 顯存不足 12 GB 時的批大小。退化為逐一（sequential）推論，確保在低階顯卡上也能運行。

---

### `VRAM_THRESHOLD_HIGH`
**型別**: `int`  
**預設值**: `16384`（`16 * 1024` MB）  
**說明**: 高顯存模式的觸發閾值（16 GB）。`batch_inference.py` 在偵測到可用 VRAM ≥ 此值時選擇 HIGH 批大小。

---

### `VRAM_THRESHOLD_MID`
**型別**: `int`  
**預設值**: `12288`（`12 * 1024` MB）  
**說明**: 中顯存模式的觸發閾值（12 GB）。可用 VRAM 介於 `VRAM_THRESHOLD_MID` 和 `VRAM_THRESHOLD_HIGH` 之間時選擇 MID 批大小。

---

## 主要函式

此模組不定義函式，僅包含常數定義。

---

## 模擬使用情境

### 情境一：model_loader 載入模型

```python
from config.model_config import MODEL_ID, MODEL_NUM_CROPS, MODEL_CACHE_DIR

# ModelLoader.load() 使用這些常數
from transformers import AutoModelForCausalLM, AutoProcessor

processor = AutoProcessor.from_pretrained(
    MODEL_ID,                        # "microsoft/Phi-3.5-vision-instruct"
    num_crops=MODEL_NUM_CROPS,       # 4
    cache_dir=MODEL_CACHE_DIR,       # None → 使用 HuggingFace 預設快取
    trust_remote_code=True,
)
# 首次執行時從 HuggingFace 下載，後續從快取讀取
```

### 情境二：Amy 進行深思決策 vs 對話的不同推論設定

```python
from config.model_config import (
    DELIBERATE_MAX_TOKENS, DELIBERATE_TEMPERATURE,
    DIALOGUE_MAX_TOKENS, DIALOGUE_TEMPERATURE,
)

# Amy 在咖啡店決定下一個行動（深思路徑）
decision_config = {
    "max_new_tokens": DELIBERATE_MAX_TOKENS,   # 600
    "temperature": DELIBERATE_TEMPERATURE,     # 0.0（確定性）
    "do_sample": False,
}

# Amy 回應 David 的問候（對話路徑）
dialogue_config = {
    "max_new_tokens": DIALOGUE_MAX_TOKENS,     # 400
    "temperature": DIALOGUE_TEMPERATURE,       # 0.3（適度多樣）
    "do_sample": True,
}

# 相同的 Amy 角色，不同場景使用不同生成策略
```

### 情境三：batch_inference 依顯存自動選擇批大小

```python
import torch
from config.model_config import (
    BATCH_SIZE_MAX_HIGH_VRAM,
    BATCH_SIZE_MAX_MID_VRAM,
    BATCH_SIZE_MAX_LOW_VRAM,
    VRAM_THRESHOLD_HIGH,
    VRAM_THRESHOLD_MID,
)

def get_batch_size() -> int:
    if not torch.cuda.is_available():
        return BATCH_SIZE_MAX_LOW_VRAM  # 1（CPU fallback）

    total_vram_mb = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
    if total_vram_mb >= VRAM_THRESHOLD_HIGH:   # ≥ 16384 MB（4090）
        return BATCH_SIZE_MAX_HIGH_VRAM        # 5 個角色一批
    elif total_vram_mb >= VRAM_THRESHOLD_MID:  # ≥ 12288 MB（3060）
        return BATCH_SIZE_MAX_MID_VRAM         # 3 個角色一批
    else:
        return BATCH_SIZE_MAX_LOW_VRAM         # 1 個角色

# RTX 4090 (24GB) → batch_size = 5（Amy、Ben、Claire、David、Emma 同時跑）
# RTX 3060 (12GB) → batch_size = 3（Amy、Ben、Claire 一批；David、Emma 第二批）
```

### 情境四：Emma 睡眠濃縮時的 token 預算分配

```python
from config.model_config import (
    CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS,   # 500
    CONSOLIDATE_SELECT_MAX_TOKENS,        # 200
    CONSOLIDATE_SUMMARY_MAX_TOKENS,       # 80
    CONSOLIDATE_RELATION_MAX_TOKENS,      # 80
    CONSOLIDATE_EMOTION_MAX_TOKENS,       # 10
    SCHEDULE_GEN_MAX_TOKENS,              # 500
)

# Emma 入睡，依序執行 8 個濃縮步驟
# Step 2: 從 STM 抽 HAM → 最多 500 tokens
# Step 3: 篩選重要 HAM → 最多 200 tokens
# Step 5: 生成 LTM 摘要（1-2句）→ 最多 80 tokens
# Step 6: 更新與 Amy 的關係摘要 → 最多 80 tokens
# Step 7: 推斷情緒（單詞）→ 最多 10 tokens（成本極低）
# Step 8: 生成明天時間表 JSON → 最多 500 tokens
total_worst_case = 500 + 200 + 80 + 80 + 10 + 500
print(f"Emma 睡眠濃縮最差情況共呼叫：{total_worst_case} tokens")
# Emma 睡眠濃縮最差情況共呼叫：1370 tokens
```

---

## 注意事項

- `DELIBERATE_TEMPERATURE=0.0` 使決策完全確定性，對於相同的輸入狀態每次都會做出相同決定，有利於除錯但可能降低模擬的多樣性。若需要引入隨機性，可調整至 0.1-0.2。
- `CONSOLIDATE_EMOTION_MAX_TOKENS=10` 非常嚴格，模型必須只輸出一個情緒詞。若模型輸出超過 10 tokens，`consolidation.py` 中應有截斷邏輯處理溢出情況。
- `STM_TOKEN_BUDGET=1500` 與 `LTM_TOKEN_BUDGET=800` 的合計約 2300 tokens，加上角色個性、場景說明等其他 prompt 區塊，完整 prompt 可能達到 3000-4000 tokens。Phi-3.5 的 128K context window 遠超此需求，但推論速度與 prompt 長度成正比，避免不必要的長度浪費。
- 若 `MODEL_CACHE_DIR=None` 且在無網路環境部署，程式啟動時會因為找不到模型而失敗。部署前請確認模型已下載至本地，或指定正確的 `MODEL_CACHE_DIR`。
- `VRAM_THRESHOLD_MID=12*1024=12288` 是精確的 12.0 GB 門檻，RTX 3060 標稱 12 GB 但驅動可用量有時略低，可考慮將此值調低至 `11 * 1024` 以留出餘裕。
