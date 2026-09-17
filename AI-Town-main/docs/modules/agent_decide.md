# agent_decide 需求規格

## 負責檔案
- `agent/agent.py`

## 功能描述
在現有 `Agent.decide()` 方法中，做兩處小改動：
1. 呼叫 `compute_action_probabilities` 時傳入 `char_code=char.code`
2. 決策結果 dict 新增 `"action_id"` 欄位（呼叫 `action_id_resolver` 取得）

其餘所有邏輯（Markov/Deliberate 切換、困惑度計算、對話接受規則、STM 寫入等）**完全不動**。

## 輸入 / 輸出
- 輸入：`Agent.decide()` 現有參數不變
- 輸出：`decide()` 回傳 dict 新增 `"action_id": int | None`

## 相依模組
- `config/action_list.py` — 需要 `action_id_resolver`（必須先完成）
- `core/markov_engine.py` — 需要 `char_code` 參數支援（必須先完成）

## 實作要求

### 修改點 1：import 新增

在 `agent/agent.py` 頂部的 import 區塊中，在 `from config.action_list import ...` 那行補上：

```python
from config.action_list import ACTION_TO_CATEGORY, action_id_resolver
```

（`ACTION_TO_CATEGORY` 原本已 import，只需加上 `action_id_resolver`。）

### 修改點 2：decide() 中呼叫 compute_action_probabilities 時加入 char_code

找到現有呼叫：
```python
markov_breakdown = compute_action_probabilities(
    schedule_slot      = slot,
    stm_recent_verbs   = self.stm.get_recent_actions(8),
    ...
)
```

在 `schedule_slot=slot,` **之前**插入一行：
```python
char_code          = char.code,
```

**只改這一個 compute_action_probabilities 呼叫（整個 agent.py 只有一處）。**

### 修改點 3：decide() 回傳 dict 新增 action_id

找到 decide() 方法中組建回傳 dict 的地方（有 "action", "target", "content", "thought", "ham", "mode", "_meta" 等 key）。

在組建最終 result dict 後，加入：
```python
result["action_id"] = action_id_resolver(
    abstract_verb    = result.get("action", ""),
    char_code        = char.code,
    current_location = char.current_location,
)
```

這行應在 result dict 已確定（Markov 或 Deliberate 路徑都完成後）再執行，
位置在 `return result` 之前。

**注意：** 若 result["action"] 是 "前往"，action_id_resolver 可能回傳 None，這是預期行為（前往沒有固定 ActionID）。

## 測試要求

### 測試工具
Python 內建 unittest + mock（mock Agent 的依賴，不跑實際模型）

### 測試情境
測試情境 1：Markov 路徑的 action_id 欄位存在
  輸入：建立一個 mock Agent（角色 A），呼叫 decide()，強制走 Markov 路徑（C < threshold）
  預期輸出：回傳 dict 含 "action_id" key，值為 int 或 None
  允許偏差：無（只驗證 key 存在且型別正確）

測試情境 2：角色 A 睡覺時的 action_id
  輸入：action="睡覺", char.code="A", char.current_location="A家"
  預期輸出：action_id_resolver("睡覺","A","A家") == 40
  允許偏差：無
  備註：直接呼叫 action_id_resolver，不需要跑完整 decide()

測試情境 3：前往動作 action_id 為 None
  輸入：action="前往", char_code="A", current_location="咖啡廳"
  預期輸出：action_id_resolver("前往","A","咖啡廳") == None（前往沒有 ActionID）
  允許偏差：無

## 禁止事項
- 除了上述三個修改點，不要修改 agent.py 中的任何其他邏輯
- 不要修改 Markov/Deliberate 切換邏輯、困惑度計算、對話規則、STM 寫入
- 不要新增其他 import（只新增 action_id_resolver）
- 規格有任何不清楚之處，停止開發並回報主控台
