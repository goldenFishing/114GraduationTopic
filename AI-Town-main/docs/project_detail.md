# AI-Town — 詳細規格（Phase 2）

> 本文件說明此次開發的模組清單、相依關係、執行批次。
> 對應 ai_town/AI_town.md §6.1.2 與 §6.2.5 的更新需求。

## 背景

現有程式碼已具備完整架構（依 ARCHITECTURE.md 實作）。
本次更新目標：引入兩階段行動系統（ActionID 表格 + character-specific Markov 過濾）。

---

## 模組清單

| 模組名稱 | 負責檔案 | 相依模組 | 執行順序 |
|---------|---------|---------|---------|
| action_list | `config/action_list.py` | 無 | 第 1 批 |
| markov_engine | `core/markov_engine.py` | action_list | 第 2 批 |
| agent_decide | `agent/agent.py` | action_list, markov_engine | 第 3 批 |

---

## 執行批次

- **第 1 批（無相依）：** action_list
- **第 2 批（依賴第 1 批）：** markov_engine
- **第 3 批（依賴前兩批）：** agent_decide

---

## 模組介面定義

### action_list（config/action_list.py）
**新增輸出（在現有 VALID_ACTIONS / ACTION_CATEGORIES 之上加入）：**
```python
ACTION_TABLE: list[dict]            # 44+1 個 ActionID 定義（含 emoji, img_file_id, chars）
CHARACTER_VALID_ACTIONS: dict       # char_code → 可用抽象動詞清單
CHARACTER_HOME_LOCATION: dict       # char_code → 家的地點簡稱（"A家"/"B家" 等）
ACTION_ABSTRACT_MAP: dict           # 抽象動詞 → ACTION_TABLE entries 清單（快速查詢）
action_id_resolver(verb, char_code, location) -> int | None
```

### markov_engine（core/markov_engine.py）
**修改點：**
```python
# compute_action_probabilities 新增 char_code 參數
compute_action_probabilities(char_code: str, ...) -> dict[str, float]
# 內部用 CHARACTER_VALID_ACTIONS[char_code] 取代全域 VALID_ACTIONS
```

### agent_decide（agent/agent.py）
**修改點（僅 decide 方法）：**
```python
# 呼叫 compute_action_probabilities 時傳入 char_code=char.code
# 決策結果 dict 新增 "action_id" 欄位
{
  "action":    str,
  "action_id": int | None,   # 新增
  "target":    str,
  ...
}
```
