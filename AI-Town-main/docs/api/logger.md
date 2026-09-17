# logger — 結構化日誌系統

> **路徑**: `utils/logger.py`  
> **職責**: 提供雙輸出（控制台 + 日誌檔）的結構化日誌

---

## 功能概覽

`logger` 模組封裝 Python 標準函式庫 `logging`，提供 AI-Town 整個系統使用的統一日誌介面。每次呼叫 `get_logger` 會回傳一個同時輸出至控制台和每日日誌檔的 logger，且透過 handler 存在性檢查避免重複附加 handler。

日誌級別可分別針對控制台和檔案進行設定，分別讀取 `config.world_config` 中的 `LOG_LEVEL_CONSOLE` 和 `LOG_LEVEL_FILE` 常數。日誌檔以日期命名（`YYYYMMDD.log`），每天自動換新檔，歷史記錄不會遺失。

除了基本的 `get_logger`，本模組還提供四個語意化的輔助函式（`log_turn`、`log_consolidation`、`log_interrupt`、`log_dialogue_invite`），讓各模組不必自行格式化關鍵事件的日誌訊息，確保跨模組的日誌風格一致。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | 讀取 `LOG_DIR`、`LOG_LEVEL_CONSOLE`、`LOG_LEVEL_FILE` |
| 被依賴 | `agent.manager` | 取得 `"world"` logger，記錄模擬主流程事件 |
| 被依賴 | `simulate.py` | 取得 `"simulate"` logger |
| 被依賴 | `main.py` | 取得 `"main"` logger |
| 被依賴 | 各 agent 模組 | 使用 `log_turn`、`log_interrupt` 等輔助函式 |

---

## 主要類別 / 函式

### `get_logger(name: str = "world") -> logging.Logger`
**功能**: 取得或建立指定名稱的 logger。初次呼叫時附加 Console handler 和 File handler；後續同名呼叫直接回傳已建立的 logger。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `name` | `str` | Logger 名稱，建議使用模組名稱，預設為 `"world"` |

**回傳**: `logging.Logger` — 已設定好雙輸出 handler 的 logger 實例  
**範例**:
```python
from utils.logger import get_logger

logger = get_logger("agent")
logger.info("Amy 開始新的一天")
logger.debug("Amy STM 目前有 3 筆記憶")
logger.warning("David LTM 命題數量超過上限")
```

---

### `log_turn(logger, code, turn_id, action, c_value, mode)`
**功能**: 記錄每個 tick 的決策摘要，包含角色代號、回合 ID、決策模式、困惑度 C 值和最終行動。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `logger` | `logging.Logger` | 目標 logger |
| `code` | `str` | 角色代號（如 `"A"`） |
| `turn_id` | `str` | 回合識別碼（如 `"D1T06:00"`） |
| `action` | `str` | 決策的行動名稱 |
| `c_value` | `float` | 困惑度最終值 C |
| `mode` | `str` | 決策模式：`"intuitive"` 或 `"deliberate"` |

**回傳**: `None`  
**輸出格式**: `[A] D1T06:00 | mode=intuitive | C=0.312 | action=工作`  
**範例**:
```python
from utils.logger import get_logger, log_turn

logger = get_logger("world")
log_turn(logger, "B", "D1T08:00", "吃早餐", 0.218, "intuitive")
# [08:00:00] [INFO] [world] [B] D1T08:00 | mode=intuitive | C=0.218 | action=吃早餐
```

---

### `log_consolidation(logger, code, day, stm_count, ltm_count)`
**功能**: 記錄睡眠濃縮完成事件，含 HAM 抽取數量和 LTM 總量。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `logger` | `logging.Logger` | 目標 logger |
| `code` | `str` | 角色代號 |
| `day` | `int` | 第幾天 |
| `stm_count` | `int` | 本次從 STM 抽取的 HAM 命題數 |
| `ltm_count` | `int` | 濃縮後 LTM 總命題數 |

**回傳**: `None`  
**範例**:
```python
log_consolidation(logger, "C", 1, 8, 23)
# [INFO] [world] [C] Day 1 睡眠濃縮完成 | 抽 HAM 8 筆 → LTM 共 23 筆
```

---

### `log_interrupt(logger, code, event_type, strength, interrupted, new_action="")`
**功能**: 記錄中斷事件的處理結果，說明角色是否因事件改變原本行動計畫。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `logger` | `logging.Logger` | 目標 logger |
| `code` | `str` | 被中斷的角色代號 |
| `event_type` | `str` | 中斷事件類型，如 `"yolo_change"`、`"dialogue_request"` |
| `strength` | `str` | 事件強度：`"weak"` / `"medium"` / `"strong"` |
| `interrupted` | `bool` | 是否真的中斷了原行動 |
| `new_action` | `str` | 若發生中斷，新的行動名稱 |

**回傳**: `None`  
**範例**:
```python
log_interrupt(logger, "D", "yolo_change", "strong", True, "與Emma對話")
# [INFO] [world] [D] 中斷事件 type=yolo_change strength=strong → 中斷→與Emma對話

log_interrupt(logger, "A", "yolo_change", "weak", False)
# [INFO] [world] [A] 中斷事件 type=yolo_change strength=weak → 繼續原行動
```

---

### `log_dialogue_invite(logger, initiator, responder, accepted)`
**功能**: 記錄對話邀請的結果。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `logger` | `logging.Logger` | 目標 logger |
| `initiator` | `str` | 發起對話的角色代號 |
| `responder` | `str` | 被邀請對話的角色代號 |
| `accepted` | `bool` | 是否接受邀請 |

**回傳**: `None`  
**範例**:
```python
log_dialogue_invite(logger, "A", "B", True)
# [INFO] [world] [A→B] 對話邀請被接受

log_dialogue_invite(logger, "E", "C", False)
# [INFO] [world] [E→C] 對話邀請被拒絕
```

---

## 模擬使用情境

### 情境一: 模組初始化並記錄模擬啟動

```python
from utils.logger import get_logger

# 在 simulate.py 中
logger = get_logger("simulate")
logger.info("=== AI-Town 離線模擬啟動 ===")
logger.info("參數：days=3, no_model=False")

# 控制台輸出（INFO 級別）：
# [10:30:00] [INFO] [simulate] === AI-Town 離線模擬啟動 ===
# [10:30:00] [INFO] [simulate] 參數：days=3, no_model=False

# 同時寫入 logs/20260519.log（DEBUG 以上全部記錄）
```

### 情境二: Amy 與 Ben 對話邀請，再記錄 Amy 的決策

```python
from utils.logger import get_logger, log_dialogue_invite, log_turn

logger = get_logger("world")

# Amy 邀請 Ben 對話，Ben 接受
log_dialogue_invite(logger, "A", "B", True)

# 下一 tick，Amy 決定繼續工作（C=0.25，直覺模式）
log_turn(logger, "A", "D2T14:00", "工作", 0.25, "intuitive")

# 輸出：
# [14:00:01] [INFO] [world] [A→B] 對話邀請被接受
# [14:00:01] [INFO] [world] [A] D2T14:00 | mode=intuitive | C=0.250 | action=工作
```

---

## 注意事項

- `get_logger` 使用 `logger.handlers` 檢查避免重複初始化；但若不同地方傳入相同 `name`，回傳的是同一個 logger 實例，這是預期行為。
- 日誌格式固定為 `[HH:MM:SS] [LEVEL] [name] message`，`datefmt` 只含時間不含日期，日期資訊體現在檔名上。
- `LOG_LEVEL_FILE` 建議設為 `"DEBUG"`（完整記錄），`LOG_LEVEL_CONSOLE` 建議設為 `"INFO"`（減少終端雜訊）。
- `_LEVEL_MAP` 中不存在的字串會 fallback：Console 預設 `INFO`，File 預設 `DEBUG`。
- 日誌目錄 `LOG_DIR` 若不存在，`get_logger` 會自動建立（`os.makedirs(exist_ok=True)`）。
