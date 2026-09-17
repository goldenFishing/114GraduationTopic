# weight_adapter — 動態 Markov 權重適應器

> **路徑**: `core/weight_adapter.py`  
> **職責**: 每天睡眠時根據 tick 記錄以 SGD-like 方式更新三源權重

---

## 功能概覽

`weight_adapter.py` 實作每個角色獨立的自適應 Markov 權重學習機制。Markov 引擎的三源架構（schedule α、inertia β、situation γ）的混合比例並非全域固定，而是每個角色根據自身的決策歷史動態調整。Amy 若長期因為「情境觸發」做出好決策，她的 γ 會逐漸提升；Ben 若習慣遵守時間表並獲得好結果，他的 α 會相對增大。

更新算法類似隨機梯度下降（SGD）：對每個 tick 的記錄，若 reward 為正且某來源的機率貢獻較高，則該來源的權重提升；若 reward 為負則懲罰。更新完成後進行剪裁（`[0.05, 0.85]`）和正規化（總和 = 1），確保數值穩定性。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 被依賴 | `core/character.py` | `get_markov_weights()` / `set_markov_weights()` 使用 |
| 被依賴 | `core/consolidation.py` | 睡眠 Step 12 前呼叫 `update_weights()` |

---

## 超參數

| 常數 | 值 | 說明 |
|------|-----|------|
| `DEFAULT_WEIGHTS` | `{"alpha": 0.40, "beta": 0.35, "gamma": 0.25}` | 所有角色的初始預設權重 |
| `LEARNING_RATE` | `0.05` | SGD 學習率 |
| `MIN_WEIGHT` | `0.05` | 每個來源的最低權重（避免任何來源完全失效） |
| `MAX_WEIGHT` | `0.85` | 每個來源的最高權重（避免某來源完全主導） |

---

## 主要類別

### `WeightAdapter`

**功能**: 單一角色的可學習 Markov 權重容器，提供記錄 tick 數據、更新權重和序列化的介面。

#### `__init__(self, weights: dict = None)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `weights` | `dict \| None` | 初始權重 `{alpha, beta, gamma}`；`None` 使用 `DEFAULT_WEIGHTS` |

缺少的 key 會從 `DEFAULT_WEIGHTS` 自動補齊。

**範例**:
```python
from core.weight_adapter import WeightAdapter

# 使用預設權重
adapter = WeightAdapter()
print(adapter.get_weights())
# {"alpha": 0.40, "beta": 0.35, "gamma": 0.25}

# 從角色 JSON 恢復
adapter = WeightAdapter({"alpha": 0.45, "beta": 0.30, "gamma": 0.25})
```

---

#### `get_weights(self) -> dict`

**功能**: 回傳當前 `{alpha, beta, gamma}` 字典（副本）。

---

#### `record_tick(self, chosen_action: str, reward: float, breakdown: dict)`

**功能**: 記錄一個 tick 的決策結果，供 `update_weights()` 使用。從 `breakdown` 中取出各來源對 `chosen_action` 的機率貢獻。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `chosen_action` | `str` | 本 tick 最終執行的行動動詞 |
| `reward` | `float` | `ActionValueTracker.compute_reward()` 計算的 reward |
| `breakdown` | `dict` | `compute_action_probabilities(return_breakdown=True)` 回傳的 `breakdown` 字段 |

**breakdown 格式**:
```python
{
    "schedule":  {"對話": 0.05, "工作": 0.65, ...},
    "inertia":   {"對話": 0.20, "工作": 0.50, ...},
    "situation": {"對話": 0.45, "工作": 0.30, ...},
}
```

---

#### `update_weights(self)`

**功能**: 每天睡覺時呼叫，用累積的 tick 記錄做 SGD-like 更新。無 tick 記錄時空跑無副作用。

**更新公式**（對每筆 tick 記錄 r）：
```
alpha += lr × r × (sched_p  - alpha)
beta  += lr × r × (iner_p   - beta)
gamma += lr × r × (situ_p   - gamma)
```

公式解讀：若 `r > 0`（好結果）且 `sched_p > alpha`（schedule 貢獻高於其目前權重），則 alpha 上升；若 `sched_p < alpha` 則 alpha 下降（說明 schedule 在這次決策中不是主要貢獻者但得了好結果，適度降低）。

**後處理**:
1. Clip 到 `[MIN_WEIGHT, MAX_WEIGHT]`
2. 正規化使總和 = 1
3. 修正浮點誤差（餘差加回 alpha）
4. 清空 `_tick_records`

---

#### `to_dict(self) -> dict`

**功能**: 序列化為 `{"alpha":..., "beta":..., "gamma":...}`，供角色 JSON 儲存。

---

#### `from_dict(cls, data: dict) -> WeightAdapter`（classmethod）

**功能**: 從 dict 還原 `WeightAdapter` 實例。

**範例**:
```python
adapter = WeightAdapter.from_dict({"alpha": 0.45, "beta": 0.35, "gamma": 0.20})
```

---

## 模擬使用情境

### 情境一：Emma 連續三天偏好情境觸發，γ 逐漸上升

```python
from core.weight_adapter import WeightAdapter

adapter = WeightAdapter()  # 初始：α=0.40, β=0.35, γ=0.25

# 模擬 3 天，每天的 tick 記錄都顯示 situation 貢獻度高
for day in range(3):
    # 假設今天 10 個 tick，每個 tick 的 situation 貢獻都很高
    for _ in range(10):
        adapter.record_tick(
            chosen_action = "對話",
            reward        = 0.4,     # 正向 reward（對話帶來好結果）
            breakdown     = {
                "schedule":  {"對話": 0.10},  # schedule 貢獻低
                "inertia":   {"對話": 0.20},  # inertia 貢獻中
                "situation": {"對話": 0.70},  # situation 貢獻高
            }
        )
    adapter.update_weights()

weights = adapter.get_weights()
print(f"α={weights['alpha']:.3f}, β={weights['beta']:.3f}, γ={weights['gamma']:.3f}")
# α 下降（schedule 貢獻低但也得到好結果），γ 上升（situation 貢獻高）
```

### 情境二：完整的睡眠濃縮中的權重更新流程

```python
from core.weight_adapter import WeightAdapter
from core.character import Character

amy = Character(load_character("A"))

# 取得當前權重（或預設值）
adapter = WeightAdapter(amy.get_markov_weights())

# 在每個 tick 中（由 agent.py 呼叫）：
# result = compute_action_probabilities(..., return_breakdown=True)
# reward = tracker.compute_reward(...)
# adapter.record_tick(chosen_action, reward, result["breakdown"])

# 睡覺時（consolidation.py Step 12 前）：
adapter.update_weights()
amy.set_markov_weights(adapter.get_weights())

# 確認更新
print(amy.get_markov_weights())
```

### 情境三：查看長期學習後的權重偏移

```python
# Ben（超市員工）長期遵守時間表帶來好結果
# → 預期 alpha 上升

# Claire（餐廳老闆）情境觸發（有客人/有突發事件）更重要
# → 預期 gamma 上升

# 比較不同角色的自適應權重
for char_code in ["A", "B", "C", "D", "E"]:
    char = Character(load_character(char_code))
    w = char.get_markov_weights()
    print(f"{char.name:8s}: α={w['alpha']:.3f}, β={w['beta']:.3f}, γ={w['gamma']:.3f}")
```

---

## 注意事項

- SGD 更新公式是「趨向」貢獻最高的來源：`lr × r × (source_p - weight)` 形式確保當某來源長期表現好（source_p 持續高於 weight）時，weight 才會持續上升。
- `MIN_WEIGHT = 0.05` 確保任何來源都不會完全退出決策（即使某來源長期表現差，仍保留 5% 的影響力），避免策略退化。
- Clip 後的正規化步驟至關重要：三個權重剪裁後加總可能不為 1，正規化確保 Markov 引擎收到的混合比例有意義。
- 浮點誤差修正（餘差加回 alpha）是細節設計，避免 `0.4001 + 0.3499 + 0.25 = 1.0000001` 這類問題影響下游計算。
- `record_tick()` 只儲存 `chosen_action` 在各來源的機率（不是全部行動），這足以計算該來源對最終決策的「貢獻度」，無需儲存完整的分布。
- 若整天沒有呼叫 `record_tick()`（如 `--no-model` 模式下 agent 不記錄），`update_weights()` 會因 `_tick_records` 為空而不執行，權重保持不變，無副作用。
