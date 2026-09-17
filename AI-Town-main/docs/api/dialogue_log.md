# dialogue_log — 對話記錄整理工具

> **路徑**: `observe/dialogue_log.py`  
> **職責**: 格式化與篩選角色間的對話歷史紀錄

---

## 功能概覽

`dialogue_log` 模組負責將 `AgentManager` 內部的原始對話歷史（`_dialogue_history`）轉換成人類可讀的格式，並提供依角色或依天數進行篩選的工具函式。

原始對話記錄中只保存角色代號（`A`、`B`、`C`、`D`、`E`），`format_dialogue_history` 會自動查找 `CHARACTER_NAMES` 映射，將代號轉換為全名（Amy、Ben、Claire、David、Emma），同時計算來回輪數，讓下游的 HTML 報告或 API 消費端不需要自己處理這些轉換邏輯。

兩個篩選函式（`filter_by_character`、`filter_by_day`）作用於已格式化的資料結構，讓使用者能快速提取特定場景的對話片段，適合用於除錯分析和分頁 dashboard 的資料準備。

---

## 依賴關係

| 方向 | 模組 | 說明 |
|------|------|------|
| 依賴 | `config.world_config` | 讀取 `CHARACTER_NAMES` dict 進行代號轉全名 |
| 被依賴 | `observe.dashboard_html` | 呼叫 `format_dialogue_history` 準備 HTML 報告的對話資料 |

---

## 主要類別 / 函式

### `format_dialogue_history(history: list) -> list`
**功能**: 將原始對話記錄 list 格式化，補全角色名字，計算來回輪數。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `history` | `list` | 原始對話記錄 list，每筆格式見下方 |

**輸入格式（單筆）**:
```python
{
    "initiator": "A",          # 發起對話的角色代號
    "responder": "B",          # 回應對話的角色代號
    "accepted": True,          # 是否接受對話邀請
    "turns": [
        {"speaker": "A", "msg": "你好！"},
        {"speaker": "B", "msg": "你也好！"}
    ]
}
```

**回傳**: `list` — 格式化後的對話清單，每筆包含:
- `initiator_code` / `initiator_name`
- `responder_code` / `responder_name`
- `accepted`
- `rounds`（來回輪數，`len(turns) // 2`）
- `turns`（含 `speaker_code`、`speaker_name`、`msg` 的清單）

**範例**:
```python
from observe.dialogue_log import format_dialogue_history

raw_history = [
    {
        "initiator": "A",
        "responder": "C",
        "accepted": True,
        "turns": [
            {"speaker": "A", "msg": "Claire，你今天有空嗎？"},
            {"speaker": "C", "msg": "有啊，怎麼了？"},
            {"speaker": "A", "msg": "我想一起去圖書館。"},
            {"speaker": "C", "msg": "好啊，我也正好要去。"}
        ]
    }
]

result = format_dialogue_history(raw_history)
print(result[0]["initiator_name"])   # "Amy"
print(result[0]["responder_name"])   # "Claire"
print(result[0]["rounds"])           # 2
print(result[0]["turns"][0]["speaker_name"])  # "Amy"
```

---

### `filter_by_character(history: list, code: str) -> list`
**功能**: 從已格式化的對話清單中，只保留包含指定角色（發起或回應）的對話。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `history` | `list` | `format_dialogue_history` 的回傳值 |
| `code` | `str` | 要篩選的角色代號（如 `"D"`） |

**回傳**: `list` — 篩選後的對話清單  
**範例**:
```python
from observe.dialogue_log import format_dialogue_history, filter_by_character

formatted = format_dialogue_history(raw_history)
david_talks = filter_by_character(formatted, "D")
# 只保留 David（D）發起或參與的對話
```

---

### `filter_by_day(simulation_data: dict, day: int) -> list`
**功能**: 從完整模擬資料（`run_autonomous_days` 的回傳值）中，提取指定天的所有原始對話記錄。  
**參數**:

| 名稱 | 型別 | 說明 |
|------|------|------|
| `simulation_data` | `dict` | `manager.run_autonomous_days()` 的回傳值 |
| `day` | `int` | 要提取的天數（從 1 開始計算） |

**回傳**: `list` — 該天所有 tick 的原始對話記錄（未格式化），`day` 超出範圍時回傳空 list  
**範例**:
```python
from observe.dialogue_log import filter_by_day, format_dialogue_history

# sim_data 是 manager.run_autonomous_days(3) 的回傳值
day1_raw = filter_by_day(sim_data, 1)
day1_formatted = format_dialogue_history(day1_raw)
print(f"第一天共有 {len(day1_formatted)} 次對話")
```

---

## 模擬使用情境

### 情境一: 格式化並印出 Emma 在第 2 天的所有對話

```python
from observe.dialogue_log import (
    filter_by_day,
    format_dialogue_history,
    filter_by_character
)

# sim_data 來自 manager.run_autonomous_days(3)
day2_raw       = filter_by_day(sim_data, 2)
day2_formatted = format_dialogue_history(day2_raw)
emma_dialogues = filter_by_character(day2_formatted, "E")

for dlg in emma_dialogues:
    status = "接受" if dlg["accepted"] else "拒絕"
    print(f"{dlg['initiator_name']} → {dlg['responder_name']} ({status}, {dlg['rounds']} 來回)")
    for turn in dlg["turns"]:
        print(f"  {turn['speaker_name']}: {turn['msg']}")
```

### 情境二: 統計三天內各角色的對話接受率

```python
from observe.dialogue_log import filter_by_day, format_dialogue_history, filter_by_character

codes = ["A", "B", "C", "D", "E"]
names = {"A": "Amy", "B": "Ben", "C": "Claire", "D": "David", "E": "Emma"}

for code in codes:
    all_dialogues = []
    for day in range(1, 4):
        raw = filter_by_day(sim_data, day)
        formatted = format_dialogue_history(raw)
        all_dialogues.extend(filter_by_character(formatted, code))

    total    = len(all_dialogues)
    accepted = sum(1 for d in all_dialogues if d["accepted"])
    rate     = accepted / total * 100 if total else 0
    print(f"{names[code]}: {accepted}/{total} ({rate:.0f}% 接受率)")
```

---

## 注意事項

- `format_dialogue_history` 中 `rounds` 計算方式為 `len(turns) // 2`，若對話回合數為奇數（例如最後一輪只有一方說話），輪數會向下捨去。
- `filter_by_character` 作用在**已格式化**的 list，使用 `initiator_code` / `responder_code` 欄位篩選，不是 `initiator` / `responder`。
- `filter_by_day` 作用在**原始** `simulation_data`（未格式化），天數索引從 1 開始，若超出範圍（`day < 1` 或 `day > len(days)`）回傳空 list，不拋出例外。
- 若 `CHARACTER_NAMES` 中找不到對應代號，`format_dialogue_history` 會用代號本身作為名字（fallback），不會報錯。
