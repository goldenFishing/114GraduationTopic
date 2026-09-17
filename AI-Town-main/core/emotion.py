# ================================================================
# core/emotion.py
# 情緒慣性與每日回歸機制
#
# 對應 ARCHITECTURE.md §6.2.7 + §2.7 情緒回歸基線
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
# ================================================================

from config.world_config import (
    VALID_EMOTIONS,
    EMOTION_RESET_THRESHOLD,
)


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
    # 取角色名字（從敘述中無法直接拿，由呼叫方在 prompt 內處理）
    # 這裡 character_name 由呼叫方包好，故 prompt 已經組好
    # 為了介面簡潔，這裡只負責 normalize
    try:
        raw = model_fn(prompt_infer_emotion("此角色",
                                              today_narrative,
                                              previous_emotion))
        return normalize_emotion(raw)
    except Exception:
        return BASELINE_EMOTION
