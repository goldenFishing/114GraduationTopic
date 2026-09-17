# file_io — 角色 JSON 檔案讀寫工具

> **路徑**: `utils/file_io.py`  
> **職責**: 讀寫磁碟上的角色 JSON 資料

---

## 功能概覽

`file_io` 模組負責 AI-Town 所有角色的持久化資料讀寫。系統運行時，角色狀態以 Python `dict` 形式保存於記憶體，只在特定時機（睡眠濃縮完成後、程式關閉時）才透過本模組寫回磁碟，以降低 I/O 開銷。

角色資料儲存為 JSON 格式，檔名慣例為 `{代號}_init.json`（如 `A_init.json`、`B_init.json`），統一放置於 `config.world_config.AI_DATA_DIR` 所指定的目錄下。讀取時若找不到檔案，會直接拋出 `FileNotFoundError`，使上層呼叫方能明確感知錯誤。

批次讀寫函式（`load_all_characters` / `save_all_characters`）讓 AgentManager 在啟動與關閉時只需一行呼叫，即可完整載入或儲存所有角色，維持介面簡潔。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | 取得 `AI_DATA_DIR`（資料目錄）和 `CHARACTER_NAMES`（合法角色代號集合） |
| 被依賴 | `agent.manager` | 啟動時呼叫 `load_all_characters`，關閉時呼叫 `save_all_characters` |
| 被依賴 | `agent.sleep_consolidation` | 睡眠濃縮完成後呼叫 `save_character` 寫回單一角色 |

---

## 主要類別 / 函式

### `load_character(code: str) -> dict`
**功能**: 從磁碟讀取單一角色的 JSON 資料，回傳 Python dict。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `code` | `str` | 角色代號，合法值為 `A`、`B`、`C`、`D`、`E` |

**回傳**: `dict` — 角色完整資料，包含名字、記憶、情緒、時間表等欄位  
**例外**: `FileNotFoundError` — 當對應的 `{code}_init.json` 不存在時拋出  
**範例**:
```python
from utils.file_io import load_character

# 載入 Amy（代號 A）的角色資料
amy_data = load_character("A")
print(amy_data["name"])       # "Amy"
print(amy_data["emotion"])    # "平靜"
```

---

### `save_character(code: str, data: dict)`
**功能**: 將角色 dict 寫回磁碟，以 UTF-8 + indent=2 格式化輸出。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `code` | `str` | 角色代號 |
| `data` | `dict` | 要儲存的角色資料 dict |

**回傳**: `None`  
**注意**: 此函式不應每個模擬 tick 都呼叫，應僅在睡眠濃縮或程式結束時使用。  
**範例**:
```python
from utils.file_io import load_character, save_character

# 修改 Ben（代號 B）的情緒後儲存
ben_data = load_character("B")
ben_data["emotion"] = "開心"
save_character("B", ben_data)
```

---

### `load_all_characters() -> dict`
**功能**: 掃描 `AI_DATA_DIR`，載入所有符合 `{code}_init.json` 格式且代號在 `CHARACTER_NAMES` 中的角色。  
**參數**: 無  
**回傳**: `dict` — 格式為 `{代號: 角色資料dict}`，例如 `{"A": {...}, "B": {...}, ...}`  
**範例**:
```python
from utils.file_io import load_all_characters

characters = load_all_characters()
for code, data in characters.items():
    print(f"{code}: {data['name']}")
# A: Amy
# B: Ben
# C: Claire
# D: David
# E: Emma
```

---

### `save_all_characters(characters: dict)`
**功能**: 將所有角色的最新狀態批次寫回磁碟。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `characters` | `dict` | `{代號: 資料dict}` 的映射 |

**回傳**: `None`  
**範例**:
```python
from utils.file_io import load_all_characters, save_all_characters

characters = load_all_characters()
# 對所有角色執行某些更新 ...
for code in characters:
    characters[code]["day"] += 1
save_all_characters(characters)
```

---

### `_get_path(code: str) -> str`（內部函式）
**功能**: 組合出角色 JSON 檔案的完整路徑。  
**回傳**: `str` — 如 `AI_Data/A_init.json`

---

## 模擬使用情境

### 情境一: 系統啟動，載入所有角色

```python
from utils.file_io import load_all_characters

# AgentManager.__init__ 中執行
characters = load_all_characters()
# 結果: {"A": {name: "Amy", ...}, "B": {name: "Ben", ...}, ...}

# 驗證五位角色都已載入
assert set(characters.keys()) == {"A", "B", "C", "D", "E"}
print(f"已載入 {len(characters)} 位角色")
```

### 情境二: Claire 睡眠濃縮結束，更新 LTM 並儲存

```python
from utils.file_io import save_character

# Claire 的代號是 C
claire_data = {
    "name": "Claire",
    "emotion": "平靜",
    "day": 2,
    "ltm": [
        {"prop_id": "p001", "subject": "Claire", "relation": "喜歡", "object": "閱讀"}
    ],
    "stm": []
}
save_character("C", claire_data)
# 寫入 AI_Data/C_init.json
```

---

## 注意事項

- `save_character` 使用 `ensure_ascii=False`，中文字元會直接寫入 JSON，不會轉成 Unicode 跳脫字元。
- `load_all_characters` 只會載入 `CHARACTER_NAMES` 中存在的角色，額外放在 `AI_DATA_DIR` 的 `*_init.json` 檔案會被忽略。
- 不包含任何 schema 驗證；如果 JSON 格式損毀，`json.load` 會拋出 `json.JSONDecodeError`，需由上層處理。
- 在多執行緒或 async 環境下，多個協程同時呼叫 `save_character` 可能造成競爭寫入，目前無鎖保護機制。
