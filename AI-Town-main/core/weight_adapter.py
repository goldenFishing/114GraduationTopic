# ================================================================
# core/weight_adapter.py
# 動態 Markov 權重適應器
#
# 每個角色有獨立的可學習權重（alpha/beta/gamma），
# 每天睡覺時根據當日 tick 記錄做 SGD-like 更新。
#
# 誰會調用：
#   core/character.py     — get/set markov_weights
#   core/consolidation.py — 睡眠時呼叫 update_weights
# ================================================================


class WeightAdapter:
    """
    Per-character adaptive Markov weights.
    每天睡覺時根據當日 tick 記錄做 SGD-like 更新。
    """

    DEFAULT_WEIGHTS = {"alpha": 0.40, "beta": 0.35, "gamma": 0.25}
    LEARNING_RATE = 0.05
    MIN_WEIGHT = 0.05
    MAX_WEIGHT = 0.85

    def __init__(self, weights: dict = None):
        """
        接受初始權重 dict，預設用 DEFAULT_WEIGHTS。
        """
        if weights is None:
            self._weights = dict(self.DEFAULT_WEIGHTS)
        else:
            # 確保三個 key 都存在，缺少的用 DEFAULT 補
            self._weights = {
                "alpha": float(weights.get("alpha", self.DEFAULT_WEIGHTS["alpha"])),
                "beta":  float(weights.get("beta",  self.DEFAULT_WEIGHTS["beta"])),
                "gamma": float(weights.get("gamma", self.DEFAULT_WEIGHTS["gamma"])),
            }
        # tick 記錄列表（每天清空）
        self._tick_records: list = []

    def get_weights(self) -> dict:
        """回傳 {alpha, beta, gamma}。"""
        return dict(self._weights)

    def record_tick(self, chosen_action: str, reward: float, breakdown: dict):
        """
        記錄一個 tick 的結果。

        breakdown 格式：
          {
            "schedule":  {action: prob, ...},
            "inertia":   {action: prob, ...},
            "situation": {action: prob, ...},
          }

        從 breakdown 中取出 chosen_action 在各 source 的機率，
        儲存供 update_weights() 使用。
        """
        sched_p = breakdown.get("schedule",  {}).get(chosen_action, 0.0)
        iner_p  = breakdown.get("inertia",   {}).get(chosen_action, 0.0)
        situ_p  = breakdown.get("situation", {}).get(chosen_action, 0.0)

        self._tick_records.append({
            "reward":  float(reward),
            "sched_p": float(sched_p),
            "iner_p":  float(iner_p),
            "situ_p":  float(situ_p),
        })

    def update_weights(self):
        """
        每天睡覺時呼叫，用累積的 tick 記錄做 SGD-like 更新。
        若無 tick 記錄則空跑無副作用。
        """
        if not self._tick_records:
            return

        alpha = self._weights["alpha"]
        beta  = self._weights["beta"]
        gamma = self._weights["gamma"]
        lr    = self.LEARNING_RATE

        for rec in self._tick_records:
            r       = rec["reward"]
            sched_p = rec["sched_p"]
            iner_p  = rec["iner_p"]
            situ_p  = rec["situ_p"]

            alpha += lr * r * (sched_p - alpha)
            beta  += lr * r * (iner_p  - beta)
            gamma += lr * r * (situ_p  - gamma)

        # Clip 到 [MIN_WEIGHT, MAX_WEIGHT]
        alpha = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, alpha))
        beta  = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, beta))
        gamma = max(self.MIN_WEIGHT, min(self.MAX_WEIGHT, gamma))

        # 正規化使總和 = 1
        total = alpha + beta + gamma
        if total > 0:
            alpha = round(alpha / total, 4)
            beta  = round(beta  / total, 4)
            gamma = round(gamma / total, 4)
            # 修正浮點誤差：把餘差加回 alpha
            remainder = round(1.0 - (alpha + beta + gamma), 4)
            alpha = round(alpha + remainder, 4)

        self._weights = {
            "alpha": alpha,
            "beta":  beta,
            "gamma": gamma,
        }

        # 清空 tick 記錄
        self._tick_records = []

    def to_dict(self) -> dict:
        """序列化：{"alpha":..., "beta":..., "gamma":...}"""
        return dict(self._weights)

    @classmethod
    def from_dict(cls, data: dict) -> "WeightAdapter":
        """classmethod，從 dict 還原 WeightAdapter。"""
        return cls(weights=data)
