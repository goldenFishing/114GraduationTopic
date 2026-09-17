# ================================================================
# core/confusion.py
# 困惑度計算 C = w1·U + w2·K + w3·S
#
# 對應 ARCHITECTURE.md §6.2.6
#
# 設計核心：
#   1. U（不確定性）：Markov 機率分布的離散程度
#   2. K（衝突程度）：邏輯衝突 + 情緒複雜性
#   3. S（驚訝程度）：當前場景與 LTM 預期的差異
#   4. C 是 System 1 / System 2 切換的閘門
#   5. K ≥ 0.5 強制 deliberate（情緒衝突 override）
#   6. 情緒影響閾值（心情差時更難深思，傾向直覺反應）
#
# 認知科學佐證：
#   Shenhav, Botvinick & Cohen (2013) ACC 衝突偵測
#   Kahneman (2011) System 1 / System 2
#   Botvinick & Cohen (2014) 認知控制與 ACC
#
# 誰會調用：
#   agent/agent.py            — 決策前計算
#   core/character.py         — get_confusion_threshold 用 adjust_threshold_by_emotion
#   agent/interrupt.py        — 中斷後判斷是否深思
# ================================================================

from config.world_config import (
    VALID_EMOTIONS,
    EMOTION_RESET_THRESHOLD,
)


# 強制 deliberate 的 K 門檻
DELIBERATE_K_OVERRIDE = 0.5


# ================================================================
# A. 計算 U（不確定性）
# ================================================================

def compute_U(action_candidates: list) -> float:
    """
    根據候選行動的機率分布計算不確定性。

    candidates : [{"action": str, "score": float}, ...]
                 通常由 Markov 機率分布轉成

    分布越分散（最高分與第二高分差距越小）→ U 越高
    只有一個候選或差距很大 → U = 0（很確定）
    """
    if not action_candidates or len(action_candidates) < 2:
        return 0.0

    scores = sorted(
        [c.get("score", 0.0) for c in action_candidates],
        reverse=True,
    )
    top1, top2 = scores[0], scores[1]
    gap = top1 - top2
    U = max(0.0, 1.0 - gap * 2)
    return round(min(U, 1.0), 4)


# ================================================================
# B. 計算 K（衝突程度）
# ================================================================

# 邏輯衝突偵測 pair：(觸發詞, 當前正在做的衝突行動)
_CONFLICT_PAIRS = [
    (["離開", "走了", "再見"],   ["等待", "休息", "工作"]),
    (["緊急", "快", "危險"],     ["休息", "睡覺", "滑手機"]),
    (["來了", "到了", "進來"],   ["工作", "整理"]),
]

# 強情緒：思緒混亂、無法處理
_STRONG_EMOTION_KW = [
    "混亂", "一片混亂", "說不清楚", "無法理解",
    "心亂", "不知所措", "不知道如何",
    "思緒很亂", "思緒紊亂",
]

# 一般情緒/關係複雜
_MOD_EMOTION_KW = [
    "心跳加速", "心跳", "緊張", "期待", "在意",
    "感情", "告白", "表白", "暗戀", "心動",
    "情緒", "心情複雜", "心情有些",
    "思緒", "心裡有些",
]


def compute_K(yolo_desc: str, input_text: str,
              current_action: str,
              scene_text: str = "") -> float:
    """
    計算衝突程度 K。

    yolo_desc      : YOLO 偵測描述
    input_text     : 接收到的對話或事件
    current_action : 角色當前正在做的事
    scene_text     : 當前場景描述

    回傳 0.0 ~ 1.0
    """
    conflict_score = 0.0

    combined     = f"{yolo_desc} {input_text}".lower()
    action_lower = current_action.lower()

    # 邏輯衝突
    for trigger_words, conflict_actions in _CONFLICT_PAIRS:
        has_trigger  = any(w in combined     for w in trigger_words)
        has_conflict = any(w in action_lower for w in conflict_actions)
        if has_trigger and has_conflict:
            conflict_score += 0.6

    # 情緒複雜性
    combined_all = f"{combined} {scene_text}".lower()
    if any(kw in combined_all for kw in _STRONG_EMOTION_KW):
        conflict_score += 0.45
    elif any(kw in combined_all for kw in _MOD_EMOTION_KW):
        conflict_score += 0.25

    return round(min(conflict_score, 1.0), 4)


# ================================================================
# C. 計算 S（驚訝程度）
# ================================================================

_HIGH_SURPRISE_KW = [
    "陌生人", "從沒見過", "完全不認識", "第一次見到", "突然闖入"
]
_MID_HIGH_SURPRISE_KW = ["第一次", "從未"]
_MID_SURPRISE_KW      = ["意外", "沒想到", "不可思議"]
_LOW_SURPRISE_KW      = ["突然"]


def compute_S(scene_text: str, ltm_summary: str,
              today_actions: list = None) -> float:
    """
    計算驚訝程度 S（當前場景與 LTM 預期的差異）。

    LTM 為空（第一天）→ S = 0
    """
    if not ltm_summary:
        return 0.0

    surprise = 0.0
    if any(kw in scene_text for kw in _HIGH_SURPRISE_KW):
        surprise += 0.6
    elif any(kw in scene_text for kw in _MID_HIGH_SURPRISE_KW):
        surprise += 0.5
    elif any(kw in scene_text for kw in _MID_SURPRISE_KW):
        surprise += 0.35
    elif any(kw in scene_text for kw in _LOW_SURPRISE_KW):
        surprise += 0.25

    return round(min(surprise, 1.0), 4)


# ================================================================
# D. 加權計算 C
# ================================================================

def compute_C(U: float, K: float, S: float, weights: dict) -> float:
    """C = w1·U + w2·K + w3·S，clamp 到 1.0"""
    w1 = weights.get("w1", 0.4)
    w2 = weights.get("w2", 0.3)
    w3 = weights.get("w3", 0.3)
    C = w1 * U + w2 * K + w3 * S
    return round(min(C, 1.0), 4)


# ================================================================
# E. 模式決策
# ================================================================

def decide_mode(C: float, threshold: float, K: float = 0.0) -> str:
    """
    回傳 "intuitive" 或 "deliberate"。

    K ≥ DELIBERATE_K_OVERRIDE → 強制 deliberate
    否則比較 C 和 threshold
    """
    if K >= DELIBERATE_K_OVERRIDE:
        return "deliberate"
    return "deliberate" if C >= threshold else "intuitive"


# ================================================================
# F. 主入口
# ================================================================

def evaluate(
    yolo_desc: str = "",
    input_text: str = "",
    current_action: str = "",
    scene_text: str = "",
    ltm_summary: str = "",
    today_actions: list = None,
    weights: dict = None,
    action_candidates: list = None,
) -> dict:
    """
    一次計算所有指數並決定模式。

    回傳：
      {
        "U": float, "K": float, "S": float, "C": float,
        "mode": "intuitive" | "deliberate"
      }
    """
    weights = weights or {"w1": 0.4, "w2": 0.3, "w3": 0.3, "threshold": 0.5}

    U = compute_U(action_candidates or [])
    K = compute_K(yolo_desc, input_text, current_action, scene_text)
    S = compute_S(scene_text, ltm_summary, today_actions)
    C = compute_C(U, K, S, weights)

    mode = decide_mode(C, weights.get("threshold", 0.5), K)

    return {"U": U, "K": K, "S": S, "C": C, "mode": mode}


# ================================================================
# G. 情緒調整閾值
#
# 設計邏輯（用戶要求）：
#   「心情差時更難思考、容易直覺反應」
#   → 負面情緒 → threshold 提高 → 更難觸發 deliberate
#   → 正面情緒 → threshold 接近 base
#
# 平靜：base
# 開心/興奮：base（無變化或略高）
# 緊張/不安/困惑：base + 0.1（情緒不穩 → 容易直覺反應）
# 難過/疲憊：base + 0.15（沒能量深思）
# ================================================================

_EMOTION_THRESHOLD_ADJUST = {
    "平靜": 0.0,
    "開心": 0.0,
    "興奮": 0.0,
    "緊張": +0.10,
    "不安": +0.10,
    "困惑": +0.10,
    "難過": +0.15,
    "疲憊": +0.15,
}


def adjust_threshold_by_emotion(base_threshold: float, emotion: str) -> float:
    """
    依情緒調整困惑度閾值。
    被 core/character.py get_confusion_threshold() 呼叫。

    調整後的 threshold 越高 → 越難觸發 deliberate（更傾向直覺反應）
    """
    adj = _EMOTION_THRESHOLD_ADJUST.get(emotion, 0.0)
    final = base_threshold + adj
    return round(max(0.0, min(final, 1.0)), 4)
