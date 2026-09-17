# ================================================================
# core/memory_graph.py
# HAM 圖譜遍歷 + 擴散激活 + 反向組句
#
# 對應 ARCHITECTURE.md §6.2.4 + §2.5
#
# 設計核心：
#   1. LTM 是純資料；這個檔案在它上面建圖譜結構
#   2. 擴散激活演算法（Anderson 1983 spreading activation）
#   3. 反向組句：命題列表 → 自然敘述（給 prompt 用）
#   4. 視覺化資料介面（給 observe/ 用）
#
# 認知科學佐證：
#   Anderson (1983) Spreading Activation Theory
#   Anderson (1996) ACT-R 活化值衰減
#   Collins & Loftus (1975) 語意網絡擴散
#
#   實證距離衰減：
#     1 跳 ~80% 活化、2 跳 ~40%、3+ 跳 <15%（低於提取閾值）
#   所以實作上：max_hops = 2 為標準
#
# 誰會調用：
#   model/prompt_builder.py    — 深思/對話組 prompt 時取相關記憶
#   core/consolidation.py      — 關係更新時取與某角色相關的命題
#   observe/memory_viewer.py   — 視覺化 LTM 圖譜
# ================================================================

from config.world_config import (
    HAM_TRAVERSE_MAX_HOPS,
    HAM_ACTIVATION_DECAY,
    HAM_RETRIEVE_THRESHOLD,
    CHARACTER_NAMES,
)


# ================================================================
# MemoryGraph
# ================================================================

class MemoryGraph:
    """
    在 LTM 上建立圖譜結構，提供擴散激活查詢與反向組句。
    """

    def __init__(self, ltm):
        """
        ltm : core.memory_ltm.LTM 實例
        """
        self.ltm = ltm

    # ================================================================
    # A. 擴散激活提取（核心方法）
    # ================================================================

    def spreading_retrieve(
        self,
        query_nodes: list,
        max_hops: int = HAM_TRAVERSE_MAX_HOPS,
        activation_decay: float = HAM_ACTIVATION_DECAY,
        threshold: float = HAM_RETRIEVE_THRESHOLD,
        top_k: int = 20,
        min_strength: float = None,
        update_access: bool = True,
    ) -> list:
        """
        從查詢節點向外擴散，收集相關命題。

        參數：
          query_nodes      : 起始節點列表（人名、地名等字串）
          max_hops         : 最多跳幾跳（預設 2）
          activation_decay : 每跳活化衰減（預設 0.4）
          threshold        : 低於此活化值的命題不取（預設 0.3）
          top_k            : 最多回傳幾筆
          min_strength     : 命題 strength 過濾門檻（None = 不過濾）
          update_access    : 命中時是否呼叫 ltm.touch()
                             （從 LTM 真的「想起來」設 True；
                               視覺化/debug 查詢設 False）

        回傳：
          [{"prop": dict, "activation": float, "hops": int}, ...]
          按 activation 降序排列
        """
        if not query_nodes:
            return []

        # 每個節點的活化值：起始節點為 1.0
        node_activation = {node: 1.0 for node in query_nodes}

        # 命中的命題：{prop_id: {"prop", "activation", "hops"}}
        hit_props = {}

        # BFS 用的當前跳數的「前沿節點」集合
        current_frontier = set(query_nodes)
        visited_nodes    = set(query_nodes)

        for hop in range(1, max_hops + 1):
            # 此跳命題的活化值（命題距離查詢源 hop-1 跳）
            prop_activation_at_hop = activation_decay ** (hop - 1)

            # 此跳下一個節點繼承的活化值
            next_node_activation = activation_decay ** hop

            next_frontier = set()

            for prop in self.ltm.get_all():
                # strength 過濾
                if (min_strength is not None
                        and prop.get("strength", 0) < min_strength):
                    continue

                subj = prop["subject"]
                obj  = prop["object"]

                # 此命題是否有一端在前沿
                hits_subj = subj in current_frontier
                hits_obj  = obj  in current_frontier

                if not (hits_subj or hits_obj):
                    continue

                # 紀錄命題（取最大活化值）
                existing = hit_props.get(prop["id"])
                if existing is None or existing["activation"] < prop_activation_at_hop:
                    hit_props[prop["id"]] = {
                        "prop":       prop,
                        "activation": prop_activation_at_hop,
                        "hops":       hop,
                    }

                # 另一端節點加入下一跳前沿（活化值衰減）
                if hits_subj and obj not in visited_nodes:
                    next_frontier.add(obj)
                    node_activation[obj] = max(
                        node_activation.get(obj, 0.0),
                        next_node_activation
                    )
                if hits_obj and subj not in visited_nodes:
                    next_frontier.add(subj)
                    node_activation[subj] = max(
                        node_activation.get(subj, 0.0),
                        next_node_activation
                    )

            visited_nodes.update(next_frontier)
            current_frontier = next_frontier
            if not current_frontier:
                break  # 沒有新節點可擴散

        # 過濾低於 threshold
        filtered = [
            h for h in hit_props.values()
            if h["activation"] >= threshold
        ]

        # 排序（活化值降序，相同則 hops 升序）
        filtered.sort(
            key=lambda x: (-x["activation"], x["hops"])
        )

        # 取 top_k
        filtered = filtered[:top_k]

        # 更新 access_count
        if update_access:
            for h in filtered:
                self.ltm.touch(h["prop"]["id"])

        return filtered

    # ================================================================
    # B. 簡易查詢：與某節點直接相關
    # ================================================================

    def get_related_to(self, node: str, max_hops: int = 2,
                        update_access: bool = False) -> list:
        """
        找與 node 相關的所有命題。
        update_access 預設 False（屬於程式內部查詢，不算「真的想起」）。

        回傳：原始 prop dict 列表。
        """
        results = self.spreading_retrieve(
            query_nodes   = [node],
            max_hops      = max_hops,
            update_access = update_access,
        )
        return [h["prop"] for h in results]

    # ================================================================
    # C. 自動從當前情境抽出查詢節點
    # ================================================================

    def auto_query_nodes(
        self,
        character_name: str,
        partner_name: str = "",
        co_located: list = None,
        recent_stm_turns: list = None,
        location: str = "",
    ) -> list:
        """
        根據當前情境，自動組成查詢節點集合。

        節點來源：
          - 角色自己
          - 對話對象（若有）
          - 同地點的人（若有）
          - 當前位置
          - 最近 3 筆 STM 中出現的角色名字

        回傳節點列表（去重）。
        """
        nodes = {character_name}

        if partner_name:
            nodes.add(partner_name)

        if co_located:
            nodes.update(co_located)

        if location:
            nodes.add(location)

        if recent_stm_turns:
            all_names = set(CHARACTER_NAMES.values())
            # 只看最近 3 筆
            for turn in recent_stm_turns[-3:]:
                text_blob = " ".join([
                    turn.get("event", {}).get("input_text", ""),
                    turn.get("event", {}).get("content", ""),
                    turn.get("event", {}).get("target", ""),
                    turn.get("inner", {}).get("thought", ""),
                ])
                for name in all_names:
                    if name in text_blob:
                        nodes.add(name)

        return list(nodes)

    # ================================================================
    # D. 反向組句（命題列表 → 自然敘述）
    # ================================================================

    def propositions_to_narrative(
        self,
        items: list,
        character_name: str,
    ) -> str:
        """
        把命題列表轉成自然敘述文字（給 prompt 注入用）。

        items : 可以是 spreading_retrieve 回傳的 [{"prop", "activation", "hops"}]
                也可以是原始 prop dict 列表

        替換規則：
          主詞 == character_name → 替換成「你」
          受詞 == character_name → 替換成「你」
        """
        if not items:
            return "（沒有相關記憶）"

        lines = []
        for item in items:
            # 取得 prop dict（兩種格式都支援）
            p = item["prop"] if "prop" in item else item

            subj_raw = p.get("subject", "")
            rel      = p.get("relation", "")
            obj_raw  = p.get("object", "")
            loc      = p.get("location") or ""
            tim      = p.get("time")     or ""

            # 自我引用替換
            subj = "你" if subj_raw == character_name else subj_raw
            obj  = "你" if obj_raw  == character_name else obj_raw

            # 組情境前綴
            ctx_parts = []
            if tim:
                ctx_parts.append(tim)
            if loc:
                ctx_parts.append(f"在{loc}")
            ctx = "".join(ctx_parts)

            # 組句
            if ctx:
                line = f"{subj}{ctx}{rel}{obj}"
            else:
                line = f"{subj}{rel}{obj}"

            lines.append(line + "。")

        return "".join(lines)

    # ================================================================
    # E. 視覺化資料介面（給 observe/memory_viewer.py 用）
    # ================================================================

    def get_all_nodes(self) -> list:
        """
        回傳所有圖譜節點（給 vis.js / cytoscape.js 用）。

        節點型別啟發式判斷：
          - 在 CHARACTER_NAMES 中 → "person"
          - 在 VALID_LOCATIONS 中 → "location"
          - 其他 → "concept"

        每個節點：
          {
            id:         "Amy",
            label:      "Amy",
            type:       "person" | "location" | "concept",
            value:      avg strength (給節點大小視覺化用),
            prop_count: 涉及此節點的命題數
          }
        """
        from config.action_list import VALID_LOCATIONS

        person_names   = set(CHARACTER_NAMES.values())
        location_names = set(VALID_LOCATIONS)

        # 收集每個節點涉及的命題
        node_props = {}
        for prop in self.ltm.get_all():
            for endpoint in (prop["subject"], prop["object"]):
                if not endpoint:
                    continue
                node_props.setdefault(endpoint, []).append(prop)

        nodes = []
        for name, props in node_props.items():
            avg_strength = sum(p.get("strength", 0) for p in props) / len(props)

            if name in person_names:
                ntype = "person"
            elif name in location_names:
                ntype = "location"
            else:
                ntype = "concept"

            nodes.append({
                "id":         name,
                "label":      name,
                "type":       ntype,
                "value":      round(avg_strength, 3),
                "prop_count": len(props),
            })

        return nodes

    def get_all_edges(self) -> list:
        """
        回傳所有圖譜邊（HAM 命題即為邊）。

        每條邊：
          {
            from:     "Amy",
            to:       "Ben",
            label:    "遇見",
            strength: 0.8,
            prop_id:  "L001",
            location: "咖啡廳",
            time:     "早上"
          }
        """
        edges = []
        for prop in self.ltm.get_all():
            edges.append({
                "from":     prop["subject"],
                "to":       prop["object"],
                "label":    prop["relation"],
                "strength": round(prop.get("strength", 0), 3),
                "prop_id":  prop["id"],
                "location": prop.get("location"),
                "time":     prop.get("time"),
            })
        return edges
