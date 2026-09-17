# action_list — 行動與地點的結構性定義與解析

> **路徑**: `config/action_list.py`  
> **職責**: 定義合法行動、地點、分類、觸發關鍵字，並提供 ActionID 解析函式

---

## 功能概覽

`action_list.py` 是 AI-Town 行動系統的核心資料層，負責定義所有角色可執行的行動與可前往的地點，以及這些行動的分類、觸發機制和 UE5 顯示對應關係。

此模組的設計分為兩個層次：「抽象動詞層」與「具體 ActionID 層」。抽象動詞層（`VALID_ACTIONS`、`CHARACTER_VALID_ACTIONS`）供 Markov 引擎的 Stage 1 使用，以簡潔的中文動詞作為決策單元。具體 ActionID 層（`ACTION_TABLE`）供 UE5 渲染引擎使用，包含 emoji 圖示和泡泡圖片 ID，每個角色在特定位置的同一種行動可能對應不同的 ActionID（例如 Amy 在 A 家吃飯是 ID 19，在餐廳吃飯是 ID 6）。

情境觸發系統（K-A 到 K-E 節）實作了 Gibson (1979) 的 Affordance Theory 與 Schank & Abelson (1977) 的 Script Theory：環境場景文字中出現的關鍵字會自動加強對應行動的情境分數，讓角色在看到「客人」時自然傾向「賣咖啡」或「服務客人」，而在「疲憊」時傾向「休息」或「睡覺」。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | （無外部依賴） | 純資料定義，不 import 任何外部模組 |
| 被依賴 | `config/prompts.py` | import `VALID_ACTIONS`、`VALID_LOCATIONS` 用於 prompt 組裝 |
| 被依賴 | `agent/markov_engine.py` | import `ACTION_CATEGORIES`、`ACTION_TO_CATEGORY`、`ACTION_KEYWORD_BOOST`、`EMOTION_TO_ACTION_BOOST`、`KEYWORD_BOOST_PER_HIT`、`get_keyword_hits()`、`get_emotion_boost()` |
| 被依賴 | `agent/dialogue_manager.py` | import `DIALOGUE_REJECT_TEMPLATES`、`CHARACTER_VALID_ACTIONS` |
| 被依賴 | `core/action_executor.py` | import `action_id_resolver()`、`ACTION_ABSTRACT_MAP`、`CHARACTER_HOME_LOCATION` |
| 被依賴 | `config/world_config.py` | import `INTERRUPT_LOCK_LEVELS` 引用的行動字串來自此模組 |

---

## 主要常數 / 資料結構

### `VALID_ACTIONS`
**型別**: `list[str]`  
**預設值**: 共 21 個行動詞（見下表）  
**說明**: 全系統合法行動的總清單。Markov Stage 1 只能選擇此清單中的動詞。行動描述文字（供 prompt 解釋用）定義在 `config/prompts.py`，此處只存結構性清單。

| 類別 | 行動 |
|------|------|
| 移動 | 前往、回家 |
| 咖啡店（Amy） | 賣咖啡、整理店面、打烊 |
| 餐廳（Emma） | 備料、煮飯、服務客人 |
| 超市（Ben） | 收銀、補貨 |
| 辦公室（Claire/David） | 工作 |
| 日常 | 吃飯、買東西、散步、休息、整理家裡、滑手機、運動 |
| 社交 | 對話 |
| 睡眠 | 起床、睡覺 |

---

### `VALID_LOCATIONS`
**型別**: `list[str]`  
**預設值**: 共 15 個地點（見下表）  
**說明**: 全系統合法地點清單。`前往` 行動的目標地點必須從此清單中選取。

| 類別 | 地點 |
|------|------|
| 住宅 | A家、B家、C家、D家、E家、公寓大廳 |
| 工作地點 | 咖啡店、咖啡店後場、超市、超市附近、餐廳、辦公室、公司附近 |
| 公共空間 | 廣場、街道 |

---

### `ACTION_CATEGORIES`
**型別**: `dict[str, list[str]]`  
**預設值**: 6 個類別（movement、work、social、rest、daily、sleep）  
**說明**: 行動的語意分類表。供 `markov_engine.schedule_score()` 計算行動與時間表的契合度：完全匹配得 1.0，同類別得 0.5，不相關得 0.0。

```
"work": ["賣咖啡", "煮飯", "收銀", "補貨", "工作", "服務客人", "備料", "整理店面", "打烊"]
"rest": ["休息", "散步", "滑手機", "運動"]
"daily": ["吃飯", "買東西", "整理家裡"]
"sleep": ["起床", "睡覺"]
```

---

### `ACTION_TO_CATEGORY`
**型別**: `dict[str, str]`  
**預設值**: 由 `ACTION_CATEGORIES` 自動反查建立，共 21 個行動 → 類別的映射  
**說明**: 快速查詢行動所屬類別的反查表，由 dict comprehension 自動產生，不需手動維護。

---

### `ACTION_SEPARATOR`
**型別**: `str`  
**預設值**: `":"`  
**說明**: 行動字串的分隔符，用於解析複合行動格式：
- 純行動：`"工作"`
- 移動行動：`"前往:咖啡店"`
- 對話行動：`"對話:你今天看起來心情不太好，還好嗎？"`

---

### `ACTION_DEFAULT_ON_INVALID`
**型別**: `str`  
**預設值**: `"休息"`  
**說明**: 模型輸出無法解析或解析出的動詞不在 `VALID_ACTIONS` 時的 fallback 行動。「休息」是最安全的中性行動，不會造成任何副作用。

---

### `ACTION_TABLE`
**型別**: `list[dict]`  
**預設值**: 共 45 個 ActionID 條目  
**說明**: 完整動作表，每筆包含以下欄位：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `int` | 唯一 ActionID（1-45） |
| `name` | `str` | 動作名稱（含括號地點說明） |
| `location` | `str` | 執行所需地點簡稱（空字串表示不限） |
| `text` | `str` | UE5 顯示用 emoji（Python 不處理，只儲存） |
| `img_file_id` | `int \| None` | UE5 對話泡泡圖片 ID（Python 不處理，只儲存） |
| `chars` | `list[str]` | 可執行此動作的角色代碼列表 |

**重要 ActionID 一覽**（節選）：

| ID | 名稱 | 角色 | 地點 |
|----|------|------|------|
| 9 | 賣咖啡 | A（Amy） | 咖啡店 |
| 12 | 收銀 | B（Ben） | 超市 |
| 14 | 工作（員工） | C（Claire） | 辦公室 |
| 15 | 工作（老闆） | D（David） | 辦公室 |
| 18 | 服務客人（外場） | E（Emma） | — |
| 40-44 | 睡覺（各家） | A/B/C/D/E | 各自家 |
| 45 | 對話 | 全體 | — |

---

### `CHARACTER_VALID_ACTIONS`
**型別**: `dict[str, list[str]]`  
**說明**: 各角色在 Markov Stage 1 可選用的抽象動詞清單，是 `VALID_ACTIONS` 的子集合。不同角色的工作行動不重疊（例如只有 A 可以「賣咖啡」，只有 E 可以「備料」）。

| 角色 | 專屬工作行動 | 通用行動 |
|------|------------|---------|
| A（Amy） | 賣咖啡、整理店面、打烊 | 前往、回家、吃飯、散步、運動、整理家裡、滑手機、睡覺、買東西、對話 |
| B（Ben） | 收銀、補貨 | 前往、回家、吃飯、散步、運動、整理家裡、滑手機、睡覺、買東西、對話 |
| C（Claire） | 工作 | 同上 |
| D（David） | 工作 | 同上 |
| E（Emma） | 備料、煮飯、服務客人 | 同上 |

---

### `CHARACTER_HOME_LOCATION`
**型別**: `dict[str, str]`  
**預設值**: `{"A": "A家", "B": "B家", "C": "C家", "D": "D家", "E": "E家"}`  
**說明**: 角色代碼到家位置名稱的映射。`action_id_resolver` 在處理「回家」等需要知道角色住所的行動時使用此表快速查詢。

---

### `ACTION_ABSTRACT_MAP`
**型別**: `dict[str, list[dict]]`  
**說明**: 抽象動詞到 `ACTION_TABLE` 條目清單的映射，在模組載入時由 `ACTION_TABLE` 自動建構。抽象動詞的提取規則依序為：
1. 名稱含底線（如 `"回家_A"`）→ 取底線前部分 `"回家"`
2. 名稱含括號（如 `"吃飯 (餐廳)"`）→ 取括號前 strip 結果 `"吃飯"`
3. 其餘（如 `"對話"`、`"賣咖啡"`）→ 整個 name 即為抽象動詞

---

### `ACTION_KEYWORD_BOOST`
**型別**: `dict[str, list[str]]`  
**說明**: 每個行動的情境觸發關鍵字列表（每個行動 3-7 個核心觸發詞）。`markov_engine.situation_score()` 掃描合併文字時，每命中一個關鍵字對對應行動加分 `KEYWORD_BOOST_PER_HIT`。

---

### `KEYWORD_BOOST_PER_HIT`
**型別**: `float`  
**預設值**: `0.15`  
**說明**: 每命中一個關鍵字的加分量。設計邏輯：
- 命中 1 個：+0.15，影響輕微，不壓過時間表（α=0.4）
- 命中 3 個：+0.45，影響明顯，可改變行動傾向
- 命中 5 個：+0.75，強情境，顯著主導決策

---

### `EMOTION_TO_ACTION_BOOST`
**型別**: `dict[str, dict[str, float]]`  
**說明**: 各情緒對特定行動的額外加分。情緒直接影響行動傾向：

| 情緒 | 偏好行動 |
|------|---------|
| 開心 | 對話 +0.2、散步 +0.1、運動 +0.1 |
| 興奮 | 對話 +0.25、運動 +0.15、散步 +0.1 |
| 疲憊 | 休息 +0.3、睡覺 +0.2、滑手機 +0.1 |
| 難過 | 休息 +0.2、滑手機 +0.15、散步 +0.1 |
| 平靜 | 無偏好（空 dict） |

---

### `DIALOGUE_REJECT_TEMPLATES`
**型別**: `list[str]`  
**預設值**: `["現在有點忙，待會再聊", "嗯…先這樣", "不好意思我趕時間", "現在不方便", "有點累，改天好嗎"]`  
**說明**: 對話被拒絕時的隨機回應模板，純規則選取，不呼叫模型。確保即使在拒絕對話時也有自然的語言輸出。

---

## 主要函式

### `action_id_resolver(abstract_verb: str, char_code: str, current_location: str) -> int | None`

**功能**: 根據抽象動詞、角色代碼與當前位置，從 `ACTION_TABLE` 中找出最符合的具體 ActionID，供 UE5 渲染引擎使用。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `abstract_verb` | `str` | Markov Stage 1 輸出的抽象動詞，例如 `"吃飯"`、`"睡覺"` |
| `char_code` | `str` | 角色代碼，例如 `"A"`、`"B"`、`"C"`、`"D"`、`"E"` |
| `current_location` | `str` | 角色當前所在地點，例如 `"A家"`、`"咖啡店"` |

**回傳**: `int | None` — 最符合條件的 ActionID；若無任何候選則回傳 `None`

**解析優先順序**:
1. 取出 `ACTION_ABSTRACT_MAP[abstract_verb]` 中該 `char_code` 可執行的候選
2. **角色專屬消歧義**：`"工作"` 且多候選時，C → ID 14（員工），D → ID 15（老闆）
3. **精確位置匹配**：`entry["location"] == current_location`
4. **不限位置匹配**：`entry["location"] == ""`
5. **fallback**：候選清單第一個
6. 若無候選：回傳 `None`

**範例**:
```python
from config.action_list import action_id_resolver

# Amy 在家吃飯 → 精確位置匹配到「吃飯 (在A家)」
result = action_id_resolver("吃飯", "A", "A家")
print(result)  # 19

# Amy 在咖啡店吃飯 → 無精確匹配，fallback 到不限位置的「吃飯 (餐廳)」
result = action_id_resolver("吃飯", "A", "咖啡店")
print(result)  # 6

# Claire 在辦公室工作 → 角色消歧義，Claire(C) → 員工版本
result = action_id_resolver("工作", "C", "辦公室")
print(result)  # 14

# David 在辦公室工作 → 角色消歧義，David(D) → 老闆版本
result = action_id_resolver("工作", "D", "辦公室")
print(result)  # 15

# Amy 嘗試執行只有 Ben 能做的「收銀」→ 無候選
result = action_id_resolver("收銀", "A", "超市")
print(result)  # None
```

---

### `get_keyword_hits(text: str, action: str) -> int`

**功能**: 計算 `text` 中命中 `action` 的關鍵字次數，供 `markov_engine` 計算情境分數。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `text` | `str` | 合併的情境文字（scene + yolo_desc + 最近 STM） |
| `action` | `str` | 要計算命中數的目標行動 |

**回傳**: `int` — 命中的關鍵字個數

**範例**:
```python
from config.action_list import get_keyword_hits

# 咖啡店場景文字
scene_text = "咖啡店內客人陸續進來，有人在排隊，Amy 在點單"

hits = get_keyword_hits(scene_text, "賣咖啡")
print(hits)  # 4（命中「客人」「排隊」「點單」「咖啡店」）

boost = hits * 0.15  # KEYWORD_BOOST_PER_HIT
print(f"賣咖啡情境加分：{boost}")  # 賣咖啡情境加分：0.6
```

---

### `get_emotion_boost(emotion: str, action: str) -> float`

**功能**: 取得指定情緒對指定行動的加分值，供 `markov_engine` 的情境分數計算使用。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `emotion` | `str` | 角色當前情緒，必須是 `VALID_EMOTIONS` 中的值 |
| `action` | `str` | 要查詢加分的目標行動 |

**回傳**: `float` — 情緒對該行動的加分（不在映射中則回傳 `0.0`）

**範例**:
```python
from config.action_list import get_emotion_boost

# Emma 今天很疲憊，查詢「睡覺」的情緒加分
boost = get_emotion_boost("疲憊", "睡覺")
print(boost)  # 0.2

# Ben 心情開心，查詢「對話」的情緒加分
boost = get_emotion_boost("開心", "對話")
print(boost)  # 0.2

# 平靜情緒對任何行動都無加成
boost = get_emotion_boost("平靜", "賣咖啡")
print(boost)  # 0.0
```

---

## 模擬使用情境

### 情境一：Amy 在咖啡店的情境分數計算

```python
from config.action_list import (
    get_keyword_hits, get_emotion_boost, KEYWORD_BOOST_PER_HIT,
    CHARACTER_VALID_ACTIONS,
)

# 當前時刻：Amy 在咖啡店，情緒「開心」，YOLO 偵測到客人排隊
scene_text = "咖啡店，早上10點，客人排隊，點單中，咖啡香氣"
amy_emotion = "開心"

# 計算 Amy 每個可選行動的情境分數
scores = {}
for action in CHARACTER_VALID_ACTIONS["A"]:
    keyword_score = get_keyword_hits(scene_text, action) * KEYWORD_BOOST_PER_HIT
    emotion_score = get_emotion_boost(amy_emotion, action)
    scores[action] = keyword_score + emotion_score

# 排序顯示
for action, score in sorted(scores.items(), key=lambda x: -x[1]):
    if score > 0:
        print(f"{action}: {score:.2f}")
# 賣咖啡: 0.75（命中「客人」「排隊」「點單」「咖啡店」共4個 +0.15×4=0.60，開心+對話0不加到賣咖啡）
# 對話: 0.20（開心情緒加成）
```

### 情境二：解析 David 的行動 ID 並傳給 UE5

```python
from config.action_list import action_id_resolver

# Markov 引擎決定 David（代號D）在辦公室執行「工作」
abstract_verb = "工作"
char_code = "D"
current_location = "辦公室"

action_id = action_id_resolver(abstract_verb, char_code, current_location)
print(f"David 的行動 ID：{action_id}")
# David 的行動 ID：15（工作 老闆版本）

# 傳給 UE5 渲染引擎
ue5_payload = {
    "character": "D",
    "action_id": action_id,  # 15
    "location": current_location,
}
```

### 情境三：Ben 的對話接受/拒絕流程

```python
import random
from config.action_list import DIALOGUE_REJECT_TEMPLATES

# Ben 正在收銀，Claire 向他搭話
# （對話接受率計算在 world_config 的 DIALOGUE_* 常數中）
accept_dialogue = False  # 假設規則計算結果為拒絕

if not accept_dialogue:
    response = random.choice(DIALOGUE_REJECT_TEMPLATES)
    print(f"Ben：「{response}」")
    # Ben：「現在有點忙，待會再聊」（或其他隨機選項）
```

---

## 注意事項

- `ACTION_ABSTRACT_MAP` 在模組 import 時自動建構完畢，使用後迴圈變數 `_entry`、`_name`、`_abstract` 被 `del` 清除，不會污染模組命名空間。
- `CHARACTER_VALID_ACTIONS` 中的行動必須是 `VALID_ACTIONS` 的子集合。新增行動時兩者都需要更新，否則 Markov 引擎可能選出 `action_id_resolver` 無法解析的動詞。
- `get_keyword_hits()` 使用的是 Python `in` 運算符（`kw in text`），因此關鍵字必須是 `text` 的 substring。這表示單字「咖啡」會命中「咖啡店」，設計關鍵字時需注意不要讓一個詞同時觸發多個行動（例如「客人」同時觸發多個工作類行動，是預期行為，代表在有客人的場合各種工作行動都加分）。
- `EMOTION_TO_ACTION_BOOST["平靜"]` 是空 dict `{}`，呼叫 `get_emotion_boost("平靜", 任何行動)` 都回傳 `0.0`，不會出錯。
- ActionID 1-5（回家_A 到回家_E）的 `chars` 欄位各只包含對應角色，確保角色只能回自己的家而不是別人家。
- `action_id_resolver` 在找不到任何候選時回傳 `None`，呼叫方必須處理 `None` 的情況（例如 fallback 到 `ACTION_DEFAULT_ON_INVALID = "休息"`）。
