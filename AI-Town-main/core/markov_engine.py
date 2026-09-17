# ================================================================
# core/markov_engine.py
# Type 1（System 1）直覺思考的決策引擎
#
# 對應 ARCHITECTURE.md §6.2.5 + §3.1
#
# 設計核心：
#   1. 完全不呼叫模型，純統計+規則
#   2. 三來源加權機率：
#        α 時間表（schedule）
#        β 行為慣性（STM 轉移）
#        γ 情境觸發（YOLO + 場景 + 情緒）
#   3. 重大事件時切換權重，但不歸零任何行動
#   4. 採樣（加權隨機，不是 argmax）
#
# 認知科學佐證：
#   Wood & Neal (2007) — 人類 43% 行為是習慣
#   Gibson (1979) Affordance — 環境邀請特定行動
#   Schank & Abelson (1977) Script — 情境腳本驅動行為
#
# 誰會調用：
#   agent/agent.py        — Markov 路徑決策
#   agent/interrupt.py    — YOLO 中斷後重新評估
#   observe/dashboard_html.py — 顯示機率分布
# ================================================================

import math
import random

from config.action_list import (
    VALID_ACTIONS, VALID_LOCATIONS,
    ACTION_SEPARATOR, ACTION_TO_CATEGORY,
)
from config.triggers import (
    ACTION_KEYWORD_BOOST,
    KEYWORD_BOOST_PER_HIT,
    EMOTION_TO_ACTION_BOOST,
)
from config.world_config import (
    MARKOV_WEIGHTS_NORMAL,
    MARKOV_WEIGHTS_EVENT,
    SLEEP_ACTION,
    WAKE_ACTION,
)


# 最低保底機率（避免任何行動完全變 0）
MIN_PROB_FLOOR = 0.005


# ================================================================
# 主入口：算機率
# ================================================================

def compute_action_probabilities(
    schedule_slot: dict = None,
    stm_recent_verbs: list = None,
    perception: dict = None,
    co_located: list = None,
    emotion: str = "平靜",
    is_major_event: bool = False,
    weights: dict = None,
    action_values: dict = None,
    return_breakdown: bool = False,
):
    """
    算出每個合法行動的機率（總和 = 1）。

    參數：
      schedule_slot     : 當前時間表時段 {time, action, location} 或 None
      stm_recent_verbs  : 最近行動動詞列表（從 STM.get_recent_actions()）
      perception        : {"location", "yolo_desc", "scene_text"}
      co_located        : 同地點角色名字列表
      emotion           : 當前情緒
      is_major_event    : True 時切換到 EVENT 權重
      weights           : 自訂 {alpha, beta, gamma, delta}（None = 用 config 預設）
      action_values     : RL-style tick 間繼承價值分數 {action: float}
                          由 ActionValueTracker.get_scores() 提供
                          正值 → 上次這個行動帶來好結果 → 機率提升
                          負值 → 上次這個行動帶來壞結果 → 機率抑制
      return_breakdown  : True → 回傳含分項分數的 dict

    回傳：
      預設：{action: prob} 字典
      return_breakdown=True：
        {"probs": {...}, "breakdown": {"schedule":..., "inertia":...,
                                       "situation":..., "value":...,
                                       "weights": (...)}}
    """
    # 選擇權重
    w = weights or (MARKOV_WEIGHTS_EVENT if is_major_event
                    else MARKOV_WEIGHTS_NORMAL)
    alpha = w.get("alpha", 0.4)
    beta  = w.get("beta",  0.3)
    gamma = w.get("gamma", 0.3)
    # delta：RL 價值源的權重
    # 當有真實 action_values 時才有意義；預設 0.15（不搶奪其他三源太多）
    delta = w.get("delta", 0.15) if action_values else 0.0

    # 三來源分數
    sched_scores = schedule_score(schedule_slot, perception)
    iner_scores  = inertia_score(stm_recent_verbs or [])
    situ_scores  = situation_score(perception or {}, co_located or [], emotion)

    # 各來源 softmax 正規化成機率分布
    sched_probs = _softmax_dict(sched_scores)
    iner_probs  = _softmax_dict(iner_scores)
    situ_probs  = _softmax_dict(situ_scores)

    # 第四源：RL 價值繼承分布
    # action_values 可含負值（抑制），先 shift 成非負再 softmax
    if action_values and delta > 0:
        # 補齊所有合法行動（沒有紀錄的給 0）
        full_values = {a: action_values.get(a, 0.0) for a in VALID_ACTIONS}
        # shift：最小值歸 0（保持相對差距，允許 softmax 運算）
        min_v = min(full_values.values())
        shifted = {a: v - min_v for a, v in full_values.items()}
        value_probs = _softmax_dict(shifted)
    else:
        value_probs = {a: 1.0 / len(VALID_ACTIONS) for a in VALID_ACTIONS}
        delta = 0.0

    # 四源加權合併（總和 ≈ alpha+beta+gamma+delta，後面再正規化）
    final_probs = {}
    for action in VALID_ACTIONS:
        p = (alpha * sched_probs.get(action, 0.0)
             + beta  * iner_probs.get(action, 0.0)
             + gamma * situ_probs.get(action, 0.0)
             + delta * value_probs.get(action, 0.0))
        final_probs[action] = max(p, MIN_PROB_FLOOR)

    # 正規化（因為加了保底且 alpha+beta+gamma+delta 不一定 = 1）
    total = sum(final_probs.values())
    final_probs = {a: round(p / total, 4) for a, p in final_probs.items()}

    if return_breakdown:
        return {
            "probs": final_probs,
            "breakdown": {
                "schedule":  sched_probs,
                "inertia":   iner_probs,
                "situation": situ_probs,
                "value":     value_probs,
                "weights":   (alpha, beta, gamma, delta),
            }
        }
    return final_probs


# ================================================================
# A. 時間表分數
# ================================================================

def schedule_score(slot: dict, perception: dict = None) -> dict:
    """
    根據當前時間表時段，回傳每個行動的契合分數。

    完全匹配 → 1.0
    同類別   → 0.5
    其他     → 0.0
    位置匹配獎勵 +0.2（候選的可能目標地點符合 perception.location）
    """
    scores = {a: 0.0 for a in VALID_ACTIONS}

    if not slot:
        return scores

    target_action = slot.get("action", "")
    target_loc    = slot.get("location", "")
    target_cat    = ACTION_TO_CATEGORY.get(target_action, None)

    for action in VALID_ACTIONS:
        # 完全匹配
        if action == target_action:
            scores[action] = 1.0
        # 同類別
        elif target_cat and ACTION_TO_CATEGORY.get(action) == target_cat:
            scores[action] = 0.5

    # 位置匹配獎勵：若時間表目標地點 = 候選地點且當前不在 → 提升「前往」
    if perception and target_loc:
        current_loc = perception.get("location", "")
        # 不在目的地 → 「前往」提升
        if target_loc and current_loc != target_loc:
            scores["前往"] = max(scores["前往"], 0.6)
        # 已在目的地 → 「前往」降低
        elif current_loc == target_loc:
            scores["前往"] = scores["前往"] * 0.3

    return scores


# ================================================================
# B. 行為慣性分數
# ================================================================

def inertia_score(stm_recent_verbs: list) -> dict:
    """
    根據最近行動動詞序列，計算轉移機率分數。

    歷史不足（< 2 筆）→ 均勻分數（讓 schedule/situation 主導）
    否則 → 從最後一個動詞的轉移統計 + Laplace 平滑
    """
    if len(stm_recent_verbs) < 2:
        # 均勻分數（後續會 softmax 變均勻機率）
        return {a: 0.0 for a in VALID_ACTIONS}

    current_verb = stm_recent_verbs[-1]
    transitions = {}
    for i in range(len(stm_recent_verbs) - 1):
        if stm_recent_verbs[i] == current_verb:
            nxt = stm_recent_verbs[i + 1]
            transitions[nxt] = transitions.get(nxt, 0) + 1

    if not transitions:
        # 沒觀察到此動詞的轉移 → 退回頻率
        for v in stm_recent_verbs:
            transitions[v] = transitions.get(v, 0) + 1

    # Laplace 平滑：每個合法行動 +1
    scores = {}
    for action in VALID_ACTIONS:
        # 用 log 是為了讓後續 softmax 等效於頻率比例
        count = transitions.get(action, 0) + 1
        scores[action] = math.log(count)

    return scores


# ================================================================
# C. 情境分數
# ================================================================

def situation_score(perception: dict,
                     co_located: list,
                     emotion: str) -> dict:
    """
    根據 perception、同地點角色、情緒，計算情境分數。

    來源：
      1. ACTION_KEYWORD_BOOST 命中（每命中 +0.15）
      2. EMOTION_TO_ACTION_BOOST 加分
      3. 同地點有人 → 對話 +0.3
    """
    scores = {a: 0.0 for a in VALID_ACTIONS}

    # 合併掃描文字
    text_blob = " ".join([
        perception.get("scene_text", ""),
        perception.get("yolo_desc", ""),
        perception.get("location", ""),
    ]) + " ".join(co_located)

    # 1. 關鍵字命中
    for action, keywords in ACTION_KEYWORD_BOOST.items():
        hits = sum(1 for kw in keywords if kw in text_blob)
        if hits > 0:
            scores[action] += hits * KEYWORD_BOOST_PER_HIT

    # 2. 情緒影響
    emotion_boost = EMOTION_TO_ACTION_BOOST.get(emotion, {})
    for action, boost in emotion_boost.items():
        if action in scores:
            scores[action] += boost

    # 3. 同地點有人 → 對話加成
    if co_located:
        scores["對話"] += 0.3

    return scores


# ================================================================
# D. 採樣
# ================================================================

def sample_action(probs: dict, exclude: list = None) -> str:
    """
    加權隨機採樣（非 argmax）。
    保持自然的行為變化。
    """
    if not probs:
        return "休息"

    candidates = {
        a: p for a, p in probs.items()
        if not exclude or a not in exclude
    }
    if not candidates:
        return "休息"

    actions = list(candidates.keys())
    weights = [candidates[a] for a in actions]
    return random.choices(actions, weights=weights, k=1)[0]


# ================================================================
# E. 對話目標解析
# ================================================================

def resolve_dialogue_target(probs: dict,
                              co_located: list,
                              boost_factor: float = 2.5) -> tuple:
    """
    決定最終動詞與目標。

    若選到「對話」：
      有人 → ("對話", 第一個同地點角色名字)
      無人 → 排除「對話」重新採樣，回傳 (其他動詞, "")

    若選到「前往」：
      回傳 ("前往", "")  目標地點由 agent 從時間表/情境補

    同地點有人時，對話機率先放大再採樣（不影響其他來源計算，只在這裡放大）
    """
    if co_located and probs.get("對話", 0) > 0:
        boosted = dict(probs)
        boosted["對話"] = probs["對話"] * boost_factor
        s = sum(boosted.values())
        boosted = {a: p / s for a, p in boosted.items()}
        best = sample_action(boosted)
    else:
        best = sample_action(probs)

    if best == "對話":
        if co_located:
            return "對話", co_located[0]
        # 沒人可對話 → 排除重抽
        best = sample_action(probs, exclude=["對話"])
        return best, ""

    if best == "前往":
        return "前往", ""

    return best, ""


# ================================================================
# F. 格式化機率顯示（debug / 視覺化）
# ================================================================

def format_probs_display(probs: dict, top_n: int = 5) -> str:
    """格式化機率分布為可讀字串。"""
    sorted_items = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    parts = [f"{a}:{p:.3f}" for a, p in sorted_items[:top_n]]
    return ", ".join(parts)


# ================================================================
# 內部工具
# ================================================================

def _softmax_dict(scores: dict, temperature: float = 1.0) -> dict:
    """對 scores 取 softmax，回傳機率分布。"""
    if not scores:
        return {}
    vals = list(scores.values())
    max_v = max(vals) if vals else 0.0
    exps = {k: math.exp((v - max_v) / temperature) for k, v in scores.items()}
    total = sum(exps.values())
    if total == 0:
        n = len(scores)
        return {k: 1.0 / n for k in scores}
    return {k: e / total for k, e in exps.items()}
