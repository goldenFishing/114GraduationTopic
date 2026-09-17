# tick_value — Tick 間行動價值追蹤（RL-style）

> **路徑**: `core/tick_value.py`  
> **職責**: 追蹤行動的累積 RL 價值與 Reward 反饋

---

## 功能概覽

`tick_value.py` 實作一個輕量的 Reinforcement Learning 風格行動價值追蹤器，類比 Q-learning 中的 `Q(s, a)` 更新機制，但特意簡化為不需要顯式狀態空間。每個 tick 結束後，系統根據四種 reward 信號計算該 tick 的 reward，累積更新行動的 `value_score`，並透過指數衰減（`VALUE_DECAY = 0.85`）讓遠端 tick 的影響逐漸消退——這正是 eligibility trace 的核心概念。

`ActionValueTracker` 的輸出（`get_scores()`）目前僅供儀表板顯示與價值追蹤，不再作為 Markov 引擎的直接輸入（與直覺決策解耦）。但它依然在後台忠實記錄角色每個行動的即時 Reward 與累計分數，用於分析決策的合理性與學習成效。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 被依賴 | `agent/agent.py` | `decide()` 結束後呼叫 `compute_reward()` 和 `update()` |
| (無) | `core/markov_engine.py` | (已解耦，不再由 Markov 引擎直接引用) |
| 被依賴 | `observe/dashboard_html.py` | 顯示 value score 視覺化 |

---

## 超參數

| 常數 | 值 | 說明 |
|------|-----|------|
| `VALUE_DECAY` | `0.85` | 每 tick 的衰減係數（類 eligibility trace λ） |
| `REWARD_EMOTION_IMPROVE` | `+0.50` | 負面情緒 → 正面情緒 |
| `REWARD_EMOTION_NEUTRAL` | `+0.15` | 負面情緒 → 平靜 |
| `REWARD_EMOTION_WORSEN` | `-0.45` | 正面/平靜 → 負面情緒 |
| `REWARD_CONFUSION_DROP` | `+0.30` | C 值明顯下降（行動消解不確定性） |
| `REWARD_CONFUSION_SPIKE` | `-0.35` | C 值明顯上升（行動引發更多不確定） |
| `REWARD_DIALOGUE_ACCEPT` | `+0.25` | 對話被接受（社交 affordance 達成） |
| `REWARD_SCHEDULE_HIT` | `+0.20` | 行動完全符合時間表 |
| `CONFUSION_DROP_THRESHOLD` | `0.12` | C 下降超過此值觸發正向 reward |
| `CONFUSION_SPIKE_THRESHOLD` | `0.15` | C 上升超過此值觸發負向 reward |

### 情緒分類

| 分類 | 情緒 |
|------|------|
| 正面（POSITIVE） | 開心、興奮、滿足 |
| 中性（NEUTRAL） | 平靜 |
| 負面（NEGATIVE） | 憤怒、悲傷、焦慮、恐懼、失落、不安 |

---

## 主要類別

### `ActionValueTracker`

**功能**: 記錄每個行動的累積 value score，維護 tick 歷史紀錄，提供 RL 風格的行動偏好影響。

#### `__init__(self)`

初始化空的 `values` dict 和 `history` 列表。

**範例**:
```python
from core.tick_value import ActionValueTracker

tracker = ActionValueTracker()
```

---

#### `decay(self)`

**功能**: 每 tick 開始前呼叫，所有 value score 乘以衰減係數 `VALUE_DECAY = 0.85`，讓舊 tick 的影響逐漸消退。

**設計類比**: eligibility trace 中的 λ 衰減，遠端的獎懲信號影響力隨時間指數遞減。

**範例**:
```python
tracker.values = {"對話": 0.5, "工作": -0.2}
tracker.decay()
# {"對話": 0.425, "工作": -0.17}
```

---

#### `update(self, action: str, reward: float)`

**功能**: 根據 reward 更新行動的 value score（累加）。正 reward → 下次更傾向此行動；負 reward → 下次更迴避。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `action` | `str` | 本 tick 執行的行動動詞 |
| `reward` | `float` | 計算出的 reward 值 |

---

#### `get_scores(self) -> dict`

**功能**: 回傳當前 value scores 字典，供儀表板與日誌追蹤使用。

**回傳**: `dict` — `{action_verb: float}`，值可為正（偏好）或負（迴避）

---

#### `reset(self)`

**功能**: 清空所有 value scores 和歷史紀錄（睡眠後呼叫，目前設計選擇重置而非跨天延續）。

---

#### `compute_reward(self, action, prev_emotion, curr_emotion, prev_C, curr_C, dialogue_accepted=False, schedule_hit=False, tick_id="") -> float`

**功能**: 根據當前 tick 的結果計算 reward，同時記錄到 history 供視覺化使用。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `action` | `str` | 本 tick 執行的行動動詞 |
| `prev_emotion` | `str` | 行動前的情緒 |
| `curr_emotion` | `str` | 行動後的情緒（下一狀態） |
| `prev_C` | `float` | 行動前的困惑度 C 值 |
| `curr_C` | `float` | 行動後的困惑度 C 值 |
| `dialogue_accepted` | `bool` | 對話行動是否被對方接受 |
| `schedule_hit` | `bool` | 行動是否完全符合時間表 |
| `tick_id` | `str` | Tick 識別碼（用於 history 記錄） |

**回傳**: `float` — 本 tick 的總 reward

**Reward 計算細節**:

① 情緒 reward（`_emotion_reward()`）：
- 前一情緒為負面，現在變正面 → +0.50
- 前一情緒為負面，現在變平靜 → +0.15
- 前一情緒為正面/中性，現在變負面 → -0.45
- 其他情緒變化 → 0.0

② 困惑度 reward（`_confusion_reward()`）：
- C 下降 ≥ 0.12 → 最高 +0.30（按比例縮放：`REWARD_CONFUSION_DROP × (delta / 0.3)`）
- C 上升 ≥ 0.15 → 最低 -0.35（按比例縮放）

③ 對話接受（僅限 `action == "對話"`）→ +0.25

④ 符合時間表 → +0.20

---

#### `top_values(self, n: int = 5) -> list`

**功能**: 回傳 value score 最高的 n 個行動（供 dashboard 顯示）。

**回傳**: `list[tuple]` — `[(action, score), ...]`，按 score 降序

---

#### `summary_str(self) -> str`

**功能**: 回傳 top 3 行動的格式化字串（debug 用）。

**輸出範例**: `"對話:+0.382  |  工作:+0.210  |  休息:-0.085"`

---

## 模擬使用情境

### 情境一：Amy 一天內的 tick 循環（完整使用流程）

```python
from core.tick_value import ActionValueTracker
from core.markov_engine import compute_action_probabilities

tracker = ActionValueTracker()
prev_emotion = "平靜"
prev_C = 0.3

# === Tick 1：Amy 選擇「對話 Ben」===
tracker.decay()  # 開始前衰減

# Markov 引擎使用目前的 value scores（初始都是 0）
probs = compute_action_probabilities(
    char_code    = "A",
    # ...其他參數
)

# 執行對話後，情緒變好
curr_emotion = "開心"
curr_C = 0.15

reward = tracker.compute_reward(
    action            = "對話",
    prev_emotion      = prev_emotion,
    curr_emotion      = curr_emotion,
    prev_C            = prev_C,
    curr_C            = curr_C,
    dialogue_accepted = True,   # Ben 接受了對話
    schedule_hit      = False,
    tick_id           = "D001_T001",
)
# reward = 0 + 0.30 + 0.25 = 0.55
# (情緒：平靜→開心，非負面→正面，不觸發；C: 0.3→0.15，下降0.15≥0.12 → +0.30；對話接受 → +0.25)

tracker.update("對話", reward)

print(f"Reward: {reward:.3f}")        # 0.55（或依實際計算）
print(f"對話 score: {tracker.values.get('對話', 0):.3f}")  # 0.55

# === Tick 2：使用更新後的 value scores ===
prev_emotion = curr_emotion  # "開心"
prev_C = curr_C               # 0.15

tracker.decay()  # 對話: 0.55 × 0.85 ≈ 0.4675

probs = compute_action_probabilities(
    char_code     = "A",
    # ...
)
# 「對話」機率比 Tick 1 更高
```

### 情境二：David 選擇錯誤行動後的負向學習

```python
tracker_david = ActionValueTracker()

# David 在工作時收到緊急消息，卻選擇「休息」
reward = tracker_david.compute_reward(
    action       = "休息",
    prev_emotion = "平靜",
    curr_emotion = "不安",   # 情緒惡化
    prev_C       = 0.2,
    curr_C       = 0.7,     # 困惑度飆升
    tick_id      = "D003_T005",
)
# reward = (-0.45) + (-0.35) = -0.80
# 情緒：平靜→不安（平靜→負面 → -0.45）
# 困惑度：0.2→0.7，上升0.5 ≥ 0.15 → -0.35

tracker_david.update("休息", reward)

print(tracker_david.summary_str())
# "休息:-0.800  ..."  → 下次 David 會更迴避「休息」
```

---

## 注意事項

- `decay()` 應在**每個 tick 開始前**呼叫，而非結束後，確保舊 tick 的分數在新 tick 的 Markov 計算前已衰減。
- `values` 可以含負值（迴避偏好），這代表該行動在過去引發了負面情緒或不確定性。
- `history` 的 `values_after` 欄位儲存的是更新後的「預覽值」（在 `compute_reward()` 中計算），實際 `update()` 呼叫後才真正修改 `self.values`。
- 睡眠後呼叫 `reset()` 的決定是設計選擇：重置讓每天從新開始，避免跨天累積偏差；未來若要實現跨天的長期偏好學習，可改為不重置或按比例縮小保留。
- 困惑度 reward 的縮放公式 `REWARD × (delta / 0.3)` 讓 C 變化幅度越大，reward 強度越高，但以 `REWARD_CONFUSION_DROP / _SPIKE` 為上下限，避免極端值。
