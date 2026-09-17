# ================================================================
# core/consolidation.py
# 睡眠濃縮主流程
#
# 對應 ARCHITECTURE.md §6.2.8 + §4.2.2
#
# 12 步驟流程：
#   Step 1  : 取出今日 STM 敘述
#   Step 2  : 模型抽取 HAM（從敘述）
#   Step 3  : 模型篩選重要 HAM
#   Step 4  : 寫入 LTM
#   Step 5  : 模型生成新 LTM 摘要
#   Step 6  : 模型更新關係摘要
#   Step 7  : 情緒判斷（重大事件才呼叫模型）
#   Step 8  : 模型生成隔天時間表（呼叫 agent/scheduler）
#   Step 9  : 規則檢查時間表
#   Step 10 : LTM 衰減 + 修剪
#   Step 11 : STM 縮減（摘要 + 最近 5 筆）
#   Step 12 : 推進到下一天
#
# 認知科學佐證：
#   Diekelmann & Born (2010) 睡眠時海馬迴 → 新皮質鞏固
#   Tulving (1972) 情節 → 語意轉換
#
# 誰會調用：
#   agent/agent.py — sleep() 方法
# ================================================================

import json
import re

from config.world_config import CHARACTER_NAMES
from config.prompts import (
    prompt_extract_ham,
    prompt_select_ltm,
    prompt_ltm_summary,
    prompt_update_relationship,
    prompt_infer_emotion,
)
from config.model_config import (
    CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS,
    CONSOLIDATE_SELECT_MAX_TOKENS,
    CONSOLIDATE_SUMMARY_MAX_TOKENS,
    CONSOLIDATE_RELATION_MAX_TOKENS,
    CONSOLIDATE_EMOTION_MAX_TOKENS,
    SCHEDULE_GEN_MAX_TOKENS,
)
from core.emotion import (
    should_update_emotion,
    reset_to_baseline,
    normalize_emotion,
    BASELINE_EMOTION,
)


# ================================================================
# 主入口
# ================================================================

def consolidate(character, stm, ltm, process_log, loader) -> dict:
    """
    執行完整睡眠濃縮。

    參數：
      character    : Character 物件
      stm          : STM 物件
      ltm          : LTM 物件
      process_log  : 當天 process_log list
      loader       : ModelLoader（用 make_model_fn / make_consolidation_fn）
                     loader = None 時走 --no-model fallback

    回傳濃縮報告 dict（給觀察工具用）
    """
    # ─ Step 1：取敘述 ────────────────────────────────────────────
    narrative = stm.get_today_narrative()
    if not narrative or narrative == "（今天還沒有任何記憶）":
        return _empty_report(character, ltm)

    # 工廠：取得各步驟的 model_fn
    def _fn(max_tokens):
        if loader is None:
            return None
        return loader.make_model_fn(max_new_tokens=max_tokens)

    # ─ Step 2：抽 HAM ────────────────────────────────────────────
    extracted = _extract_ham(
        character, narrative,
        _fn(CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS)
    )

    # ─ Step 3：篩選 ──────────────────────────────────────────────
    important = _select_important(
        character, narrative, extracted,
        _fn(CONSOLIDATE_SELECT_MAX_TOKENS)
    )

    # ─ Step 4：寫 LTM ────────────────────────────────────────────
    ltm.encode_batch(important, day=character.day)

    # ─ Step 5：LTM 摘要 ──────────────────────────────────────────
    new_summary = _generate_summary(
        character, ltm, _fn(CONSOLIDATE_SUMMARY_MAX_TOKENS)
    )
    ltm.set_summary(new_summary)

    # ─ Step 6：關係更新 ──────────────────────────────────────────
    relationship_changes = _update_relationships(
        character, narrative, _fn(CONSOLIDATE_RELATION_MAX_TOKENS)
    )

    # ─ Step 7：情緒 ──────────────────────────────────────────────
    today_max_K = _today_max_K(process_log)
    old_emotion = character.emotion
    new_emotion = _decide_emotion(
        character, narrative, today_max_K,
        _fn(CONSOLIDATE_EMOTION_MAX_TOKENS)
    )
    character.emotion = new_emotion

    # ─ Step 8：時間表 ────────────────────────────────────────────
    from agent.scheduler import generate_next_day_schedule
    important_events_text = _format_important_events(important)
    new_schedule = generate_next_day_schedule(
        character, narrative, important_events_text,
        _fn(SCHEDULE_GEN_MAX_TOKENS)
    )

    # ─ Step 9：寫入新時間表（已在 scheduler 內做過 validate）─────
    character.replace_schedule(new_schedule)

    # ─ Step 10：LTM 衰減 + 修剪 ──────────────────────────────────
    ltm.apply_decay()
    pruned = ltm.prune()

    # ─ Step 11：STM 縮減 ─────────────────────────────────────────
    next_day = character.day + 1
    stm.shrink_to_summary(new_summary, new_day=next_day)

    # ─ Step 12：推進日 ───────────────────────────────────────────
    character.advance_day()
    # 注意：advance_day 已經重置 schedule completed，但我們剛剛 replace
    # 過了，這裡再次重置確保所有 slot 都是 completed=False
    for slot in character.get_schedule():
        slot["completed"] = False

    return {
        "ham_extracted":        len(extracted),
        "ham_kept":             len(important),
        "ltm_total":            ltm.count(),
        "ltm_pruned":           pruned,
        "ltm_summary":          new_summary,
        "relationship_updates": relationship_changes,
        "emotion_change":       {"from": old_emotion, "to": new_emotion},
        "next_day_schedule":    new_schedule,
        "stm_kept":             stm.count(),
        "today_max_K":          today_max_K,
    }


# ================================================================
# 各步驟內部實作
# ================================================================

def _extract_ham(character, narrative, model_fn) -> list:
    """Step 2：從敘述抽 HAM 5 元組。"""
    if model_fn is None:
        return _fallback_extract_ham(character, narrative)

    try:
        prompt = prompt_extract_ham(character.name, narrative)
        raw = model_fn(prompt)
        return _parse_ham_lines(raw)
    except Exception:
        return _fallback_extract_ham(character, narrative)


def _select_important(character, narrative, props, model_fn) -> list:
    """Step 3：篩選重要 HAM。"""
    if not props:
        return []
    if model_fn is None or len(props) <= 5:
        # 沒模型或本來就少 → 全留
        return props[:5]

    try:
        props_text = _format_props_pipe(props)
        prompt = prompt_select_ltm(character.name, narrative, props_text)
        raw = model_fn(prompt)
        selected = _parse_ham_lines(raw)
        return selected[:5] if selected else props[:5]
    except Exception:
        return props[:5]


def _generate_summary(character, ltm, model_fn) -> str:
    """Step 5：生成 LTM 摘要。"""
    if ltm.count() == 0:
        return ""
    if model_fn is None:
        # 沒模型 fallback：用最近命題簡述
        latest = ltm.get_all()[-5:]
        return ltm.to_readable(latest).replace("\n", " ")[:200]

    try:
        prompt = prompt_ltm_summary(character.name, ltm.to_text())
        summary = model_fn(prompt).strip()
        return summary[:200] if len(summary) > 200 else summary
    except Exception:
        return ""


def _update_relationships(character, narrative, model_fn) -> dict:
    """
    Step 6：對所有「今天有任何相關」的角色更新關係摘要。
    回傳 {target_code: new_summary} 變更紀錄。
    """
    changes = {}

    # 找出今天敘述中出現的角色名字
    involved_codes = []
    for code, name in CHARACTER_NAMES.items():
        if code == character.code:
            continue
        if name in narrative:
            involved_codes.append(code)

    if model_fn is None:
        return changes

    for code in involved_codes:
        name    = CHARACTER_NAMES[code]
        rel     = character.get_relationship(code)
        initial = rel.get("initial", "")
        old_sum = rel.get("summary", "")

        try:
            prompt = prompt_update_relationship(
                character.name, name, initial, old_sum, narrative
            )
            new_summary = model_fn(prompt).strip()
            if new_summary and new_summary != "無變化":
                character.update_relationship_summary(code, new_summary)
                changes[code] = new_summary
        except Exception:
            continue

    return changes


def _decide_emotion(character, narrative, today_max_K, model_fn) -> str:
    """Step 7：判斷新情緒。"""
    if not should_update_emotion(today_max_K):
        return reset_to_baseline()
    if model_fn is None:
        return reset_to_baseline()

    try:
        prompt = prompt_infer_emotion(
            character.name, narrative, character.emotion
        )
        raw = model_fn(prompt)
        return normalize_emotion(raw)
    except Exception:
        return reset_to_baseline()


# ================================================================
# 工具函式
# ================================================================

def _today_max_K(process_log: list) -> float:
    """取當天 K 值峰值。"""
    if not process_log:
        return 0.0
    ks = []
    for entry in process_log:
        c = entry.get("confusion", {})
        if isinstance(c, dict):
            ks.append(c.get("K", 0.0))
    return max(ks) if ks else 0.0


def _parse_ham_lines(raw: str) -> list:
    """
    從模型輸出解析 HAM 命題（每行一筆，| 分隔）。

    格式：subject | relation | object | location | time
    """
    if not raw:
        return []

    # 移除 markdown 標記
    raw = re.sub(r"```\w*|```", "", raw).strip()

    props = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 移除 - 開頭
        if line.startswith("-"):
            line = line[1:].strip()
        # 必須有 |
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        # 補足 5 個欄位
        while len(parts) < 5:
            parts.append("")

        loc = parts[3] if parts[3] not in ("", "無", "無地點") else None
        tim = parts[4] if parts[4] not in ("", "無", "無時間") else None

        props.append({
            "subject":  parts[0],
            "relation": parts[1],
            "object":   parts[2],
            "location": loc,
            "time":     tim,
        })

    return props


def _format_props_pipe(props: list) -> str:
    """命題列表 → pipe 分隔文字。"""
    lines = []
    for p in props:
        loc = p.get("location") or "無"
        tim = p.get("time")     or "無"
        lines.append(
            f"{p.get('subject','')} | {p.get('relation','')} | "
            f"{p.get('object','')} | {loc} | {tim}"
        )
    return "\n".join(lines)


def _format_important_events(props: list) -> str:
    """重要事件文字（給時間表生成 prompt 用）。"""
    if not props:
        return ""
    lines = []
    for p in props:
        lines.append(
            f"- {p.get('subject','')} {p.get('relation','')} {p.get('object','')}"
        )
    return "\n".join(lines)


def _fallback_extract_ham(character, narrative: str) -> list:
    """
    --no-model 模式或模型失敗時的 fallback。
    從敘述中抓出角色名字，建立簡單命題。
    """
    props = []
    for code, name in CHARACTER_NAMES.items():
        if code == character.code:
            continue
        if name in narrative:
            props.append({
                "subject":  character.name,
                "relation": "互動",
                "object":   name,
                "location": None,
                "time":     None,
            })
    # 至少加一條當天的基本命題
    if not props:
        props.append({
            "subject":  character.name,
            "relation": "度過",
            "object":   "平凡的一天",
            "location": None,
            "time":     None,
        })
    return props[:5]


def _empty_report(character, ltm) -> dict:
    """STM 完全空時的空報告。"""
    return {
        "ham_extracted":        0,
        "ham_kept":             0,
        "ltm_total":            ltm.count(),
        "ltm_pruned":           0,
        "ltm_summary":          ltm.get_summary(),
        "relationship_updates": {},
        "emotion_change":       {"from": character.emotion,
                                 "to":   character.emotion},
        "next_day_schedule":    character.get_schedule(),
        "stm_kept":             0,
        "today_max_K":          0.0,
    }
