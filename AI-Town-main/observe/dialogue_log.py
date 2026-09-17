# ================================================================
# observe/dialogue_log.py
# 對話記錄整理工具
#
# 對應 ARCHITECTURE.md §6.5.3
# ================================================================

from config.world_config import CHARACTER_NAMES


def format_dialogue_history(history: list) -> list:
    """
    把 manager 的 _dialogue_history 整理成可讀格式。

    輸入結構（單筆）：
      {
        "initiator":  "A",
        "responder":  "B",
        "accepted":   True,
        "turns":      [{"speaker": "A", "msg": "..."}, ...]
      }
    """
    formatted = []
    for entry in history:
        init_code = entry.get("initiator", "")
        resp_code = entry.get("responder", "")
        init_name = CHARACTER_NAMES.get(init_code, init_code)
        resp_name = CHARACTER_NAMES.get(resp_code, resp_code)

        turns_text = []
        for t in entry.get("turns", []):
            spk_code = t.get("speaker", "")
            spk_name = CHARACTER_NAMES.get(spk_code, spk_code)
            turns_text.append({
                "speaker_code": spk_code,
                "speaker_name": spk_name,
                "msg":          t.get("msg", ""),
            })

        formatted.append({
            "initiator_code": init_code,
            "initiator_name": init_name,
            "responder_code": resp_code,
            "responder_name": resp_name,
            "accepted":       entry.get("accepted", False),
            "rounds":         len(turns_text) // 2 if turns_text else 0,
            "turns":          turns_text,
        })
    return formatted


def filter_by_character(history: list, code: str) -> list:
    """只取含指定角色的對話。"""
    return [
        e for e in history
        if e.get("initiator_code") == code or e.get("responder_code") == code
    ]


def filter_by_day(simulation_data: dict, day: int) -> list:
    """從完整模擬資料中提取指定天的對話。"""
    if day < 1 or day > len(simulation_data.get("days", [])):
        return []
    day_data = simulation_data["days"][day - 1]
    all_dialogues = []
    for tick_data in day_data.get("ticks", []):
        all_dialogues.extend(tick_data.get("dialogues", []))
    return all_dialogues
