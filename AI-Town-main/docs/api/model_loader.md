# ModelLoader — Phi-3.5-Vision 模型載入器

> **路徑**: `model/model_loader.py`  
> **職責**: 單例載入 Phi-3.5-Vision，並提供各場景的推論工廠方法

---

## 功能概覽

`ModelLoader` 是整個模擬系統的模型管理中心，採用**單例模式**（Singleton Pattern）：模型只載入一次（`load()`），之後所有角色的 `Agent` 共用同一份模型，避免重複佔用 VRAM。

載入時會自動選擇最佳推論裝置（`pick_device()`：CUDA → MPS → CPU 優先順序），並初始化三個引擎元件：`VisionEncoder`（圖片編碼）、`TextEncoder`（prompt 建構）、`FusionDecoder`（圖文融合推論），全部來自 `model/inference_engine.py`。

**工廠方法**是 `ModelLoader` 的核心設計。`make_model_fn()` 回傳一個可呼叫的推論函式（`model_fn(prompt: str) -> str`），避免呼叫端直接操作底層 tensor 邏輯。不同場景（深思、對話、睡眠濃縮各步驟）各有專屬工廠方法，從 `config/model_config` 讀取對應的 token 預算，確保一致性。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `torch` | 裝置選擇、模型載入 |
| 依賴 | `transformers` | `AutoModelForCausalLM`、`AutoProcessor` |
| 依賴 | `config.model_config` | 模型 ID、快取路徑、各場景 token 預算 |
| 依賴 | `model.inference_engine` | `VisionEncoder`、`TextEncoder`、`FusionDecoder`、`GenerationConfig` |
| 被依賴 | `main.py` / `simulate.py` | 啟動時呼叫 `load()` |
| 被依賴 | `agent.manager.AgentManager` | 取 loader 傳給每個 `Agent` |
| 被依賴 | `agent.agent.Agent` | 呼叫 `_call_model()` 時使用 `loader` |
| 被依賴 | `core.consolidation` | 呼叫 `make_consolidation_fn(step)` |
| 被依賴 | `agent.scheduler` | 呼叫 `make_model_fn(SCHEDULE_GEN_MAX_TOKENS)` |

---

## 模組層函式

### `pick_device() -> torch.device`

**功能**: 自動偵測並回傳最佳推論裝置。

| 優先順序 | 裝置 | 條件 |
|---------|------|------|
| 1 | `cuda:0` | `torch.cuda.is_available()` |
| 2 | `mps` | `torch.backends.mps.is_available()`（Apple Silicon） |
| 3 | `cpu` | 其他 |

**範例**:

```python
device = pick_device()
print(device)  # torch.device('cuda:0')（若有 NVIDIA GPU）
```

---

## 主要類別

### `ModelLoader`

**功能**: Phi-3.5-Vision 單例載入器。管理模型生命週期，提供推論工廠方法。

#### `__init__(self)`

初始化所有成員為 `None` 或 `False`，呼叫 `pick_device()` 決定裝置。**不載入模型**，需明確呼叫 `load()`。

| 屬性 | 型別 | 說明 |
|------|------|------|
| `device` | `torch.device` | 推論裝置 |
| `model` | `AutoModelForCausalLM` \| `None` | 已載入的模型 |
| `processor` | `AutoProcessor` \| `None` | 模型對應的 processor |
| `vision` | `VisionEncoder` \| `None` | 圖片編碼器 |
| `text` | `TextEncoder` \| `None` | 文字 prompt 建構器 |
| `fusion` | `FusionDecoder` \| `None` | 圖文融合推論器 |
| `_loaded` | `bool` | 是否已載入（防止重複載入） |

---

#### `load(self)`

**功能**: 載入 Phi-3.5-Vision 模型與 processor（首次執行會從 HuggingFace 下載或從 `MODEL_CACHE_DIR` 讀取快取）。已載入時直接回傳（冪等操作）。

**載入流程**:
1. 若 `_loaded == True` → 直接回傳
2. 以 `AutoModelForCausalLM.from_pretrained(MODEL_ID, trust_remote_code=True, torch_dtype="auto", _attn_implementation="eager")` 載入模型
3. `.to(self.device)` 搬移至目標裝置
4. 以 `AutoProcessor.from_pretrained(MODEL_ID, num_crops=MODEL_NUM_CROPS)` 載入 processor
5. 初始化 `VisionEncoder`、`TextEncoder`、`FusionDecoder`
6. 設 `_loaded = True`

**注意**: `_attn_implementation="eager"` 是明確指定使用 eager attention（非 flash attention），確保在各種硬體上的相容性。

**範例**:

```python
loader = ModelLoader()
loader.load()  # 首次執行：下載/讀取快取，約需數分鐘
loader.load()  # 第二次：直接回傳，不重複載入
print(loader.is_loaded())  # True
```

---

#### `is_loaded(self) -> bool`

**功能**: 回傳模型是否已載入。`Agent._call_model()` 在呼叫模型前先檢查此值。

---

#### `make_model_fn(self, max_new_tokens, temperature) -> Callable`

**功能**: 回傳一個純文字推論 callable，signature 為 `model_fn(prompt: str) -> str`。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `max_new_tokens` | `int` | 最多生成幾個 token（預設 256） |
| `temperature` | `float` | 採樣溫度（0.0 為貪婪解碼，預設 0.0） |

**注意**: 若模型未載入（`_loaded == False`），呼叫時拋出 `RuntimeError`。

**內部行為**:
1. `text.build_prompt(prompt, num_images=0)` 建構純文字 prompt
2. `fusion.fuse_inputs(text=..., image_inputs={})` 融合（無圖片）
3. 設定 `fused["use_cache"] = False`（防止 KV cache 跨呼叫汙染）
4. `fusion.generate(...)` 推論並回傳文字

**範例**:

```python
loader.load()
fn = loader.make_model_fn(max_new_tokens=200, temperature=0.5)
output = fn("Amy 今天心情如何？請用一句話回答。")
print(output)  # 模型生成的回答
```

---

#### `make_deliberate_fn(self) -> Callable`

**功能**: 深思路徑專用 model_fn。使用 `DELIBERATE_MAX_TOKENS` 和 `DELIBERATE_TEMPERATURE`。

**範例**:

```python
deliberate_fn = loader.make_deliberate_fn()
output = deliberate_fn(deliberate_prompt_text)
# 使用較多 token（例如 512），溫度 0（確定性）
```

---

#### `make_dialogue_fn(self) -> Callable`

**功能**: 對話生成專用 model_fn。使用 `DIALOGUE_MAX_TOKENS` 和 `DIALOGUE_TEMPERATURE`。

**範例**:

```python
dialogue_fn = loader.make_dialogue_fn()
output = dialogue_fn(dialogue_prompt_text)
# 使用較少 token（例如 128），溫度可能 > 0（增加對話多樣性）
```

---

#### `make_consolidation_fn(self, step: str) -> Callable`

**功能**: 睡眠濃縮各步驟專用 model_fn。依 `step` 名稱從 token map 查詢對應的最大 token 數，`temperature=0.0`（確定性）。

**有效 `step` 值與對應 token 預算**:

| `step` | config 常數 | 說明 |
|--------|-------------|------|
| `"ham_extract"` | `CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS` | 從 STM 提取 HAM 命題 |
| `"select"` | `CONSOLIDATE_SELECT_MAX_TOKENS` | 選擇重要命題加入 LTM |
| `"summary"` | `CONSOLIDATE_SUMMARY_MAX_TOKENS` | 生成今日摘要 |
| `"relation"` | `CONSOLIDATE_RELATION_MAX_TOKENS` | 更新角色關係 |
| `"emotion"` | `CONSOLIDATE_EMOTION_MAX_TOKENS` | 更新情緒狀態 |
| `"schedule"` | `SCHEDULE_GEN_MAX_TOKENS` | 生成明日時間表 |

**未知 step** → fallback 為 256 tokens。

**範例**:

```python
# 睡眠濃縮中，提取 HAM 命題的步驟
ham_fn = loader.make_consolidation_fn("ham_extract")
ham_output = ham_fn(stm_to_ham_prompt)

# 更新情緒的步驟
emotion_fn = loader.make_consolidation_fn("emotion")
emotion_output = emotion_fn(emotion_update_prompt)
```

---

## 模擬使用情境

### 情境一: 系統啟動（`simulate.py` 或 `main.py`）

```python
from model.model_loader import ModelLoader
from world.world_clock import WorldClock
from agent.manager import AgentManager

# 1. 初始化並載入模型
loader = ModelLoader()
loader.load()
print(f"模型載入完成，裝置：{loader.device}")  # torch.device('cuda:0')

# 2. 建立時鐘與 manager（loader 共用）
clock   = WorldClock()
manager = AgentManager(loader, clock)  # 所有角色共用 loader

# 3. 開始模擬
result = manager.run_autonomous_days(3)
```

### 情境二: 睡眠濃縮（`core/consolidation.py` 使用）

```python
# consolidation.py 在 consolidate() 中呼叫各步驟的 model_fn
ham_fn    = loader.make_consolidation_fn("ham_extract")
select_fn = loader.make_consolidation_fn("select")
summary_fn = loader.make_consolidation_fn("summary")

# 各步驟獨立呼叫，token 預算各自不同
ham_result     = ham_fn(prompt_ham)
select_result  = select_fn(prompt_select)
summary_result = summary_fn(prompt_summary)
```

### 情境三: FakeLoader 替換（測試用）

```python
# 在單元測試中，可用 FakeLoader 替換 ModelLoader
class FakeLoader:
    def is_loaded(self):
        return True
    def make_model_fn(self, max_new_tokens=256, temperature=0.0):
        # 回傳固定字串的假 model_fn
        return lambda prompt: "[ACTION] 休息\n[TARGET] \n[CONTENT] \n[THOUGHT] \n[HAM]\n[/HAM]"

# Agent 會走 FakeLoader 的 make_model_fn 路徑
agent = Agent(char, stm, ltm, graph, FakeLoader(), builder)
```

---

## 注意事項

- **單例設計**：`_loaded` 標誌確保冪等性，重複呼叫 `load()` 安全且無副作用。但若需要多個模型實例（例如不同配置），則需要建立多個 `ModelLoader` 物件。
- **`use_cache = False`**：`make_model_fn()` 建構的 `model_fn` 會設定 `fused["use_cache"] = False`，防止不同角色的 KV cache 意外交叉汙染。
- **`torch_dtype="auto"`**：讓 transformers 自動選擇精度（通常為 `float16` 或 `bfloat16`），節省顯存。
- **快取路徑**：若 `MODEL_CACHE_DIR` 為空字串或 `None`，則使用 transformers 預設快取（`~/.cache/huggingface`）；設定後可加速離線環境的載入。
- **`Agent._call_model()` 的兩條路徑**：若 `loader.text` 或 `loader.fusion` 為 `None`（FakeLoader 場景），直接走 `make_model_fn()` 的簡化路徑；完整模型走圖文 pipeline。
