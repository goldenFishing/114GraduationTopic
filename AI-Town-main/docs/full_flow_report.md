# AI-Town 全流程模擬報告（無 LLM 模式）

模擬天數：3 天

## 1. 摘要表

| 角色 | 天數 | 總 Tick 數 | 行動次數 | 最常見行動 |
|------|------|-----------|---------|-----------|
| Amy(A) | 第4天 | 19 | 16 | 賣咖啡 |
| Amy(A) | 第5天 | 20 | 17 | 對話 |
| Amy(A) | 第6天 | 20 | 17 | 回家 |
| Ben(B) | 第4天 | 19 | 16 | 回家 |
| Ben(B) | 第5天 | 20 | 17 | 前往 |
| Ben(B) | 第6天 | 20 | 17 | 買東西 |
| Claire(C) | 第4天 | 19 | 16 | 吃飯 |
| Claire(C) | 第5天 | 20 | 17 | 買東西 |
| Claire(C) | 第6天 | 20 | 17 | 散步 |
| David(D) | 第4天 | 19 | 18 | 散步 |
| David(D) | 第5天 | 20 | 19 | 對話 |
| David(D) | 第6天 | 20 | 19 | 前往 |
| Emma(E) | 第4天 | 19 | 18 | 滑手機 |
| Emma(E) | 第5天 | 20 | 19 | 整理家裡 |
| Emma(E) | 第6天 | 20 | 19 | 整理家裡 |

## 2. 行動序列（每天每角色）

### 第 4 天

#### Amy（A）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 07:00 | 起床 | A家 | intuitive |
| 08:00 | 前往 | 咖啡店 | intuitive |
| 09:00 | 賣咖啡 | A家 | intuitive |
| 10:00 | 吃飯 | A家 | intuitive |
| 11:00 | 前往 | 咖啡店 | intuitive |
| 12:00 | 吃飯 | A家 | intuitive |
| 13:00 | 散步 | A家 | intuitive |
| 14:00 | 整理店面 | A家 | intuitive |
| 15:00 | 散步 | A家 | intuitive |
| 16:00 | 賣咖啡 | A家 | intuitive |
| 17:00 | 買東西 | A家 | intuitive |
| 18:00 | 買東西 | A家 | intuitive |
| 19:00 | 整理家裡 | A家 | intuitive |
| 20:00 | 吃飯 | A家 | intuitive |
| 21:00 | 整理店面 | A家 | intuitive |
| 22:00 | 打烊 | A家 | intuitive |
| 23:00 | 賣咖啡 | A家 | schedule |
| 00:00 | — | A家 | — |
| 01:00 | — | A家 | — |

#### Ben（B）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 07:00 | 起床 | B家 | intuitive |
| 08:00 | 運動 | B家 | intuitive |
| 09:00 | 買東西 | B家 | intuitive |
| 10:00 | 前往 | 超市 | intuitive |
| 11:00 | 補貨 | B家 | intuitive |
| 12:00 | 回家 | B家 | intuitive |
| 13:00 | 回家 | B家 | intuitive |
| 14:00 | 收銀 | B家 | intuitive |
| 15:00 | 整理家裡 | B家 | intuitive |
| 16:00 | 吃飯 | B家 | intuitive |
| 17:00 | 回家 | B家 | intuitive |
| 18:00 | 休息 | B家 | intuitive |
| 19:00 | 收銀 | B家 | intuitive |
| 20:00 | 補貨 | B家 | intuitive |
| 21:00 | 回家 | B家 | intuitive |
| 22:00 | 散步 | B家 | intuitive |
| 23:00 | 散步 | B家 | schedule |
| 00:00 | — | B家 | — |
| 01:00 | — | B家 | — |

#### Claire（C）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 07:00 | 起床 | C家 | intuitive |
| 08:00 | 吃飯 | C家 | intuitive |
| 09:00 | 散步 | C家 | intuitive |
| 10:00 | 散步 | C家 | intuitive |
| 11:00 | 吃飯 | C家 | intuitive |
| 12:00 | 前往 | 辦公室 | intuitive |
| 13:00 | 買東西 | C家 | intuitive |
| 14:00 | 工作 | C家 | intuitive |
| 15:00 | 吃飯 | C家 | intuitive |
| 16:00 | 整理家裡 | C家 | intuitive |
| 17:00 | 散步 | C家 | intuitive |
| 18:00 | 工作 | C家 | intuitive |
| 19:00 | 對話 | C家 | intuitive |
| 20:00 | 對話 | C家 | intuitive |
| 21:00 | 整理家裡 | C家 | intuitive |
| 22:00 | 對話 | C家 | intuitive |
| 23:00 | 前往 | C家 | schedule |
| 00:00 | — | C家 | — |
| 01:00 | — | C家 | — |

#### David（D）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 07:00 | 休息 | D家 | intuitive |
| 08:00 | 滑手機 | D家 | intuitive |
| 09:00 | 起床 | D家 | intuitive |
| 10:00 | 散步 | D家 | intuitive |
| 11:00 | 滑手機 | D家 | intuitive |
| 12:00 | 運動 | D家 | intuitive |
| 13:00 | 前往 | 咖啡店 | intuitive |
| 14:00 | 運動 | D家 | intuitive |
| 15:00 | 吃飯 | D家 | intuitive |
| 16:00 | 前往 | 辦公室 | intuitive |
| 17:00 | 散步 | D家 | intuitive |
| 18:00 | 吃飯 | D家 | intuitive |
| 19:00 | 對話 | D家 | intuitive |
| 20:00 | 對話 | D家 | intuitive |
| 21:00 | 休息 | D家 | intuitive |
| 22:00 | 對話 | D家 | intuitive |
| 23:00 | 買東西 | D家 | intuitive |
| 00:00 | 散步 | D家 | intuitive |
| 01:00 | 工作 | D家 | schedule |

#### Emma（E）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 07:00 | 休息 | E家 | intuitive |
| 08:00 | 備料 | E家 | intuitive |
| 09:00 | 整理家裡 | E家 | intuitive |
| 10:00 | 滑手機 | E家 | intuitive |
| 11:00 | 起床 | E家 | intuitive |
| 12:00 | 煮飯 | E家 | intuitive |
| 13:00 | 備料 | E家 | intuitive |
| 14:00 | 買東西 | E家 | intuitive |
| 15:00 | 煮飯 | E家 | intuitive |
| 16:00 | 散步 | E家 | intuitive |
| 17:00 | 買東西 | E家 | intuitive |
| 18:00 | 滑手機 | E家 | intuitive |
| 19:00 | 前往 | 餐廳 | intuitive |
| 20:00 | 回家 | E家 | intuitive |
| 21:00 | 散步 | E家 | intuitive |
| 22:00 | 休息 | E家 | intuitive |
| 23:00 | 服務客人 | E家 | intuitive |
| 00:00 | 滑手機 | E家 | intuitive |
| 01:00 | 運動 | E家 | schedule |

### 第 5 天

#### Amy（A）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 賣咖啡 | A家 | intuitive |
| 07:00 | 起床 | A家 | intuitive |
| 08:00 | 運動 | A家 | intuitive |
| 09:00 | 前往 | 咖啡店 | intuitive |
| 10:00 | 打烊 | A家 | intuitive |
| 11:00 | 吃飯 | A家 | intuitive |
| 12:00 | 對話 | A家 | intuitive |
| 13:00 | 散步 | A家 | intuitive |
| 14:00 | 整理家裡 | A家 | intuitive |
| 15:00 | 對話 | A家 | intuitive |
| 16:00 | 運動 | A家 | intuitive |
| 17:00 | 休息 | A家 | intuitive |
| 18:00 | 賣咖啡 | A家 | intuitive |
| 19:00 | 對話 | A家 | intuitive |
| 20:00 | 對話 | A家 | intuitive |
| 21:00 | 對話 | A家 | intuitive |
| 22:00 | 賣咖啡 | A家 | intuitive |
| 23:00 | 回家 | A家 | schedule |
| 00:00 | — | A家 | — |
| 01:00 | — | A家 | — |

#### Ben（B）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 散步 | B家 | intuitive |
| 07:00 | 前往 | B家 | intuitive |
| 08:00 | 起床 | B家 | intuitive |
| 09:00 | 前往 | 超市 | intuitive |
| 10:00 | 滑手機 | B家 | intuitive |
| 11:00 | 整理家裡 | B家 | intuitive |
| 12:00 | 吃飯 | B家 | intuitive |
| 13:00 | 買東西 | B家 | intuitive |
| 14:00 | 散步 | B家 | intuitive |
| 15:00 | 補貨 | B家 | intuitive |
| 16:00 | 補貨 | B家 | intuitive |
| 17:00 | 收銀 | B家 | intuitive |
| 18:00 | 前往 | 超市附近 | intuitive |
| 19:00 | 前往 | 超市附近 | intuitive |
| 20:00 | 回家 | B家 | intuitive |
| 21:00 | 休息 | B家 | intuitive |
| 22:00 | 買東西 | B家 | intuitive |
| 23:00 | 買東西 | B家 | schedule |
| 00:00 | — | B家 | — |
| 01:00 | — | B家 | — |

#### Claire（C）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 前往 | C家 | intuitive |
| 07:00 | 前往 | C家 | intuitive |
| 08:00 | 起床 | C家 | intuitive |
| 09:00 | 前往 | 辦公室 | intuitive |
| 10:00 | 買東西 | C家 | intuitive |
| 11:00 | 買東西 | C家 | intuitive |
| 12:00 | 買東西 | C家 | intuitive |
| 13:00 | 滑手機 | C家 | intuitive |
| 14:00 | 吃飯 | C家 | intuitive |
| 15:00 | 吃飯 | C家 | intuitive |
| 16:00 | 工作 | C家 | intuitive |
| 17:00 | 散步 | C家 | intuitive |
| 18:00 | 買東西 | C家 | intuitive |
| 19:00 | 工作 | C家 | intuitive |
| 20:00 | 買東西 | C家 | intuitive |
| 21:00 | 整理家裡 | C家 | intuitive |
| 22:00 | 買東西 | C家 | intuitive |
| 23:00 | 運動 | C家 | schedule |
| 00:00 | — | C家 | — |
| 01:00 | — | C家 | — |

#### David（D）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 工作 | D家 | intuitive |
| 07:00 | 買東西 | D家 | intuitive |
| 08:00 | 買東西 | D家 | intuitive |
| 09:00 | 起床 | D家 | intuitive |
| 10:00 | 前往 | 咖啡店 | intuitive |
| 11:00 | 吃飯 | D家 | intuitive |
| 12:00 | 對話 | D家 | intuitive |
| 13:00 | 吃飯 | D家 | intuitive |
| 14:00 | 滑手機 | D家 | intuitive |
| 15:00 | 對話 | D家 | intuitive |
| 16:00 | 回家 | D家 | intuitive |
| 17:00 | 買東西 | D家 | intuitive |
| 18:00 | 回家 | D家 | intuitive |
| 19:00 | 對話 | D家 | intuitive |
| 20:00 | 對話 | D家 | intuitive |
| 21:00 | 對話 | D家 | intuitive |
| 22:00 | 整理家裡 | D家 | intuitive |
| 23:00 | 滑手機 | D家 | intuitive |
| 00:00 | 整理家裡 | D家 | intuitive |
| 01:00 | 前往 | 辦公室 | schedule |

#### Emma（E）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 運動 | E家 | intuitive |
| 07:00 | 買東西 | E家 | intuitive |
| 08:00 | 服務客人 | E家 | intuitive |
| 09:00 | 買東西 | E家 | intuitive |
| 10:00 | 散步 | E家 | intuitive |
| 11:00 | 起床 | E家 | intuitive |
| 12:00 | 整理家裡 | E家 | intuitive |
| 13:00 | 煮飯 | E家 | intuitive |
| 14:00 | 回家 | E家 | intuitive |
| 15:00 | 回家 | E家 | intuitive |
| 16:00 | 前往 | 餐廳 | intuitive |
| 17:00 | 滑手機 | E家 | intuitive |
| 18:00 | 服務客人 | E家 | intuitive |
| 19:00 | 整理家裡 | E家 | intuitive |
| 20:00 | 前往 | 餐廳 | intuitive |
| 21:00 | 滑手機 | E家 | intuitive |
| 22:00 | 整理家裡 | E家 | intuitive |
| 23:00 | 吃飯 | E家 | intuitive |
| 00:00 | 服務客人 | E家 | intuitive |
| 01:00 | 整理家裡 | E家 | schedule |

### 第 6 天

#### Amy（A）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 回家 | A家 | intuitive |
| 07:00 | 起床 | A家 | intuitive |
| 08:00 | 回家 | A家 | intuitive |
| 09:00 | 前往 | 咖啡店 | intuitive |
| 10:00 | 賣咖啡 | A家 | intuitive |
| 11:00 | 整理店面 | A家 | intuitive |
| 12:00 | 回家 | A家 | intuitive |
| 13:00 | 前往 | 咖啡店 | intuitive |
| 14:00 | 整理店面 | A家 | intuitive |
| 15:00 | 打烊 | A家 | intuitive |
| 16:00 | 打烊 | A家 | intuitive |
| 17:00 | 吃飯 | A家 | intuitive |
| 18:00 | 賣咖啡 | A家 | intuitive |
| 19:00 | 散步 | A家 | intuitive |
| 20:00 | 運動 | A家 | intuitive |
| 21:00 | 賣咖啡 | A家 | intuitive |
| 22:00 | 吃飯 | A家 | intuitive |
| 23:00 | 吃飯 | A家 | schedule |
| 00:00 | — | A家 | — |
| 01:00 | — | A家 | — |

#### Ben（B）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 買東西 | B家 | intuitive |
| 07:00 | 運動 | B家 | intuitive |
| 08:00 | 起床 | B家 | intuitive |
| 09:00 | 整理家裡 | B家 | intuitive |
| 10:00 | 補貨 | B家 | intuitive |
| 11:00 | 前往 | 超市 | intuitive |
| 12:00 | 吃飯 | B家 | intuitive |
| 13:00 | 補貨 | B家 | intuitive |
| 14:00 | 補貨 | B家 | intuitive |
| 15:00 | 買東西 | B家 | intuitive |
| 16:00 | 補貨 | B家 | intuitive |
| 17:00 | 吃飯 | B家 | intuitive |
| 18:00 | 整理家裡 | B家 | intuitive |
| 19:00 | 買東西 | B家 | intuitive |
| 20:00 | 整理家裡 | B家 | intuitive |
| 21:00 | 運動 | B家 | intuitive |
| 22:00 | 買東西 | B家 | intuitive |
| 23:00 | 散步 | B家 | schedule |
| 00:00 | — | B家 | — |
| 01:00 | — | B家 | — |

#### Claire（C）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 運動 | C家 | intuitive |
| 07:00 | 滑手機 | C家 | intuitive |
| 08:00 | 起床 | C家 | intuitive |
| 09:00 | 運動 | C家 | intuitive |
| 10:00 | 吃飯 | C家 | intuitive |
| 11:00 | 工作 | C家 | intuitive |
| 12:00 | 前往 | 辦公室 | intuitive |
| 13:00 | 滑手機 | C家 | intuitive |
| 14:00 | 工作 | C家 | intuitive |
| 15:00 | 對話 | C家 | intuitive |
| 16:00 | 運動 | C家 | intuitive |
| 17:00 | 散步 | C家 | intuitive |
| 18:00 | 散步 | C家 | intuitive |
| 19:00 | 散步 | C家 | intuitive |
| 20:00 | 休息 | C家 | intuitive |
| 21:00 | 散步 | C家 | intuitive |
| 22:00 | 前往 | 公司附近 | intuitive |
| 23:00 | 散步 | C家 | schedule |
| 00:00 | — | C家 | — |
| 01:00 | — | C家 | — |

#### David（D）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 前往 | 辦公室 | intuitive |
| 07:00 | 回家 | D家 | intuitive |
| 08:00 | 買東西 | D家 | intuitive |
| 09:00 | 起床 | D家 | intuitive |
| 10:00 | 滑手機 | D家 | intuitive |
| 11:00 | 運動 | D家 | intuitive |
| 12:00 | 滑手機 | D家 | intuitive |
| 13:00 | 吃飯 | D家 | intuitive |
| 14:00 | 回家 | D家 | intuitive |
| 15:00 | 對話 | D家 | intuitive |
| 16:00 | 運動 | D家 | intuitive |
| 17:00 | 運動 | D家 | intuitive |
| 18:00 | 買東西 | D家 | intuitive |
| 19:00 | 前往 | 咖啡店 | intuitive |
| 20:00 | 吃飯 | D家 | intuitive |
| 21:00 | 休息 | D家 | intuitive |
| 22:00 | 前往 | 辦公室 | intuitive |
| 23:00 | 運動 | D家 | intuitive |
| 00:00 | 前往 | 辦公室 | intuitive |
| 01:00 | 工作 | D家 | schedule |

#### Emma（E）

| 時間 | 行動 | 位置 | 模式 |
|------|------|------|------|
| 06:00 | 整理家裡 | E家 | intuitive |
| 07:00 | 服務客人 | E家 | intuitive |
| 08:00 | 散步 | E家 | intuitive |
| 09:00 | 散步 | E家 | intuitive |
| 10:00 | 整理家裡 | E家 | intuitive |
| 11:00 | 起床 | E家 | intuitive |
| 12:00 | 前往 | 餐廳 | intuitive |
| 13:00 | 滑手機 | E家 | intuitive |
| 14:00 | 吃飯 | E家 | intuitive |
| 15:00 | 整理家裡 | E家 | intuitive |
| 16:00 | 買東西 | E家 | intuitive |
| 17:00 | 服務客人 | E家 | intuitive |
| 18:00 | 買東西 | E家 | intuitive |
| 19:00 | 買東西 | E家 | intuitive |
| 20:00 | 滑手機 | E家 | intuitive |
| 21:00 | 吃飯 | E家 | intuitive |
| 22:00 | 運動 | E家 | intuitive |
| 23:00 | 煮飯 | E家 | intuitive |
| 00:00 | 休息 | E家 | intuitive |
| 01:00 | 滑手機 | E家 | schedule |

## 3. 對話記錄

- 第4天 19:00：**Claire** 發起對話 → **David** 接受（2 句話）
- 第4天 20:00：**Claire** 發起對話 → **David** 接受（2 句話）
- 第4天 22:00：**David** 發起對話 → **Claire** 接受（2 句話）
- 第5天 12:00：**David** 發起對話 → **Amy** 拒絕（2 句話）
- 第5天 15:00：**David** 發起對話 → **Amy** 拒絕（2 句話）
- 第5天 19:00：**Amy** 發起對話 → **David** 接受（2 句話）
- 第5天 20:00：**Amy** 發起對話 → **David** 接受（2 句話）
- 第5天 21:00：**David** 發起對話 → **Amy** 接受（2 句話）
- 第6天 15:00：**Claire** 發起對話 → **David** 接受（2 句話）

## 4. 睡眠時間統計

| 角色 | 天數 | 最後 Tick 時間 |
|------|------|--------------|
| Amy(A) | 第4天 | 01:00 |
| Ben(B) | 第4天 | 01:00 |
| Claire(C) | 第4天 | 01:00 |
| David(D) | 第4天 | 01:00 |
| Emma(E) | 第4天 | 01:00 |
| Amy(A) | 第5天 | 01:00 |
| Ben(B) | 第5天 | 01:00 |
| Claire(C) | 第5天 | 01:00 |
| David(D) | 第5天 | 01:00 |
| Emma(E) | 第5天 | 01:00 |
| Amy(A) | 第6天 | 01:00 |
| Ben(B) | 第6天 | 01:00 |
| Claire(C) | 第6天 | 01:00 |
| David(D) | 第6天 | 01:00 |
| Emma(E) | 第6天 | 01:00 |

---

*本報告由 `tests/test_full_flow.py` 自動生成（無 LLM 模式）。*
