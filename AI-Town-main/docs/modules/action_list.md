# action_list 需求規格

## 負責檔案
- `config/action_list.py`

## 功能描述
在現有的 `VALID_ACTIONS`、`ACTION_CATEGORIES`、`ACTION_TO_CATEGORY` 之上，
新增 ActionID 完整動作表、角色可用動作清單、家位置對應，以及 Stage 2 解析函式。

**不要修改或刪除現有的任何常數**（VALID_ACTIONS、ACTION_CATEGORIES 等），
因為其他模組仍在使用它們。只做新增。

## 輸入 / 輸出
- 輸入：無（模組級常數 + 一個純函式）
- 輸出：新增以下常數與函式

## 相依模組
- 無（此檔案是所有其他模組的資料來源）

## 實作要求

### 1. ACTION_TABLE
在檔案末尾新增一個 `ACTION_TABLE` list，每筆為 dict，欄位如下：
- `id: int` — 唯一 ActionID（1~45）
- `name: str` — 動作名稱（含括號地點說明）
- `location: str` — 執行所需地點簡稱（空字串 = 不限）
- `text: str` — UE5 顯示用 emoji（Python 不處理，只儲存）
- `img_file_id: int | None` — UE5 對話泡泡圖片 ID（Python 不處理，只儲存）
- `chars: list[str]` — 可執行此動作的角色代碼清單

完整資料（依序照 ActionID 1~45）：

| id | name | location | text | img_file_id | chars |
|----|------|----------|------|------------|-------|
| 1 | 回家_A | A家 | "" | None | ["A"] |
| 2 | 回家_B | B家 | "" | None | ["B"] |
| 3 | 回家_C | C家 | "" | None | ["C"] |
| 4 | 回家_D | D家 | "" | None | ["D"] |
| 5 | 回家_E | E家 | "" | None | ["E"] |
| 6 | 吃飯 (餐廳) | "" | "🍽️" | 1 | ["A","B","C","D","E"] |
| 7 | 散步 (廣場) | "" | "" | None | ["A","B","C","D","E"] |
| 8 | 運動 (廣場) | "" | "🤾" | None | ["A","B","C","D","E"] |
| 9 | 賣咖啡 | 咖啡店 | "🧑‍🍳☕" | 7 | ["A"] |
| 10 | 整理店面 | 咖啡店 | "🪣🧹🫧" | None | ["A"] |
| 11 | 打烊 (關店整理) | 咖啡店 | "🈺❌" | None | ["A"] |
| 12 | 收銀 | 超市 | "🧾💰" | None | ["B"] |
| 13 | 補貨 | 超市 | "📦" | None | ["B"] |
| 14 | 工作 (員工) | 辦公桌前 | "👨‍💼💻" | 9 | ["C","D"] |
| 15 | 工作 (老闆) | 辦公區前 | "👨‍💼" | None | ["C","D"] |
| 16 | 備料 (內場) | "" | "🔪🥩" | None | ["E"] |
| 17 | 煮飯 (內場) | "" | "🍳" | None | ["E"] |
| 18 | 服務客人 (外場) | "" | "🤵" | 10 | ["E"] |
| 19 | 吃飯 (在A家) | A家 | "🍽️" | 1 | ["A"] |
| 20 | 吃飯 (在B家) | B家 | "🍽️" | 1 | ["B"] |
| 21 | 吃飯 (在C家) | C家 | "🍽️" | 1 | ["C"] |
| 22 | 吃飯 (在D家) | D家 | "🍽️" | 1 | ["D"] |
| 23 | 吃飯 (在E家) | E家 | "🍽️" | 1 | ["E"] |
| 24 | 買東西 (超市) | "" | "🫳🥫🛒" | 3 | ["A","B","C","D","E"] |
| 25 | 整理家裡 (在A家) | A家 | "🪣🧹🫧" | None | ["A"] |
| 26 | 整理家裡 (在B家) | B家 | "🪣🧹🫧" | None | ["B"] |
| 27 | 整理家裡 (在C家) | C家 | "🪣🧹🫧" | None | ["C"] |
| 28 | 整理家裡 (在D家) | D家 | "🪣🧹🫧" | None | ["D"] |
| 29 | 整理家裡 (在E家) | E家 | "🪣🧹🫧" | None | ["E"] |
| 30 | 滑手機 (在A家) | A家 | "📱" | None | ["A"] |
| 31 | 滑手機 (在B家) | B家 | "📱" | None | ["B"] |
| 32 | 滑手機 (在C家) | C家 | "📱" | None | ["C"] |
| 33 | 滑手機 (在D家) | D家 | "📱" | None | ["D"] |
| 34 | 滑手機 (在E家) | E家 | "📱" | None | ["E"] |
| 35 | 起床 (在A家) | A家 | "🥱🫧" | None | ["A"] |
| 36 | 起床 (在B家) | B家 | "🥱🫧" | None | ["B"] |
| 37 | 起床 (在C家) | C家 | "🥱🫧" | None | ["C"] |
| 38 | 起床 (在D家) | D家 | "🥱🫧" | None | ["D"] |
| 39 | 起床 (在E家) | E家 | "🥱🫧" | None | ["E"] |
| 40 | 睡覺 (在A家) | A家 | "🛌💤" | 6 | ["A"] |
| 41 | 睡覺 (在B家) | B家 | "🛌💤" | 6 | ["B"] |
| 42 | 睡覺 (在C家) | C家 | "🛌💤" | 6 | ["C"] |
| 43 | 睡覺 (在D家) | D家 | "🛌💤" | 6 | ["D"] |
| 44 | 睡覺 (在E家) | E家 | "🛌💤" | 6 | ["E"] |
| 45 | 對話 | "" | "" | None | ["A","B","C","D","E"] |

### 2. CHARACTER_VALID_ACTIONS
角色代碼 → 該角色可執行的抽象動詞清單（Markov Stage 1 候選集）：
```python
CHARACTER_VALID_ACTIONS = {
    "A": ["回家","吃飯","散步","運動","賣咖啡","整理店面","打烊",
          "整理家裡","滑手機","起床","睡覺","買東西","對話"],
    "B": ["回家","吃飯","散步","運動","收銀","補貨",
          "整理家裡","滑手機","起床","睡覺","買東西","對話"],
    "C": ["回家","吃飯","散步","運動","工作",
          "整理家裡","滑手機","起床","睡覺","買東西","對話"],
    "D": ["回家","吃飯","散步","運動","工作",
          "整理家裡","滑手機","起床","睡覺","買東西","對話"],
    "E": ["回家","吃飯","散步","運動","備料","煮飯","服務客人",
          "整理家裡","滑手機","起床","睡覺","買東西","對話"],
}
```

### 3. CHARACTER_HOME_LOCATION
```python
CHARACTER_HOME_LOCATION = {
    "A": "A家",
    "B": "B家",
    "C": "C家",
    "D": "D家",
    "E": "E家",
}
```

### 4. ACTION_ABSTRACT_MAP（查詢輔助）
從 ACTION_TABLE 自動建立：抽象動詞 → 符合的 ACTION_TABLE entries 清單。
抽象動詞提取規則：`name` 中括號前的部分（去掉空格），再與 VALID_ACTIONS 對照取交集。
例如：`"吃飯 (餐廳)"` → 抽象動詞 `"吃飯"`；`"回家_A"` → 抽象動詞 `"回家"`。

```python
ACTION_ABSTRACT_MAP: dict[str, list[dict]] = {}
# 由程式在模組底部自動建立（for 迴圈解析 ACTION_TABLE）
```

### 5. action_id_resolver 函式
```python
def action_id_resolver(
    abstract_verb: str,
    char_code: str,
    current_location: str,
) -> int | None:
```

**邏輯（優先順序）：**
1. 從 `ACTION_ABSTRACT_MAP[abstract_verb]` 取出候選清單
2. 過濾：`char_code` 在 `entry["chars"]` 中
3. 若無符合候選 → 回傳 `None`
4. 在候選中找 `entry["location"] == current_location`（精確匹配）→ 回傳此 id
5. 若無精確匹配，找 `entry["location"] == ""`（不限位置）→ 回傳此 id
6. 若前兩者都沒有 → 回傳候選清單第一個的 id（fallback）

**抽象動詞提取規則（用於 ACTION_ABSTRACT_MAP 建立）：**
- `"回家_X"` 系列 → 抽象動詞 `"回家"`
- `"xxx (yyy)"` 格式 → 取括號前部分並 strip
- 無括號 → 整個 name 就是抽象動詞

## 測試要求

### 測試工具
Python 內建 unittest（不引入新依賴）

### 測試情境
測試情境 1：action_id_resolver 位置精確匹配
  輸入：abstract_verb="吃飯", char_code="A", current_location="A家"
  預期輸出：19
  允許偏差：無

測試情境 2：action_id_resolver 不限位置 fallback
  輸入：abstract_verb="吃飯", char_code="A", current_location="咖啡廳"
  預期輸出：6（吃飯 餐廳，location=""）
  允許偏差：無

測試情境 3：角色無法執行的動作
  輸入：abstract_verb="收銀", char_code="A", current_location="超市"
  預期輸出：None
  允許偏差：無

測試情境 4：睡覺位置匹配
  輸入：abstract_verb="睡覺", char_code="B", current_location="B家"
  預期輸出：41
  允許偏差：無

測試情境 5：CHARACTER_VALID_ACTIONS 完整性
  輸入：char_code="E"
  預期輸出：CHARACTER_VALID_ACTIONS["E"] 包含 "備料","煮飯","服務客人"，不含 "收銀","賣咖啡"
  允許偏差：無

測試情境 6：ACTION_TABLE 長度
  輸入：len(ACTION_TABLE)
  預期輸出：45
  允許偏差：無

## 禁止事項
- 不要修改現有的 VALID_ACTIONS、VALID_LOCATIONS、ACTION_CATEGORIES、ACTION_TO_CATEGORY、ACTION_DEFAULT_ON_INVALID、ACTION_SEPARATOR
- 不要刪除任何現有常數
- action_id_resolver 不要呼叫任何外部模組
- 規格有任何不清楚之處，停止開發並回報主控台
