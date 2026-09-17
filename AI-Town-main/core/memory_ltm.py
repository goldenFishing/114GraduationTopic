# ================================================================
# core/memory_ltm.py
# 長期記憶（LTM）— HAM 5 元組命題的純資料結構
#
# 對應 ARCHITECTURE.md §6.2.3 + §7.4
#
# 設計核心：
#   1. 純 CRUD + 衰減/修剪，不含圖譜遍歷
#   2. 圖譜遍歷邏輯獨立在 core/memory_graph.py
#   3. 直接操作 character_data["ltm"]，不複製資料
#
# 認知科學佐證：
#   Anderson & Bower (1973) HAM — 5 元組命題網絡儲存
#   Anderson (1983) ACT-R — 活化值衰減
#   常被提取的記憶衰減慢（access_count 高 → 衰減率低）
#
# 命題格式：
#   {
#     "id":           "L001",
#     "subject":      "Amy",
#     "relation":     "遇見",
#     "object":       "Ben",
#     "location":     "咖啡廳",       # 可空
#     "time":         "第3天 早上",   # 可空
#     "strength":     1.0,            # 0.0 ~ 1.0
#     "access_count": 0,              # 被提取次數
#     "encoded_day":  3               # 第幾天存入
#   }
#
# 誰會調用：
#   agent/manager.py            — 建立 LTM 物件
#   core/consolidation.py       — 寫入/衰減/修剪/摘要
#   core/memory_graph.py        — 取所有命題建圖譜
#   model/prompt_builder.py     — 條件查詢備用
#   observe/memory_viewer.py    — 視覺化
# ================================================================

from config.world_config import LTM_DECAY_RATE, LTM_FORGET_THRESHOLD


# ================================================================
# LTM
# ================================================================

class LTM:
    """
    長期記憶管理。
    直接操作 Character._data["ltm"]，不複製資料。
    """

    def __init__(self, character_data: dict):
        # 確保結構存在
        ltm_dict = character_data.setdefault("ltm", {})
        ltm_dict.setdefault("ltm_summary", "")
        ltm_dict.setdefault("propositions", [])
        self._ltm = ltm_dict

    # ================================================================
    # A. 寫入
    # ================================================================

    def encode(self, subject: str, relation: str, obj: str,
               location: str = None, time: str = None,
               day: int = 1) -> dict:
        """
        寫入一筆 HAM 命題。

        location 和 time 可為 None 或空字串。
        回傳寫入的命題 dict。
        """
        prop = {
            "id":           self._next_id(),
            "subject":      subject,
            "relation":     relation,
            "object":       obj,
            "location":     location or None,
            "time":         time or None,
            "strength":     1.0,
            "access_count": 0,
            "encoded_day":  day,
        }
        self._ltm["propositions"].append(prop)
        return prop

    def encode_batch(self, propositions: list, day: int = 1):
        """
        批次寫入命題 list（睡眠濃縮 Step 4 用）。

        每個元素必須含 subject / relation / object，
        location 和 time 可省略。
        """
        for p in propositions:
            self.encode(
                subject  = p.get("subject", ""),
                relation = p.get("relation", ""),
                obj      = p.get("object", ""),
                location = p.get("location"),
                time     = p.get("time"),
                day      = day,
            )

    # ================================================================
    # B. 查詢
    # ================================================================

    def retrieve(self,
                 query_subject:  str = None,
                 query_relation: str = None,
                 query_object:   str = None,
                 query_location: str = None,
                 query_time:     str = None,
                 top_k: int = 10,
                 update_access: bool = False) -> list:
        """
        條件查詢命題。所有條件為 AND，None 表示不限制。

        update_access : 是否在命中時更新 access_count（預設 False）
                        圖譜遍歷會自己處理 access_count，
                        所以這裡預設不更新，避免重複計數。
                        observe / debug 查詢用 False；
                        如果是真的「想起」這筆記憶，呼叫方應傳 True。

        回傳符合條件的命題 list（最多 top_k 筆）。
        """
        results = []
        for prop in self._ltm["propositions"]:
            if query_subject  and prop["subject"]  != query_subject:  continue
            if query_relation and prop["relation"] != query_relation: continue
            if query_object   and prop["object"]   != query_object:   continue
            if query_location and prop.get("location") != query_location: continue
            if query_time     and prop.get("time")     != query_time:     continue

            if update_access:
                self._touch(prop)

            results.append(prop)
            if len(results) >= top_k:
                break

        return results

    def get_all(self) -> list:
        """回傳所有命題（不更新 access_count）。"""
        return self._ltm["propositions"]

    def get_by_id(self, prop_id: str) -> dict | None:
        """用 ID 取單筆命題。"""
        for prop in self._ltm["propositions"]:
            if prop["id"] == prop_id:
                return prop
        return None

    def count(self) -> int:
        return len(self._ltm["propositions"])

    # ================================================================
    # C. 摘要
    # ================================================================

    def get_summary(self) -> str:
        """回傳 LTM 壓縮摘要文字（由 consolidation 在睡眠時更新）。"""
        return self._ltm.get("ltm_summary", "")

    def set_summary(self, summary: str):
        """睡眠濃縮 Step 5 呼叫。"""
        self._ltm["ltm_summary"] = summary

    # ================================================================
    # D. 衰減與修剪（睡眠濃縮 Step 10 呼叫）
    # ================================================================

    def apply_decay(self):
        """
        對所有命題套用衰減。

        公式：
          actual_decay = LTM_DECAY_RATE / (1 + access_count × 0.5)
          strength = max(0.0, strength - actual_decay)

        效果：
          access_count = 0  → 每天衰減 0.05
          access_count = 2  → 每天衰減 0.025
          access_count = 10 → 每天衰減 ≈ 0.008
        """
        for prop in self._ltm["propositions"]:
            ac = prop.get("access_count", 0)
            actual_decay = LTM_DECAY_RATE / (1 + ac * 0.5)
            prop["strength"] = max(0.0, prop["strength"] - actual_decay)

    def prune(self) -> int:
        """
        刪除 strength 低於 LTM_FORGET_THRESHOLD 的命題。
        回傳刪除筆數。
        """
        before = self.count()
        self._ltm["propositions"] = [
            p for p in self._ltm["propositions"]
            if p["strength"] >= LTM_FORGET_THRESHOLD
        ]
        return before - self.count()

    def delete(self, prop_id: str) -> bool:
        """
        手動刪除指定 ID 的命題（debug / 手動修正用）。
        回傳是否成功刪除。
        """
        before = self.count()
        self._ltm["propositions"] = [
            p for p in self._ltm["propositions"] if p["id"] != prop_id
        ]
        return self.count() < before

    # ================================================================
    # E. 內部：更新 access_count（給 memory_graph 用）
    # ================================================================

    def touch(self, prop_id: str):
        """
        標記某命題為「剛被提取」：
          access_count += 1
          strength 重置為 1.0

        memory_graph 的擴散激活完成後，對所有命中的命題呼叫此方法。
        """
        prop = self.get_by_id(prop_id)
        if prop:
            self._touch(prop)

    def _touch(self, prop: dict):
        """內部：對命題物件直接操作。"""
        prop["access_count"] = prop.get("access_count", 0) + 1
        prop["strength"]     = 1.0

    # ================================================================
    # F. 格式化輸出
    # ================================================================

    def to_text(self, props: list = None) -> str:
        """
        命題列表 → pipe 分隔文字（給 prompt 注入用，和輸出格式一致）。

        範例：
          Amy | 遇見 | David | 咖啡廳 | 早上
          Ben | 工作 | 超市 | 無 | 無

        props=None 時用全部命題。
        """
        if props is None:
            props = self._ltm["propositions"]
        if not props:
            return "（目前沒有相關記憶）"

        lines = []
        for p in props:
            loc = p.get("location") or "無"
            tim = p.get("time")     or "無"
            lines.append(
                f"{p['subject']} | {p['relation']} | {p['object']} | {loc} | {tim}"
            )
        return "\n".join(lines)

    def to_readable(self, props: list = None) -> str:
        """
        命題列表 → 自然語言（給觀察工具 / log 用）。

        範例：
          - Amy 在咖啡廳 早上 遇見 David
          - Ben 工作 超市
        """
        if props is None:
            props = self._ltm["propositions"]
        if not props:
            return "（目前沒有相關記憶）"

        lines = []
        for p in props:
            ctx_parts = []
            if p.get("location"):
                ctx_parts.append(f"在{p['location']}")
            if p.get("time"):
                ctx_parts.append(p["time"])
            ctx = " ".join(ctx_parts)
            if ctx:
                lines.append(
                    f"- {p['subject']} {ctx} {p['relation']} {p['object']}"
                )
            else:
                lines.append(f"- {p['subject']} {p['relation']} {p['object']}")
        return "\n".join(lines)

    # ================================================================
    # G. 工具
    # ================================================================

    def _next_id(self) -> str:
        """
        產生下一個命題 ID（格式 L001）。
        用已有 ID 的最大值 +1，避免 prune 後 ID 重複。
        """
        props = self._ltm["propositions"]
        if not props:
            return "L001"
        max_n = 0
        for p in props:
            try:
                n = int(p["id"][1:])
                if n > max_n:
                    max_n = n
            except (ValueError, KeyError):
                pass
        return f"L{max_n + 1:03d}"
