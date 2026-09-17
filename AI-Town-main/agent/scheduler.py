# ================================================================
# agent/scheduler.py
# 時間表生成器（睡眠濃縮 Step 8 呼叫）
#
# 對應 ARCHITECTURE.md §6.3.3
#
# 流程：
#   1. 取出該角色職業的範本
#   2. 組 prompt（個性 + LTM 摘要 + 今日重要事件 + 範本）
#   3. 模型生成新時間表（JSON list）
#   4. 解析失敗 → fallback 用範本
#   5. 規則檢查必要時段（REQUIRED_SLOTS）
#   6. 失敗 → 補必要時段
#   7. 回傳新時間表
#
# 誰會調用：
#   core/consolidation.py — 睡眠 Step 8
# ================================================================

import json
import re

from config.schedule_templates import (
    get_template,
    get_required_slots,
    validate_schedule,
)
from config.prompts import prompt_generate_schedule


def generate_next_day_schedule(
    character,
    today_narrative: str,
    important_events: str,
    model_fn=None,
) -> list:
    """
    為角色生成隔天的時間表。

    參數：
      character         : Character 物件
      today_narrative   : 當天 STM 敘述化
      important_events  : 今天的重要事件摘要（從 LTM 提取或濃縮中產生）
      model_fn          : loader.make_model_fn(SCHEDULE_GEN_MAX_TOKENS)
                          若 None → 直接 fallback 範本

    回傳：新時間表 slots（list of dict）
    """
    template = get_template(character.role)

    # 沒有模型 → fallback 範本
    if model_fn is None:
        return _normalize_slots(template)

    # 組 prompt
    yesterday_text = _format_slots_for_prompt(character.get_schedule())
    template_text  = _format_slots_for_prompt(template)
    ltm_summary    = ""  # 由 consolidation 已更新，但這裡為簡化先不重複取

    try:
        from core.memory_ltm import LTM
        # 假設 character._data["ltm"]["ltm_summary"] 已被 set
        ltm_summary = character._data.get("ltm", {}).get("ltm_summary", "")
    except Exception:
        pass

    prompt = prompt_generate_schedule(
        character_name          = character.name,
        personality_short       = character.get_personality(short=True),
        habit                   = character.get_habit(),
        role                    = character.role,
        day                     = character.day + 1,
        ltm_summary             = ltm_summary,
        today_important_events  = important_events,
        yesterday_schedule_text = yesterday_text,
        template_text           = template_text,
    )

    # 呼叫模型
    try:
        raw = model_fn(prompt)
        slots = _parse_json_list(raw)
    except Exception:
        slots = []

    # 解析失敗 → fallback
    if not slots:
        return _normalize_slots(template)

    # 規則檢查
    is_valid, missing = validate_schedule(slots, character.role)
    if not is_valid:
        # 補必要時段（從範本中取）
        slots = _fix_missing_slots(slots, missing, template)

    return _normalize_slots(slots)


# ================================================================
# 內部工具
# ================================================================

def _format_slots_for_prompt(slots: list) -> str:
    """把 slot list 轉成可讀文字給 prompt 用。"""
    if not slots:
        return "（無）"
    lines = []
    for s in slots:
        loc = s.get("location", "")
        lines.append(f"  {s['time']}  {s['action']}  {loc}")
    return "\n".join(lines)


def _parse_json_list(raw: str) -> list:
    """從模型輸出解析 JSON list。"""
    try:
        # 移除 markdown code block 標記
        raw = re.sub(r"```json|```", "", raw).strip()
        # 取第一個 [...] block
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except Exception:
        pass
    return []


def _fix_missing_slots(slots: list, missing: list,
                       template: list) -> list:
    """從範本中找出缺少的必要時段，補進 slots。"""
    template_by_action = {s["action"]: s for s in template}
    for action in missing:
        if action in template_by_action:
            slots.append(dict(template_by_action[action]))
    # 按時間排序
    slots.sort(key=lambda s: s.get("time", "23:59"))
    return slots


def _normalize_slots(slots: list) -> list:
    """確保每個 slot 都有完整欄位。"""
    normalized = []
    for s in slots:
        normalized.append({
            "time":      s.get("time", "00:00"),
            "action":    s.get("action", "休息"),
            "location":  s.get("location", ""),
            "type":      s.get("type", "fixed"),
            "completed": False,  # 新時間表全部未完成
        })
    return normalized
