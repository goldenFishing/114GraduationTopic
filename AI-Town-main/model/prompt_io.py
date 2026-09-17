# ================================================================
# model/prompt_io.py
# 合併：prompt_builder + output_parser
# ================================================================

# ── PromptBuilder ──────────────────────────────────────────────────────────────

from config.prompts import prompt_deliberate, prompt_dialogue
from config.model_config import STM_TOKEN_BUDGET, LTM_TOKEN_BUDGET
from config.world_config import CHARACTER_NAMES


class PromptBuilder:
    """
    依角色狀態與當前情境組裝 prompt。
    """

    def __init__(self, character, stm, ltm, memory_graph):
        """
        character    : Character 物件
        stm          : STM 物件
        ltm          : LTM 物件
        memory_graph : MemoryGraph 物件
        """
        self.character = character
        self.stm       = stm
        self.ltm       = ltm
        self.graph     = memory_graph

    # ================================================================
    # A. 深思路徑（決策）
    # ================================================================

    def build_deliberate(self,
                          scene: str,
                          perception: dict = None,
                          co_located_codes: list = None,
                          input_text: str = "") -> str:
        """
        組裝深思路徑 prompt。

        scene             : 場景文字（含時間+地點）
        perception        : {"location", "yolo_desc"}
                            yolo_desc 現為角色代號 list（["A","B"] 或 []）
                            scene_text 已移除，改由 SCENE_TEXT_TABLE 查表
        co_located_codes  : 同地點角色代號列表
        input_text        : 當前事件文字（對話輸入等）
        """
        char = self.character
        co_located_names = [
            CHARACTER_NAMES.get(c, c) for c in (co_located_codes or [])
        ]

        # STM 敘述化（受 token 預算限制）
        stm_narrative = self.stm.get_today_narrative(
            max_chars = STM_TOKEN_BUDGET * 2
        )

        # LTM 圖譜反向組句
        query_nodes = self.graph.auto_query_nodes(
            character_name   = char.name,
            partner_name     = co_located_names[0] if co_located_names else "",
            co_located       = co_located_names,
            recent_stm_turns = self.stm.get_recent(3),
            location         = (perception or {}).get("location", ""),
        )
        ltm_hits = self.graph.spreading_retrieve(
            query_nodes   = query_nodes,
            top_k         = 15,
            update_access = True,
        )
        ltm_narrative = self.graph.propositions_to_narrative(
            ltm_hits, char.name
        )
        ltm_narrative = _truncate(ltm_narrative, LTM_TOKEN_BUDGET * 2)

        # 關係文字（取第一個同地點角色，主要決策對象）
        rel_text = ""
        if co_located_codes:
            rel_text = char.get_relationship_text(
                co_located_codes[0], include_summary=True
            )

        # 同地點角色字串
        co_text = "、".join(co_located_names) if co_located_names else ""

        return prompt_deliberate(
            character_name    = char.name,
            personality       = char.get_personality(short=False),
            habit             = char.get_habit(),
            emotion           = char.emotion,
            relationship_text = rel_text,
            stm_narrative     = stm_narrative,
            ltm_narrative     = ltm_narrative,
            scene             = scene,
            co_located_text   = co_text,
            current_event     = input_text,
        )

    # ================================================================
    # B. 對話路徑
    # ================================================================

    def build_dialogue(self,
                        scene: str,
                        partner_code: str,
                        partner_message: str,
                        recent_dialogue: str = "") -> str:
        """
        組裝對話一輪的 prompt。

        scene           : 場景文字
        partner_code    : 對話對象代號
        partner_message : 對方剛剛說的話
        recent_dialogue : 最近 3 輪對話歷史（雙方說了什麼）
        """
        char = self.character
        partner_name = CHARACTER_NAMES.get(partner_code, partner_code)

        # STM 敘述
        stm_narrative = self.stm.get_today_narrative(
            max_chars = STM_TOKEN_BUDGET * 2
        )

        # LTM 圖譜（以對方為查詢核心）
        query_nodes = self.graph.auto_query_nodes(
            character_name   = char.name,
            partner_name     = partner_name,
            recent_stm_turns = self.stm.get_recent(3),
        )
        ltm_hits = self.graph.spreading_retrieve(
            query_nodes   = query_nodes,
            top_k         = 10,
            update_access = True,
        )
        ltm_narrative = self.graph.propositions_to_narrative(
            ltm_hits, char.name
        )
        ltm_narrative = _truncate(ltm_narrative, LTM_TOKEN_BUDGET * 2)

        # 關係（完整版）
        rel_text = char.get_relationship_text(
            partner_code, include_summary=True
        )

        return prompt_dialogue(
            character_name    = char.name,
            personality       = char.get_personality(short=False),
            emotion           = char.emotion,
            partner_name      = partner_name,
            relationship_text = rel_text,
            stm_narrative     = stm_narrative,
            ltm_narrative     = ltm_narrative,
            scene             = scene,
            recent_dialogue   = recent_dialogue,
            partner_message   = partner_message,
        )


# ================================================================
# 工具
# ================================================================

def _truncate(text: str, max_chars: int) -> str:
    """超過 max_chars 截斷。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...（已截斷）"


# ── OutputParser ───────────────────────────────────────────────────────────────

import re

from config.action_list import (
    VALID_ACTIONS,
    ACTION_DEFAULT_ON_INVALID,
)


def parse_decision_output(raw: str) -> dict:
    """
    解析模型的完整輸出。

    回傳：
      {
        "action":  str,        # 動詞，例如「對話」「前往」
        "target":  str,        # 目標（對話對象/地點/空）
        "content": str,        # 對話內容（其他行動空）
        "thought": str,
        "ham":     list,       # [{subject, relation, object, location, time}, ...]
        "raw":     str
      }
    """
    action  = _parse_block_value(raw, "ACTION")
    target  = _parse_block_value(raw, "TARGET")
    content = _parse_block_value(raw, "CONTENT")
    thought = _parse_block_multiline(raw, "THOUGHT")
    ham     = _parse_ham_block(raw)

    # 驗證 action
    action = _validate_action(action)

    return {
        "action":  action,
        "target":  target,
        "content": content,
        "thought": thought,
        "ham":     ham,
        "raw":     raw,
    }


# ================================================================
# 內部解析
# ================================================================

def _parse_block_value(raw: str, tag: str) -> str:
    """
    解析 [TAG] xxx 的單行內容（只取同一行）。
    遇到下一行（即使內容是另一個 [TAG]）就停。
    """
    pattern_open = f"[{tag}]"
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith(pattern_open):
            # 取 [TAG] 後的內容（可能有冒號）
            value = stripped[len(pattern_open):].strip()
            if value.startswith(":"):
                value = value[1:].strip()
            return value
    return ""


def _parse_block_multiline(raw: str, tag: str) -> str:
    """
    解析 [TAG] 後直到下一個 [TAG] 之前的多行內容。
    用於 THOUGHT。
    """
    pattern_open = f"[{tag}]"
    capturing = False
    collected = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if not capturing:
            if stripped.startswith(pattern_open):
                # 同行可能有部分內容
                first = stripped[len(pattern_open):].strip()
                if first.startswith(":"):
                    first = first[1:].strip()
                if first:
                    collected.append(first)
                capturing = True
        else:
            # 遇到下一個 [TAG] 停止
            if stripped.startswith("[") and "]" in stripped:
                break
            if stripped:
                collected.append(stripped)
    return " ".join(collected)


def _parse_ham_block(raw: str) -> list:
    """
    從 [HAM]...[/HAM] block 中解析命題。

    每行格式：- subject | relation | object | location | time
    """
    # 優先抓 block 形式
    match = re.search(r"\[HAM\]\s*(.*?)\s*\[/HAM\]", raw, re.DOTALL)
    if match:
        block_text = match.group(1)
    else:
        # fallback：找 [HAM] 後面所有內容
        match = re.search(r"\[HAM\]\s*(.*)", raw, re.DOTALL)
        if not match:
            return []
        block_text = match.group(1)

    return _parse_ham_lines(block_text)


def _parse_ham_lines(text: str) -> list:
    """
    從文字解析每行 HAM 命題。
    格式：subject | relation | object | location | time
    """
    props = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
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


def _validate_action(action: str) -> str:
    """
    驗證 action 是否在 VALID_ACTIONS 中。

    不在 → 嘗試找文字中包含的合法動詞 → 都沒有 fallback。
    """
    action = action.strip()
    if action in VALID_ACTIONS:
        return action

    for valid in VALID_ACTIONS:
        if valid in action:
            return valid

    return ACTION_DEFAULT_ON_INVALID
