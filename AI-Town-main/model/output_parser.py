# ================================================================
# model/output_parser.py
# 解析模型輸出（新版 block 格式）
#
# 對應 ARCHITECTURE.md §6.4.6
#
# 模型輸出格式：
#   [ACTION] 對話
#   [TARGET] Amy
#   [CONTENT] 你今天看起來累累的
#
#   [THOUGHT] 我想關心她但不知道怎麼開口
#
#   [HAM]
#   - Amy | 看起來 | 疲憊 | 咖啡廳 | 下午
#   - Ben | 想 | 關心Amy | 咖啡廳 | 下午
#   [/HAM]
#
# 改寫重點：
#   1. ACTION 從「動詞:目標」改為三個獨立區塊 ACTION/TARGET/CONTENT
#   2. HAM 從 JSON 改為 pipe 分隔（更穩定）
#   3. 解析失敗 fallback 用 ACTION_DEFAULT_ON_INVALID
# ================================================================

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
