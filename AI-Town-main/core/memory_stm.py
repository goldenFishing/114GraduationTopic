# ================================================================
# core/memory_stm.py
# 短期記憶（STM）— 情節敘述形式
#
# 對應 ARCHITECTURE.md §6.2.2 + §7.2
#
# 設計核心：
#   1. 不含 HAM（HAM 在睡眠濃縮時才從敘述中抽取）
#   2. 三層結構：perception（感知）/ event（事件）/ inner（內在）
#   3. 不限筆數，只有安全閥（SAFETY_LIMIT=50）
#   4. 睡眠後不全清空，而是縮減（保留摘要 + 最近 5 筆）
#
# 認知科學佐證：
#   Tulving (1972) 情節記憶 — 敘述形式編碼
#   Conway & Pleydell-Pearce (2000) 自傳記憶三層
#   Diekelmann & Born (2010) 睡眠不清空，是「轉移與整合」
#
# 誰會調用：
#   agent/manager.py        — 建立 STM 物件、檢查安全閥
#   agent/agent.py          — 寫入決策/執行/對話記錄
#   model/prompt_builder.py — 取敘述化文字 / 最近 N 筆
#   core/markov_engine.py   — 取最近行動算慣性
#   core/consolidation.py   — 取全部敘述抽 HAM、縮減 STM
#   observe/dashboard_html.py — 視覺化今天 STM
# ================================================================

from config.world_config import STM_SAFETY_LIMIT, STM_KEEP_AFTER_CONS


# ================================================================
# STM
# ================================================================

class STM:
    """
    短期記憶管理。
    直接操作 Character._data["stm"]，不複製資料。
    """

    def __init__(self, character_data: dict):
        # 直接引用，修改 STM 等於修改原始 dict
        # 確保結構存在
        stm_dict = character_data.setdefault("stm", {})
        stm_dict.setdefault("turns", [])

        # 舊版的 capacity 欄位若存在則忽略（已改為 SAFETY_LIMIT）
        self._stm = stm_dict

    # ================================================================
    # A. 寫入
    # ================================================================

    def add_turn(self, turn_id: str, time: str,
                 perception: dict, event: dict, inner: dict) -> dict:
        """
        寫入一筆新的 STM 記錄。

        turn_id    : 唯一 ID，格式 D{day:03d}_T{turn:03d}
        time       : 該時段時間 "HH:MM"
        perception : {"location":..., "yolo_desc":..., "scene_text":...}
        event      : {"input_text":..., "action":..., "target":..., "content":...}
        inner      : {"thought":..., "emotion":...}

        回傳寫入的 turn dict。
        """
        turn = {
            "turn_id":    turn_id,
            "time":       time,
            "perception": _normalize_perception(perception),
            "event":      _normalize_event(event),
            "inner":      _normalize_inner(inner),
        }
        self._stm["turns"].append(turn)
        return turn

    def add_summary_turn(self, day: int, summary_text: str):
        """
        新一天起始時加入「昨日摘要」turn（shrink_to_summary 內部呼叫）。
        turn_id 用 T000 標示這是摘要 turn。
        """
        summary_turn = {
            "turn_id":    make_turn_id(day, 0),
            "time":       "00:00",
            "perception": {
                "location":   "",
                "yolo_desc":  "",
                "scene_text": "（昨日經歷濃縮摘要）",
            },
            "event": {
                "input_text": "",
                "action":     "回顧",
                "target":     "",
                "content":    "",
            },
            "inner": {
                "thought":  summary_text,
                "emotion":  "平靜",
            },
        }
        # 摘要 turn 永遠放最前面
        self._stm["turns"].insert(0, summary_turn)

    # ================================================================
    # B. 讀取
    # ================================================================

    def get_all(self) -> list:
        """回傳所有 STM 記錄（含摘要 turn）。"""
        return self._stm["turns"]

    def get_recent(self, n: int) -> list:
        """回傳最近 n 筆（排除摘要 turn）。"""
        non_summary = [t for t in self._stm["turns"]
                       if not _is_summary_turn(t)]
        return non_summary[-n:]

    def get_today_narrative(self, max_chars: int = None) -> str:
        """
        把今天所有 STM 記錄組成敘述化文字（給 prompt 注入用）。

        max_chars : 字元上限（超過會在前面截斷，保留最新部分）
        """
        lines = []
        for turn in self._stm["turns"]:
            lines.append(_turn_to_narrative(turn))

        text = "\n\n".join(lines)
        if max_chars and len(text) > max_chars:
            # 保留最新的，截斷舊的
            text = "...（更早的記憶已濃縮）\n\n" + text[-max_chars:]
        return text if text else "（今天還沒有任何記憶）"

    def get_recent_actions(self, n: int = 5) -> list:
        """
        回傳最近 n 筆的行動動詞序列（給 markov 算慣性用）。
        排除摘要 turn 和空行動。
        """
        verbs = []
        for turn in self._stm["turns"][-n*2:]:  # 多取一些避開摘要
            if _is_summary_turn(turn):
                continue
            action = turn.get("event", {}).get("action", "")
            if action:
                verbs.append(action)
        return verbs[-n:]

    def count(self) -> int:
        return len(self._stm["turns"])

    # ================================================================
    # C. 安全閥
    # ================================================================

    def is_over_safety_limit(self) -> bool:
        """STM 是否超過安全閥（觸發中途濃縮）。"""
        return self.count() >= STM_SAFETY_LIMIT

    # ================================================================
    # D. 濃縮後縮減
    # ================================================================

    def shrink_to_summary(self, summary_text: str,
                          new_day: int,
                          keep_recent: int = STM_KEEP_AFTER_CONS):
        """
        睡眠濃縮後縮減 STM。

        做法：
          1. 取出最近 keep_recent 筆原始記錄
          2. 清空 STM
          3. 新增一筆摘要 turn 在最前面
          4. 把保留的最近記錄接在後面

        new_day      : 新一天的編號（給摘要 turn 的 turn_id 用）
        summary_text : 模型生成的當天摘要文字
        keep_recent  : 保留最近幾筆原始記錄
        """
        # 取出非摘要的最近記錄
        non_summary = [t for t in self._stm["turns"]
                       if not _is_summary_turn(t)]
        kept = non_summary[-keep_recent:] if keep_recent > 0 else []

        # 重建 STM
        self._stm["turns"] = []
        self.add_summary_turn(new_day, summary_text)
        self._stm["turns"].extend(kept)

    def clear(self):
        """
        完全清空 STM（少用，只在特殊情況呼叫，例如 reset）。
        正常睡眠濃縮應該用 shrink_to_summary。
        """
        self._stm["turns"] = []

    # ================================================================
    # E. 工具
    # ================================================================

    def next_turn_number(self, day: int) -> int:
        """
        產生下一個 turn 編號。
        每天從 1 開始（T001、T002...），T000 保留給摘要 turn。
        """
        max_n = 0
        for turn in self._stm["turns"]:
            tid = turn.get("turn_id", "")
            if tid.startswith(f"D{day:03d}_T"):
                try:
                    n = int(tid.split("_T")[1])
                    if n > max_n:
                        max_n = n
                except (ValueError, IndexError):
                    pass
        return max_n + 1


# ================================================================
# 模組級工具函式
# ================================================================

def make_turn_id(day: int, turn_number: int) -> str:
    """產生唯一 turn_id：D001_T003。"""
    return f"D{day:03d}_T{turn_number:03d}"


def _is_summary_turn(turn: dict) -> bool:
    """判斷是否為摘要 turn（T000）。"""
    tid = turn.get("turn_id", "")
    return tid.endswith("_T000")


def _normalize_perception(d: dict) -> dict:
    """確保 perception 三個欄位都存在（字串型別）。"""
    return {
        "location":   str(d.get("location", "")),
        "yolo_desc":  str(d.get("yolo_desc", "")),
        "scene_text": str(d.get("scene_text", "")),
    }


def _normalize_event(d: dict) -> dict:
    """確保 event 四個欄位都存在。"""
    return {
        "input_text": str(d.get("input_text", "")),
        "action":     str(d.get("action", "")),
        "target":     str(d.get("target", "")),
        "content":    str(d.get("content", "")),
    }


def _normalize_inner(d: dict) -> dict:
    """確保 inner 兩個欄位都存在。"""
    return {
        "thought": str(d.get("thought", "")),
        "emotion": str(d.get("emotion", "")),
    }


def _turn_to_narrative(turn: dict) -> str:
    """
    把單筆 STM turn 轉成敘述化文字。

    範例：
      [08:00] 在咖啡廳，看到 2個人、1個杯子。
      聽到 Ben對你說：早安。
      做了：對話 → Ben，說「早安，今天想喝什麼」。
      內心想：Ben 看起來心情不錯。（情緒：平靜）
    """
    # 摘要 turn 特殊處理
    if _is_summary_turn(turn):
        thought = turn.get("inner", {}).get("thought", "")
        return f"[昨日摘要]\n{thought}"

    t = turn.get("time", "")
    perc = turn.get("perception", {})
    evt = turn.get("event", {})
    inn = turn.get("inner", {})

    lines = [f"[{t}]"]

    # 感知層
    loc = perc.get("location", "")
    yolo = perc.get("yolo_desc", "")
    scene = perc.get("scene_text", "")
    if loc:
        if yolo:
            lines.append(f"在{loc}，看到{yolo}。")
        else:
            lines.append(f"在{loc}。")
    if scene and scene not in (yolo, ""):
        lines.append(f"場景：{scene}")

    # 事件層
    inp = evt.get("input_text", "")
    act = evt.get("action", "")
    tgt = evt.get("target", "")
    cnt = evt.get("content", "")

    if inp:
        lines.append(f"聽到：{inp}")
    if act:
        if act == "對話" and tgt and cnt:
            lines.append(f"對 {tgt} 說：「{cnt}」")
        elif tgt:
            lines.append(f"做了：{act} → {tgt}")
        else:
            lines.append(f"做了：{act}")

    # 內在層
    thought = inn.get("thought", "")
    emo = inn.get("emotion", "")
    if thought:
        if emo:
            lines.append(f"內心想：{thought}（情緒：{emo}）")
        else:
            lines.append(f"內心想：{thought}")

    return "\n".join(lines)
