# markov_engine 需求規格

## 負責檔案
- `core/markov_engine.py`

## 功能描述
在現有的三來源加權 Markov 決策基礎上，新增 `char_code` 參數，
讓 `compute_action_probabilities` 只計算該角色合法的抽象動詞集合（Stage 1）。
不修改三個分項函式（schedule_score / inertia_score / situation_score）的邏輯，
只修改它們被呼叫的方式與候選集。

## 輸入 / 輸出
- 輸入：`char_code: str`（新增），其餘參數不變
- 輸出：`{抽象動詞: prob}` dict，鍵集合 = `CHARACTER_VALID_ACTIONS[char_code]`（若 char_code 無效則退回全域 VALID_ACTIONS）

## 相依模組
- `config/action_list.py` — 必須先完成，因為需要 `CHARACTER_VALID_ACTIONS`

## 實作要求

### 修改點 1：函式簽章新增 char_code

```python
def compute_action_probabilities(
    char_code: str = "",           # ← 新增（放第一個參數）
    schedule_slot: dict = None,
    stm_recent_verbs: list = None,
    perception: dict = None,
    co_located: list = None,
    emotion: str = "平靜",
    is_major_event: bool = False,
    weights: dict = None,
    action_values: dict = None,
    return_breakdown: bool = False,
):
```

### 修改點 2：內部候選集改用 char_code 過濾

在函式開頭（計算 sched_scores 前）加入：

```python
from config.action_list import CHARACTER_VALID_ACTIONS
valid_actions = CHARACTER_VALID_ACTIONS.get(char_code) or VALID_ACTIONS
```

接下來所有分項函式的計算，將原本遍歷 `VALID_ACTIONS` 的地方改為遍歷 `valid_actions`：
- `schedule_score` 的 `scores = {a: 0.0 for a in VALID_ACTIONS}` → `for a in valid_actions`
- `inertia_score` 的 `scores = {}; for action in VALID_ACTIONS:` → `for action in valid_actions`
- `situation_score` 的 `scores = {a: 0.0 for a in VALID_ACTIONS}` → `for a in valid_actions`
- value_probs 的 `full_values = {a: ... for a in VALID_ACTIONS}` → `for a in valid_actions`
- final_probs 合併迴圈的 `for action in VALID_ACTIONS:` → `for action in valid_actions`

**注意：三個分項函式（schedule_score, inertia_score, situation_score）本身的實作邏輯不要改，
只修改 compute_action_probabilities 傳遞給它們時所用的候選集。**

實際做法：在 compute_action_probabilities 內，於三個分項函式呼叫後，
對回傳的 dict 做過濾，只保留 `valid_actions` 中的 key：

```python
sched_scores = {k: v for k, v in schedule_score(schedule_slot, perception).items()
                if k in valid_actions}
iner_scores  = {k: v for k, v in inertia_score(stm_recent_verbs or []).items()
                if k in valid_actions}
situ_scores  = {k: v for k, v in situation_score(perception or {}, co_located or [], emotion).items()
                if k in valid_actions}
```

這樣三個分項函式不需要修改，只在呼叫後過濾。

### 修改點 3：其他用到 VALID_ACTIONS 的地方同步過濾

在 `compute_action_probabilities` 內：
- value_probs 計算：`full_values = {a: action_values.get(a, 0.0) for a in valid_actions}`
- final_probs 迴圈：`for action in valid_actions:`

### 修改點 4：MIN_PROB_FLOOR 邏輯不變

保底機率 0.005 邏輯維持不變。

### import 新增

在檔案頂部的 import 區塊加入：
```python
from config.action_list import (
    VALID_ACTIONS, VALID_LOCATIONS,
    ACTION_SEPARATOR, ACTION_TO_CATEGORY,
    CHARACTER_VALID_ACTIONS,          # ← 新增
)
```

（`CHARACTER_VALID_ACTIONS` 也可在函式內部 lazy import，
但若放在頂部 import 更清楚，請選擇頂部 import 方式。）

## 測試要求

### 測試工具
Python 內建 unittest（不引入新依賴）

### 測試情境
測試情境 1：角色 A 的機率分布鍵集合
  輸入：char_code="A", 其他參數使用預設（空 schedule_slot, 空 STM 等）
  預期輸出：probs.keys() == set(CHARACTER_VALID_ACTIONS["A"])
  允許偏差：無

測試情境 2：機率總和
  輸入：char_code="B", 各參數用合理預設值
  預期輸出：sum(probs.values()) 約等於 1.0
  允許偏差：±0.001（浮點精度）

測試情境 3：B 的機率分布不含 A 專屬動作
  輸入：char_code="B"
  預期輸出："賣咖啡" 不在 probs.keys()，"收銀" 在 probs.keys()
  允許偏差：無

測試情境 4：char_code 為空字串時退回全域 VALID_ACTIONS
  輸入：char_code=""
  預期輸出：probs.keys() == set(VALID_ACTIONS)
  允許偏差：無

測試情境 5：return_breakdown=True 時的 probs 鍵集合
  輸入：char_code="C", return_breakdown=True
  預期輸出：result["probs"].keys() == set(CHARACTER_VALID_ACTIONS["C"])
  允許偏差：無

## 禁止事項
- 不要修改 schedule_score、inertia_score、situation_score、sample_action、resolve_dialogue_target、format_probs_display、_softmax_dict 函式的內部邏輯
- 不要修改 MIN_PROB_FLOOR 的值
- 不要引入新的外部依賴（math, random 已存在）
- 規格有任何不清楚之處，停止開發並回報主控台
