# mental_state — 情緒與困惑度計算

> **路徑**: `core/mental_state.py`  
> **職責**: 計算困惑度 C 值並決定 System 1/2 切換模式

---

## 功能概覽

`mental_state.py` 整合了原本分開的 `emotion.py` 和 `confusion.py` 兩個模組，負責 AI-Town 角色的「心理狀態」計算。在認知架構上，這個模組是 Kahneman（2011）System 1 / System 2 雙歷程理論的實作核心，決定角色在每個 tick 要採用「直覺反應」（intuitive）還是「深思熟慮」（deliberate）模式。

困惑度 **C = w1·U + w2·K + w3·S**，由三個獨立指數加權合計：
- **U（不確定性）**：Markov 機率分布的離散程度（前兩名差距越小 → U 越高）
- **K（衝突程度）**：邏輯衝突（如「有人要離開但角色在等待」）+ 情緒複雜性
- **S（驚訝程度）**：當前場景與 LTM 預期的差異程度

當 C 超過閾值（或 K ≥ 0.5 強制觸發）時，角色切換為 deliberate 模式呼叫 LLM 深思，否則走 intuitive 路徑直接採樣 Markov 結果。情緒也會影響切換閾值：負面情緒讓閾值升高，角色更難深思，更傾向直覺反應。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | `VALID_EMOTIONS`、`EMOTION_RESET_THRESHOLD` |
| 依賴 | `config.prompts` | `prompt_infer_emotion()`（情緒推斷 prompt） |
| 被依賴 | `agent/agent.py` | 每個 tick 決策前計算 C 值與模式 |
| 被依賴 | `core/character.py` | `get_confusion_threshold()` 呼叫 `adjust_threshold_by_emotion()` |
| 被依賴 | `agent/interrupt.py` | 中斷後判斷是否深思 |
| 被依賴 | `core/consolidation.py` | 睡眠 Step 7 情緒判斷 |

---

## 常數與閾值

| 常數 | 值 | 說明 |
|------|-----|------|
| `BASELINE_EMOTION` | `"平靜"` | 預設情緒基線，每天睡眠後回歸 |
| `DELIBERATE_K_OVERRIDE` | `0.5` | K 值達此閾值強制切換 deliberate 模式 |
| `CONFUSION_DROP_THRESHOLD` | `0.12` | C 下降超過此值→正向 reward（`tick_value.py` 用） |
| `CONFUSION_SPIKE_THRESHOLD` | `0.15` | C 上升超過此值→負向 reward |

### 情緒對閾值的調整量

| 情緒 | 調整量 | 效果 |
|------|--------|------|
| 平靜 | +0.00 | 基準，不調整 |
| 開心 | +0.00 | 基準，不調整 |
| 興奮 | +0.00 | 基準，不調整 |
| 緊張 | +0.10 | 更難深思，容易直覺反應 |
| 不安 | +0.10 | 更難深思，容易直覺反應 |
| 困惑 | +0.10 | 更難深思，容易直覺反應 |
| 難過 | +0.15 | 缺乏能量深思 |
| 疲憊 | +0.15 | 缺乏能量深思 |

---

## 主要函式

### 情緒（Emotion）部分

#### `should_update_emotion(today_max_K: float) -> bool`

**功能**: 判斷當天是否有重大事件（K 值峰值是否超過 `EMOTION_RESET_THRESHOLD`），決定是否需要呼叫模型推斷新情緒。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `today_max_K` | `float` | 當天 process_log 中所有 tick 的 K 值最大值 |

**回傳**: `bool` — True 表示需要呼叫模型

---

#### `reset_to_baseline() -> str`

**功能**: 回傳預設情緒 `"平靜"`。

---

#### `normalize_emotion(emotion_str: str) -> str`

**功能**: 驗證模型輸出的情緒字串是否在 `VALID_EMOTIONS` 中，否則回退為 `"平靜"`。

**範例**:
```python
normalize_emotion("開心")    # "開心"
normalize_emotion("高興")    # "平靜"（不在 VALID_EMOTIONS 中）
normalize_emotion("")        # "平靜"
```

---

#### `decide_new_emotion(today_max_K, today_narrative, previous_emotion, model_fn=None) -> str`

**功能**: 決定睡眠後的新情緒。若今天沒有重大事件或無模型可用，直接回歸 `"平靜"`；否則呼叫模型根據敘述推斷情緒，並通過 `normalize_emotion()` 驗證。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `today_max_K` | `float` | 當天 K 值峰值 |
| `today_narrative` | `str` | 當天 STM 敘述化文字（給模型參考） |
| `previous_emotion` | `str` | 昨天的情緒 |
| `model_fn` | `callable \| None` | 模型呼叫函式；`None` 代表 `--no-model` 模式 |

**回傳**: `str` — 合法的情緒字串

---

### 困惑度（Confusion）部分

#### `compute_U(action_candidates: list) -> float`

**功能**: 根據候選行動的機率分布計算不確定性 U。前兩名機率差距越小，U 越高（分布越分散）。

公式：`U = max(0.0, 1.0 - gap × 2)`，其中 `gap = top1_score - top2_score`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `action_candidates` | `list[dict]` | `[{"action": str, "score": float}, ...]`，通常由 Markov 分布轉換 |

**回傳**: `float` — 0.0 ~ 1.0

**範例**:
```python
# 前兩名差距大（確定）→ U 低
compute_U([{"action": "工作", "score": 0.8}, {"action": "休息", "score": 0.2}])
# gap = 0.6 → U = max(0, 1 - 1.2) = 0.0

# 前兩名差距小（不確定）→ U 高
compute_U([{"action": "工作", "score": 0.52}, {"action": "休息", "score": 0.48}])
# gap = 0.04 → U = max(0, 1 - 0.08) = 0.92
```

---

#### `compute_K(yolo_desc, input_text, current_action, scene_text="") -> float`

**功能**: 計算衝突程度 K。偵測兩類衝突：
1. **邏輯衝突**：觸發詞與當前行動相衝（如收到「緊急！」但在「休息」）→ +0.6
2. **情緒複雜性**：強情緒詞（混亂/不知所措）→ +0.45；一般情緒詞（心跳加速/暗戀）→ +0.25

**邏輯衝突偵測對**:

| 觸發詞 | 衝突的當前行動 |
|--------|--------------|
| 離開、走了、再見 | 等待、休息、工作 |
| 緊急、快、危險 | 休息、睡覺、滑手機 |
| 來了、到了、進來 | 工作、整理 |

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `yolo_desc` | `str` | YOLO 偵測描述 |
| `input_text` | `str` | 收到的對話或事件 |
| `current_action` | `str` | 角色當前行動 |
| `scene_text` | `str` | 當前場景描述 |

**回傳**: `float` — 0.0 ~ 1.0（clamp）

---

#### `compute_S(scene_text, ltm_summary, today_actions=None) -> float`

**功能**: 計算驚訝程度 S（當前場景與 LTM 預期的差異）。第一天 LTM 為空時回傳 0.0。

**驚訝強度關鍵字**:

| 強度 | 關鍵字 | 加分 |
|------|--------|------|
| 高 | 陌生人、從沒見過、完全不認識、突然闖入 | +0.6 |
| 中高 | 第一次、從未 | +0.5 |
| 中 | 意外、沒想到、不可思議 | +0.35 |
| 低 | 突然 | +0.25 |

**回傳**: `float` — 0.0 ~ 1.0

---

#### `compute_C(U, K, S, weights) -> float`

**功能**: 加權計算總困惑度 C = w1·U + w2·K + w3·S，clamp 到 1.0。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `U` | `float` | 不確定性 |
| `K` | `float` | 衝突程度 |
| `S` | `float` | 驚訝程度 |
| `weights` | `dict` | `{"w1": 0.4, "w2": 0.3, "w3": 0.3, "threshold": 0.5}` |

**回傳**: `float` — 0.0 ~ 1.0

---

#### `decide_mode(C, threshold, K=0.0) -> str`

**功能**: 決定處理模式。K ≥ `DELIBERATE_K_OVERRIDE (0.5)` 時強制 deliberate，否則比較 C 和 threshold。

**回傳**: `str` — `"intuitive"` 或 `"deliberate"`

---

#### `evaluate(...) -> dict`

**功能**: 一次計算所有指數並決定模式的主入口函式。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `yolo_desc` | `str` | YOLO 偵測描述 |
| `input_text` | `str` | 接收到的輸入 |
| `current_action` | `str` | 當前行動 |
| `scene_text` | `str` | 場景描述 |
| `ltm_summary` | `str` | LTM 摘要（S 計算用） |
| `today_actions` | `list` | 今日行動列表 |
| `weights` | `dict` | 困惑度加權 |
| `action_candidates` | `list` | Markov 候選行動（U 計算用） |

**回傳**:
```python
{
    "U": float,
    "K": float,
    "S": float,
    "C": float,
    "mode": "intuitive" | "deliberate"
}
```

---

#### `adjust_threshold_by_emotion(base_threshold: float, emotion: str) -> float`

**功能**: 依情緒調整困惑度閾值，由 `core/character.py` 的 `get_confusion_threshold()` 呼叫。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `base_threshold` | `float` | 基礎閾值（通常為 `confusion_weights["threshold"] = 0.5`） |
| `emotion` | `str` | 當前情緒字串 |

**回傳**: `float` — 調整後的閾值（clamp 到 [0.0, 1.0]）

**範例**:
```python
adjust_threshold_by_emotion(0.5, "平靜")  # 0.5
adjust_threshold_by_emotion(0.5, "難過")  # 0.65（+0.15）
adjust_threshold_by_emotion(0.5, "緊張")  # 0.60（+0.10）
```

---

## 模擬使用情境

### 情境一：Amy 在咖啡店聽到「有人闖入」後的困惑度計算

```python
from core.mental_state import evaluate

result = evaluate(
    yolo_desc        = "陌生人 走進 咖啡店",
    input_text       = "陌生人：你們這裡有沒有看到一個男人？",
    current_action   = "工作",
    scene_text       = "一個從沒見過的陌生人突然闖入咖啡店，神情慌張。",
    ltm_summary      = "Amy 在咖啡店認識 Ben 和 David，每天工作。",
    action_candidates = [
        {"action": "工作", "score": 0.45},
        {"action": "對話", "score": 0.40},
        {"action": "休息", "score": 0.15},
    ],
    weights          = {"w1": 0.4, "w2": 0.3, "w3": 0.3, "threshold": 0.5},
)

print(result)
# {"U": 0.9, "K": 0.6, "S": 0.6, "C": 0.72, "mode": "deliberate"}
# → C=0.72 > threshold=0.5，且 K=0.6 ≥ 0.5 強制 deliberate
# → Amy 需要深思如何應對這個陌生人
```

### 情境二：Emma 情緒「難過」時的閾值調整

```python
from core.mental_state import adjust_threshold_by_emotion, evaluate

# Emma 今天心情很差，閾值升高（更難觸發深思）
emma_threshold = adjust_threshold_by_emotion(0.5, "難過")
print(f"Emma 的困惑度閾值：{emma_threshold}")  # 0.65

# 同樣的情境下，Emma 比 Amy 更不容易進入 deliberate 模式
result = evaluate(
    yolo_desc    = "Ben 走進來",
    input_text   = "Ben: 妳還好嗎？",
    current_action = "整理",
    scene_text   = "今天已是第二次有人問同樣的問題。",
    action_candidates = [
        {"action": "對話", "score": 0.5},
        {"action": "整理", "score": 0.45},
    ],
    weights = {"w1": 0.4, "w2": 0.3, "w3": 0.3, "threshold": emma_threshold},
)
print(result["mode"])  # 可能為 "intuitive"，因為 threshold 較高
```

---

## 注意事項

- K ≥ `0.5` 會強制進入 deliberate 模式，不受 C 值和 threshold 影響，是安全網機制。
- `evaluate()` 的 `action_candidates` 是 Markov 輸出轉換後的格式，score 不需要加總為 1.0。
- 情緒閾值調整只影響 deliberate/intuitive 的**切換門檻**，不影響 U/K/S/C 本身的計算。
- 負面情緒（難過/疲憊）調整量 +0.15 > 情緒不穩（緊張/不安）+0.10，因為前者代表「能量耗竭」，後者代表「情緒波動但還有能力思考」。
- `decide_new_emotion()` 的模型推斷只在 `today_max_K ≥ EMOTION_RESET_THRESHOLD` 時觸發，避免每天都呼叫模型更新情緒，節省算力。
