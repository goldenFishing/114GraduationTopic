# Agent — 單一角色的決策與行動執行

> **路徑**: `agent/agent.py`  
> **職責**: 管理單角色 tick 決策、對話生成、中斷重評估、睡眠濃縮

---

## 功能概覽

`Agent` 是 AI-Town 中每位虛擬角色的「大腦」。每個 tick，它負責決定角色接下來要做什麼（`decide()`），並輸出一個包含行動、目標、思緒的結構化結果。決策有兩條路徑：**直覺路徑（Markov）** 完全不呼叫模型，僅根據機率分布採樣行動；**深思路徑（Deliberate）** 則建構完整的 prompt 呼叫 LLM，生成帶思緒的詳細決策。

除了主決策之外，`Agent` 也處理對話生成（`generate_dialogue_response()`）與中斷後的重新評估（`re_evaluate_on_interrupt()`）。對話接受與否採用純規則計算（不呼叫模型），透過基礎接受率、關係加成、當前行動類別與情緒懲罰來決定機率。

此外，`Agent` 內建 RL 風格的 `ActionValueTracker`，在每個 tick 結束時計算 reward、更新 value score，供下一個 tick 的 Markov 計算作為第四來源（δ = 0.15）。睡覺時呼叫 `sleep()` 觸發 STM → LTM 的記憶濃縮，並清空 `process_log` 與 value tracker。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `core.markov_engine` | Markov 機率計算、行動採樣、對話目標解析 |
| 依賴 | `core.mental_state` | 困惑度評估（決定直覺/深思模式） |
| 依賴 | `core.memory_stm` | STM 短期記憶讀寫 |
| 依賴 | `core.tick_value` | RL-style ActionValueTracker |
| 依賴 | `core.consolidation` | 睡眠時的記憶濃縮 |
| 依賴 | `model.prompt_io` | PromptBuilder + 輸出解析 |
| 依賴 | `model.inference_engine` | GenerationConfig |
| 依賴 | `config.world_config` | 對話接受率常數、睡覺/起床動作名稱 |
| 依賴 | `config.action_list` | 動作分類、action_id_resolver |
| 被依賴 | `agent.manager.AgentManager` | 每 tick 呼叫 `decide()`、`sleep()` 等 |

---

## 主要類別 / 函式

### `Agent`

**功能**: 單一虛擬角色的推論代理人，持有角色所有記憶與狀態的引用。

#### `__init__(self, character, stm, ltm, memory_graph, loader, prompt_builder)`

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `character` | `Character` | 角色物件（名字、職業、情緒、時間表等） |
| `stm` | `STM` | 短期記憶（當天的敘述流水帳） |
| `ltm` | `LTM` | 長期記憶（結構化命題） |
| `memory_graph` | `MemoryGraph` | LTM 圖譜（用於語意擴散查詢） |
| `loader` | `ModelLoader` | 模型載入器，可為 `None` 或 FakeLoader |
| `prompt_builder` | `PromptBuilder` | 依角色狀態組裝 prompt |

---

#### `decide(self, scene, perception, co_located_codes, input_text, image) -> dict`

**功能**: 一個 tick 的主決策函式。計算困惑度 → 選擇路徑（直覺/深思）→ 採樣或呼叫模型 → 寫入 STM 與 process_log → 更新 value_tracker。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `scene` | `str` | 場景文字，例如 `"第1天 08:00 咖啡店"` |
| `perception` | `dict` | `{"location", "yolo_desc", "scene_text"}` |
| `co_located_codes` | `list` | 同地點角色代號，例如 `["amy", "ben"]` |
| `input_text` | `str` | 外部輸入文字（可為空） |
| `image` | `PIL.Image` \| `None` | 場景截圖（可選） |

**回傳**: 包含以下鍵的 `dict`：

| 鍵 | 說明 |
|----|------|
| `action` | 動詞，例如 `"工作"` `"對話"` `"前往"` |
| `target` | 目標角色或地點 |
| `content` | 對話內容（非對話行動時為空字串） |
| `thought` | 內心獨白（Markov 路徑時為空） |
| `ham` | 模型自己提取的命題列表（深思路徑才有） |
| `mode` | `"markov"` 或 `"deliberate"` |
| `action_id` | 標準化行動 ID |
| `_meta` | 包含困惑度、機率分布、reward 等元數據 |

**決策流程**:

1. `value_tracker.decay()` — 上 tick 影響衰減
2. 計算 Markov 機率分布（帶入 `action_values` 第四來源）
3. `eval_confusion()` — 評估困惑度，決定 `mode`
4. **強制起床檢查**：若時間表 slot 要求 `WAKE_ACTION` 且上一動作不是起床 → 直接回傳起床，**不進入 Markov 或 Deliberate 路徑**（只在每天第一個起床 tick 觸發一次）
5. `mode == "intuitive"` → `_decide_markov()`；`mode == "deliberate"` → `_decide_deliberate()`
6. 寫入 STM、process_log
7. 計算 RL reward，更新 `value_tracker`

**範例**:

```python
# Amy 在咖啡店，Ben 也在場，外部沒有特殊輸入
result = amy_agent.decide(
    scene            = "第1天 09:00 咖啡店",
    perception       = {
        "location":   "咖啡店",
        "yolo_desc":  "顧客正在點餐",
        "scene_text": "早上，咖啡香瀰漫",
    },
    co_located_codes = ["ben"],
    input_text       = "",
    image            = None,
)
print(result["action"])   # "工作"
print(result["mode"])     # "markov"
print(result["_meta"]["tick_reward"])  # 0.12
```

---

#### `_decide_markov(self, action_probs, co_located_names, scene, perception, char) -> dict`

**功能**: 直覺路徑（Intuitive Mode）。從已計算好的機率分布採樣一個動詞，若是「對話」則解析目標，若是「前往」則從時間表或職業預設補目標。**完全不呼叫模型**，速度極快。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `action_probs` | `dict` | `{動詞: 機率}` 字典 |
| `co_located_names` | `list` | 同地點角色名字列表 |
| `scene` | `str` | 場景文字（目前未使用，保留擴充用） |
| `perception` | `dict` | 感知資料 |
| `char` | `Character` | 當前角色物件 |

**回傳**: `{"action", "target", "content", "thought", "ham", "should_sleep"}`

**補目標邏輯**:
- `verb == "前往"` 且無目標 → 優先查時間表 slot 的 `location` → 再查職業預設位置（`咖啡師→咖啡店`、`律師→辦公室` 等）→ 若仍無目標則改為「休息」

**範例**:

```python
# Ben 的 Markov 機率分布，同地點有 Claire
probs = {"工作": 0.55, "休息": 0.25, "對話": 0.15, "前往": 0.05}
result = ben_agent._decide_markov(
    action_probs    = probs,
    co_located_names = ["Claire"],
    scene           = "第2天 14:00 辦公室",
    perception      = {"location": "辦公室", "yolo_desc": "", "scene_text": ""},
    char            = ben_character,
)
print(result["action"])  # "工作"（機率最高）
print(result["should_sleep"])  # False
```

---

#### `_decide_deliberate(self, scene, perception, co_located_codes, input_text, image) -> dict`

**功能**: 深思路徑（Deliberate Mode）。建構完整 prompt（含 STM 敘述、LTM 命題、關係文字），呼叫模型，解析輸出。適用於困惑度高或重大事件發生時。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `scene` | `str` | 場景文字 |
| `perception` | `dict` | 感知資料 |
| `co_located_codes` | `list` | 同地點角色代號 |
| `input_text` | `str` | 當前事件文字 |
| `image` | `PIL.Image` \| `None` | 場景截圖（可選） |

**回傳**: 同 `_decide_markov()`，但 `thought` 與 `ham` 有實際內容。

**範例**:

```python
# Claire 遇到突發狀況（困惑度高），走深思路徑
result = claire_agent._decide_deliberate(
    scene            = "第3天 11:00 超市",
    perception       = {
        "location":   "超市",
        "yolo_desc":  "陌生人倒在地上",
        "scene_text": "突然發生意外",
    },
    co_located_codes = ["david"],
    input_text       = "David：Claire，快來幫忙！",
    image            = None,
)
print(result["action"])   # "對話"（模型判斷需要回應）
print(result["thought"])  # "David 在求助，我應該立刻過去..."
```

---

#### `generate_dialogue_response(self, scene, perception, partner_code, partner_message, recent_dialogue, image) -> dict`

**功能**: 對話一輪生成。被 `AgentManager._handle_dialogue()` 在對話循環中呼叫。每輪呼叫一次模型，生成角色的回應，並寫入 STM。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `scene` | `str` | 場景文字 |
| `perception` | `dict` | 感知資料 |
| `partner_code` | `str` | 對話對象代號，例如 `"ben"` |
| `partner_message` | `str` | 對方說的話 |
| `recent_dialogue` | `str` | 最近 6 行對話歷史（換行分隔） |
| `image` | `PIL.Image` \| `None` | 可選場景圖 |

**回傳**: `{"action", "target", "content", "thought", "ham", "mode": "dialogue"}`

**範例**:

```python
# Amy 回應 Emma 的問候
resp = amy_agent.generate_dialogue_response(
    scene           = "第1天 12:00 餐廳",
    perception      = {"location": "餐廳", "yolo_desc": "", "scene_text": ""},
    partner_code    = "emma",
    partner_message = "今天中午一起吃飯嗎？",
    recent_dialogue = "",
    image           = None,
)
print(resp["content"])  # "好啊，我剛好有空！"
print(resp["mode"])     # "dialogue"
```

---

#### `should_accept_dialogue(self, inviter_code: str) -> bool`

**功能**: 判斷是否接受對方的對話邀請。**純規則計算，不呼叫模型。**

計算公式（基礎值 + 各加成/懲罰，最後 clamp）：

| 因子 | 值 |
|------|----|
| `DIALOGUE_BASE_ACCEPT` | 基礎接受率（從 `config/world_config` 讀取） |
| `DIALOGUE_RELATION_BONUS` | 關係正面關鍵字命中時加成 |
| `DIALOGUE_LEISURE_BONUS` | 當前行動是 `rest` 或 `daily` 類別時加成 |
| `DIALOGUE_WORK_PENALTY` | 當前行動是 `work` 類別時懲罰（負數） |
| `DIALOGUE_EMOTION_PENALTY` | 情緒不在 `["平靜", "開心", "興奮"]` 時懲罰（負數） |

最終以 `DIALOGUE_ACCEPT_MIN` 和 `DIALOGUE_ACCEPT_MAX` clamp 後，用 `random.random() < acc` 採樣。

**範例**:

```python
# Ben 正在工作中，情緒焦慮，David 想來找他聊天
accepted = ben_agent.should_accept_dialogue("david")
# 工作懲罰 + 情緒懲罰 → 接受率低
print(accepted)  # False（高機率）
```

---

#### `re_evaluate_on_interrupt(self, interrupt_event, perception, co_located_codes) -> dict`

**功能**: 收到中斷事件後，用 Markov 重算動作機率，可能改變 `pending_action`。強度為 `"strong"` 的事件視為 major_event（用事件權重重算）。結果寫入 `process_log`（不寫 STM，避免重複）。

**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `interrupt_event` | `dict` | 中斷事件，需含 `"strength"` 欄位 |
| `perception` | `dict` | 當前感知資料 |
| `co_located_codes` | `list` | 同地點角色代號 |

**回傳**: `{"action", "target", "mode": "interrupt", "action_probs"}`

**範例**:

```python
# Emma 正在休息，突然有強力中斷（火災警報）
new_decision = emma_agent.re_evaluate_on_interrupt(
    interrupt_event  = {"type": "external_input", "strength": "strong", "data": {"msg": "火災警報！"}},
    perception       = {"location": "辦公室", "yolo_desc": "警報閃爍", "scene_text": "緊急狀況"},
    co_located_codes = ["claire"],
)
print(new_decision["action"])  # "前往"（可能逃離）
print(new_decision["mode"])    # "interrupt"
```

---

#### `sleep(self) -> dict`

**功能**: 觸發睡眠濃縮。呼叫 `core.consolidation.consolidate()`，將 STM 記憶壓縮至 LTM，清空當天 `process_log`，重置 `value_tracker` 與情緒基準值。

**回傳**: 濃縮報告 dict（由 `consolidate()` 回傳，包含 `ham_extracted`、`ltm_total` 等統計）

**範例**:

```python
# David 在 22:00 後觸發睡眠
report = david_agent.sleep()
print(report["ham_extracted"])  # 今天從 STM 提取的命題數量，例如 12
print(report["ltm_total"])      # LTM 目前總節點數，例如 47
# process_log 已清空
print(david_agent.process_log)  # []
```

---

## 模擬使用情境

### 情境一: 一般 tick 直覺決策（Amy 在咖啡店工作）

```python
from agent.agent import Agent
from core.character import Character
from core.memory_stm import STM
from core.memory_ltm import LTM
from core.memory_graph import MemoryGraph
from model.prompt_io import PromptBuilder

# 假設各物件已初始化
amy_agent = Agent(amy_char, amy_stm, amy_ltm, amy_graph, None, amy_builder)

result = amy_agent.decide(
    scene            = "第1天 09:00 咖啡店",
    perception       = {
        "location":   "咖啡店",
        "yolo_desc":  "顧客排隊中",
        "scene_text": "早晨人潮",
    },
    co_located_codes = [],
    input_text       = "",
    image            = None,
)
# 直覺模式，不呼叫模型
print(result["mode"])    # "markov"
print(result["action"])  # "工作"
```

### 情境二: Ben 拒絕 Claire 的對話邀請（Ben 在工作中且情緒焦慮）

```python
# Ben 的當前狀態：action = "工作"，emotion = "焦慮"
# Claire 嘗試邀請對話
accepted = ben_agent.should_accept_dialogue("claire")

if not accepted:
    print("Ben 拒絕了 Claire 的對話邀請")
    # manager 會從 DIALOGUE_REJECT_TEMPLATES 中隨機取一個回應
```

### 情境三: Emma 睡前記憶濃縮

```python
# 第1天結束，Emma 觸發睡眠
report = emma_agent.sleep()

print(f"今天提取了 {report['ham_extracted']} 個命題")
print(f"LTM 現有 {report['ltm_total']} 個節點")

# 隔天重新開始時，value_tracker 已清零
print(emma_agent.value_tracker.get_scores())  # {}
```

---

## 注意事項

- **強制起床只觸發一次**：`decide()` 中的起床邏輯判斷條件是 `slot.action == WAKE_ACTION and char.current_action != WAKE_ACTION`，確保同一時段不會重複觸發。
- **Markov 路徑完全無模型呼叫**：直覺模式下 `thought`、`ham` 均為空字串/空列表，這是設計意圖。
- **`process_log` 不進 STM**：元數據（困惑度、機率分布等）儲存於 `process_log`，睡眠時才被收集，不會汙染角色的敘述記憶。
- **`loader` 為 `None` 或未載入時**：`_call_model()` 直接回傳空字串，深思路徑的 `parse_decision_output("")` 會回傳 fallback 行動。
- **RL reward 的 `dialogue_accepted` 預設為 `False`**：實際對話被接受後，`manager` 需補呼叫 `value_tracker.update()` 修正，目前設計為 manager 層處理。
- **跨午夜時間表**：`sleep()` 後 `value_tracker` 完全重置，避免舊 reward 汙染新一天的決策。
