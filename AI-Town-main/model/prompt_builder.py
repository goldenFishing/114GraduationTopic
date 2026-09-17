# ================================================================
# model/prompt_builder.py
# Prompt 組裝
#
# 對應 ARCHITECTURE.md §6.4.5
#
# 設計核心：
#   1. 只負責「組 prompt」，不呼叫模型
#   2. 整合 STM 敘述化 + LTM 圖譜反向組句
#   3. 兩個主要入口：build_deliberate / build_dialogue
#
# 誰會調用：
#   agent/agent.py — 走 deliberate 路徑時組 prompt
#                   生成對話回應時組 prompt
# ================================================================

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
        perception        : {"location", "yolo_desc", "scene_text"}
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
