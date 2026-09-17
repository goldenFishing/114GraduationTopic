# prompt_io — Prompt 組裝與輸出解析

> **路徑**: `model/prompt_io.py`  
> **職責**: 依角色狀態組裝推論 prompt，並解析模型結構化輸出

---

## 功能概覽

`prompt_io.py` 包含兩個主要部分：`PromptBuilder` 類別負責組裝推論用的完整 prompt，`parse_decision_output()` 及相關函式負責解析模型輸出為結構化 dict。

`PromptBuilder` 根據角色的 STM（短期記憶）、LTM（長期記憶圖譜）、關係文字、場景、同地點角色等資訊，呼叫 `config/prompts.py` 中定義的 prompt 模板函式，生成可直接送入 LLM 的完整文字。STM 和 LTM 的內容都受 token 預算限制（分別來自 `STM_TOKEN_BUDGET` 和 `LTM_TOKEN_BUDGET`），超過時截斷。

輸出解析部分處理模型以 `[TAG] 內容` 格式輸出的結構化文字。`ACTION`、`TARGET`、`CONTENT` 為單行標籤，`THOUGHT` 為多行標籤，`HAM` 區塊為命題列表（每行 `subject | relation | object | location | time` 格式），解析後轉為 Python list。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.prompts` | `prompt_deliberate()`、`prompt_dialogue()` 模板函式 |
| 依賴 | `config.model_config` | `STM_TOKEN_BUDGET`、`LTM_TOKEN_BUDGET` |
| 依賴 | `config.world_config` | `CHARACTER_NAMES`（代號 → 名字對照） |
| 依賴 | `config.action_list` | `VALID_ACTIONS`、`ACTION_DEFAULT_ON_INVALID` |
| 被依賴 | `agent.agent.Agent` | `_decide_deliberate()` 和 `generate_dialogue_response()` 呼叫 `parse_decision_output()` |
| 被依賴 | `agent.manager.AgentManager` | 初始化時建立 `PromptBuilder` 實例傳給 `Agent` |

---

## 主要類別 / 函式

### `PromptBuilder`

**功能**: 依角色狀態與當前情境組裝 prompt。每個角色一個實例，在 `AgentManager.__init__()` 中建立。

#### `__init__(self, character, stm, ltm, memory_graph)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `character` | `Character` | 角色物件（名字、性格、習慣、情緒、關係等） |
| `stm` | `STM` | 短期記憶 |
| `ltm` | `LTM` | 長期記憶 |
| `memory_graph` | `MemoryGraph` | LTM 圖譜（用於語意擴散查詢） |

---

#### `build_deliberate(self, scene, perception, co_located_codes, input_text) -> str`

**功能**: 組裝深思路徑（Deliberate Mode）的完整推論 prompt。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `scene` | `str` | 場景文字，例如 `"第2天 14:00 辦公室"` |
| `perception` | `dict` \| `None` | `{"location", "yolo_desc", "scene_text"}` |
| `co_located_codes` | `list` \| `None` | 同地點角色代號列表 |
| `input_text` | `str` | 當前事件（外部輸入或對話內容） |

**內部組裝流程**:

1. **STM 敘述化**：`stm.get_today_narrative(max_chars = STM_TOKEN_BUDGET * 2)`
2. **LTM 語意查詢**：以角色名字、同地點角色第一人為核心，加上最近 3 輪 STM，呼叫 `graph.auto_query_nodes()` → `graph.spreading_retrieve(top_k=15)` → `graph.propositions_to_narrative()`，截斷至 `LTM_TOKEN_BUDGET * 2`
3. **關係文字**：取第一個同地點角色的完整關係描述（`include_summary=True`）
4. **同地點角色字串**：用 `、` 連接所有同地點角色名字

**回傳**: 完整 prompt 字串（由 `config/prompts.prompt_deliberate()` 渲染）

**範例**:

```python
# Amy 在咖啡店，Ben 也在場
prompt_text = amy_builder.build_deliberate(
    scene            = "第1天 10:00 咖啡店",
    perception       = {
        "location":   "咖啡店",
        "yolo_desc":  "Ben 走近",
        "scene_text": "咖啡香，顧客稀少",
    },
    co_located_codes = ["ben"],
    input_text       = "Ben：Amy，早安！",
)
# prompt_text 包含：Amy 的性格、STM 今日敘述、
# 與 Ben 的關係文字、LTM 相關記憶、當前場景與 Ben 的發言
```

---

#### `build_dialogue(self, scene, partner_code, partner_message, recent_dialogue) -> str`

**功能**: 組裝對話一輪的 prompt。以對方角色為查詢核心，從 LTM 圖譜取出最相關的共同記憶（`top_k=10`，比深思路徑少），加入最近對話歷史。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `scene` | `str` | 場景文字 |
| `partner_code` | `str` | 對話對象代號，例如 `"claire"` |
| `partner_message` | `str` | 對方剛說的話 |
| `recent_dialogue` | `str` | 最近 3 輪對話歷史（換行分隔的字串） |

**與 `build_deliberate()` 的差異**:

| 面向 | `build_deliberate()` | `build_dialogue()` |
|------|---------------------|-------------------|
| LTM top_k | 15 | 10 |
| 是否含 co_located | 是（多個） | 否（只有 partner） |
| 額外資訊 | `yolo_desc`、`scene_text` | `partner_message`、`recent_dialogue` |
| prompt 模板 | `prompt_deliberate()` | `prompt_dialogue()` |

**範例**:

```python
# Claire 回應 David 的問話，已有 2 輪對話歷史
prompt_text = claire_builder.build_dialogue(
    scene           = "第3天 15:00 超市",
    partner_code    = "david",
    partner_message = "今天超市很忙嗎？",
    recent_dialogue = "David：Claire，你好。\nClaire：你好，David！",
)
```

---

### `parse_decision_output(raw: str) -> dict`

**功能**: 解析模型的完整輸出字串為結構化 dict。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `raw` | `str` | 模型輸出的原始文字 |

**回傳**:

```python
{
    "action":  str,    # 動詞，例如 "工作" "對話" "前往"
    "target":  str,    # 目標（地點、對象或空字串）
    "content": str,    # 對話內容（非對話行動時為空）
    "thought": str,    # 內心獨白（多行合併為一行）
    "ham":     list,   # 命題列表，見下方格式
    "raw":     str     # 原始輸出（供除錯）
}
```

**HAM 命題格式**:

```python
{
    "subject":  "Amy",
    "relation": "喜歡",
    "object":   "咖啡",
    "location": "咖啡店",   # 可為 None
    "time":     "早上",      # 可為 None
}
```

**範例**:

```python
raw = """
[ACTION] 對話
[TARGET] Ben
[CONTENT] 你今天怎麼這麼早來？
[THOUGHT] Ben 好像有什麼心事，我想關心一下。
[HAM]
- Amy | 關心 | Ben | 咖啡店 | 早上
- Ben | 表情 | 憂慮 | 咖啡店 | 無時間
[/HAM]
"""
result = parse_decision_output(raw)
print(result["action"])   # "對話"
print(result["target"])   # "Ben"
print(result["content"])  # "你今天怎麼這麼早來？"
print(result["thought"])  # "Ben 好像有什麼心事，我想關心一下。"
print(len(result["ham"])) # 2
print(result["ham"][0])   # {"subject": "Amy", "relation": "關心", ...}
```

---

### 內部解析函式

#### `_parse_block_value(raw, tag) -> str`

**功能**: 解析 `[TAG] 單行內容` 格式。只取標籤所在行的內容，可選地支援 `[TAG]: 內容` 的冒號格式。

---

#### `_parse_block_multiline(raw, tag) -> str`

**功能**: 解析 `[TAG]` 後到下一個 `[TAG]` 之前的多行內容，用於 `THOUGHT` 標籤。所有非空行合併為一個以空格分隔的字串。

---

#### `_parse_ham_block(raw) -> list`

**功能**: 從 `[HAM]...[/HAM]` 區塊解析命題列表。若無閉合標籤則 fallback 為 `[HAM]` 後所有內容。呼叫 `_parse_ham_lines()` 做逐行解析。

---

#### `_parse_ham_lines(text) -> list`

**功能**: 逐行解析 `subject | relation | object | location | time` 格式的命題。行首的 `-` 會被去除。欄位少於 5 個時自動補空字串。`location` 和 `time` 若為 `""`, `"無"`, `"無地點"`, `"無時間"` 則設為 `None`。

---

#### `_validate_action(action) -> str`

**功能**: 驗證動詞是否在 `VALID_ACTIONS` 中。

**驗證流程**:
1. 完全匹配 `VALID_ACTIONS` → 直接回傳
2. `VALID_ACTIONS` 中有任一動詞包含在 `action` 字串內 → 回傳那個動詞（模糊匹配）
3. 都不符合 → 回傳 `ACTION_DEFAULT_ON_INVALID`（fallback 行動）

---

### `_truncate(text, max_chars) -> str`

**功能**: 超過 `max_chars` 字元時截斷，並在末尾加上 `"\n...（已截斷）"` 提示。用於 STM 和 LTM 敘述的 token 預算控制。

---

## 模擬使用情境

### 情境一: 深思路徑 prompt 組裝（Emma 在辦公室遇到緊急事件）

```python
# Emma 的 PromptBuilder，已有 5 輪 STM 記憶
prompt_text = emma_builder.build_deliberate(
    scene            = "第2天 15:30 辦公室",
    perception       = {
        "location":   "辦公室",
        "yolo_desc":  "同事跑來跑去，面色焦急",
        "scene_text": "緊張氣氛",
    },
    co_located_codes = ["claire", "david"],
    input_text       = "Claire：Emma，系統當掉了！",
)
# 傳入模型推論
raw = loader.fusion.generate(
    loader.fusion.fuse_inputs(
        loader.text.build_prompt(prompt_text, num_images=0).prompt,
        image_inputs={}
    ),
    GenerationConfig.deliberate()
)
result = parse_decision_output(raw)
print(result["action"])  # 例如 "工作"（處理系統問題）
```

### 情境二: 對話 prompt 組裝與輸出解析

```python
# Amy 與 Ben 第 2 輪對話
prompt_text = amy_builder.build_dialogue(
    scene           = "第1天 12:00 餐廳",
    partner_code    = "ben",
    partner_message = "我最近工作壓力很大...",
    recent_dialogue = "Amy：你看起來很疲倦。\nBen：是啊，睡眠不足。",
)
raw = loader.fusion.generate(
    loader.fusion.fuse_inputs(
        loader.text.build_prompt(prompt_text).prompt,
        image_inputs={}
    ),
    GenerationConfig.dialogue()
)
result = parse_decision_output(raw)
print(result["content"])  # Amy 的回應，例如 "要不要喝杯咖啡，放鬆一下？"
print(result["ham"])      # 可能含 [{subject: "Ben", relation: "感到", object: "壓力"}]
```

### 情境三: 解析無效 ACTION 的 fallback

```python
raw = "[ACTION] 飛翔\n[TARGET] 天空\n[CONTENT] \n[THOUGHT] 想去外太空"
result = parse_decision_output(raw)
print(result["action"])  # ACTION_DEFAULT_ON_INVALID（例如 "休息"）
# "飛翔" 不在 VALID_ACTIONS 中，fallback 生效
```

---

## 注意事項

- **Token 預算是字元數的 2 倍**：`max_chars = STM_TOKEN_BUDGET * 2` 是粗略估算（中文字元 ≈ 1-2 tokens），實際 token 數因 tokenizer 而異。
- **LTM `spreading_retrieve` 設定 `update_access=True`**：查詢時會更新節點的存取時間，影響後續查詢的優先順序。
- **`build_deliberate()` 的 LTM 查詢含位置資訊**：`graph.auto_query_nodes()` 接收 `location` 參數，會優先查詢與當前地點相關的記憶；`build_dialogue()` 不傳 `location`，只以人物關係為查詢核心。
- **HAM 解析優先抓 `[HAM]...[/HAM]`**：有閉合標籤時精確解析，無閉合標籤時用貪婪 fallback（`[HAM]` 後所有內容），可能誤包含其他部分。
- **`_validate_action()` 的模糊匹配**：若模型輸出 `"進行對話"` 而非 `"對話"`，模糊匹配能正確回傳 `"對話"`，但若多個 `VALID_ACTIONS` 都出現在 `action` 中，回傳第一個匹配（按 `VALID_ACTIONS` 順序）。
