# markov_engine — 三源加權 Markov 決策引擎

> **路徑**: `core/markov_engine.py`  
> **職責**: 純統計規則合成行動機率分布（不呼叫 LLM）

---

## 功能概覽

`markov_engine` 是 AI-Town System 1（直覺思考）路徑的核心引擎，完全不呼叫任何 LLM，純粹依靠統計與規則計算出每個合法行動的機率分布。它對應人類「慣性行為」的神經機制：Wood & Neal（2007）的研究顯示，人類約 43% 的日常行為是習慣驅動；Gibson（1979）的 Affordance 理論說明環境會邀請特定行動；Schank & Abelson（1977）的腳本理論則說明情境觸發行為序列。

擺脫了繁重的 LLM 呼叫，該引擎採用**三源架構**，每個來源各自計算分數並通過 softmax 轉為機率分布，再以動態權重加權合併：
- **α · schedule**（時間表符合度）：角色該做什麼
- **β · inertia**（行為慣性）：角色習慣做什麼
- **γ · situation**（情境觸發）：環境邀請什麼

最後套用睡覺時間抑制曲線（`_time_sleep_score()`），確保角色在早晨幾乎不可能睡著、深夜則自然傾向入眠。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.action_list` | `VALID_ACTIONS`、`ACTION_KEYWORD_BOOST`、`EMOTION_TO_ACTION_BOOST` 等 |
| 依賴 | `config.world_config` | `MARKOV_WEIGHTS_NORMAL`、`MARKOV_WEIGHTS_EVENT`、`SLEEP_ACTION` |
| 被依賴 | `agent/agent.py` | Markov 路徑決策 |
| 被依賴 | `agent/interrupt.py` | YOLO 中斷後重新評估機率 |
| 被依賴 | `observe/dashboard_html.py` | 顯示機率分布視覺化 |

---

## 三源架構詳解

```
                    ┌─────────────────────────────────────────────────────┐
                    │            compute_action_probabilities              │
                    │                                                     │
  schedule_slot ──▶ │ schedule_score()  → softmax(T=0.4) → α · p_sched  │
  stm_verbs    ──▶ │ inertia_score()   → softmax(T=1.0) → β · p_iner   │─▶ 合併 → 保底 → 睡眠修正 → 正規化
  perception   ──▶ │ situation_score() → softmax(T=1.0) → γ · p_situ   │
                    └─────────────────────────────────────────────────────┘
```

---

## 重要常數

| 常數 | 值 | 說明 |
|------|-----|------|
| `MIN_PROB_FLOOR` | `0.005` | 最低保底機率，任何行動都不會被完全歸零 |
| schedule 溫度 | `0.4` | 較低溫度讓時間表信號更集中 |
| inertia/situation 溫度 | `1.0` | 預設 softmax 溫度 |

---

## 睡眠時間抑制曲線

### `_time_sleep_score(time_minutes: int) -> float`

**功能**: 根據當前時間（從 00:00 起的分鐘數）計算「睡覺」行動的附加分數，用於 `compute_action_probabilities()` 中的後期修正步驟。

**設計邏輯**:

| 時間區間 | 分數 | 乘數（`exp(score*2.0)`） | 效果 |
|----------|------|--------------------------|------|
| 07:00 → 18:00（工作時段） | -1.5 | `exp(-3.0) ≈ 0.050` | 睡覺機率壓到底（約 0.5%） |
| 18:00 → 23:00（線性回升） | 0.0 → +0.5 | 1.0 → `exp(0.5) ≈ 1.65` | 睡覺機率溫和提升 |
| 23:00 以後 | +0.5 | `exp(0.5) ≈ 1.65` | 睡覺機率維持提升 |

**閾值**:
- `WAKE_MIN = 420`（07:00）
- `WORK_END = 1080`（18:00）
- `SLEEP_MIN = 1380`（23:00）

**實作細節**: 負分時用 `exp(score * 2.0)` 強力抑制，正分時用 `exp(score)` 溫和提升，兩者的非對稱設計確保「強壓制易、微提升難」。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `time_minutes` | `int` | 當前時間（分鐘數，如 `8 * 60 = 480` 代表 08:00） |

**回傳**: `float` — -1.5 到 +0.5 的分數

**範例**:
```python
_time_sleep_score(8 * 60)    # 480，早上 08:00 → -1.5（強壓制）
_time_sleep_score(21 * 60)   # 1260，晚上 21:00 → 0.25（開始回升）
_time_sleep_score(23 * 60)   # 1380，晚上 23:00 → +0.5（最大提升）
```

---

## 主要函式

### `compute_action_probabilities(...) -> dict | dict`

**功能**: 算出每個合法行動的機率（總和 = 1），為三源加權架構的主入口。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `char_code` | `str` | 角色代碼（`"A"` 到 `"E"`），空字串退回全域 `VALID_ACTIONS` |
| `schedule_slot` | `dict \| None` | 當前時間表時段 `{time, action, location}` |
| `stm_recent_verbs` | `list[str] \| None` | 最近行動動詞（`STM.get_recent_actions()` 提供） |
| `perception` | `dict \| None` | `{"location", "yolo_desc", "scene_text", "time_minutes"}` |
| `co_located` | `list[str] \| None` | 同地點角色名字列表 |
| `emotion` | `str` | 當前情緒（預設 `"平靜"`） |
| `is_major_event` | `bool` | True 時 ΔScene 額外加值（較重視情境） |
| `weights` | `dict \| None` | 自訂 `{alpha, beta, gamma}`；`None` 用 config 預設 |
| `return_breakdown` | `bool` | `True` 時額外回傳各來源分項分數 |

**回傳**:
- 預設：`{action: prob}` 字典
- `return_breakdown=True`：
```python
{
    "probs": {action: prob, ...},
    "breakdown": {
        "schedule":  {action: prob, ...},
        "inertia":   {action: prob, ...},
        "situation": {action: prob, ...},
        "weights":   (alpha, beta, gamma),
    }
}
```

**睡眠抑制實作**（關鍵片段）：
```python
# 合併後直接縮放，效果不被其他來源稀釋
if SLEEP_ACTION in final_probs and perception:
    tm = perception.get("time_minutes")
    if tm is not None:
        ts = _time_sleep_score(int(tm))
        scale = math.exp(ts * 2.0) if ts < 0 else math.exp(ts)
        final_probs[SLEEP_ACTION] = max(
            final_probs[SLEEP_ACTION] * scale, MIN_PROB_FLOOR
        )
```

---

### A. 時間表分數

#### `schedule_score(slot: dict, perception: dict = None) -> dict`

**功能**: 根據時間表時段，回傳每個行動的契合分數。

**計分規則**:
- 完全匹配時間表行動：`1.0`
- 同類別行動：`0.5`
- 不相關行動：`0.0`
- 位置匹配獎勵（已在目的地）：降低「前往」分數（× 0.3）
- 位置不匹配（還未到達）：提升「前往」至 `max(score, 0.6)`

**範例**:
```python
slot = {"time": "09:00", "action": "工作", "location": "咖啡店"}
perception = {"location": "住家"}
scores = schedule_score(slot, perception)
# scores["工作"] = 1.0
# scores["前往"] = 0.6（尚未在咖啡店）
```

---

### B. 行為慣性分數

#### `inertia_score(stm_recent_verbs: list) -> dict`

**功能**: 從 STM 最近行動動詞序列計算一階 Markov 轉移分數，使用 Laplace 平滑（每個行動基礎加 1）。

**設計**:
- 歷史不足（< 2 筆）→ 均勻分數（讓 schedule/situation 主導）
- 從最後一個動詞的出現後計算轉移統計
- `math.log(count + 1)` 轉換後進入 softmax，等效於頻率比例

**範例**:
```python
# Amy 最近行動：工作→工作→對話→工作
verbs = ["工作", "工作", "對話", "工作"]
scores = inertia_score(verbs)
# 最後一個是「工作」，從歷史看：工作後→工作(2次)，工作後→對話(1次)
# scores["工作"] > scores["對話"] >> 其他
```

---

### C. 情境分數

#### `situation_score(perception: dict, co_located: list, emotion: str) -> dict`

**功能**: 根據感知資訊、同地點角色、情緒計算情境觸發分數。

**計分來源**:
1. `ACTION_KEYWORD_BOOST`：場景文字中出現關鍵字，每命中 +`KEYWORD_BOOST_PER_HIT`（預設 0.15）
2. `EMOTION_TO_ACTION_BOOST`：依情緒加分（如「開心」提升「對話」）
3. 同地點有人 → 「對話」+0.3

---

### D. 採樣

#### `sample_action(probs: dict, exclude: list = None) -> str`

**功能**: 加權隨機採樣，保持自然的行為變化（非 argmax）。`exclude` 可排除特定行動。

**回傳**: `str` — 採樣到的行動動詞，無候選時回傳 `"休息"`

---

### E. 對話目標解析

#### `resolve_dialogue_target(probs: dict, co_located: list, boost_factor: float = 2.5) -> tuple`

**功能**: 決定最終動詞與目標。同地點有人時，先將「對話」機率放大 `boost_factor=2.5` 倍再採樣；若最終選到「對話」但沒有對象，則排除「對話」重新採樣。

**回傳**: `tuple(str, str)` — `(動詞, 目標)`

**範例**:
```python
probs = {"對話": 0.4, "工作": 0.35, "休息": 0.25}
verb, target = resolve_dialogue_target(probs, co_located=["Ben"])
# 可能回傳 ("對話", "Ben") 或 ("工作", "") 等
```

---

### F. 格式化顯示

#### `format_probs_display(probs: dict, top_n: int = 5) -> str`

**功能**: 格式化機率分布為可讀字串（debug / 視覺化用）。

**範例**:
```python
format_probs_display({"工作": 0.45, "對話": 0.30, "休息": 0.15, "前往": 0.10})
# "工作:0.450, 對話:0.300, 休息:0.150, 前往:0.100"
```

---

### 內部工具

#### `_softmax_dict(scores: dict, temperature: float = 1.0) -> dict`

**功能**: 數值穩定的 softmax，以最大值做偏移避免溢位。`temperature` 越低分布越尖銳，越高越均勻。

---

## 模擬使用情境

### 情境一：Amy 早上 09:00 在咖啡店的正常決策

```python
from core.markov_engine import compute_action_probabilities, format_probs_display

result = compute_action_probabilities(
    char_code        = "A",
    schedule_slot    = {"time": "09:00", "action": "工作", "location": "咖啡店"},
    stm_recent_verbs = ["工作", "對話", "工作", "工作"],
    perception       = {
        "location":     "咖啡店",
        "yolo_desc":    "Ben 在等待",
        "scene_text":   "早上的咖啡店，Ben 站在吧台前等咖啡",
        "time_minutes": 9 * 60,   # 09:00 → 強壓制睡覺
    },
    co_located       = ["Ben"],
    emotion          = "開心",
    return_breakdown = True,
)

print(format_probs_display(result["probs"]))
# 對話:0.382, 工作:0.341, 前往:0.089, 休息:0.072, ...
# 睡覺 ≈ 0.005（保底，已被壓到底）

alpha, beta, gamma = result["breakdown"]["weights"]
print(f"α={alpha}, β={beta}, γ={gamma}")
```

### 情境二：David 晚上 23:30 決定是否睡覺

```python
from core.markov_engine import compute_action_probabilities, _time_sleep_score
import math

# 檢視 23:30 的睡覺分數
t_min = 23 * 60 + 30  # 1410
score = _time_sleep_score(t_min)  # +0.5（超過 23:00）
scale = math.exp(score)           # exp(0.5) ≈ 1.649

probs = compute_action_probabilities(
    char_code        = "D",
    schedule_slot    = {"time": "00:30", "action": "睡覺", "location": "住家"},
    stm_recent_verbs = ["休息", "滑手機", "休息"],
    perception       = {
        "location":     "住家",
        "yolo_desc":    "",
        "scene_text":   "夜深了，David 感到疲憊",
        "time_minutes": t_min,
    },
    co_located       = [],
    emotion          = "疲憊",
)

sleep_prob = probs.get("睡覺", 0)
print(f"睡覺機率：{sleep_prob:.3f}")
# 應顯著高於白天的 0.5% 保底值
```

### 情境三：重大事件發生時切換權重

```python
# Emma 目擊意外事件，切換到 MARKOV_WEIGHTS_EVENT
probs = compute_action_probabilities(
    char_code        = "E",
    schedule_slot    = {"time": "14:00", "action": "休息", "location": "公園"},
    stm_recent_verbs = ["休息", "散步"],
    perception       = {
        "location":  "公園",
        "yolo_desc": "有人突然倒下",
        "scene_text": "意外！有人在公園突然暈倒",
        "time_minutes": 14 * 60,
    },
    co_located      = [],
    emotion         = "緊張",
    is_major_event  = True,   # 切換到 EVENT 權重，γ 更大
)

print(format_probs_display(probs))
# situation 來源的權重更大 → 「前往（急救站）」或「對話（呼救）」機率上升
```

---

## 注意事項

- 睡覺抑制是在三源合併**之後**才套用，確保不被其他來源稀釋。負分時用 `exp(ts * 2.0)` 強力抑制，正分時用 `exp(ts)` 溫和提升，兩者的乘數計算故意不對稱。
- `MIN_PROB_FLOOR = 0.005` 確保任何行動都不會完全歸零，避免行為空間收縮；即使睡覺被強壓到 ~0.5%，仍存在極小機率（模擬特殊情況下角色意外入睡）。
- `resolve_dialogue_target()` 的 `boost_factor=2.5` 在採樣前放大對話機率，但不修改傳入的 `probs`，不影響後續步驟。
- `inertia_score()` 的 Laplace 平滑（每個行動基礎 +1）使得即使從未在 STM 中出現的行動也有最低保底機率，避免慣性來源完全封殺某些行動。
- `return_breakdown=True` 時回傳的機率是 softmax 後的各來源分布，而非乘以權重後的值，供 `WeightAdapter.record_tick()` 使用來計算各來源對最終決策的貢獻。
