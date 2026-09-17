# ================================================================
# perception/event_trigger.py
# 感知層事件觸發器（後期實作）
#
# 對應 ARCHITECTURE.md §6.9.2
#
# 設計目標：
#   YOLO 持續偵測場景變化 → 寫入 manager.interrupts
#   像 WebSocket 一樣常駐運行（async）
#
# 目前狀態：stub 介面
# 未來實作：
#   1. async watch_loop 每秒偵測一次
#   2. 比較前後幀偵測結果（diff）
#   3. 依變化強度分級（weak/medium/strong）
#   4. 推入 manager.push_interrupt(code, event)
#
# 注意：前期不依賴此模組，agent/manager 設計成「YOLO 是可選輸入」
# ================================================================

from typing import Optional


# ================================================================
# 事件強度分級規則
# ================================================================

def classify_event_strength(diff: dict) -> str:
    """
    依 YOLO 偵測差異分級事件強度。

    diff : {
      "objects_added":   list[str],
      "objects_removed": list[str],
      "new_person":      str | None
    }

    回傳：'weak' / 'medium' / 'strong'
    """
    if diff.get("new_person"):
        return "strong"
    if "person" in diff.get("objects_added", []):
        return "medium"
    if diff.get("objects_added") or diff.get("objects_removed"):
        return "weak"
    return "weak"


def diff_detections(prev: list, curr: list) -> dict:
    """比較兩次偵測結果。"""
    prev_classes = {d.get("class") for d in (prev or [])}
    curr_classes = {d.get("class") for d in (curr or [])}

    return {
        "objects_added":   list(curr_classes - prev_classes),
        "objects_removed": list(prev_classes - curr_classes),
        "new_person":      None,  # YOLO 不知道身分；接 UE 後填
    }


# ================================================================
# PerceptionWatcher — async 監聽器（stub）
# ================================================================

class PerceptionWatcher:
    """
    持續監聽各角色的視覺輸入，偵測變化後觸發中斷。

    後期實作 async loop：
      while running:
          for code in active_characters:
              frame = await get_frame_from_ue(code)
              detections = yolo.detect(frame)
              diff = diff_detections(prev[code], detections)
              if diff has changes:
                  strength = classify_event_strength(diff)
                  manager.push_interrupt(code, {
                    type: "yolo_change",
                    strength: strength,
                    data: diff,
                    timestamp: clock.time_str
                  })
              prev[code] = detections
          await asyncio.sleep(1.0)
    """

    def __init__(self, manager, yolo_handler):
        self.manager     = manager
        self.yolo        = yolo_handler
        self._prev_detections: dict = {}
        self._running    = False

    def push_frame_sync(self, code: str, image):
        """
        同步呼叫介面（給 ws_server 收到圖片時用）。
        不啟用 async loop 時可用。
        """
        if image is None:
            return None

        try:
            detections = self.yolo.detect(image)
        except Exception:
            return None

        prev = self._prev_detections.get(code, [])
        diff = diff_detections(prev, detections)
        self._prev_detections[code] = detections

        if diff["objects_added"] or diff["objects_removed"]:
            strength = classify_event_strength(diff)
            event = {
                "type":      "yolo_change",
                "strength":  strength,
                "data":      diff,
                "timestamp": self.manager.clock.time_str,
            }
            self.manager.push_interrupt(code, event)
            return event

        return None
