# world_config — 全域常數的單一來源

> **路徑**: `config/world_config.py`  
> **職責**: 集中管理所有模擬參數，提供全域常數唯一來源

---

## 功能概覽

`world_config.py` 是整個 AI-Town 專案的參數中樞。所有涉及時間、角色、記憶、情緒、Markov 決策、對話、中斷、日誌的數值，都在這一個檔案中定義。其他模組需要任何設定值時，統一從這裡 import，不在各自檔案中硬編碼數字。

這樣的設計讓整個系統的行為調整集中在單一位置。例如想讓記憶保留更久，只需修改 `LTM_FORGET_THRESHOLD`；想讓一天多跑幾個 tick，只需改 `MAX_TICKS_PER_DAY`，而不必去翻找分散在各處的魔術數字。

除了純數值常數外，此模組也定義了兩個核心映射表：`CHARACTER_NAMES`（代號 → 名字）與 `CHARACTER_CODES`（名字 → 代號），以及 `INTERRUPT_LOCK_LEVELS` 這張複雜的行動中斷優先級表。這些結構性常數與模擬邏輯深度耦合，放在此模組可確保所有使用方看到的是同一份定義。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `os` | 計算 `BASE_DIR`、`AI_DATA_DIR`、`LOG_DIR`、`REPORT_DIR` 等路徑常數 |
| 被依賴 | `config/prompts.py` | import `VALID_EMOTIONS` 用於 prompt 組裝 |
| 被依賴 | `config/action_list.py` | import `INTERRUPT_LOCK_LEVELS`、`SLEEP_ACTION`、`WAKE_ACTION` |
| 被依賴 | `core/consolidation.py` | import 記憶相關常數（STM_KEEP_AFTER_CONS、LTM_DECAY_RATE 等）|
| 被依賴 | `agent/markov_engine.py` | import Markov 三來源權重、情緒閾值 |
| 被依賴 | `model/prompt_builder.py` | import 角色名字映射、世界時間設定 |
| 被依賴 | `simulate.py` | import `SIMULATION_DEFAULT_DAYS`、`SIMULATION_REPORT_PATTERN` |

---

## 主要常數 / 資料結構

### `BASE_DIR`
**型別**: `str`  
**預設值**: 自動計算（`world_config.py` 所在目錄的上一層）  
**說明**: 整個專案的根目錄絕對路徑，用於建構所有其他路徑常數，確保無論從哪個位置執行腳本都能正確定位檔案。

---

### `AI_DATA_DIR`
**型別**: `str`  
**預設值**: `{BASE_DIR}/AI_Data`  
**說明**: 存放各角色 JSON 資料檔（記憶、個性、時間表）的目錄。所有角色資料的讀寫都以此為根路徑。

---

### `LOG_DIR`
**型別**: `str`  
**預設值**: `{BASE_DIR}/logs`  
**說明**: 日誌輸出目錄，DEBUG 級別的完整記錄寫入此處。

---

### `REPORT_DIR`
**型別**: `str`  
**預設值**: `{BASE_DIR}/reports`  
**說明**: `observe/` 模組產生的 HTML 觀察報告輸出目錄。

---

### `CHARACTER_NAMES`
**型別**: `dict[str, str]`  
**預設值**: `{"A": "Amy", "B": "Ben", "C": "Claire", "D": "David", "E": "Emma"}`  
**說明**: 角色代號到名字的正向對應表。程式內部全程使用代號（A~E）處理邏輯，只有在組 prompt、產生報告等需要呈現給人看的時候，才透過此表轉換為真實名字。新增角色只需在此加一行並在 `AI_Data/` 放入對應 JSON。

---

### `CHARACTER_CODES`
**型別**: `dict[str, str]`  
**預設值**: `{"Amy": "A", "Ben": "B", "Claire": "C", "David": "D", "Emma": "E"}`  
**說明**: `CHARACTER_NAMES` 的反查表，由 dict comprehension 自動產生。在需要從名字回查代號時使用（例如解析模型輸出中的人名）。

---

### `DAY_START_HOUR`
**型別**: `int`  
**預設值**: `6`  
**說明**: 模擬世界一天的時鐘起點（06:00）。搭配 `MAX_TICKS_PER_DAY` 與 `MINUTES_PER_TICK` 決定每天的完整時間範圍。

---

### `DAY_END_HOUR`
**型別**: `int`  
**預設值**: `2`  
**說明**: 一天最晚的睡覺時間（凌晨 02:00）。各角色的實際睡覺時間由其 `sleep_pattern` 控制，但不得晚於此值。

---

### `MINUTES_PER_TICK`
**型別**: `int`  
**預設值**: `60`  
**說明**: 每個模擬 tick 代表的現實時間（60 分鐘）。改小此值可使模擬更精細，但會增加模型呼叫次數與運算成本。

---

### `MAX_TICKS_PER_DAY`
**型別**: `int`  
**預設值**: `20`  
**說明**: 每天的最大 tick 數（06:00 到 02:00 共 20 小時 = 20 個 tick）。超過此數量後強制進入睡眠階段。

---

### `STM_SAFETY_LIMIT`
**型別**: `int`  
**預設值**: `50`  
**說明**: 短期記憶（STM）筆數的安全上限。超過此值時觸發中途濃縮（mid-day consolidation），將部分 STM 轉為長期記憶，防止記憶體無限增長。

---

### `STM_KEEP_AFTER_CONS`
**型別**: `int`  
**預設值**: `5`  
**說明**: 睡眠期間進行 STM 濃縮後，保留最近幾筆 STM 記錄。這幾筆記錄作為「近期緩衝」，讓角色次日醒來時有最新的脈絡可參考。

---

### `LTM_DECAY_RATE`
**型別**: `float`  
**預設值**: `0.05`  
**說明**: 長期記憶（LTM）命題每天的衰減量。`access_count` 越高（越常被提取）的命題衰減越慢，模擬「常用知識不易遺忘」的認知特性。

---

### `LTM_FORGET_THRESHOLD`
**型別**: `float`  
**預設值**: `0.2`  
**說明**: LTM 命題 `strength` 低於此值時，在每日 prune 步驟中被刪除。調高此值會讓記憶遺忘更快；調低則保留更久。

---

### `LTM_FALLBACK_COUNT`
**型別**: `int`  
**預設值**: `3`  
**說明**: 模型解析 LTM 失敗時，fallback 取前幾筆命題作為替代。確保即使解析出錯，系統仍能繼續運行。

---

### `HAM_TRAVERSE_MAX_HOPS`
**型別**: `int`  
**預設值**: `2`  
**說明**: HAM 圖譜擴散激活時的最大跳數。根據 Anderson (1983) 的擴散激活理論，活化值隨距離指數衰減；超過 2 跳後活化值通常已低於提取閾值，繼續遍歷只會增加計算量而無實質貢獻。

---

### `HAM_ACTIVATION_DECAY`
**型別**: `float`  
**預設值**: `0.4`  
**說明**: HAM 圖譜每跳的活化衰減係數。1 跳後保留 40%（0.4），2 跳後保留 16%（0.4²=0.16）。與 `HAM_RETRIEVE_THRESHOLD=0.3` 搭配，使得超過 2 跳的節點幾乎無法被提取。

---

### `HAM_RETRIEVE_THRESHOLD`
**型別**: `float`  
**預設值**: `0.3`  
**說明**: HAM 擴散激活的提取門檻。活化值低於 0.3 的節點不納入記憶提取結果，減少雜訊注入 prompt。

---

### `VALID_EMOTIONS`
**型別**: `list[str]`  
**預設值**: `["平靜", "開心", "緊張", "不安", "難過", "興奮", "困惑", "疲憊"]`  
**說明**: 角色可持有的情緒詞彙列表。每天睡眠時預設回歸「平靜」；只有當天的困惑度 K 超過 `EMOTION_RESET_THRESHOLD` 時，才呼叫模型重新推斷情緒。

---

### `EMOTION_RESET_THRESHOLD`
**型別**: `float`  
**預設值**: `0.5`  
**說明**: 觸發情緒更新所需的最低困惑度 K 值。低於此值時情緒直接回歸「平靜」，不浪費模型推論資源。

---

### `MARKOV_WEIGHTS_NORMAL`
**型別**: `dict[str, float]`  
**預設值**: `{"alpha": 0.4, "beta": 0.3, "gamma": 0.3}`  
**說明**: 平常狀態下 Markov 三來源的加權比例。`alpha`（時間表）佔最高比重，確保角色大致遵守日程；`beta`（行為慣性）與 `gamma`（情境觸發）各佔 30%，提供彈性與環境響應能力。

---

### `MARKOV_WEIGHTS_EVENT`
**型別**: `dict[str, float]`  
**預設值**: `{"alpha": 0.1, "beta": 0.3, "gamma": 0.6}`  
**說明**: 重大事件（K ≥ 0.6）時的 Markov 加權。情境觸發權重大幅提升至 60%，時間表降至 10%，但未歸零——模擬「地震時有人繼續工作、有人逃跑」的個體差異。

---

### `MAJOR_EVENT_K_THRESHOLD`
**型別**: `float`  
**預設值**: `0.6`  
**說明**: 切換 Markov 加權模式的 K 值門檻。困惑度超過 0.6 時從 `MARKOV_WEIGHTS_NORMAL` 切換到 `MARKOV_WEIGHTS_EVENT`。

---

### `DIALOGUE_MAX_TURNS`
**型別**: `int`  
**預設值**: `10`  
**說明**: 一次對話的最多來回輪數（10 輪 = 雙方各說最多 10 句，共 20 句）。超過後強制結束對話，防止對話無限循環。

---

### `DIALOGUE_BASE_ACCEPT`
**型別**: `float`  
**預設值**: `0.5`  
**說明**: 對話接受的基礎機率，在計算各項加減分之前的起點。

---

### `DIALOGUE_RELATION_BONUS`
**型別**: `float`  
**預設值**: `0.3`  
**說明**: 與對方關係正向時的接受率加成。

---

### `DIALOGUE_LEISURE_BONUS`
**型別**: `float`  
**預設值**: `0.2`  
**說明**: 自己目前在進行休閒活動時，接受對話邀請的加成。

---

### `DIALOGUE_WORK_PENALTY`
**型別**: `float`  
**預設值**: `-0.3`  
**說明**: 自己目前在工作時，接受對話邀請的懲罰。工作中的角色較不願意被打擾。

---

### `DIALOGUE_EMOTION_PENALTY`
**型別**: `float`  
**預設值**: `-0.2`  
**說明**: 情緒非「平靜」時的接受率懲罰。負面情緒下角色較不願意互動。

---

### `DIALOGUE_ACCEPT_MIN` / `DIALOGUE_ACCEPT_MAX`
**型別**: `float`  
**預設值**: `0.05` / `0.95`  
**說明**: 對話接受率的下限與上限。保留隨機性：即使關係最差也有 5% 機會接受；即使條件最好也有 5% 機會拒絕。

---

### `INTERRUPT_LOCK_LEVELS`
**型別**: `dict[str, int]`  
**預設值**: 見下方表格  
**說明**: 各行動的中斷鎖等級。決定行動是否可被突發事件打斷。

| 等級 | 意義 | 行動 |
|------|------|------|
| 2 | 不可中斷 | 對話、睡覺 |
| 1 | 重要事件可中斷 | 賣咖啡、煮飯、服務客人、收銀、補貨、工作、備料、整理店面、打烊 |
| 0 | 容易中斷 | 前往、回家、散步、休息、滑手機、吃飯、買東西、整理家裡、運動、起床 |

---

### `SLEEP_ACTION` / `WAKE_ACTION`
**型別**: `str`  
**預設值**: `"睡覺"` / `"起床"`  
**說明**: 特殊行動的字串常數，供其他模組做字串比對。避免各處硬編碼中文字串導致維護困難。

---

### `SIMULATION_DEFAULT_DAYS`
**型別**: `int`  
**預設值**: `3`  
**說明**: `simulate.py` 的預設模擬天數，未指定命令列參數時使用此值。

---

### `SIMULATION_REPORT_PATTERN`
**型別**: `str`  
**預設值**: `"simulation_{timestamp}.html"`  
**說明**: 報告檔案的命名格式，`{timestamp}` 由 `observe/` 模組在生成時替換為實際時間戳。

---

### `LOG_LEVEL_CONSOLE` / `LOG_LEVEL_FILE`
**型別**: `str`  
**預設值**: `"INFO"` / `"DEBUG"`  
**說明**: 螢幕輸出與日誌檔案的最低記錄級別。開發時可改 `LOG_LEVEL_CONSOLE = "DEBUG"` 取得詳細輸出。

---

## 主要函式

此模組不定義函式，僅包含常數定義與 `CHARACTER_CODES` 的 dict comprehension 自動建構。

---

## 模擬使用情境

### 情境一：Amy 一天的時間範圍計算

```python
from config.world_config import DAY_START_HOUR, MINUTES_PER_TICK, MAX_TICKS_PER_DAY

# 計算 Amy 一天 20 個 tick 對應的時鐘時間
for tick in range(MAX_TICKS_PER_DAY):
    hour = DAY_START_HOUR + tick * (MINUTES_PER_TICK // 60)
    print(f"Tick {tick:02d} → {hour:02d}:00")
# Tick 00 → 06:00
# Tick 01 → 07:00
# ...
# Tick 19 → 01:00（凌晨）
```

### 情境二：David 觸發重大事件後的 Markov 切換

```python
from config.world_config import (
    MAJOR_EVENT_K_THRESHOLD,
    MARKOV_WEIGHTS_NORMAL,
    MARKOV_WEIGHTS_EVENT,
)

# David 目擊街道上的打架事件，K 值飆升至 0.75
david_K = 0.75

if david_K >= MAJOR_EVENT_K_THRESHOLD:
    weights = MARKOV_WEIGHTS_EVENT
    print(f"切換到重大事件權重：alpha={weights['alpha']}, gamma={weights['gamma']}")
    # 切換到重大事件權重：alpha=0.1, gamma=0.6
else:
    weights = MARKOV_WEIGHTS_NORMAL

# 情境觸發（gamma）從 0.3 上升到 0.6，時間表（alpha）從 0.4 降至 0.1
# David 可能放棄原本的辦公室工作時段，轉為「前往」或「散步」
```

### 情境三：Claire 的對話接受率計算

```python
from config.world_config import (
    DIALOGUE_BASE_ACCEPT,
    DIALOGUE_RELATION_BONUS,
    DIALOGUE_WORK_PENALTY,
    DIALOGUE_ACCEPT_MIN,
    DIALOGUE_ACCEPT_MAX,
)

# Claire 正在工作，Ben 向她搭話，兩人關係正向
accept_rate = DIALOGUE_BASE_ACCEPT          # 0.5
accept_rate += DIALOGUE_RELATION_BONUS     # +0.3 → 0.8
accept_rate += DIALOGUE_WORK_PENALTY       # -0.3 → 0.5
accept_rate = max(DIALOGUE_ACCEPT_MIN, min(DIALOGUE_ACCEPT_MAX, accept_rate))
print(f"Claire 接受對話的機率：{accept_rate:.2f}")
# Claire 接受對話的機率：0.50
```

---

## 注意事項

- `CHARACTER_CODES` 由 `CHARACTER_NAMES` 自動反查建立，修改 `CHARACTER_NAMES` 後 `CHARACTER_CODES` 會同步更新，不需手動維護兩份表。
- `MARKOV_WEIGHTS_NORMAL` 與 `MARKOV_WEIGHTS_EVENT` 中三個權重相加分別為 1.0（1.0 / 1.0），若手動調整請確保合計仍為 1.0，否則機率正規化結果會偏離預期。
- `DAY_END_HOUR=2` 跨越午夜，時鐘計算需注意 `hour % 24`，24 點之後的時間以凌晨表示。
- `LTM_DECAY_RATE=0.05` 是每天的衰減量，代表一個 `strength=1.0` 的記憶在無任何存取的情況下，約 16 天後降至 `LTM_FORGET_THRESHOLD=0.2` 而被刪除。
- 所有路徑常數（`BASE_DIR`、`AI_DATA_DIR` 等）在模組 import 時立即計算，可直接作為字串使用，無需再呼叫任何函式。
