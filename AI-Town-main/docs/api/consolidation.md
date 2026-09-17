# consolidation — 睡眠濃縮主流程

> **路徑**: `core/consolidation.py`  
> **職責**: 執行 12 步驟睡眠記憶鞏固與隔天時間表生成

---

## 功能概覽

`consolidation.py` 實作 AI-Town 最核心的認知過程——睡眠濃縮（sleep consolidation）。對應 Diekelmann & Born（2010）的研究：睡眠期間海馬迴將情節記憶轉移並鞏固到新皮質，形成語意長期記憶。在 AI-Town 中，每當角色入睡，此模組執行完整的 12 步驟流程，將 STM 的情節敘述轉換為 LTM 的 HAM 命題，更新關係摘要、情緒、生成隔天時間表，並縮減 STM。

模組也包含原本在 `agent/scheduler.py` 中的時間表生成邏輯（`generate_next_day_schedule()`），整合在睡眠流程的第 8 步驟中。整個流程設計具備完善的 fallback 機制：若無 LLM 可用（`loader=None` 或 `--no-model` 模式），每個步驟都有對應的規則式替代方案，確保模擬不會因為模型不可用而中斷。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `core/mental_state.py` | 情緒判斷函式 |
| 依賴 | `core/weight_adapter.py` | 睡眠後更新 Markov 自適應權重 |
| 依賴 | `config/prompts.py` | 各步驟的 LLM prompt 模板 |
| 依賴 | `config/schedule_templates.py` | 時間表範本與驗證規則 |
| 依賴 | `config/model_config.py` | 各步驟的 max_tokens 設定 |
| 被依賴 | `agent/agent.py` | `sleep()` 方法呼叫 `consolidate()` |

---

## 12 步驟流程

```
Step 1  : 取出今日 STM 敘述
Step 2  : 模型抽取 HAM（從敘述）
Step 3  : 模型篩選重要 HAM（最多保留 5 筆）
Step 4  : 批次寫入 LTM
Step 5  : 模型生成新 LTM 摘要（最多 200 字元）
Step 6  : 模型更新關係摘要（每位今天出現的角色）
Step 7  : 情緒判斷（今日最大 K 值 ≥ 閾值才呼叫模型）
Step 8  : 模型生成隔天時間表
Step 9  : 規則驗證時間表（補必要時段）
Step 10 : LTM 衰減 + 修剪
Step 11 : STM 縮減（摘要 + 最近 5 筆）
Step 12 : 推進到下一天（day + 1，更新 Markov 自適應權重）
```

---

## 主要函式

### `consolidate(character, stm, ltm, process_log, loader) -> dict`

**功能**: 執行完整睡眠濃縮的主入口。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `character` | `Character` | 正在睡覺的角色物件 |
| `stm` | `STM` | 角色的短期記憶物件 |
| `ltm` | `LTM` | 角色的長期記憶物件 |
| `process_log` | `list` | 當天每個 tick 的處理紀錄（用於取最大 K 值） |
| `loader` | `ModelLoader \| None` | LLM 載入器；`None` 走 `--no-model` fallback |

**回傳**: `dict` — 濃縮報告：

```python
{
    "ham_extracted":        12,      # Step 2：抽出的 HAM 命題數
    "ham_kept":             5,       # Step 3：篩選後保留的命題數
    "ltm_total":            38,      # 目前 LTM 總命題數
    "ltm_pruned":           3,       # Step 10：修剪掉的命題數
    "ltm_summary":          "...",   # 新生成的 LTM 摘要
    "relationship_updates": {        # Step 6：關係更新
        "B": "Amy 和 Ben 的關係更加熟絡..."
    },
    "emotion_change": {              # Step 7：情緒變化
        "from": "開心",
        "to":   "平靜"
    },
    "next_day_schedule":    [...],   # Step 8：隔天時間表
    "stm_kept":             6,       # 縮減後 STM 筆數（摘要+5）
    "today_max_K":          0.6,     # 今天最高衝突程度
}
```

---

## 各步驟內部實作

### `_extract_ham(character, narrative, model_fn) -> list`

**功能（Step 2）**: 呼叫 LLM，從 STM 敘述化文字中抽取 HAM 5 元組命題。

- **模型輸入**：`prompt_extract_ham(character.name, narrative)`
- **解析格式**：每行一筆，pipe 分隔（`subject | relation | object | location | time`）
- **Fallback**：若無模型，掃描敘述中出現的角色名字，為每個出現的角色建立 `"互動"` 命題；無任何角色時建立 `"度過平凡的一天"` 命題

---

### `_select_important(character, narrative, props, model_fn) -> list`

**功能（Step 3）**: 從抽出的 HAM 命題中篩選最重要的，最多保留 5 筆。

- 若無模型或命題已 ≤ 5 筆 → 直接取前 5 筆
- 有模型 → 呼叫 LLM 評分篩選，解析後取前 5 筆

---

### `_generate_summary(character, ltm, model_fn) -> str`

**功能（Step 5）**: 根據目前 LTM 所有命題生成壓縮摘要，最多 200 字元。

- Fallback：取最近 5 筆命題的 `to_readable()` 輸出，截斷至 200 字元

---

### `_update_relationships(character, narrative, model_fn) -> dict`

**功能（Step 6）**: 找出今天敘述中出現的所有角色，為每個角色呼叫 LLM 更新關係摘要。若模型回傳 `"無變化"` 則不更新。

- **掃描方式**：遍歷 `CHARACTER_NAMES`，確認名字是否出現在 narrative 中
- **Fallback**：無模型時直接回傳空 dict（不更新關係）

---

### `_decide_emotion(character, narrative, today_max_K, model_fn) -> str`

**功能（Step 7）**: 判斷睡眠後的新情緒。

- `today_max_K < EMOTION_RESET_THRESHOLD` → 直接回歸 `"平靜"`
- 否則呼叫 `prompt_infer_emotion()`，模型輸出通過 `normalize_emotion()` 驗證
- Fallback：無模型 → 回歸 `"平靜"`

---

### `generate_next_day_schedule(character, today_narrative, important_events, model_fn=None) -> list`

**功能（Step 8-9）**: 為角色生成隔天的時間表。

**流程**:
1. 取得職業對應的範本（`get_template(character.role)`）
2. 無模型 → 直接使用範本
3. 有模型 → 組 prompt，包含個性摘要、習慣、LTM 摘要、今日重要事件、昨日時間表、範本
4. 解析 JSON list 格式的模型輸出
5. 解析失敗 → fallback 用範本
6. 驗證必要時段（`validate_schedule()`），缺少則從範本補齊
7. 正規化所有 slot 欄位（補齊 `type="fixed"`, `completed=False`）

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `character` | `Character` | 角色物件（取個性、習慣、職業） |
| `today_narrative` | `str` | 當天 STM 敘述化文字 |
| `important_events` | `str` | 今天重要事件摘要（HAM 篩選後） |
| `model_fn` | `callable \| None` | 模型呼叫函式 |

**回傳**: `list[dict]` — 正規化後的時間表 slots

---

## 工具函式

### `_parse_ham_lines(raw: str) -> list`

**功能**: 從模型輸出解析 HAM 命題（pipe 分隔格式），移除 Markdown 標記和行首 `-`。

**解析規則**:
- 每行格式：`subject | relation | object | location | time`
- 不足 5 欄位時補空字串
- `location`/`time` 為 `"無"` 或 `"無地點"/"無時間"` 時轉為 `None`

---

### `_today_max_K(process_log: list) -> float`

**功能**: 從當天的 process_log 中提取所有 K 值，回傳最大值。

---

## 模擬使用情境

### 情境一：Amy 第一天結束後的完整睡眠濃縮

```python
from core.consolidation import consolidate
from core.character import Character
from core.memory_stm import STM
from core.memory_ltm import LTM

amy = Character(load_character("A"))
stm = STM(amy._data)
ltm = LTM(amy._data)

# 假設今天 Amy 有 8 筆 STM 記錄，與 Ben 和 David 都有互動
process_log = [
    {"confusion": {"K": 0.2}},
    {"confusion": {"K": 0.6}},  # 有人闖入，K 值高峰
    {"confusion": {"K": 0.1}},
]

# 執行睡眠濃縮（使用真實模型）
report = consolidate(amy, stm, ltm, process_log, loader=model_loader)

print(f"抽取 {report['ham_extracted']} 筆 HAM，保留 {report['ham_kept']} 筆")
print(f"情緒：{report['emotion_change']['from']} → {report['emotion_change']['to']}")
print(f"今日最大 K 值：{report['today_max_K']}")  # 0.6
print(f"STM 縮減後：{report['stm_kept']} 筆")
```

### 情境二：--no-model 模式下的 fallback 行為

```python
# 傳入 loader=None 觸發所有 fallback 邏輯
report = consolidate(amy, stm, ltm, process_log, loader=None)

# fallback 行為：
# - HAM 從敘述掃描角色名字建立「互動」命題
# - LTM 摘要用最近 5 筆命題的自然語言
# - 情緒不呼叫模型 → 回歸「平靜」
# - 時間表使用職業範本
print(report["emotion_change"]["to"])   # "平靜"
print(report["ham_extracted"] > 0)      # True（fallback 至少建立互動命題）
```

### 情境三：查看隔天時間表

```python
report = consolidate(claire, stm, ltm, process_log, loader=model_loader)

for slot in report["next_day_schedule"]:
    print(f"  {slot['time']}  {slot['action']:8s}  {slot['location']}")
# 09:30  工作      餐廳
# 12:00  用餐      餐廳
# 15:00  休息      住家
# 00:30  睡覺      住家
```

---

## 注意事項

- STM 完全空（`"（今天還沒有任何記憶）"`）時，`consolidate()` 直接回傳 `_empty_report()`，不執行任何 LLM 呼叫，保留現有 LTM 狀態。
- Step 3 篩選上限為 5 筆重要命題，限制 LTM 每天新增的命題數，防止無限膨脹。
- 關係更新（Step 6）只對「今天敘述中出現的角色」呼叫模型，而非所有關係，節省 LLM 資源。
- `advance_day()` 在 Step 12 呼叫後，下面的程式碼確保 `replace_schedule()` 寫入的新時間表所有 slot 的 `completed` 都是 `False`（因為 `advance_day()` 內部的 `reset_schedule()` 對新插入的 slots 可能不完整）。
- `generate_next_day_schedule()` 的 `_fix_missing_slots()` 只在驗證失敗時補齊缺少的必要時段，不會刪除模型已生成的合法時段。
