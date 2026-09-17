# prompts — Phi-3.5 推論 prompt 模板集

> **路徑**: `config/prompts.py`  
> **職責**: 集中定義所有送給模型的 prompt 模板函式

---

## 功能概覽

`prompts.py` 是 AI-Town 與 Phi-3.5-Vision-Instruct 模型之間的語言接口層，集中定義所有 prompt 模板函式。全系統共有八個需要呼叫模型的場景，每個場景對應一個函式，從深思決策、對話生成，到睡眠濃縮的七個子步驟（HAM 抽取、篩選、LTM 摘要、關係更新、情緒推斷、時間表生成）。

此模組的設計哲學是「輸出格式決定穩定性」。決策與對話使用 block-style 格式（`[ACTION]`、`[TARGET]`、`[CONTENT]`、`[THOUGHT]`、`[HAM]`），因為 Phi-3.5 在固定標籤上比 JSON 格式穩定得多，不易出現引號問題。HAM 命題使用 `|` 管道符分隔，避免中文 JSON 引號的混亂。只有時間表生成才使用 JSON，因為結構化陣列資料需要精確的機器解析。

每個 prompt 函式都以 `{_LANGUAGE_REMINDER}` 開頭（「請務必使用繁體中文回應，不要夾雜英文」），這行提醒在 prompt 前端置入，確保模型輸出保持繁體中文，不會混入英文字元而破壞後續的字串解析邏輯。

值得注意的是，Markov 直覺路徑（Stage 1-3 的快速決策）完全不呼叫模型，因此此模組中不存在 `prompt_intuitive`——這是刻意的架構決定，體現了「低認知負荷行為不需要深度推理」的設計原則。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config/action_list` | import `VALID_ACTIONS`、`VALID_LOCATIONS` 用於 prompt 中列舉可選行動與地點 |
| 依賴 | `config/world_config` | import `VALID_EMOTIONS` 用於情緒推斷 prompt |
| 被依賴 | `model/prompt_builder.py` | import `prompt_deliberate`、`prompt_dialogue` 並在其中填入角色資料後呼叫 |
| 被依賴 | `core/consolidation.py` | import `prompt_extract_ham`、`prompt_select_ltm`、`prompt_ltm_summary`、`prompt_update_relationship`、`prompt_infer_emotion` |
| 被依賴 | `agent/scheduler.py` | import `prompt_generate_schedule` 用於睡眠濃縮的時間表生成步驟 |

---

## 主要常數 / 資料結構

### `_LANGUAGE_REMINDER`
**型別**: `str`  
**預設值**: `"請務必使用繁體中文回應，不要夾雜英文。"`  
**說明**: 私有常數（以 `_` 開頭），每個 prompt 函式在 f-string 開頭都插入此提醒。確保 Phi-3.5（英文預訓練模型）在中文情境下穩定輸出繁體中文，不摻雜英文或簡體。

---

## 主要函式

### `_action_list_str() -> str`

**功能**: 將 `VALID_ACTIONS` 轉換為頓號分隔的單行字串，嵌入 prompt 的「可執行行動」區塊。

**回傳**: `str` — 例如 `"前往、回家、賣咖啡、整理店面、...、睡覺"`

**範例**:
```python
from config.prompts import _action_list_str
print(_action_list_str())
# 前往、回家、賣咖啡、整理店面、打烊、備料、煮飯、服務客人、收銀、補貨、工作、吃飯、買東西、散步、休息、整理家裡、滑手機、運動、對話、起床、睡覺
```

---

### `_location_list_str() -> str`

**功能**: 將 `VALID_LOCATIONS` 轉換為頓號分隔的單行字串，嵌入 prompt 的「可前往地點」區塊。

**回傳**: `str` — 例如 `"A家、B家、...、廣場、街道"`

---

### `prompt_deliberate(character_name, personality, habit, emotion, relationship_text, stm_narrative, ltm_narrative, scene, co_located_text, current_event) -> str`

**功能**: 構建 System 2 深思路徑的決策 prompt，讓模型扮演指定角色，根據記憶、情緒與當下情境決定下一個行動。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 角色名字，例如 `"Amy"` |
| `personality` | `str` | 完整個性描述，來自角色 JSON |
| `habit` | `str` | 習慣描述，來自角色 JSON |
| `emotion` | `str` | 當前情緒，`VALID_EMOTIONS` 之一 |
| `relationship_text` | `str` | 與當前可能互動對象的關係摘要文字 |
| `stm_narrative` | `str` | STM 敘述化文字（今天的經歷） |
| `ltm_narrative` | `str` | LTM 圖譜反向組句後的相關長期記憶 |
| `scene` | `str` | 當前場景（含時間+地點+環境描述） |
| `co_located_text` | `str` | 同地點有誰（選填，空字串時不加入 prompt） |
| `current_event` | `str` | 當前發生的事件（選填，例如有人開口說話） |

**回傳**: `str` — 完整 prompt 字串，期待模型輸出 `[ACTION][TARGET][CONTENT][THOUGHT][HAM]` 格式

**期待輸出格式**:
```
[ACTION] 賣咖啡
[TARGET] 
[CONTENT] 

[THOUGHT] 現在是早上尖峰時段，客人陸續進來，我應該專心沖咖啡。

[HAM]
- Amy | 工作 | 咖啡 | 咖啡店 | 早上
- Amy | 感到 | 充實 | 咖啡店 | 早上
[/HAM]
```

**範例**:
```python
from config.prompts import prompt_deliberate

p = prompt_deliberate(
    character_name="Amy",
    personality="開朗、有責任感、重視人際關係，對自己的咖啡師工作感到驕傲",
    habit="每天06:00起床，固定在07:30開店前整理店面",
    emotion="開心",
    relationship_text="David：熟識的常客，每天早上必來買咖啡，關係良好",
    stm_narrative="06:00 起床，整理儀容。07:30 到咖啡店整理店面、清潔機器。",
    ltm_narrative="Amy 認識 David 已超過一年，David 固定每天早上來買咖啡。",
    scene="咖啡店，08:45，早上尖峰時段，陽光透過玻璃窗灑進來",
    co_located_text="David 剛推開門進來",
    current_event="",
)
print(p[:200])  # 顯示 prompt 開頭部分
# 請務必使用繁體中文回應，不要夾雜英文。
# 你正在扮演 Amy，依據你的記憶、個性與當下狀況，決定此刻最想做的事。...
```

---

### `prompt_dialogue(character_name, personality, emotion, partner_name, relationship_text, stm_narrative, ltm_narrative, scene, recent_dialogue, partner_message) -> str`

**功能**: 構建對話循環中單輪的 prompt，讓角色根據對方說的話和自身狀態決定如何回應。此 prompt 在對話循環中會被多次呼叫（每輪一次，最多 `DIALOGUE_MAX_TURNS` 輪）。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 當前回應的角色名字 |
| `personality` | `str` | 角色個性描述 |
| `emotion` | `str` | 角色當前情緒 |
| `partner_name` | `str` | 對話對象名字 |
| `relationship_text` | `str` | 與對方的關係摘要 |
| `stm_narrative` | `str` | 自己今天的經歷敘述 |
| `ltm_narrative` | `str` | 與對方相關的長期記憶 |
| `scene` | `str` | 當前場景 |
| `recent_dialogue` | `str` | 最近 3 輪對話歷史（雙方各說了什麼） |
| `partner_message` | `str` | 對方剛剛說的這句話 |

**回傳**: `str` — 完整對話輪 prompt；通常 `ACTION=對話`，除非角色決定結束對話

**期待輸出格式**:
```
[ACTION] 對話
[TARGET] David
[CONTENT] 你今天來得比平常晚一點，是有什麼事嗎？

[THOUGHT] David 看起來有些疲憊，我想關心一下。

[HAM]
- Amy | 關心 | David | 咖啡店 | 早上
[/HAM]
```

**範例**:
```python
from config.prompts import prompt_dialogue

p = prompt_dialogue(
    character_name="Amy",
    personality="開朗、有責任感、重視人際關係",
    emotion="開心",
    partner_name="David",
    relationship_text="熟識的常客，每天早上必來，關係良好",
    stm_narrative="07:30 整理店面，08:30 開始服務客人",
    ltm_narrative="David 是公司老闆，工作壓力很大，常聊工作上的煩惱",
    scene="咖啡店，08:55，早上尖峰時段",
    recent_dialogue="",  # 第一輪，無歷史
    partner_message="早安，Amy，給我一杯老樣子",
)
# 模型收到後回應：[ACTION] 對話\n[TARGET] David\n[CONTENT] 好的，馬上來！...
```

---

### `prompt_extract_ham(character_name: str, today_narrative: str) -> str`

**功能**: 從角色今天的 STM 敘述化文字中，抽取值得長期保存的 HAM 5 元組命題（睡眠濃縮 Step 2）。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 角色名字 |
| `today_narrative` | `str` | 將當天全部 STM 記錄敘述化後的長文字 |

**回傳**: `str` — prompt 字串；期待模型輸出 `主詞 | 關係 | 受詞 | 地點 | 時間` 格式，每行一筆，最多 10 筆

**期待輸出範例**（模型回應）:
```
Emma | 遇見 | Amy | 廣場 | 傍晚
Emma | 感到 | 疲憊 | 餐廳 | 晚上
Amy | 詢問 | Emma | 廣場 | 傍晚
Emma | 完成 | 晚餐高峰服務 | 餐廳 | 晚上
```

**範例**:
```python
from config.prompts import prompt_extract_ham

narrative = """
09:00 起床，感覺有點睏。
11:00 備料，今天食材很新鮮。
12:00 到 14:00 午餐高峰，很忙，但覺得充實。
14:30 傍晚在廣場遇到 Amy，聊了一下最近的疲憊感。
18:00 晚餐高峰，非常忙碌，一個人扛廚房。
22:00 回家，精疲力竭。
"""

p = prompt_extract_ham("Emma", narrative)
# 包含抽取規則：優先人物互動與情感變化，忽略純粹日常瑣事
```

---

### `prompt_select_ltm(character_name: str, today_narrative: str, extracted_props: str) -> str`

**功能**: 從 Step 2 抽取的所有 HAM 命題中，篩選出最值得長期記憶的（最多保留 5 筆），刪除瑣碎和重複的（睡眠濃縮 Step 3）。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 角色名字 |
| `today_narrative` | `str` | 今天的經歷敘述（供模型判斷重要性） |
| `extracted_props` | `str` | Step 2 輸出的全部命題（`|` 分隔格式） |

**回傳**: `str` — prompt 字串；期待模型輸出精選後的命題列表（同格式，最多 5 筆）

**範例**:
```python
from config.prompts import prompt_select_ltm

extracted = """
Ben | 遇見 | Claire | 廣場 | 傍晚
Ben | 感到 | 開心 | 廣場 | 傍晚
Ben | 補貨 | 貨架 | 超市 | 早上
Ben | 收銀 | 客人 | 超市 | 下午
Claire | 聊到 | 工作壓力 | 廣場 | 傍晚
"""

p = prompt_select_ltm(
    "Ben",
    "今天工作如常，傍晚在廣場巧遇 Claire，聊了工作上的事情",
    extracted,
)
# 模型應保留人際互動（遇見Claire、Claire聊工作壓力）
# 刪除純粹工作瑣事（補貨、收銀）
```

---

### `prompt_ltm_summary(character_name: str, all_props_text: str) -> str`

**功能**: 根據目前 LTM 中所有命題生成 1-2 句話的整體摘要（睡眠濃縮 Step 5）。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 角色名字 |
| `all_props_text` | `str` | LTM 目前所有命題的文字呈現 |

**回傳**: `str` — prompt 字串；期待模型輸出純文字摘要（1-2 句，以角色視角撰寫，聚焦重要人際關係與關鍵事件）

**範例**:
```python
from config.prompts import prompt_ltm_summary

all_props = """
Claire | 認識 | David | 辦公室 | 第一天上班
Claire | 尊敬 | David | 辦公室 | 長期
David | 對Claire嚴格 | 報告 | 辦公室 | 上週
Claire | 感到 | 壓力 | 辦公室 | 最近
"""

p = prompt_ltm_summary("Claire", all_props)
# 期待模型輸出類似：
# "Claire 認識 David 已一段時間，對他帶有尊敬，但最近感受到工作上的壓力，兩人關係仍維持在專業的上下屬層面。"
```

---

### `prompt_update_relationship(character_name: str, target_name: str, initial: str, old_summary: str, today_narrative: str) -> str`

**功能**: 根據今天發生的事件，更新與特定角色的關係摘要（睡眠濃縮 Step 6）。若今天無重大互動，可直接回傳「無變化」。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 自己的名字 |
| `target_name` | `str` | 關係更新對象的名字 |
| `initial` | `str` | 兩人的初始關係設定（不會改變的基底） |
| `old_summary` | `str` | 昨天的關係摘要（空字串時 prompt 顯示「目前沒有先前的摘要紀錄」） |
| `today_narrative` | `str` | 今天的完整經歷敘述 |

**回傳**: `str` — prompt 字串；期待模型輸出一句話的新關係摘要，或「無變化」

**範例**:
```python
from config.prompts import prompt_update_relationship

p = prompt_update_relationship(
    character_name="Amy",
    target_name="David",
    initial="Amy 是咖啡師，David 是 Amy 咖啡店的固定常客，彼此認識約一年",
    old_summary="David 每天早上準時來買咖啡，Amy 對他有好感，關係輕鬆友好",
    today_narrative="今天 David 來買咖啡時看起來很疲憊，Amy 多問了幾句，David 透露最近公司有麻煩",
)
# 期待輸出：
# "Amy 與 David 的關係更加熟絡，Amy 開始關心 David 工作上的狀況，不只是普通客人關係。"
```

---

### `prompt_infer_emotion(character_name: str, today_narrative: str, previous_emotion: str) -> str`

**功能**: 根據今天的事件推斷角色的新情緒（睡眠濃縮 Step 7）。**注意**：此函式只在 `today_max_K >= EMOTION_RESET_THRESHOLD (0.5)` 時才被呼叫；平時直接回歸「平靜」不呼叫模型。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 角色名字 |
| `today_narrative` | `str` | 今天的完整經歷敘述 |
| `previous_emotion` | `str` | 昨天（上次）的情緒 |

**回傳**: `str` — prompt 字串；期待模型輸出 `VALID_EMOTIONS` 中的**單一情緒詞**（不帶任何其他文字），最多 10 tokens

**期待輸出**: `"疲憊"` 或 `"開心"` 或 `"緊張"` 等單詞

**範例**:
```python
from config.prompts import prompt_infer_emotion

# Emma 今天工作超時，獨自撐過晚餐高峰，但有遇到 Amy 聊天稍微緩和了情緒
p = prompt_infer_emotion(
    character_name="Emma",
    today_narrative="一個人撐過午晚兩個用餐高峰，廚房非常忙碌，身體很累。傍晚遇到 Amy 稍微聊天，心情稍好。22:00 回家，精疲力竭。",
    previous_emotion="平靜",
)
# 模型應輸出：「疲憊」
# （有強烈身體疲勞的記述，即使有短暫正面互動，整體仍偏疲憊）
```

---

### `prompt_generate_schedule(character_name, personality_short, habit, role, day, ltm_summary, today_important_events, yesterday_schedule_text, template_text) -> str`

**功能**: 睡眠濃縮的最後步驟（Step 8），根據角色個性、長期記憶、今日重要事件、昨天時間表與職業範本，生成隔天的時間表 JSON 陣列。

**參數**:
| 名稱 | 型別 | 說明 |
|------|------|------|
| `character_name` | `str` | 角色名字 |
| `personality_short` | `str` | 個性簡述（比 `prompt_deliberate` 中更簡短） |
| `habit` | `str` | 習慣描述 |
| `role` | `str` | 職業名稱，例如 `"咖啡師"` |
| `day` | `int` | 明天是第幾天（模擬日計數） |
| `ltm_summary` | `str` | LTM 整體摘要（空字串時顯示「尚無重要記憶」） |
| `today_important_events` | `str` | 今天的重要事件摘要（空字串時顯示「無特殊事件」） |
| `yesterday_schedule_text` | `str` | 昨天的時間表序列化文字（供模型維持作息連續性） |
| `template_text` | `str` | 職業範本序列化文字（供模型參考但可大幅修改） |

**回傳**: `str` — prompt 字串；期待模型回傳純 JSON 陣列（不帶任何其他文字）

**期待輸出格式**:
```json
[
  {"time": "06:00", "action": "起床", "location": "A家"},
  {"time": "07:00", "action": "前往", "location": "咖啡店"},
  {"time": "07:30", "action": "整理店面", "location": "咖啡店"},
  {"time": "08:30", "action": "賣咖啡", "location": "咖啡店"}
]
```

**範例**:
```python
from config.prompts import prompt_generate_schedule

p = prompt_generate_schedule(
    character_name="David",
    personality_short="有野心、工作狂、偶爾體貼下屬",
    habit="每天早上先去咖啡店買咖啡，再進辦公室",
    role="公司老闆",
    day=3,
    ltm_summary="David 與 Claire 合作密切，近期公司有重要案子壓力較大",
    today_important_events="與 Claire 開了重要會議，案子進展順利，心情不錯。傍晚在廣場散步時遇見 Ben",
    yesterday_schedule_text="08:00 起床 @ D家\n08:30 前往 @ 咖啡店\n09:00 前往 @ 辦公室\n...",
    template_text="08:00 起床 @ D家\n08:30 前往 @ 咖啡店\n...",
)
# 模型可能因為今天心情好、案子順利而安排提早一點回家
# 輸出 JSON 中可能出現「散步」或「買東西」等動態時段
```

---

## 模擬使用情境

### 情境一：Amy 面對突發事件的深思決策

```python
from config.prompts import prompt_deliberate

# 情境：Amy 在咖啡店工作中，David 突然面色凝重走進來
p = prompt_deliberate(
    character_name="Amy",
    personality="開朗、有責任感，善於察覺他人情緒",
    habit="店裡有客人時全神貫注，但遇到熟客會主動關心",
    emotion="平靜",
    relationship_text="David：每天早上的常客，已建立友好關係，Amy 知道他最近工作壓力大",
    stm_narrative="07:30 整理店面，08:30 開始服務客人，已接待數位客人",
    ltm_narrative="David 上次透露公司有麻煩，Amy 有些擔心他的狀況",
    scene="咖啡店，09:10，早上，David 推開門進來，臉色看起來不太好",
    co_located_text="David 剛進門",
    current_event="",
)
# 模型考量：Amy 的個性善於察覺情緒 + LTM 有David有壓力的記憶
# → 可能選擇「對話」並主動詢問 David 狀況，而非繼續「賣咖啡」
```

### 情境二：Ben 和 Claire 在廣場的對話往返

```python
from config.prompts import prompt_dialogue

# 第一輪：Claire 向 Ben 搭話
round_1_prompt = prompt_dialogue(
    character_name="Ben",
    personality="隨和、務實、不喜歡複雜的事",
    emotion="平靜",
    partner_name="Claire",
    relationship_text="認識的鄰居，偶爾在廣場碰面，關係普通",
    stm_narrative="下班後在廣場散步，心情放鬆",
    ltm_narrative="",
    scene="廣場，18:30，傍晚，涼風習習",
    recent_dialogue="",
    partner_message="Ben，你今天下班也很早嘛，超市今天沒什麼事嗎？",
)
# Ben 的回應可能是：「還好啦，今天客人不多，提早收工。你呢？」

# 第二輪（帶入對話歷史）
round_2_prompt = prompt_dialogue(
    character_name="Claire",
    personality="認真負責、有條理、容易緊張",
    emotion="疲憊",
    partner_name="Ben",
    relationship_text="認識的鄰居，偶爾在廣場碰面，關係普通",
    stm_narrative="加班到18:00，終於完成報告",
    ltm_narrative="",
    scene="廣場，18:35，傍晚",
    recent_dialogue="Claire：Ben，你今天下班也很早嘛，超市今天沒什麼事嗎？\nBen：還好啦，今天客人不多，提早收工。你呢？",
    partner_message="還好啦，今天客人不多，提早收工。你呢？",
)
```

### 情境三：Emma 睡覺時的完整濃縮流程

```python
from config.prompts import (
    prompt_extract_ham, prompt_select_ltm,
    prompt_ltm_summary, prompt_infer_emotion,
    prompt_generate_schedule,
)
from config.schedule_templates import get_template

emma_narrative = "午餐高峰忙碌，傍晚在廣場遇到 Amy 聊了一下，晚餐高峰一個人扛，精疲力竭回家"

# Step 2：抽取命題
p2 = prompt_extract_ham("Emma", emma_narrative)

# Step 3：假設 Step 2 輸出如下，進行篩選
extracted = "Emma | 遇見 | Amy | 廣場 | 傍晚\nEmma | 感到 | 疲憊 | 餐廳 | 晚上"
p3 = prompt_select_ltm("Emma", emma_narrative, extracted)

# Step 5：生成 LTM 摘要
p5 = prompt_ltm_summary("Emma", extracted)

# Step 7：推斷情緒（今天K值超過閾值）
p7 = prompt_infer_emotion("Emma", emma_narrative, "平靜")

# Step 8：生成明天時間表
template = get_template("廚師")
template_text = "\n".join(
    f"{s['time']} {s['action']} @ {s['location']}" for s in template
)
p8 = prompt_generate_schedule(
    character_name="Emma",
    personality_short="溫柔、有耐心，烹飪是她的熱情",
    habit="晚起晚睡，廚房是她的主場",
    role="廚師",
    day=2,
    ltm_summary="Emma 和 Amy 在廣場有過短暫友好的互動",
    today_important_events="午晚兩個高峰都獨自撐，身體很累，傍晚遇到 Amy 心情稍微好一點",
    yesterday_schedule_text="09:00 起床 @ E家\n10:30 前往 @ 餐廳\n...",
    template_text=template_text,
)
# 模型可能因為今天很累，在第 2 天的時間表中安排更多休息時間
```

---

## 注意事項

- `prompt_deliberate` 和 `prompt_dialogue` 中的選填參數（`co_located_text`、`current_event`、`relationship_text`、`ltm_narrative`）若為空字串，對應的 prompt 區塊會被完全省略（不插入空的區塊標題），讓 prompt 保持簡潔。
- `prompt_infer_emotion` 要求模型只輸出一個情緒詞，且對應的 `CONSOLIDATE_EMOTION_MAX_TOKENS=10`（在 `model_config.py` 中）。若模型輸出超過一個詞，`consolidation.py` 的解析邏輯需能容錯處理（取第一個詞或用正則提取 `VALID_EMOTIONS` 中的詞）。
- `prompt_generate_schedule` 期待模型回傳純 JSON 陣列，不帶任何說明文字。實際上模型有時會在 JSON 前後加上說明句，`scheduler.py` 的解析邏輯應使用正則或 `json.loads` 嘗試提取 `[...]` 區塊，而非假設整個輸出都是 JSON。
- HAM 格式（`主詞 | 關係 | 受詞 | 地點 | 時間`）使用全形空格和管道符，解析時應 `strip()` 每個欄位以去除多餘空白。
- `prompt_update_relationship` 中若 `old_summary` 為空字串，prompt 會顯示「目前沒有先前的摘要紀錄」而非插入空行，這是刻意的行為——避免讓模型對空字串產生困惑。
- 所有 prompt 函式都是純函式（不含副作用），可安全地在測試中直接呼叫並觀察輸出字串，無需 mock 任何外部依賴。
