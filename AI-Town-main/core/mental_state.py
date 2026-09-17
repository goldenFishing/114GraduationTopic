# ================================================================
# core/mental_state.py
# 情緒 + 困惑度（合併自 core/emotion.py + core/confusion.py）
#
# 對應 ARCHITECTURE.md §6.2.6 + §6.2.7 + §2.7
# ================================================================

from config.world_config import (
    VALID_EMOTIONS,
    EMOTION_RESET_THRESHOLD,
)


# ── 情緒（Emotion）──────────────────────────────────────────────
#
# 情緒慣性與每日回歸機制
#
# 設計核心：
#   1. 預設每天睡眠後重置為「平靜」
#   2. 當天 K 值峰值超過閾值才更新情緒（呼叫模型）
#   3. 避免角色情緒集體崩壞
#
# 認知科學佐證：
#   Frijda (1988) Laws of Emotion — 情緒會自然衰減
#   Diener (2000) Subjective Well-being — 預設情緒基線
#   Russell (2003) Core Affect — 情緒是動態浮動狀態
#
# 誰會調用：
#   core/consolidation.py — 睡眠 Step 7 情緒判斷
# ────────────────────────────────────────────────────────────────

BASELINE_EMOTION = "平靜"


def should_update_emotion(today_max_K: float) -> bool:
    """
    當天 K 值峰值是否足以觸發情緒更新。

    today_max_K : 當天 process_log 中 K 值的最大值
    回傳：True → 呼叫模型推斷新情緒
          False → 直接回歸 BASELINE_EMOTION
    """
    return today_max_K >= EMOTION_RESET_THRESHOLD


def reset_to_baseline() -> str:
    """回傳預設情緒（平靜）。"""
    return BASELINE_EMOTION


def normalize_emotion(emotion_str: str) -> str:
    """
    確保情緒在 VALID_EMOTIONS 中，否則 fallback 為平靜。
    用於模型輸出後的驗證。
    """
    emotion_str = (emotion_str or "").strip()
    if emotion_str in VALID_EMOTIONS:
        return emotion_str
    return BASELINE_EMOTION


def decide_new_emotion(
    character_name: str,
    today_max_K: float,
    today_narrative: str,
    previous_emotion: str,
    model_fn=None,
) -> str:
    """
    決定睡眠後的新情緒。

    流程：
      1. today_max_K < threshold → 直接回歸平靜
      2. 否則呼叫模型推斷
      3. 模型輸出驗證並 normalize

    參數：
      character_name  : 角色名字
      today_max_K     : 當天 K 值峰值
      today_narrative : 當天 STM 敘述化文字（給模型看）
      previous_emotion: 昨天的情緒（給模型參考）
      model_fn        : loader.make_model_fn(max_tokens=10) 的 callable
                        若 None → 直接回歸平靜（用於 --no-model 模式）

    回傳：合法的情緒字串
    """
    # 沒有重大事件 → 回歸平靜
    if not should_update_emotion(today_max_K):
        return BASELINE_EMOTION

    # 沒有模型可用 → 也回歸平靜
    if model_fn is None:
        return BASELINE_EMOTION

    # 呼叫模型推斷
    from config.prompts import prompt_infer_emotion
    try:
        raw = model_fn(prompt_infer_emotion(character_name,
                                              today_narrative,
                                              previous_emotion))
        return normalize_emotion(raw)
    except Exception:
        return BASELINE_EMOTION


# ── 困惑度（Confusion）──────────────────────────────────────────
#
# 困惑度計算 C = w1·U + w2·K + w3·S
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
# ────────────────────────────────────────────────────────────────

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


def compute_K(this_tick_event: str, current_action: str,
              delta_people: dict = None) -> float:
    """
    計算衝突程度 K。Salience-First 設計：只讀本 tick 最多 1 筆事件。

    this_tick_event : 本 tick 的事件文字（interrupt 或 STM 最新 1 筆），可為 ""
    current_action  : 角色當前正在做的事
    delta_people    : {"arrived": [...], "departed": [...]}，可為 None

    回傳 0.0 ~ 1.0
    早退條件：若 this_tick_event=="" 且 delta_people 無變化 → 直接回傳 0.0（不讀任何記憶）
    """
    if delta_people is None:
        delta_people = {"arrived": [], "departed": []}

    # 早退條件：沒有事件、沒有人員變動 → K = 0
    if (not this_tick_event
            and not delta_people.get("arrived")
            and not delta_people.get("departed")):
        return 0.0

    action_lower = current_action.lower()
    event_lower  = this_tick_event.lower()

    # K_event：事件與當前行動的邏輯衝突
    conflict_score = 0.0
    for trigger_words, conflict_actions in _CONFLICT_PAIRS:
        has_trigger  = any(w in event_lower  for w in trigger_words)
        has_conflict = any(w in action_lower for w in conflict_actions)
        if has_trigger and has_conflict:
            conflict_score += 0.6

    # 情緒複雜性（從事件文字判斷）
    if any(kw in event_lower for kw in _STRONG_EMOTION_KW):
        conflict_score += 0.45
    elif any(kw in event_lower for kw in _MOD_EMOTION_KW):
        conflict_score += 0.25

    K_event  = min(conflict_score, 1.0)

    # K_social：人員變動帶來的社交衝突
    arrived  = delta_people.get("arrived",  [])
    departed = delta_people.get("departed", [])
    K_social = min(0.3 * len(arrived) + 0.2 * len(departed), 0.4)

    K = 0.5 * K_event + 0.5 * K_social
    return round(min(K, 1.0), 4)


# ================================================================
# C. 計算 S（驚訝程度）
# ================================================================

# 各地點的基礎驚訝值（無先驗記憶時的底噪）
LOCATION_BASE_S: dict = {
    "A家": 0.03, "B家": 0.03, "C家": 0.03, "D家": 0.03, "E家": 0.03,
    "咖啡店": 0.08, "超市": 0.06, "辦公室": 0.05,
    "餐廳": 0.07, "廣場": 0.06, "街道": 0.05, "公寓大廳": 0.04,
}


def compute_S(curr_people: list, location: str,
              ltm_index: dict = None,
              today_actions: list = None) -> float:
    """
    計算驚訝程度 S（Bayesian Surprise：當前組合與 LTM 先驗的差異）。

    curr_people  : 本 tick 在場的角色代號 list，如 ["A","B"] 或 []
    location     : 當前地點名稱（與 SCENE_TEXT_TABLE 同鍵）
    ltm_index    : {(location, frozenset(people)): count}，由 LTM 提供
                   若為 None 或空 → Day 1 / 冷啟動，以最大新奇度計算
    today_actions: 今天已執行的行動 list（越多樣 → variety 越高）

    回傳 0.0 ~ 1.0
    """
    if ltm_index is None:
        ltm_index = {}

    # O(1) cued retrieval
    cue  = (location, frozenset(curr_people))
    freq = ltm_index.get(cue, 0)

    # Bayesian Surprise ≈ 1 / (1 + freq)
    S_novelty  = (1.0 / (1.0 + freq)) * 0.7

    # 今日行動多樣性（越多樣越不驚訝 → 此項貢獻小幅驚訝）
    today_actions = today_actions or []
    S_variety  = min(len(set(today_actions)) / 5.0, 1.0) * 0.2

    # 地點基礎噪音
    S_base     = LOCATION_BASE_S.get(location, 0.05)

    return round(min(S_novelty + S_variety + S_base, 1.0), 4)


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
    this_tick_event: str = "",
    current_action: str = "",
    delta_people: dict = None,
    curr_people: list = None,
    location: str = "",
    ltm_index: dict = None,
    today_actions: list = None,
    weights: dict = None,
    action_candidates: list = None,
    # ── 舊參數保留（向下相容，但不再使用）──
    yolo_desc=None,
    input_text: str = "",
    scene_text: str = "",
    ltm_summary: str = "",
) -> dict:
    """
    一次計算所有指數並決定模式。

    主要參數（新）：
      this_tick_event : 本 tick 事件文字（interrupt OR stm latest this tick）
      current_action  : 角色當前行動
      delta_people    : {"arrived": [...], "departed": [...]}
      curr_people     : 當前在場角色代號 list
      location        : 當前地點
      ltm_index       : {(location, frozenset): count}
      today_actions   : 今天行動 list（for variety）

    回傳：{"U": float, "K": float, "S": float, "C": float, "mode": str}
    """
    weights = weights or {"w1": 0.4, "w2": 0.3, "w3": 0.3, "threshold": 0.5}

    U = compute_U(action_candidates or [])
    K = compute_K(this_tick_event, current_action, delta_people)
    S = compute_S(curr_people or [], location, ltm_index, today_actions)
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
