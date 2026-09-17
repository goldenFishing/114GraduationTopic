# AI-Town 重構架構規格書 v2.0

> 本文件為 AI-Town 專案重構的完整設計規格。所有重寫工作以此為依據。
> 文件版本：2.0
> 最後更新：架構討論定稿
> 認知模型基礎：雙歷程理論（Kahneman）+ HAM（Anderson & Bower）+ 擴散激活（ACT-R）

---

## 目錄

1. [系統總覽](#一系統總覽)
2. [認知科學理論基礎](#二認知科學理論基礎)
3. [核心設計理念](#三核心設計理念)
4. [整體架構與資料流](#四整體架構與資料流)
5. [檔案結構](#五檔案結構)
6. [模組詳細規格](#六模組詳細規格)
7. [核心資料結構](#七核心資料結構)
8. [設定參數總表](#八設定參數總表)
9. [關鍵流程圖](#九關鍵流程圖)
10. [輸入輸出介面契約](#十輸入輸出介面契約)
11. [與舊架構對應表](#十一與舊架構對應表)
12. [開發路線圖](#十二開發路線圖)
13. [未來擴充建議](#十三未來擴充建議)

---

# 一、系統總覽

## 1.1 專案定位

AI-Town 是一個多角色自主生活模擬系統，每個角色由 AI 模型驅動，模擬真實人類的：
- 雙系統思考（直覺 vs 深思）
- 情節 / 語意記憶分層
- 感知驅動的注意力中斷
- 動態作息與時間規劃
- 情緒影響的決策偏移

## 1.2 核心目標

```
1. 貼近真實人類認知模型（不只是 LLM 聊天機器人）
2. 硬體效能可控（不是每個決策都打模型）
3. 模組化清晰（每個檔案輸入輸出明確）
4. 可觀察可除錯（記憶與決策過程視覺化）
5. 可擴充（角色數量、地點、行動皆可增加）
```

## 1.3 系統規模

| 項目 | 規模 |
|------|------|
| 角色數量 | 5（Amy, Ben, Claire, David, Emma），可擴充 |
| 地點數量 | 15 |
| 行動類型 | 21 |
| 模擬時間 | 1 天 = 20 ticks（06:00 ~ 02:00） |
| 模型 | Phi-3.5-Vision-Instruct（local） |
| 輔助模型 | YOLOv8n（視覺感知） |

---

# 二、認知科學理論基礎

每個設計決策都對應一篇研究，以下是主要文獻與設計對應：

## 2.1 雙歷程理論（Dual-Process Theory）
**Kahneman (2011) Thinking, Fast and Slow / Evans & Stanovich (2013)**

人類決策分兩個系統：
- **System 1（直覺）**：快速、自動、無意識，佔 ~85-95% 日常決策
- **System 2（深思）**：緩慢、刻意、消耗認知資源

**對應實作：**
- Markov 路徑 = System 1（純統計，不呼叫模型）
- Deliberate 路徑 = System 2（呼叫 Phi-3.5）
- 困惑度 C 是兩者切換器（ACC 衝突偵測類比）

## 2.2 工作記憶模型
**Baddeley (2000) The Episodic Buffer; Cowan (2001) The Magical Number 4**

工作記憶有限容量（~4 個 chunk），但情節緩衝可整合一天經驗。

**對應實作：**
- STM 不限筆數（情節緩衝），睡眠時做歸納
- 安全閥 50 筆（防止記憶體爆炸）

## 2.3 情節記憶 vs 語意記憶
**Tulving (1972, 1985) Episodic and Semantic Memory**

- **情節記憶**：親身經歷，敘述形式編碼（「我今天看到 Ben 走進咖啡廳」）
- **語意記憶**：抽象事實，命題形式儲存（「Ben 是超市員工」）

**對應實作：**
- STM = 情節記憶（敘述化儲存）
- LTM = 語意記憶（HAM 5 元組）
- 睡眠時 STM → LTM 是「敘述 → 命題」的轉換

## 2.4 HAM 人類聯想記憶模型
**Anderson & Bower (1973) Human Associative Memory**

語意記憶以「主詞-關係-客詞」命題網絡儲存，命題之間透過共享節點關聯。

**對應實作：**
- LTM 用 5 元組：(subject, relation, object, location, time)
- 共享節點自動建立關聯（Amy → 認識 → Ben；Ben → 工作 → 超市）

## 2.5 擴散激活理論
**Anderson (1983, 1996) Spreading Activation; Collins & Loftus (1975)**

記憶提取從查詢點向相連節點擴散，活化值隨距離指數衰減：A(d) = A(0) × e^(-d × decay)

**實證距離衰減：**
- 1 跳：~80% 活化
- 2 跳：~40% 活化
- 3+ 跳：< 15%（通常低於提取閾值）

**對應實作：**
- HAM 圖譜遍歷最大 2 跳
- 1 跳活化 1.0、2 跳活化 0.4
- 活化 < 0.3 不取

## 2.6 睡眠記憶鞏固
**Diekelmann & Born (2010) The memory function of sleep**

睡眠時海馬迴將當天情節記憶轉移到新皮質長期儲存，並進行模式抽取與冗餘剔除。

**對應實作：**
- 角色入睡觸發 consolidation
- STM 敘述 → 模型抽 HAM → 寫入 LTM
- 衰減 + 修剪

## 2.7 情緒回歸基線
**Frijda (1988) Laws of Emotion; Diener (2000) Subjective Well-being**

情緒會自然衰減回歸基線，重大事件造成偏移後逐漸復原。

**對應實作：**
- 每日睡眠時情緒重置為「平靜」
- 當日重大事件（K ≥ 0.5）才更新情緒
- 避免角色情緒集體崩壞

## 2.8 預測編碼與注意力
**Friston (2010) Predictive Coding; Itti & Koch (2001) Saliency Map**

大腦持續預測環境，只有預測誤差才觸發注意力與深層處理。

**對應實作：**
- YOLO 偵測場景變化作為「預測誤差」訊號
- 變化 → 提升困惑度 → 可能觸發深思
- 無變化 → 維持當前行動

## 2.9 行為慣性與功能可供性
**Wood & Neal (2007) Habit Formation; Gibson (1979) Affordance Theory**

人類 43% 行為是無意識習慣；環境本身會「邀請」特定行動（看到杯子想喝）。

**對應實作：**
- Markov 三來源加權：時間表（α）+ 慣性（β）+ 情境（γ）
- 場景關鍵字觸發行動機率提升

---

# 三、核心設計理念

## 3.1 雙路徑決策（Type 1 / Type 2 思考）

```
每個 tick，每個角色的決策流程：

  感知輸入（場景 + YOLO + 對話）
        ↓
  計算困惑度 C = w1·U + w2·K + w3·S
        ↓
  ┌───────────────────────────┐
  │  C < threshold（情況熟悉）  │  → Markov 三來源加權 → 選行動
  │  C ≥ threshold（情況複雜）  │  → Phi-3.5 深思推理 → 選行動
  │  K ≥ 0.5（情緒/邏輯衝突）   │  → 強制深思（override）
  └───────────────────────────┘
        ↓
  執行行動（一般 / 對話 / 移動）
        ↓
  寫入 STM（敘述化）
```

## 3.2 記憶分層（情節 vs 語意）

```
即時感知 → STM（情節）→ 睡眠濃縮 → LTM（語意命題）
                    ↑
              敘述形式儲存
              不含 HAM
              不含決策元數據
              
LTM 使用 HAM 圖譜：
  節點：人 / 物 / 地
  連線：關係（subject-relation-object）
  提取：擴散激活（最大 2 跳）
```

## 3.3 處理元數據與記憶分離

```
STM = 角色「會記得的事」（敘述、感受、行動）
process_log = 系統「運作的方式」（困惑度數值、機率分布、模型呼叫）

兩者分離：
  process_log 給觀察工具用
  STM 進入 prompt 時不含 process_log
  Amy 不會記得「我今天因為 K=0.42 走了 deliberate」
  Amy 會記得「我看到 Ben 進來，跟他打招呼」
```

## 3.4 感知中斷機制

```
YOLO 持續偵測（背景 async 迴圈）
  ↓
偵測到變化 → 寫入該角色的 interrupt_queue
  ↓
角色執行行動時定期檢查 queue
  ↓
評估事件強度 vs 當前行動鎖等級
  ↓
可中斷 → Markov 重算 → 可能改變行動
不可中斷 → 繼續原行動
```

## 3.5 自主作息

```
不再強制「全員 06:00 起 / 凌晨 04:00 強制睡」
改為：
  每個角色有 sleep_pattern（預設值寫在 JSON）
  時間表由模型每天睡前生成（含起床/睡覺時段）
  時間到 → 模型快速確認 → 起床或睡覺
  最晚 force_wake / force_sleep 時間強制執行
```

## 3.6 平行決策

```
同 tick 內所有角色「邏輯上同時行動」
實作：
  收集所有需要模型推論的 prompt
  Batch 推論一次跑完
  顯存不足時自動切換 sequential
  
對話特殊處理：
  發起 → 接受/拒絕（規則）→ 對話循環（同 tick 內）
  雙方鎖定，避免對方走掉
```

---

# 四、整體架構與資料流

## 4.1 模組分層

```
┌─────────────────────────────────────────────────┐
│ 進入層       main.py   simulate.py              │
├─────────────────────────────────────────────────┤
│ 協調層       agent/manager.py                   │
├─────────────────────────────────────────────────┤
│ 推論層       agent/agent.py                     │
│              agent/scheduler.py                 │
│              agent/interrupt.py                 │
├─────────────────────────────────────────────────┤
│ 認知層       core/character.py                  │
│              core/memory_stm.py                 │
│              core/memory_ltm.py                 │
│              core/memory_graph.py               │
│              core/markov_engine.py              │
│              core/confusion.py                  │
│              core/emotion.py                    │
│              core/consolidation.py              │
├─────────────────────────────────────────────────┤
│ 模型層       model/model_loader.py              │
│              model/vision_encoder.py            │
│              model/text_encoder.py              │
│              model/fusion_decoder.py            │
│              model/prompt_builder.py            │
│              model/output_parser.py             │
│              model/batch_inference.py           │
├─────────────────────────────────────────────────┤
│ 感知層 *     perception/yolo_handler.py         │
│              perception/event_trigger.py        │
├─────────────────────────────────────────────────┤
│ 通訊層 *     server/ws_server.py                │
├─────────────────────────────────────────────────┤
│ 觀察層       observe/memory_viewer.py           │
│              observe/dashboard_html.py          │
│              observe/dialogue_log.py            │
├─────────────────────────────────────────────────┤
│ 世界層       world/world_clock.py               │
├─────────────────────────────────────────────────┤
│ 設定層       config/world_config.py             │
│              config/action_list.py              │
│              config/triggers.py                 │
│              config/prompts.py                  │
│              config/schedule_templates.py       │
│              config/model_config.py             │
├─────────────────────────────────────────────────┤
│ 工具層       utils/file_io.py                   │
│              utils/logger.py                    │
└─────────────────────────────────────────────────┘

* 標記層在最終階段才實作，前期維持 stub interface
```

## 4.2 主要資料流

### 4.2.1 一個 Tick 的完整流程

```
[Tick T 開始]
  ↓
[時鐘檢查]
  ├─ 各角色是否到 force_wake_time？→ 強制起床
  ├─ 各角色是否到 force_sleep_time？→ 強制入睡
  └─ 收集本 tick 應參與決策的角色（未睡）
  ↓
[感知層收集]
  ├─ 從 YOLO interrupt_queue 取出累積事件（YOLO 已在背景跑）
  ├─ 場景描述更新
  └─ 對話輸入收集
  ↓
[中斷處理]
  對於正在執行多 tick 行動的角色（如「前往咖啡廳」需 3 ticks）：
    檢查 interrupt_queue → 評估強度 vs 行動鎖
    可中斷 → Markov 重算 → 可能改變行動
  ↓
[Phase 1: 執行階段]
  各角色執行上一 tick 決策的 pending_action
    對話行動 → 進入對話循環（雙方多輪）
    一般行動 → 更新位置、狀態
    多 tick 行動 → 推進進度
  寫入 STM（記錄這 tick 做了什麼）
  ↓
[Phase 2: 決策階段]
  ├─ 收集所有角色的決策 prompt（如需深思）
  ├─ Batch 推論 / Sequential 推論（依 GPU）
  ├─ 解析輸出 → 設定 pending_action（給下 tick 用）
  └─ 寫入 STM（記錄這 tick 想了什麼）
  ↓
[STM 安全閥檢查]
  任一角色 STM > 50 → 觸發中途濃縮
  ↓
[寫入 process_log]（給觀察工具用）
  ↓
[時鐘推進 → Tick T+1]
```

### 4.2.2 睡眠濃縮資料流

```
角色決策「睡覺」或時間到 force_sleep_time
  ↓
[Step 1] 取出當天所有 STM（敘述形式）
  ↓
[Step 2] 模型讀 STM → 抽 HAM 5 元組
         （這是新流程：STM 不預存 HAM）
  ↓
[Step 3] 模型篩選重要 HAM（最多 N 筆）
  ↓
[Step 4] 寫入 LTM
  ↓
[Step 5] 模型生成新的 LTM 摘要（1-2 句）
  ↓
[Step 6] 模型更新關係摘要（與當天有任何相關的角色）
  ↓
[Step 7] 模型推斷新情緒（重大事件後才更新，否則「平靜」）
  ↓
[Step 8] 模型生成隔天時間表（範本 + LTM + 個性）
  ↓
[Step 9] 規則檢查時間表（必有起床/睡覺/工作時段）
  ↓
[Step 10] LTM 衰減 + 修剪
  ↓
[Step 11] STM 縮減（保留摘要當一筆 STM，刪除最舊事件）
  ↓
[Step 12] 寫入 JSON 檔
  ↓
角色 day += 1
```

### 4.2.3 對話發起資料流

```
A 角色決策結果是「對話:Amy」
  ↓
[檢查同地點]
  Amy 不在同地點 → 改為「前往 Amy 所在處」（找人）
  Amy 在同地點   → 進入發起流程
  ↓
[A 鎖定 + Amy 鎖定]（同 tick 不可被中斷）
  ↓
[Amy 接受判斷]（純規則，不呼叫模型）
  基礎 50%
  + 關係正向 +30%
  + Amy 在休閒中 +20%
  - Amy 在工作中 -30%
  - Amy 情緒非平靜 -20%
  → 隨機決定接受 / 拒絕
  ↓
[拒絕分支]
  Amy 簡短回應（從拒絕模板隨機）
  A 改回原本要做的事
  雙方都寫 STM（影響關係）
  ↓
[接受分支]
  進入對話循環（最多 10 來回）
    每輪：
      A 說 → Phi-3.5 生成回應 → STM
      Amy 說 → Phi-3.5 生成回應 → STM
      任一方決策不再對話 → 結束
  ↓
[對話結束]
  雙方解鎖
  寫入完整對話到 STM
  下一 tick 各自決策後續行動
```

---

# 五、檔案結構

## 5.1 新檔案樹

```
ai-town/
│
├── ARCHITECTURE.md                    本規格書
├── README.md                          專案說明（後期更新）
├── requirements.txt
│
├── main.py                            UE 對接進入點（最後改）
├── simulate.py                        離線模擬進入點
│
├── config/
│   ├── world_config.py                全域設定
│   ├── action_list.py                 行動與地點清單
│   ├── triggers.py                    [新] 行動觸發關鍵字
│   ├── prompts.py                     Prompt 模板
│   ├── schedule_templates.py          [新] 時間表範本
│   └── model_config.py                模型設定（修正 token 預算）
│
├── core/
│   ├── character.py                   角色狀態
│   ├── memory_stm.py                  [改名] 短期記憶（敘述化）
│   ├── memory_ltm.py                  [改名] 長期記憶（HAM）
│   ├── memory_graph.py                [新] HAM 圖譜遍歷
│   ├── markov_engine.py               [改寫] 三來源加權 Markov
│   ├── confusion.py                   困惑度（情緒影響閾值）
│   ├── emotion.py                     [新] 情緒慣性與回歸
│   └── consolidation.py               [改寫] 睡眠濃縮 + 時間表生成
│
├── agent/
│   ├── agent.py                       單角色推論
│   ├── manager.py                     [改寫] 多角色協調 + Batch
│   ├── scheduler.py                   [新] 時間表生成器
│   └── interrupt.py                   [新] 中斷處理器
│
├── model/
│   ├── model_loader.py                Phi-3.5 載入
│   ├── vision_encoder.py              圖片處理
│   ├── text_encoder.py                文字處理
│   ├── fusion_decoder.py              融合推論
│   ├── prompt_builder.py              [改寫] Prompt 組裝
│   ├── output_parser.py               [改寫] block 格式解析
│   └── batch_inference.py             [新] Batch 推論工具
│
├── perception/                        [後期實作]
│   ├── yolo_handler.py                YOLO 偵測（保留現狀）
│   └── event_trigger.py               [新, 後期] 持續感知 + 中斷產生
│
├── server/                            [後期實作]
│   └── ws_server.py                   WebSocket（保留現狀）
│
├── observe/                           [新資料夾]
│   ├── dashboard_html.py              HTML 儀表板生成
│   ├── memory_viewer.py               LTM 圖譜視覺化
│   └── dialogue_log.py                對話記錄整理
│
├── world/
│   └── world_clock.py                 世界時鐘（小改）
│
├── utils/
│   ├── file_io.py                     檔案讀寫
│   └── logger.py                      日誌
│
├── AI_Data/                           角色 JSON
│   ├── A_init.json                    Amy
│   ├── B_init.json                    Ben
│   ├── C_init.json                    Claire
│   ├── D_init.json                    David
│   └── E_init.json                    Emma
│
├── logs/                              執行日誌
│
└── reports/                           [新] 模擬報告
    └── *.html                         HTML 儀表板輸出
```

## 5.2 要刪除的舊檔

```
✗ test.ipynb
✗ ai_data.zip
✗ Project_description.docx
✗ Project_description.md（被 ARCHITECTURE.md 取代）
✗ utils/test_reset.py
✗ logs/2026*.log（舊日誌）
✗ sim_*.log（舊模擬日誌）
✗ simulate_report.html（會重新生成到 reports/）
✗ 全部 __pycache__/
```

---

# 六、模組詳細規格

> 每個檔案的規格包含：用途、主要類別與函式、輸入輸出、依賴關係、認知對應

## 6.1 設定層（config/）

### 6.1.1 `config/world_config.py`

**用途：** 全域常數，所有其他檔案的設定來源。

**主要常數：**

```python
# 路徑
BASE_DIR, AI_DATA_DIR, LOG_DIR, REPORT_DIR

# 角色對應表
CHARACTER_NAMES = {"A":"Amy", "B":"Ben", ...}
CHARACTER_CODES = {"Amy":"A", ...}

# 時間
DAY_START_HOUR        = 6      # 一天最早起床時間
DAY_END_HOUR          = 2      # 一天最晚睡覺時間（凌晨 2 點）
MINUTES_PER_TICK      = 60     # 每 tick 60 分鐘
MAX_TICKS_PER_DAY     = 20     # 06:00 ~ 02:00 共 20 ticks

# 記憶
STM_SAFETY_LIMIT      = 50     # 超過觸發中途濃縮
STM_KEEP_AFTER_CONS   = 5      # 濃縮後保留最近幾筆
LTM_DECAY_RATE        = 0.05
LTM_FORGET_THRESHOLD  = 0.2

# 圖譜
HAM_TRAVERSE_MAX_HOPS = 2
HAM_ACTIVATION_DECAY  = 0.4    # 1 跳→2 跳的衰減
HAM_RETRIEVE_THRESHOLD = 0.3

# 對話
DIALOGUE_MAX_TURNS    = 10     # 來回 10 次（20 句話）

# 情緒
VALID_EMOTIONS = ["平靜","開心","緊張","不安","難過","興奮","困惑","疲憊"]
EMOTION_RESET_THRESHOLD = 0.5  # K 超過此值才更新情緒

# Markov
MARKOV_WEIGHTS_NORMAL = {"alpha": 0.4, "beta": 0.3, "gamma": 0.3}
MARKOV_WEIGHTS_EVENT  = {"alpha": 0.1, "beta": 0.3, "gamma": 0.6}
MAJOR_EVENT_K_THRESHOLD = 0.6

# 中斷
INTERRUPT_LOCK_LEVELS = {
    "對話": 2, "睡覺": 2,
    "工作": 1, "煮飯": 1, "賣咖啡": 1, "服務客人": 1,
    "前往": 0, "散步": 0, "滑手機": 0, "休息": 0
}

# 行動
SLEEP_ACTION = "睡覺"
WAKE_ACTION  = "起床"
```

**輸入：** 無
**輸出：** 模組級常數

---

### 6.1.2 `config/action_list.py`

**用途：** 角色可執行的所有行動與可前往的地點。

**主要常數：**
```python
VALID_ACTIONS = [21 個行動]    # 不變
VALID_LOCATIONS = [15 個地點]  # 不變
ACTION_SEPARATOR = ":"
```

**新增：**
```python
# 行動類別（給中斷分級用）
ACTION_CATEGORIES = {
    "movement":   ["前往", "回家"],
    "work":       ["賣咖啡","煮飯","收銀","補貨","工作","服務客人","備料","整理店面","打烊"],
    "social":     ["對話"],
    "rest":       ["休息","散步","滑手機","運動"],
    "daily":      ["吃飯","買東西","整理家裡"],
    "sleep":      ["睡覺"]
}
```

---

### 6.1.3 `config/triggers.py` [新檔]

**用途：** 行動觸發關鍵字字典（情境 → 行動機率加成）。

**主要常數：**
```python
# Markov 情境來源（γ）的核心資料
ACTION_KEYWORD_BOOST = {
    "對話":       ["人", "Ben", "Amy", "Claire", "David", "Emma", "說", "問", "聊", "笑", "打招呼"],
    "賣咖啡":     ["客人", "點餐", "咖啡", "外帶", "排隊"],
    "服務客人":   ["客人", "點餐", "用餐", "上菜"],
    "煮飯":       ["餓", "點餐", "用餐時段", "客人"],
    "備料":       ["食材", "備餐", "下午"],
    "收銀":       ["客人", "結帳", "排隊"],
    "補貨":       ["缺貨", "貨架", "補充"],
    "工作":       ["報告", "會議", "案子", "客戶", "公文"],
    "整理店面":   ["亂", "髒", "結束", "打烊前"],
    "整理家裡":   ["亂", "髒", "假日", "下班"],
    "打烊":       ["關店", "結束", "晚上", "客人少"],
    "休息":       ["累", "疲憊", "想休息", "壓力", "煩"],
    "睡覺":       ["疲憊", "睏", "深夜", "想睡"],
    "回家":       ["收工", "下班", "晚了", "結束"],
    "散步":       ["煩悶", "透氣", "走走", "心情"],
    "滑手機":     ["無聊", "等待"],
    "吃飯":       ["餓", "用餐時段", "中午", "晚上"],
    "買東西":     ["缺", "需要", "生活用品"],
    "運動":       ["健康", "活動", "肌肉"]
}

# 每命中一個關鍵字加多少分
KEYWORD_BOOST_PER_HIT = 0.15

# 拒絕對話的回應模板
DIALOGUE_REJECT_TEMPLATES = [
    "現在有點忙，待會再聊",
    "嗯...先這樣",
    "不好意思我趕時間",
    "現在不方便",
    "有點累，改天好嗎"
]
```

---

### 6.1.4 `config/prompts.py`

**用途：** 所有 Prompt 模板集中管理。

**主要函式：**

| 函式 | 用途 | 路徑 |
|------|------|------|
| `prompt_deliberate(...)` | 深思決策 prompt | 唯一決策 prompt |
| `prompt_dialogue(...)` | 對話生成 prompt | 對話路徑 |
| `prompt_extract_ham(...)` | 從 STM 抽 HAM | 睡眠濃縮 |
| `prompt_select_ltm(...)` | 篩選重要命題 | 睡眠濃縮 |
| `prompt_ltm_summary(...)` | LTM 摘要 | 睡眠濃縮 |
| `prompt_update_relationship(...)` | 關係更新 | 睡眠濃縮 |
| `prompt_infer_emotion(...)` | 情緒推斷 | 睡眠濃縮（重大事件後）|
| `prompt_generate_schedule(...)` | 時間表生成 | 睡眠濃縮最後步驟 |

**注意：直覺路徑（Markov）不需要 Prompt，所以沒有 `prompt_intuitive`。**

**輸出格式（深思路徑）：**
```
[ACTION] 對話
[TARGET] Amy
[CONTENT] 你今天看起來有點累

[THOUGHT] Ben 想關心 Amy 但不知道從哪裡開口

[HAM]
- Amy | 看起來 | 疲憊 | 咖啡廳 | 下午
- Ben | 想 | 關心Amy | 咖啡廳 | 下午
```

---

### 6.1.5 `config/schedule_templates.py` [新檔]

**用途：** 各職業的時間表範本，作為模型生成隔天時間表的基礎。

**主要常數：**
```python
SCHEDULE_TEMPLATES = {
    "咖啡師": [
        {"time":"06:00","action":"起床","location":"公寓三樓"},
        {"time":"07:00","action":"前往","location":"咖啡廳"},
        {"time":"07:30","action":"整理店面","location":"咖啡廳"},
        {"time":"08:30","action":"賣咖啡","location":"咖啡廳"},
        {"time":"12:00","action":"吃飯","location":"咖啡廳後場"},
        {"time":"13:00","action":"賣咖啡","location":"咖啡廳"},
        {"time":"18:00","action":"打烊","location":"咖啡廳"},
        {"time":"19:00","action":"回家","location":"公寓三樓"},
        {"time":"22:30","action":"睡覺","location":"公寓三樓"}
    ],
    "超市員工": [...],
    "餐廳員工": [...],
    "辦公室員工": [...],
    "公司老闆": [...],
    "廚師": [...],
    "律師": [...],
    "工程師": [...]
}

# 必要時段（規則檢查用）
REQUIRED_SLOTS = {
    "咖啡師":     ["起床","賣咖啡","睡覺"],
    "超市員工":   ["起床","收銀","睡覺"],
    "餐廳員工":   ["起床","服務客人","睡覺"],
    ...
}
```

---

### 6.1.6 `config/model_config.py`

**用途：** Phi-3.5 推論參數。

**主要常數（修正後）：**
```python
MODEL_ID        = "microsoft/Phi-3.5-vision-instruct"
MODEL_NUM_CROPS = 4

# 深思路徑（決策）
DELIBERATE_MAX_TOKENS  = 600  # 從 300 提高（HAM 容易截斷）
DELIBERATE_TEMPERATURE = 0.0

# 對話生成
DIALOGUE_MAX_TOKENS    = 400  # 新增獨立預算
DIALOGUE_TEMPERATURE   = 0.3  # 對話略提高創意

# 睡眠濃縮各步驟
CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS = 500  # 新：從 STM 抽 HAM
CONSOLIDATE_SELECT_MAX_TOKENS      = 200  # 從 100 提高
CONSOLIDATE_SUMMARY_MAX_TOKENS     = 80   # 從 60 略提高
CONSOLIDATE_RELATION_MAX_TOKENS    = 80
CONSOLIDATE_EMOTION_MAX_TOKENS     = 10
SCHEDULE_GEN_MAX_TOKENS            = 500  # 新：時間表生成

# Prompt token 預算（給 prompt_builder 截斷用）
STM_TOKEN_BUDGET = 1500
LTM_TOKEN_BUDGET = 800   # 從 500 提高（HAM 提取更豐富）

# 注意：不再有 INTUITIVE_MAX_TOKENS（直覺路徑不呼叫模型）
```

---

## 6.2 認知層（core/）

### 6.2.1 `core/character.py`

**用途：** 角色狀態的封裝，所有讀寫角色資料都透過這個類別。

**主要類別：** `Character`

**修改重點：**
- 新增 `sleep_pattern` 屬性
- `current_action` 改為支援多 tick 行動（前往咖啡廳可能要 3 ticks）
- 新增 `action_progress` 追蹤進度

**主要屬性：**
```python
code, name, role, gender, age, residence
emotion (可讀寫)
day, current_location, current_action

# 個性與關係
get_personality(short=False)
get_habit()
get_relationship(target_code) -> dict
get_relationship_text(target_code, include_summary=True)
update_relationship_summary(target_code, summary)

# 時間表
get_schedule()
get_current_slot()
mark_slot_completed(time_str)
insert_dynamic_slot(time_str, action, location)
replace_schedule(new_slots)  # 新：替換整個時間表

# 睡眠模式（新）
get_sleep_pattern() -> dict
update_sleep_pattern(field, value)

# 多 tick 行動（新）
set_pending_action(action, target, ticks_required=1)
get_pending_action() -> dict
advance_action_progress() -> bool  # 回傳是否完成
clear_pending_action()

# 情緒影響
get_confusion_threshold() -> float  # 含情緒調整後的最終值

# 今日紀錄
add_today_action(action)
get_today_actions()

# 跨日
advance_day()
reset_slot_state()

# 序列化
to_dict()
```

**輸入輸出契約：**
- 建構：接受 dict（從 JSON 讀）
- 輸出：to_dict() 回傳完整 dict（寫回 JSON）

---

### 6.2.2 `core/memory_stm.py` [改名+改寫]

**用途：** 短期記憶儲存（情節敘述形式，**不含 HAM**）。

**主要類別：** `STM`

**核心改變：**
- 取消 `ham_propositions` 欄位（HAM 在睡眠濃縮才抽）
- 結構分三層：perception / event / inner
- 不限筆數，只有安全閥 50

**主要方法：**
```python
add_turn(turn_id, time, perception, event, inner) -> dict
  # perception = {"location":..., "yolo_desc":..., "scene_text":...}
  # event      = {"input_text":..., "action":..., "target":..., "content":...}
  # inner      = {"thought":..., "emotion":...}

get_all() -> list
get_recent(n) -> list
get_today_narrative() -> str   # 把所有 STM 轉為敘述文字（給濃縮用）
count() -> int
is_over_safety_limit() -> bool  # > 50

# 濃縮後縮減
shrink_to_summary(summary_text, keep_recent=5)
  # 把最舊的事件清掉，新增一筆「歸納摘要」當第一筆
  # 保留最近 keep_recent 筆原始記錄
  
# 工具
make_turn_id(day, turn_number)
next_turn_number()
```

**STM 一筆記錄的結構（重要）：**
```python
{
    "turn_id":    "D001_T003",
    "time":       "08:00",
    "perception": {
        "location":   "咖啡廳",
        "yolo_desc":  "咖啡廳裡有2個人、1個杯子",
        "scene_text": "早晨陽光充足"
    },
    "event": {
        "input_text": "Ben對你說：早安",  # 別人說的（可空）
        "action":     "對話",
        "target":     "Ben",
        "content":    "早安，今天想喝什麼？"  # 自己做的/說的
    },
    "inner": {
        "thought": "Ben 看起來心情不錯",
        "emotion": "平靜"
    }
    # 注意：沒有 ham 欄位
    # 注意：沒有困惑度等元數據（在 process_log）
}
```

---

### 6.2.3 `core/memory_ltm.py` [改名+改寫]

**用途：** 長期記憶（HAM 5 元組命題），純資料結構，圖譜遍歷另在 memory_graph.py。

**主要類別：** `LTM`

**主要方法：**
```python
encode(subject, relation, obj, location, time, day) -> dict
encode_batch(propositions, day)
get_all() -> list
count() -> int

# 條件查詢（保留）
retrieve(subject=None, relation=None, obj=None, top_k=10, update_access=True)

# 摘要
get_summary() -> str
set_summary(summary)

# 衰減與修剪
apply_decay()
prune() -> int  # 回傳刪除筆數

# 格式化
to_text(props=None) -> str
```

**HAM 命題結構：**
```python
{
    "id":           "L001",
    "subject":      "Amy",
    "relation":     "遇見",
    "object":       "Ben",
    "location":     "咖啡廳",
    "time":         "第3天 早上",
    "strength":     1.0,
    "access_count": 0,
    "encoded_day":  3
}
```

---

### 6.2.4 `core/memory_graph.py` [新檔]

**用途：** 在 LTM 上做圖譜遍歷，實作擴散激活，提取相關記憶。

**主要類別：** `MemoryGraph`

**主要方法：**
```python
__init__(ltm: LTM)

# 提取（核心方法）
spreading_retrieve(
    query_nodes: list,        # 起始節點，例如 ["Amy", "Ben"]
    max_hops: int = 2,
    activation_decay: float = 0.4,
    threshold: float = 0.3,
    top_k: int = 20
) -> list[dict]
    # 回傳：[{命題, 活化值, 跳數}, ...]

# 反向組句
propositions_to_narrative(props: list, character_name: str) -> str
    # 把命題列表轉成連貫敘述文字
    # 例：[Amy 遇見 Ben, Ben 工作 超市] 
    #   → "你之前在咖啡廳遇見 Ben，他在超市工作"

# 關係查詢
get_related_to(node: str, max_hops: int = 2) -> list
    # 找所有跟 node 相關的命題

# 路徑查詢
find_path(from_node: str, to_node: str, max_hops: int = 3) -> list
    # 找從 A 到 B 的記憶路徑（角色的「我怎麼認識他」）
```

**擴散激活演算法：**
```
1. 初始化：query_nodes 活化值 = 1.0
2. BFS 遍歷：
   for hop = 1 to max_hops:
       對 hop-1 的所有活化節點，找相連命題
       命題的另一端節點活化 = 來源節點活化 × decay
       命題本身活化 = 兩端節點活化最大值
3. 收集所有活化 ≥ threshold 的命題
4. 按活化值降序排列，取 top_k
```

---

### 6.2.5 `core/markov_engine.py` [改寫]

**用途：** Type 1 思考的決策引擎，從三個來源加權算出行動機率。

**主要函式：**

```python
compute_action_probabilities(
    schedule_slot: dict,     # 當前時間表時段
    stm_recent: list,        # 最近 N 筆 STM
    perception: dict,        # 當前感知（location, yolo_desc, scene_text）
    co_located: list,        # 同地點角色名字
    is_major_event: bool,    # 是否重大事件（影響權重）
    weights: dict = None     # 可覆寫的權重
) -> dict[str, float]
    # 回傳每個行動的機率（總和=1）

# 三個分項函式
schedule_score(action: str, schedule_slot: dict) -> float
    # 行動跟當前時段契合度
    # 完全匹配 → 1.0
    # 同類別 → 0.5
    # 不相關 → 0.0
    
inertia_score(action: str, stm_recent: list) -> float
    # 從 STM 行動序列算 Markov 轉移
    # 用 Laplace 平滑

situation_score(action: str, perception: dict, co_located: list) -> float
    # 掃描 yolo_desc + scene_text 中的關鍵字
    # 對照 ACTION_KEYWORD_BOOST 加分
    # 同地點有人 → 對話 +0.3

# 採樣
sample_action(probs: dict, exclude: list = None) -> str
    # 加權隨機採樣（不是 argmax）

# 對話目標解析
resolve_dialogue_target(probs: dict, co_located: list) -> tuple
    # 回傳 (verb, target_name)
```

**權重邏輯：**
```python
if is_major_event:
    weights = MARKOV_WEIGHTS_EVENT  # {0.1, 0.3, 0.6}
else:
    weights = MARKOV_WEIGHTS_NORMAL # {0.4, 0.3, 0.3}

P(action) = α·schedule + β·inertia + γ·situation
最後 softmax 正規化
```

---

### 6.2.6 `core/confusion.py` [小改]

**用途：** 計算困惑度 C，決定走 Markov 還是 Deliberate。

**主要修改：**
- 閾值受情緒影響（情緒煩躁時閾值降低，更容易深思）
- K 強制 override 從 0.4 提高到 0.5

**主要函式：**
```python
compute_U(action_candidates) -> float
compute_K(yolo_desc, input_text, current_action, scene_text) -> float
compute_S(scene_text, ltm_summary, today_actions) -> float
compute_C(U, K, S, weights) -> float

decide_mode(C, threshold, K) -> str
    # K >= 0.5 → 強制 deliberate
    # 否則比較 C 和 threshold

evaluate(...) -> dict
    # 一次跑完，回傳 {U, K, S, C, mode}

# 新：情緒調整閾值（給 Character.get_confusion_threshold 用）
adjust_threshold_by_emotion(base_threshold: float, emotion: str) -> float
    # 平靜：base
    # 緊張/不安/困惑：base - 0.1（更容易深思）
    # 開心/興奮：base + 0.05（較不易深思）
    # 難過/疲憊：base - 0.05
```

---

### 6.2.7 `core/emotion.py` [新檔]

**用途：** 情緒慣性與每日回歸機制。

**主要函式：**

```python
should_update_emotion(today_max_K: float) -> bool
    # 當天遇到的最大 K 值 >= 0.5 才更新

reset_to_baseline() -> str
    # 回傳 "平靜"（每日睡眠時呼叫）

infer_new_emotion_via_model(stm_today, model_fn) -> str
    # 只有當天有重大事件才會被呼叫
    # 模型推斷新情緒（限制在 VALID_EMOTIONS 中）
```

**整合到睡眠濃縮：**
```python
# 在 consolidation 中：
today_max_K = max(turn 的 K from process_log)
if should_update_emotion(today_max_K):
    new_emotion = infer_new_emotion_via_model(stm_today, model_fn)
else:
    new_emotion = reset_to_baseline()
character.emotion = new_emotion
```

---

### 6.2.8 `core/consolidation.py` [改寫]

**用途：** 睡眠濃縮主流程，含時間表生成。

**主要函式：**
```python
consolidate(
    character: Character,
    stm: STM,
    ltm: LTM,
    process_log: list,        # 今日 process_log（給情緒判斷用）
    make_model_fn: callable
) -> dict
    # 回傳濃縮報告
```

**內部步驟（12 步）：**
```python
def consolidate(...):
    # Step 1: 取出 STM 敘述
    narrative = stm.get_today_narrative()
    
    # Step 2: 模型抽 HAM（新流程）
    extracted_ham = _extract_ham_from_narrative(narrative, model_fn)
    
    # Step 3: 模型篩選重要 HAM
    important_ham = _select_important(extracted_ham, narrative, model_fn)
    
    # Step 4: 寫入 LTM
    ltm.encode_batch(important_ham, day=character.day)
    
    # Step 5: LTM 摘要
    new_summary = _generate_summary(ltm, model_fn)
    ltm.set_summary(new_summary)
    
    # Step 6: 更新關係（任何相關都動）
    _update_relationships(character, narrative, model_fn)
    
    # Step 7: 情緒判斷
    today_max_K = max([log.confusion.K for log in process_log])
    character.emotion = _decide_new_emotion(
        today_max_K, narrative, model_fn
    )
    
    # Step 8: 時間表生成
    new_schedule = _generate_next_day_schedule(
        character, narrative, model_fn
    )
    character.replace_schedule(new_schedule)
    
    # Step 9: LTM 衰減 + 修剪
    ltm.apply_decay()
    pruned = ltm.prune()
    
    # Step 10: STM 縮減
    summary_for_stm = _make_stm_summary(narrative, model_fn)
    stm.shrink_to_summary(summary_for_stm, keep_recent=5)
    
    # Step 11: 推進到下一天
    character.advance_day()
    
    # Step 12: 回傳報告
    return {...}
```

**注意：HAM 抽取從這裡開始（之前是 STM 寫入時就抽）。**

---

## 6.3 推論層（agent/）

### 6.3.1 `agent/agent.py` [改寫]

**用途：** 單一角色的決策與行動執行。

**主要類別：** `Agent`

**主要方法：**
```python
__init__(character, stm, ltm, ltm_graph, loader)

# 決策
decide(
    perception: dict,        # location, yolo_desc, scene_text
    co_located_names: list,
    input_text: str = "",
    image: PIL.Image = None
) -> dict
    # 回傳：{action, verb, target, content, mode, thought, ...}

# 對話生成
generate_dialogue_response(
    perception: dict,
    partner_code: str,
    partner_message: str,
    image: PIL.Image = None
) -> dict

# 對話接受判斷（純規則，不呼叫模型）
should_accept_dialogue(inviter_code: str) -> bool

# 中斷後重新決策
re_evaluate_on_interrupt(
    interrupt_event: dict,
    perception: dict,
    co_located_names: list
) -> dict

# 起床/睡覺確認（純規則）
should_wake_up() -> bool   # 看時間表
should_sleep() -> bool     # 看時間表

# 睡眠
sleep(process_log: list) -> dict
```

**decide() 內部邏輯：**
```python
def decide(self, perception, co_located_names, input_text="", image=None):
    # 1. 計算困惑度
    confusion = compute_confusion(...)
    
    # 2. 取得當前情緒調整後的閾值
    threshold = self.character.get_confusion_threshold()
    
    # 3. 決定模式
    mode = decide_mode(confusion.C, threshold, confusion.K)
    is_major = confusion.K >= MAJOR_EVENT_K_THRESHOLD
    
    if mode == "intuitive":
        # Markov 路徑
        result = self._decide_markov(
            perception, co_located_names, is_major
        )
    else:
        # Deliberate 路徑
        result = self._decide_deliberate(
            perception, co_located_names, input_text, image
        )
    
    # 4. 寫入 STM（敘述化）
    self._write_stm_entry(perception, input_text, result)
    
    # 5. 寫入 process_log（不進 STM）
    self._write_process_log(confusion, mode, result)
    
    return result
```

---

### 6.3.2 `agent/manager.py` [改寫]

**用途：** 多角色協調，管理 tick 推進、batch 推論、對話、中斷分派。

**主要類別：** `AgentManager`

**核心改變：**
- 加入 batch 推論支援
- 加入中斷佇列分派
- 對話發起→接受/拒絕分流
- 整合 process_log

**主要方法：**
```python
__init__(loader, clock)

# 主迴圈
run_tick() -> dict
    # 執行一整個 tick（依照 4.2.1 流程）
    # 內部呼叫 _execute_phase, _decide_phase 等

# 自主多日模擬
run_autonomous_days(n_days: int) -> dict
    # 跑 N 天，每天用 run_tick
    # 收集所有資料給觀察工具

# 中斷
push_interrupt(code: str, event: dict)
    # 給 perception layer 用，注入中斷事件

# 取得資料
get_character(code) -> Character
get_process_log(code) -> list
pop_dialogue_history() -> list
get_observation_data() -> dict   # 給觀察工具
```

**內部方法：**
```python
_execute_phase(perception_map: dict)
_decide_phase(perception_map: dict)
_run_dialogue(initiator, target, scene)
_handle_dialogue_invitation(initiator, target) -> bool
_find_co_located(code) -> list
_check_interrupts() -> dict
_do_sleep(code)
_batch_deliberate(prompts: list) -> list  # batch 模式
```

---

### 6.3.3 `agent/scheduler.py` [新檔]

**用途：** 時間表生成器，睡眠濃縮時呼叫。

**主要函式：**
```python
generate_next_day_schedule(
    character: Character,
    today_narrative: str,
    ltm_summary: str,
    model_fn: callable
) -> list[dict]
    # 回傳新的時間表 slots

# 內部
_get_template_for_role(role: str) -> list
_validate_schedule(schedule: list, role: str) -> bool
_fix_schedule(schedule: list, role: str) -> list  # 補必要時段
```

**生成流程：**
```
1. 取出該角色的職業範本
2. 組裝 prompt（個性 + LTM 摘要 + 今日重要事件 + 範本）
3. 模型輸出新時間表（JSON 格式）
4. 解析失敗 → fallback 用範本
5. 規則檢查：必要時段都在嗎？時間順序合理嗎？
6. 失敗 → 補必要時段
7. 回傳新時間表
```

---

### 6.3.4 `agent/interrupt.py` [新檔]

**用途：** 中斷事件處理。

**主要類別：** `InterruptHandler`

**主要方法：**
```python
__init__()

# 中斷佇列管理
push(code: str, event: dict)
pop_all(code: str) -> list

# 評估是否中斷當前行動
should_interrupt(
    current_action: str,
    event: dict
) -> bool
    # 比較事件強度 vs 行動鎖等級

# 中斷後處理
process_interrupt(
    agent: Agent,
    event: dict,
    perception: dict
) -> dict
    # 1. 暫停當前行動
    # 2. Markov 重算
    # 3. 比較新行動和原行動
    # 4. 決定要不要改變
```

**中斷事件結構：**
```python
{
    "type":      "yolo_change",   # 或 "external_input"
    "strength":  "medium",         # weak/medium/strong
    "data": {
        "objects_added":   ["person"],
        "objects_removed": [],
        "new_person":      "Ben"   # 如有
    },
    "timestamp": "08:30"
}
```

---

## 6.4 模型層（model/）

### 6.4.1 `model/model_loader.py` [小改]

**用途：** Phi-3.5 模型載入，所有角色共用。

主要修改：增加 `make_dialogue_fn`, `make_schedule_fn` 等不同預算的工廠方法。

```python
class ModelLoader:
    load()
    make_model_fn(max_new_tokens, temperature) -> callable
    make_deliberate_fn() -> callable
    make_dialogue_fn() -> callable
    make_consolidation_fn(step: str) -> callable  # 各步驟不同預算
    is_loaded() -> bool
```

---

### 6.4.2 `model/vision_encoder.py` [不變]
### 6.4.3 `model/text_encoder.py` [不變]
### 6.4.4 `model/fusion_decoder.py` [小改]

新增 batch 推論支援：
```python
class FusionDecoder:
    fuse_inputs(text, image_inputs)
    generate(fused_inputs, gen_cfg) -> str
    generate_batch(fused_inputs_list, gen_cfg) -> list[str]  # 新
```

---

### 6.4.5 `model/prompt_builder.py` [改寫]

**用途：** 組裝給模型的 prompt（敘述化 STM + HAM 反向組句）。

**主要類別：** `PromptBuilder`

```python
class PromptBuilder:
    __init__(character, stm, ltm, ltm_graph)
    
    # 深思路徑
    build_deliberate(
        perception: dict,
        co_located: list,
        input_text: str = ""
    ) -> str
    
    # 對話路徑
    build_dialogue(
        perception: dict,
        partner_code: str,
        partner_message: str
    ) -> str
    
    # 內部工具
    _format_stm_as_narrative(turns: list) -> str
        # 把 STM 結構轉為敘述文字
        # 「08:00 在咖啡廳，看到 Ben 走進來，跟他打招呼」
    
    _retrieve_relevant_ltm(query_nodes: list) -> str
        # 用 ltm_graph.spreading_retrieve 找相關記憶
        # 轉為敘述文字
```

---

### 6.4.6 `model/output_parser.py` [改寫]

**用途：** 解析模型輸出（block 格式 + pipe-separated HAM）。

**主要函式：**
```python
parse_decision_output(raw: str) -> dict
    # 解析 [ACTION] [TARGET] [CONTENT] [THOUGHT] [HAM]
    # 回傳：{action, verb, target, content, thought, ham, raw}

parse_consolidation_output(raw: str, expected_format: str) -> Any
    # 給濃縮各步驟用，依 expected_format 解析

# 內部
_parse_block(raw: str, tag: str) -> str
_parse_ham_lines(raw: str) -> list
    # 解析 - subj | rel | obj | loc | time
```

---

### 6.4.7 `model/batch_inference.py` [新檔]

**用途：** Batch 推論工具。

**主要函式：**
```python
detect_gpu_memory() -> int  # 回傳可用 VRAM (MB)

decide_batch_size(num_prompts: int, vram_mb: int) -> int
    # 顯存 ≥ 16GB → max batch 5
    # 顯存 ≥ 12GB → max batch 3
    # 否則 → batch 1（sequential）

batch_generate(
    loader: ModelLoader,
    prompts: list[str],
    images_list: list = None,
    gen_cfg: GenerationConfig = None
) -> list[str]
    # 自動分批，回傳和 prompts 等長的結果列表
```

---

## 6.5 觀察層（observe/）[新資料夾]

### 6.5.1 `observe/dashboard_html.py`

**用途：** 生成完整的 HTML 儀表板。

**主要函式：**
```python
generate_report(
    simulation_data: dict,
    output_path: str
) -> str
    # 寫入 HTML 檔案，回傳路徑

# 內部 — 各分頁區塊
_render_overview_section(data) -> str
_render_stm_section(data) -> str
_render_ltm_graph_section(data) -> str  # 用 vis.js
_render_confusion_section(data) -> str  # 用 chart.js
_render_dialogue_section(data) -> str
_render_consolidation_section(data) -> str
```

---

### 6.5.2 `observe/memory_viewer.py`

**用途：** LTM 圖譜視覺化資料準備。

**主要函式：**
```python
ltm_to_graph_data(ltm: LTM) -> dict
    # 回傳 vis.js 可用的格式：
    # {
    #   nodes: [{id, label, group, value(=活化), title(hover)}],
    #   edges: [{from, to, label, width(=strength), title}]
    # }

stm_to_timeline_data(stm: STM) -> list
    # 回傳時間軸資料
```

---

### 6.5.3 `observe/dialogue_log.py`

**用途：** 對話記錄整理。

**主要函式：**
```python
format_dialogue_history(history: list) -> list
    # 把 raw history 整理成可讀格式
    # [
    #   {turn, time, speaker_a, message_a, speaker_b, response_b, ...},
    #   ...
    # ]

filter_by_character(history: list, code: str) -> list
filter_by_day(history: list, day: int) -> list
```

---

## 6.6 世界層（world/）

### 6.6.1 `world/world_clock.py` [小改]

**用途：** 世界時鐘。

**主要修改：**
- `MAX_TICKS_PER_DAY` 從 22 改 20
- 不再「凌晨 04:00 強制睡」，改為各角色 `force_sleep_time`

```python
class WorldClock:
    @property time_str
    @property day
    @property ticks_today
    
    tick()
    advance_day()
    scene_prefix() -> str
    
    # 新方法
    is_past_force_wake(character) -> bool
    is_past_force_sleep(character) -> bool
```

---

## 6.7 工具層（utils/）

### 6.7.1 `utils/file_io.py` [不變]
### 6.7.2 `utils/logger.py` [小改]

新增 `log_interrupt`, `log_dialogue_invite` 等。

---

## 6.8 進入層

### 6.8.1 `simulate.py` [改寫]

**用途：** 離線模擬，產生 HTML 報告。

```python
# 命令行
python simulate.py --days 3              # 跑 3 天
python simulate.py --days 1 --no-model   # 假模型快速測
python simulate.py --report-only         # 只重新生成報告

# 主流程
def main():
    parse_args()
    setup_system()                # ModelLoader + AgentManager + Clock
    
    for day in range(n_days):
        run_one_day()
        save_intermediate_data()
    
    generate_html_report()
```

---

### 6.8.2 `main.py` [後期改]

**用途：** UE 對接的進入點。

最後階段才動，前期保留現狀但確認不會被破壞。

---

## 6.9 感知與通訊層 [後期實作]

### 6.9.1 `perception/yolo_handler.py` [後期改]
### 6.9.2 `perception/event_trigger.py` [新, 後期]
### 6.9.3 `server/ws_server.py` [後期改]

**前期注意事項：**
- 這三個檔案維持現狀
- agent/manager.py 的介面要設計成「YOLO 是可選輸入」，沒有也能跑
- WSServer 要能 plug into manager，不需要重寫核心

---

# 七、核心資料結構

## 7.1 角色 JSON Schema（完整）

```json
{
  "name": "Amy",
  "name_code": "A",
  "role": "咖啡師",
  "gender": "女",
  "age": 24,
  "residence": "公寓三樓",
  
  "personality_short": "溫柔體貼但壓抑自己...",
  "personality": "Amy對工作投入...",
  "habit": "Amy每天早起泡咖啡...",
  
  "relationships": {
    "B": {"initial": "...", "summary": "..."},
    "C": {"initial": "...", "summary": "..."},
    "D": {"initial": "...", "summary": "..."},
    "E": {"initial": "...", "summary": "..."}
  },
  
  "emotion": "平靜",
  
  "sleep_pattern": {
    "default_wake_time":  "06:00",
    "force_wake_time":    "08:00",
    "default_sleep_time": "22:30",
    "force_sleep_time":   "01:00"
  },
  
  "stm": {
    "turns": [
      {
        "turn_id": "D004_T001",
        "time":    "06:00",
        "perception": {
          "location":   "公寓三樓",
          "yolo_desc":  "",
          "scene_text": "第4天 06:00 公寓三樓，早晨"
        },
        "event": {
          "input_text": "",
          "action":     "起床",
          "target":     "",
          "content":    ""
        },
        "inner": {
          "thought": "",
          "emotion": "平靜"
        }
      }
    ]
  },
  
  "ltm": {
    "ltm_summary": "Amy 是公寓三樓的咖啡師...",
    "propositions": [
      {
        "id":           "L001",
        "subject":      "Amy",
        "relation":     "認識",
        "object":       "Ben",
        "location":     "咖啡廳",
        "time":         "第1天 早上",
        "strength":     0.95,
        "access_count": 3,
        "encoded_day":  1
      }
    ]
  },
  
  "state": {
    "day":              4,
    "current_location": "公寓三樓",
    "current_action":   "起床",
    "today_actions":    [],
    "pending_action":   {
      "action":          "前往",
      "target":          "咖啡廳",
      "ticks_required":  1,
      "ticks_done":      0
    }
  },
  
  "schedule": {
    "slots": [
      {"time":"06:00","action":"起床","location":"公寓三樓",
       "type":"fixed","completed":false},
      {"time":"07:00","action":"前往","location":"咖啡廳",
       "type":"fixed","completed":false}
    ]
  },
  
  "confusion_weights": {
    "w1": 0.4,
    "w2": 0.3,
    "w3": 0.3,
    "threshold": 0.5
  }
}
```

---

## 7.2 STM Turn 結構

```python
{
    "turn_id":    "D001_T003",
    "time":       "08:00",
    "perception": {
        "location":   str,
        "yolo_desc":  str,    # 來自 YOLO，前期可空
        "scene_text": str
    },
    "event": {
        "input_text": str,    # 別人說/做了什麼
        "action":     str,    # 自己做的（動詞）
        "target":     str,    # 對象（地點或人）
        "content":    str     # 對話內容（如有）
    },
    "inner": {
        "thought": str,       # 內心想法
        "emotion": str        # 該時刻情緒
    }
}
```

---

## 7.3 Process Log 結構（不進 STM）

```python
{
    "turn_id":    "D001_T003",
    "code":       "A",
    "time":       "08:00",
    "decision_mode": "deliberate",   # markov/deliberate/interrupt
    "confusion": {
        "U": 0.4, "K": 0.3, "S": 0.2, "C": 0.32
    },
    "is_major_event": false,
    "action_probs":   {"工作":0.4, "對話":0.2, ...},  # markov 才有
    "model_called":   true,
    "tokens_used":    245,
    "interrupt_event": null,         # 有中斷時填
    "duration_ms":    1234
}
```

---

## 7.4 LTM 命題結構

```python
{
    "id":           "L001",
    "subject":      str,
    "relation":     str,
    "object":       str,
    "location":     str | None,
    "time":         str | None,
    "strength":     float,    # 0.0 ~ 1.0
    "access_count": int,
    "encoded_day":  int
}
```

---

## 7.5 中斷事件結構

```python
{
    "type":      "yolo_change" | "external_input",
    "strength":  "weak" | "medium" | "strong",
    "data": {
        "objects_added":   list,
        "objects_removed": list,
        "new_person":      str | None
    },
    "timestamp": str  # "HH:MM"
}
```

---

# 八、設定參數總表

## 8.1 時間參數

| 參數 | 值 | 說明 |
|------|----|------|
| MINUTES_PER_TICK | 60 | 每 tick 1 小時 |
| MAX_TICKS_PER_DAY | 20 | 06:00 ~ 02:00 |
| DAY_START_HOUR | 6 | 一天最早起床 |
| DAY_END_HOUR | 2 | 凌晨最晚 |

## 8.2 記憶參數

| 參數 | 值 | 說明 |
|------|----|------|
| STM_SAFETY_LIMIT | 50 | 超過觸發中途濃縮 |
| STM_KEEP_AFTER_CONS | 5 | 濃縮後保留最近筆數 |
| LTM_DECAY_RATE | 0.05 | 每天衰減量 |
| LTM_FORGET_THRESHOLD | 0.2 | 忘記門檻 |
| HAM_TRAVERSE_MAX_HOPS | 2 | 圖譜最多 2 跳 |
| HAM_ACTIVATION_DECAY | 0.4 | 1→2 跳衰減 |
| HAM_RETRIEVE_THRESHOLD | 0.3 | 提取活化門檻 |

## 8.3 決策參數

| 參數 | 值 | 說明 |
|------|----|------|
| MAJOR_EVENT_K_THRESHOLD | 0.6 | 重大事件 K 門檻 |
| EMOTION_RESET_THRESHOLD | 0.5 | 情緒更新 K 門檻 |
| MARKOV_WEIGHTS_NORMAL | (0.4, 0.3, 0.3) | 平時 α/β/γ |
| MARKOV_WEIGHTS_EVENT | (0.1, 0.3, 0.6) | 重大事件時 |
| KEYWORD_BOOST_PER_HIT | 0.15 | 每命中加分 |

## 8.4 對話參數

| 參數 | 值 | 說明 |
|------|----|------|
| DIALOGUE_MAX_TURNS | 10 | 最多 10 來回（20 句）|
| DIALOGUE_BASE_ACCEPT | 0.5 | 基礎接受率 |
| DIALOGUE_RELATION_BONUS | 0.3 | 關係正向加成 |
| DIALOGUE_LEISURE_BONUS | 0.2 | 休閒中加成 |
| DIALOGUE_WORK_PENALTY | -0.3 | 工作中懲罰 |
| DIALOGUE_EMOTION_PENALTY | -0.2 | 非平靜情緒懲罰 |

## 8.5 模型參數

| 參數 | 值 | 說明 |
|------|----|------|
| MODEL_ID | microsoft/Phi-3.5-vision-instruct | |
| DELIBERATE_MAX_TOKENS | 600 | 深思輸出上限 |
| DIALOGUE_MAX_TOKENS | 400 | 對話輸出上限 |
| DIALOGUE_TEMPERATURE | 0.3 | 對話溫度 |
| CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS | 500 | HAM 抽取 |
| CONSOLIDATE_SELECT_MAX_TOKENS | 200 | 篩選命題 |
| CONSOLIDATE_SUMMARY_MAX_TOKENS | 80 | 摘要 |
| CONSOLIDATE_RELATION_MAX_TOKENS | 80 | 關係更新 |
| CONSOLIDATE_EMOTION_MAX_TOKENS | 10 | 情緒推斷 |
| SCHEDULE_GEN_MAX_TOKENS | 500 | 時間表生成 |
| STM_TOKEN_BUDGET | 1500 | STM 注入上限 |
| LTM_TOKEN_BUDGET | 800 | LTM 注入上限 |

---

# 九、關鍵流程圖

## 9.1 單 Tick 完整流程

```
┌─────────────────────────────────────────────┐
│  Tick T 開始（時間例：08:00）                │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  時鐘檢查                                    │
│  ├─ 各角色是否該強制起床？                   │
│  └─ 各角色是否該強制睡覺？                   │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  感知收集                                    │
│  ├─ 從 YOLO interrupt_queue 取累積事件       │
│  ├─ 場景描述 perception_map[code]            │
│  └─ 對話輸入收集                             │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Phase 1: 執行                              │
│  for each 角色（活躍中）:                    │
│    if 有 interrupt:                          │
│      → interrupt.process()                   │
│      → 可能改變 pending_action              │
│    執行 pending_action                       │
│      ├─ 對話 → 進入對話循環                 │
│      ├─ 一般 → 更新位置/狀態                │
│      └─ 多 tick → 推進進度                  │
│    寫入 STM（記錄做了什麼）                 │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  Phase 2: 決策                              │
│  Step 1: 對所有角色計算困惑度                │
│  Step 2: 分流                                │
│    ├─ Markov 角色 → 立刻算（無模型）        │
│    └─ Deliberate 角色 → 加入 batch queue    │
│  Step 3: Batch 推論（顯存夠的話）           │
│  Step 4: 解析輸出，設定 pending_action       │
│  Step 5: 寫入 STM（記錄想了什麼）           │
│  Step 6: 寫入 process_log                   │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  STM 安全閥                                  │
│  for each 角色: if STM > 50: 中途濃縮        │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│  時鐘推進 → Tick T+1                        │
└─────────────────────────────────────────────┘
```

---

## 9.2 決策路徑分流

```
                    decide()
                       │
                       ↓
              ┌─ 計算困惑度 C ─┐
              │  U, K, S, C    │
              └────────┬───────┘
                       ↓
            取得情緒調整後 threshold
                       ↓
              ┌────────┴────────┐
              │   K ≥ 0.5?      │
              └─┬──────────────┬┘
            是  │              │  否
                ↓              ↓
         強制 deliberate    C ≥ threshold?
                            ┌─┴──┐
                          否│    │是
                            ↓    ↓
                   intuitive    deliberate
                       │           │
                       ↓           ↓
                  Markov 三來源   Phi-3.5 推理
                   加權採樣         
                       │           │
                       └─────┬─────┘
                             ↓
                        寫入 STM（敘述）
                        寫入 process_log
```

---

## 9.3 對話發起流程

```
A 決策 = 對話:Amy
     │
     ↓
Amy 同地點？
  否 → 改為「前往 Amy 所在處」
  是 → 繼續
     ↓
雙方鎖定（同 tick 內）
     ↓
Amy 接受判斷（純規則）
  接受率 = 50%
  ± 關係正向 +30%
  ± Amy 在休閒 +20% / 工作 -30%
  ± Amy 情緒非平靜 -20%
     │
     ↓
   接受？
   否 → Amy 簡短拒絕（模板）
        A 改回原行動
        雙方寫 STM
   是 → 進入對話循環
     ↓
循環（最多 10 來回）：
  for round in 1..10:
    A.generate_dialogue_response(input=last_msg)
    寫 STM
    if A 不再對話: break
    last_msg = A 說的
    
    Amy.generate_dialogue_response(input=last_msg)
    寫 STM
    if Amy 不再對話: break
    last_msg = Amy 說的
     ↓
對話結束
雙方解鎖
下 tick 各自決策
```

---

## 9.4 睡眠濃縮流程

```
觸發（角色決策睡覺 / 到 force_sleep_time）
     │
     ↓
[1] 取出今日 STM 敘述
     │
     ↓
[2] 模型抽取 HAM 命題（從敘述）
     │
     ↓
[3] 模型篩選重要 HAM（最多 N 筆）
     │
     ↓
[4] 寫入 LTM
     │
     ↓
[5] 模型生成新 LTM 摘要
     │
     ↓
[6] 模型更新關係摘要（每個有相關的角色）
     │
     ↓
[7] 情緒判斷
    today_max_K ≥ 0.5？
      是 → 模型推斷新情緒
      否 → 重置為「平靜」
     │
     ↓
[8] 模型生成隔天時間表
     │
     ↓
[9] 規則檢查時間表
     │
     ↓
[10] LTM 衰減 + 修剪
     │
     ↓
[11] STM 縮減
     原始 STM 摘要成一句話
     + 保留最近 5 筆
     變成新 STM 起點
     │
     ↓
[12] 寫入 JSON 檔
     character.day += 1
```

---

## 9.5 中斷處理流程

```
YOLO 偵測到場景變化（某角色處）
     │
     ↓
封裝為 InterruptEvent
     │
     ↓
推入 interrupt_queue[code]
     │
     ↓ ─── （非同步，等下一 tick）

下一 tick 開始
     │
     ↓
manager 檢查 interrupt_queue
     │
     ↓
有事件 → InterruptHandler.process_interrupt()
     │
     ↓
比較事件強度 vs 當前行動鎖
     │
     ↓
   可中斷？
   否 → 繼續原行動（事件記入 STM 但不改變決策）
   是 → 暫停原行動
     │
     ↓
Markov 重算（用新感知）
     │
     ↓
新行動 ≠ 原行動？
   是 → 改變 pending_action
        記錄中斷事件到 STM
        記錄到 process_log
   否 → 繼續原行動
        記錄事件到 STM（但不改）
```

---

# 十、輸入輸出介面契約

> 重要：以下介面是模組間溝通的契約，不可隨意改變。

## 10.1 Agent.decide() 契約

**輸入：**
```python
{
    "perception": {                     # 必填
        "location":   str,
        "yolo_desc":  str,              # 可空，給 YOLO 後期用
        "scene_text": str
    },
    "co_located_names": list[str],      # 必填，可為空 list
    "input_text":       str = "",       # 可空
    "image":            PIL.Image | None
}
```

**輸出：**
```python
{
    "action":  str,           # 完整字串
    "verb":    str,
    "target":  str,
    "content": str,           # 對話才有
    "thought": str,           # deliberate 才有
    "mode":    str,           # markov / deliberate
    "ham":     list,          # 注意：實際 HAM 抽取在睡眠，這裡只是 deliberate 模型自己提的初稿，不一定用
    "should_sleep": bool,
    
    # 元數據（給 process_log，不進 STM）
    "_meta": {
        "confusion": dict,
        "action_probs": dict,
        "is_major_event": bool,
        "tokens_used": int
    }
}
```

---

## 10.2 Manager.run_tick() 契約

**輸入：**
```python
perception_input: dict = {
    "A": {"location":..., "yolo_desc":..., "scene_text":...},
    "B": {...},
    ...
}
external_input: dict = {
    "A": "input_text from external",  # 可選
    ...
}
```

**輸出：**
```python
{
    "tick":          int,
    "time":          str,
    "day":           int,
    "execute":       {code: result},
    "decide":        {code: result},
    "interrupts":    list,
    "dialogues":     list,
    "consolidations": list,    # 本 tick 觸發的睡眠
    "process_logs":  {code: list}
}
```

---

## 10.3 Consolidation.consolidate() 契約

**輸入：**
```python
character: Character
stm: STM
ltm: LTM
process_log: list             # 今日 process_log
make_model_fn: callable       # loader.make_consolidation_fn
```

**輸出：**
```python
{
    "ham_extracted":     int,    # 從敘述抽出
    "ham_kept":          int,    # 篩選後留下
    "ltm_total":         int,
    "ltm_pruned":        int,
    "ltm_summary":       str,
    "relationship_updates": dict,
    "emotion_change":    {"from":..., "to":...},
    "next_day_schedule": list,
    "stm_kept":          int
}
```

---

## 10.4 YOLO 介面契約（前期 stub）

**目前簡化介面（後期擴充）：**
```python
# perception/yolo_handler.py
class YoloHandler:
    detect(image) -> list[dict]            # 維持現有
    process(image, location) -> tuple      # 維持現有

# perception/event_trigger.py [後期]
class PerceptionWatcher:
    """後期實作，前期 manager 不依賴此模組"""
    push_frame(code, image)
    consume_events(code) -> list[InterruptEvent]
```

**前期作法：**
- agent.decide() 接受 `perception["yolo_desc"]`，前期由 simulate.py 給空字串或假資料
- manager 不主動跑 YOLO 迴圈
- 後期接 PerceptionWatcher 時，只需 manager 在 tick 開始時 `consume_events`

---

## 10.5 WebSocket 介面契約（前期 stub）

**前期保留現有介面：**
```python
# server/ws_server.py
class WSServer:
    """前期不主動依賴，後期接 manager"""
    __init__(manager, yolo, host, port)
    run()
    _process(raw_msg) -> dict
```

**後期接通：**
- UE 傳入 → ws_server → 寫入 perception_input → manager.run_tick

---

# 十一、與舊架構對應表

## 11.1 檔案層

| 舊檔案 | 新檔案 | 改動程度 |
|--------|--------|----------|
| main.py | main.py | 後期改 |
| simulate.py | simulate.py | 改寫 |
| agent/agent.py | agent/agent.py | 改寫 |
| agent/agent_manager.py | agent/manager.py | 改寫 + 改名 |
| - | agent/scheduler.py | 新增 |
| - | agent/interrupt.py | 新增 |
| core/character.py | core/character.py | 小改 |
| core/stm.py | core/memory_stm.py | 改寫 + 改名 |
| core/ltm.py | core/memory_ltm.py | 小改 + 改名 |
| - | core/memory_graph.py | 新增 |
| core/markov.py | core/markov_engine.py | 改寫 + 改名 |
| core/confusion.py | core/confusion.py | 小改 |
| - | core/emotion.py | 新增 |
| core/memory_consolidation.py | core/consolidation.py | 改寫 + 改名 |
| model/model_loader.py | model/model_loader.py | 小改 |
| model/vision_encoder.py | model/vision_encoder.py | 不變 |
| model/text_encoder.py | model/text_encoder.py | 不變 |
| model/fusion_decoder.py | model/fusion_decoder.py | 小改（batch）|
| model/prompt_builder.py | model/prompt_builder.py | 改寫 |
| model/output_parser.py | model/output_parser.py | 改寫 |
| - | model/batch_inference.py | 新增 |
| world/world_clock.py | world/world_clock.py | 小改 |
| config/world_config.py | config/world_config.py | 改 |
| config/action_list.py | config/action_list.py | 小改 |
| - | config/triggers.py | 新增 |
| config/prompts.py | config/prompts.py | 改 |
| - | config/schedule_templates.py | 新增 |
| config/model_config.py | config/model_config.py | 改 |
| utils/file_io.py | utils/file_io.py | 不變 |
| utils/logger.py | utils/logger.py | 小改 |
| utils/test_reset.py | - | 刪除 |
| perception/yolo_handler.py | perception/yolo_handler.py | 後期改 |
| - | perception/event_trigger.py | 後期新增 |
| server/ws_server.py | server/ws_server.py | 後期改 |
| - | observe/dashboard_html.py | 新增 |
| - | observe/memory_viewer.py | 新增 |
| - | observe/dialogue_log.py | 新增 |

## 11.2 概念層

| 舊概念 | 新概念 | 變化 |
|--------|--------|------|
| STM 含 ham_propositions | STM 純敘述（perception/event/inner）| HAM 抽取移到睡眠 |
| 困惑度資料寫進 STM | process_log 獨立 | 記憶 vs 元數據分離 |
| Markov 只用 STM 轉移 | 三來源加權（時間表 + 慣性 + 情境）| 更貼近真人 |
| 直覺路徑可能呼叫模型 | 直覺路徑完全不用模型 | 效能提升 |
| 凌晨 04:00 強制全員睡 | 各角色 force_sleep_time | 自主作息 |
| 22 ticks/day | 20 ticks/day | 縮短 |
| 情緒每天可能更新 | 預設回歸平靜，重大事件才更新 | 避免崩壞 |
| 對話必須同地點 | 同地點 + 邀請接受/拒絕 | 更真實 |
| 無中斷機制 | YOLO 觸發中斷 → Markov 重算 | 感知驅動 |
| 對話內容無 token 預算 | 獨立 DIALOGUE_MAX_TOKENS | 可調 |
| - | LTM 圖譜 2 跳擴散激活 | 認知科學支撐 |

---

# 十二、開發路線圖

## 12.1 修改順序（每階段先解釋再實作）

```
階段 0：規格確認
  ✓ ARCHITECTURE.md（本文件）

階段 1：設定層（根基）
  □ config/world_config.py        — 新常數、移除舊常數
  □ config/action_list.py         — 加 ACTION_CATEGORIES
  □ config/triggers.py            [新]
  □ config/schedule_templates.py  [新]
  □ config/model_config.py        — token 預算修正
  □ config/prompts.py             — 改寫所有模板

階段 2：核心資料結構
  □ core/character.py             — 加 sleep_pattern, pending_action
  □ core/memory_stm.py            — 改寫，分三層結構
  □ core/memory_ltm.py            — 小改，移除部分功能到 graph
  □ core/memory_graph.py          [新]

階段 3：認知決策
  □ core/markov_engine.py         — 三來源加權
  □ core/confusion.py             — 情緒影響閾值
  □ core/emotion.py               [新]

階段 4：睡眠濃縮
  □ core/consolidation.py         — 改寫，含時間表生成
  □ agent/scheduler.py            [新]

階段 5：模型層
  □ model/prompt_builder.py       — 敘述化 + 圖譜檢索
  □ model/output_parser.py        — block 格式
  □ model/model_loader.py         — 多種 model_fn 工廠
  □ model/fusion_decoder.py       — batch 支援
  □ model/batch_inference.py      [新]

階段 6：協調層
  □ agent/agent.py                — 改寫
  □ agent/interrupt.py            [新]
  □ agent/manager.py              — 改寫

階段 7：世界與工具
  □ world/world_clock.py          — 20 ticks
  □ utils/logger.py               — 新增 log 函式
  □ utils/file_io.py              — 不變（順手檢查）

階段 8：觀察工具
  □ observe/dashboard_html.py     [新]
  □ observe/memory_viewer.py      [新]
  □ observe/dialogue_log.py       [新]

階段 9：進入點
  □ simulate.py                   — 改寫
  □ main.py                       — 後期確認

階段 10：感知與通訊（最後）
  □ perception/yolo_handler.py    — 接 manager
  □ perception/event_trigger.py   [新]
  □ server/ws_server.py           — 接 manager

階段 11：清理與文件
  □ 刪除舊檔
  □ 更新 README.md
  □ 跑完整測試
```

## 12.2 每個檔案的修改流程

```
對每個要修改的檔案：

Step 1: 我向你解釋
  - 這個檔案做什麼
  - 輸入輸出契約
  - 主要邏輯
  - 對應規格書哪一節
  - 跟舊版差異

Step 2: 你確認 / 修改

Step 3: 我寫程式

Step 4: 你看程式

Step 5: 修改 / 通過

Step 6: 進下一個檔案
```

---

# 十三、未來擴充建議

## 13.1 短期擴充（架構穩定後）

```
1. 角色擴充
   - 從 5 個增加到 10+ 個
   - 新增職業（醫生、學生、退休老人）
   - 新增地點（醫院、學校、公園 2）

2. 時間粒度
   - 30 分鐘 / tick 細化模式
   - 動態粒度（白天 1 小時，重要事件 30 分鐘）

3. 行動擴充
   - 新增「思考事情」「打電話」等社交行動
   - 動作子類別（工作 → 開會 / 寫報告 / 處理客戶）
```

## 13.2 中期擴充（半年內）

```
4. 個體差異深化
   - 個性會隨經驗微調
   - 學習機制（重複失敗會調整偏好）

5. 多日記憶模式
   - 週期性事件（每週日休息）
   - 季節性（春節等特殊日子）

6. 天氣與環境
   - 天氣影響情緒與行動
   - 場景動態變化

7. 群體行為
   - 三人以上聚會（取消「只能兩人對話」限制）
   - 群體情緒擴散
```

## 13.3 長期擴充（一年以上）

```
8. 感知擴充
   - 多模態輸入（聲音、文字訊息）
   - 角色視線追蹤

9. 模型升級
   - 嘗試 Qwen2.5-VL / Llama-3.2-Vision
   - LoRA 微調個性化

10. 物件記憶
    - 角色擁有物（手機、咖啡杯、書）
    - 物件 → 記憶觸發

11. 動態關係圖
    - 關係強度可變
    - 朋友/敵人/曖昧多層

12. 學習與成長
    - 角色技能提升
    - 個性變化（負面事件影響）
```

## 13.4 工程擴充

```
13. 多執行緒 / 異步推論
    - Manager 改 async-first
    - 各角色獨立 event loop

14. 分散式運算
    - 多 GPU 分配角色
    - 不同模型給不同角色（Amy 用 Phi、Ben 用 Qwen）

15. 即時 Web Dashboard
    - WebSocket 即時更新
    - 互動式時間軸

16. 模擬重播
    - 完整快照儲存
    - 可從任意 tick 重啟
```

---

# 附錄 A：研究文獻清單

| 領域 | 文獻 | 應用 |
|------|------|------|
| 雙歷程 | Kahneman 2011 | Markov vs Deliberate |
| 雙歷程 | Evans & Stanovich 2013 | 95% System 1 比例 |
| 工作記憶 | Cowan 2001 | 容量設計 |
| 工作記憶 | Baddeley 2000 | 多模態緩衝 |
| 情節記憶 | Tulving 1972, 1985 | STM 敘述化 |
| 自傳記憶 | Conway & Pleydell-Pearce 2000 | STM 三層感知/事件/內在 |
| HAM | Anderson & Bower 1973 | LTM 命題網絡 |
| ACT-R | Anderson 1996 | 活化值 |
| 擴散激活 | Anderson 1983 | 2 跳極限 |
| 語意網絡 | Collins & Loftus 1975 | 圖譜架構 |
| 睡眠記憶 | Diekelmann & Born 2010 | 睡眠濃縮 |
| 情緒法則 | Frijda 1988 | 情緒衰減 |
| 幸福基線 | Diener 2000 | 平靜回歸 |
| 預測編碼 | Friston 2010 | YOLO 預測誤差 |
| 注意力 | Itti & Koch 2001 | 顯著性觸發 |
| 習慣形成 | Wood & Neal 2007 | 慣性 43% |
| 功能可供性 | Gibson 1979 | 情境觸發行動 |
| 認知控制 | Botvinick & Cohen 2014 | ACC 衝突偵測 |

---

# 附錄 B：詞彙表

| 術語 | 定義 |
|------|------|
| Tick | 模擬時間單位（1 小時）|
| STM | 短期記憶（情節敘述）|
| LTM | 長期記憶（HAM 命題）|
| HAM | Human Associative Memory，5 元組命題 |
| 擴散激活 | 從查詢點向相連節點傳遞活化值 |
| 困惑度 C | w1·U + w2·K + w3·S |
| U / K / S | 不確定性 / 衝突 / 驚訝 |
| Markov 路徑 | Type 1 直覺思考（不用模型）|
| Deliberate 路徑 | Type 2 深思（用模型）|
| 重大事件 | K ≥ 0.6，影響 Markov 權重 |
| 行動鎖 | 中斷阻力等級（0/1/2）|
| process_log | 系統元數據，不進記憶 |
| 敘述化 | STM 轉自然語言，給 prompt 用 |
| 反向組句 | HAM 命題重組為敘述句 |
| pending_action | 已決策、待執行的行動 |
| sleep_pattern | 角色起床/睡覺時間設定 |

---

**規格書 v2.0 結束**

下一步：
1. 等你看完此文件確認沒問題
2. 從「階段 1：設定層」開始
3. 每個檔案先解釋再寫
