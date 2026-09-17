# ================================================================
# core/tick_value.py
# Tick 間行動價值追蹤器（RL-style eligibility trace）
#
# 設計原理：
#   每個 tick 結束後，根據「結果」計算 reward，
#   累積更新每個行動的 value_score，並帶入下一 tick 的 Markov 計算。
#   透過指數衰減（DECAY）讓遠端 tick 的影響逐漸消退。
#
# 類比：
#   Q-learning 的 Q(s,a) 更新，但這裡 state 簡化為「當前情緒+困惑度」
#   eligibility trace：recent actions 得到更多更新
#
# Reward 來源：
#   ① 情緒改善 / 惡化
#   ② 困惑度下降（行動讓環境變「可預期」）
#   ③ 對話被接受（社交成功）
#   ④ 行動符合時間表（目標達成）
#
# 接入點：
#   agent/agent.py → decide() 結束後呼叫 update()
#   markov_engine.py → compute_action_probabilities() 接收 action_values
# ================================================================

# ──────────────────────────────────────────────
# 超參數
# ──────────────────────────────────────────────

# 每 tick 的衰減係數（類似 eligibility trace 的 λ）
VALUE_DECAY = 0.85

# 各 reward 信號強度
REWARD_EMOTION_IMPROVE  = +0.50   # 負面 → 正面情緒
REWARD_EMOTION_NEUTRAL  = +0.15   # 負面 → 平靜
REWARD_EMOTION_WORSEN   = -0.45   # 正面/平靜 → 負面
REWARD_CONFUSION_DROP   = +0.30   # C 值明顯下降（行動消解不確定性）
REWARD_CONFUSION_SPIKE  = -0.35   # C 值明顯上升（行動引發更多不確定）
REWARD_DIALOGUE_ACCEPT  = +0.25   # 對話被接受（social affordance 達成）
REWARD_SCHEDULE_HIT     = +0.20   # 行動完全符合時間表

# 情緒分類
POSITIVE_EMOTIONS = {"開心", "興奮", "滿足"}
NEUTRAL_EMOTIONS  = {"平靜"}
NEGATIVE_EMOTIONS = {"憤怒", "悲傷", "焦慮", "恐懼", "失落", "不安"}

# C 值變化閾值
CONFUSION_DROP_THRESHOLD  =  0.12   # C 下降超過此值 → 正向 reward
CONFUSION_SPIKE_THRESHOLD =  0.15   # C 上升超過此值 → 負向 reward


# ================================================================
# ActionValueTracker
# ================================================================

class ActionValueTracker:
    """
    記錄每個行動的累積 value score，提供 tick 間的 RL-style 影響。

    使用方式：
        tracker = ActionValueTracker()

        # 每 tick 開始前：衰減
        tracker.decay()

        # 執行行動後：更新
        reward = tracker.compute_reward(
            action, prev_emotion, curr_emotion,
            prev_C, curr_C,
            dialogue_accepted, schedule_hit
        )
        tracker.update(action, reward)

        # 傳入 Markov 引擎
        probs = compute_action_probabilities(
            ...,
            action_values=tracker.get_scores()
        )
    """

    def __init__(self):
        # {action_verb: accumulated_value_score}
        self.values: dict = {}

        # 每 tick 完整紀錄（供 dashboard 可視化）
        self.history: list = []   # [{tick, action, reward, values_snapshot}, ...]

    # ────────────────────────────────────────────
    # 核心操作
    # ────────────────────────────────────────────

    def decay(self):
        """每 tick 開始前呼叫：所有 value score 乘以衰減係數。"""
        self.values = {a: v * VALUE_DECAY for a, v in self.values.items()}

    def update(self, action: str, reward: float):
        """
        根據 reward 更新行動的 value score。
        正 reward → 下次更傾向執行此行動
        負 reward → 下次更迴避
        """
        current = self.values.get(action, 0.0)
        self.values[action] = current + reward

    def get_scores(self) -> dict:
        """回傳當前 value scores 供 Markov 引擎使用。"""
        return dict(self.values)

    def reset(self):
        """睡眠後重置（或保留讓跨天效果延續，目前選擇重置）。"""
        self.values.clear()
        self.history.clear()

    # ────────────────────────────────────────────
    # Reward 計算
    # ────────────────────────────────────────────

    def compute_reward(
        self,
        action:            str,
        prev_emotion:      str,
        curr_emotion:      str,
        prev_C:            float,
        curr_C:            float,
        dialogue_accepted: bool  = False,
        schedule_hit:      bool  = False,
        tick_id:           str   = "",
    ) -> float:
        """
        根據當前 tick 結果計算 reward，並記錄歷史。

        參數：
          action            : 本 tick 執行的行動動詞
          prev_emotion      : 行動前的情緒
          curr_emotion      : 行動後的情緒（下一狀態）
          prev_C            : 行動前的困惑度 C 值
          curr_C            : 行動後的困惑度 C 值
          dialogue_accepted : 若本 tick 為對話且被接受 → True
          schedule_hit      : 行動完全符合時間表 → True
          tick_id           : 用於 history 記錄
        """
        reward = 0.0
        components = {}

        # ① 情緒 reward
        em_r = self._emotion_reward(prev_emotion, curr_emotion)
        reward += em_r
        components["emotion"] = round(em_r, 3)

        # ② 困惑度 reward
        conf_r = self._confusion_reward(prev_C, curr_C)
        reward += conf_r
        components["confusion"] = round(conf_r, 3)

        # ③ 對話接受 reward
        if dialogue_accepted and action == "對話":
            reward += REWARD_DIALOGUE_ACCEPT
            components["dialogue"] = REWARD_DIALOGUE_ACCEPT

        # ④ 時間表符合 reward
        if schedule_hit:
            reward += REWARD_SCHEDULE_HIT
            components["schedule"] = REWARD_SCHEDULE_HIT

        # 記錄歷史
        self.history.append({
            "tick_id":    tick_id,
            "action":     action,
            "reward":     round(reward, 4),
            "components": components,
            "values_after": {
                a: round(v + (reward if a == action else 0), 4)
                for a, v in self.values.items()
            },
        })

        return reward

    # ────────────────────────────────────────────
    # 內部工具
    # ────────────────────────────────────────────

    def _emotion_reward(self, prev: str, curr: str) -> float:
        """情緒變化的 reward。"""
        if prev in NEGATIVE_EMOTIONS:
            if curr in POSITIVE_EMOTIONS:
                return REWARD_EMOTION_IMPROVE
            if curr in NEUTRAL_EMOTIONS:
                return REWARD_EMOTION_NEUTRAL
        if prev in POSITIVE_EMOTIONS or prev in NEUTRAL_EMOTIONS:
            if curr in NEGATIVE_EMOTIONS:
                return REWARD_EMOTION_WORSEN
        return 0.0

    def _confusion_reward(self, prev_C: float, curr_C: float) -> float:
        """困惑度 C 值變化的 reward。"""
        delta = prev_C - curr_C   # 正 = C 下降（好）
        if delta >= CONFUSION_DROP_THRESHOLD:
            # C 下降越多，reward 越高（最高封頂在 DROP 值）
            return min(REWARD_CONFUSION_DROP,
                       REWARD_CONFUSION_DROP * (delta / 0.3))
        if -delta >= CONFUSION_SPIKE_THRESHOLD:
            return max(REWARD_CONFUSION_SPIKE,
                       REWARD_CONFUSION_SPIKE * (-delta / 0.3))
        return 0.0

    # ────────────────────────────────────────────
    # Debug / 視覺化
    # ────────────────────────────────────────────

    def top_values(self, n: int = 5) -> list:
        """回傳 value score 最高的 n 個行動（供 dashboard 顯示）。"""
        sorted_items = sorted(
            self.values.items(), key=lambda x: x[1], reverse=True
        )
        return [(a, round(v, 4)) for a, v in sorted_items[:n]]

    def summary_str(self) -> str:
        top = self.top_values(3)
        parts = [f"{a}:{v:+.3f}" for a, v in top]
        return "  |  ".join(parts) if parts else "(empty)"
