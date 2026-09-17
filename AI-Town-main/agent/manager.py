# ================================================================
# agent/manager.py
# 多角色協調器（兩段式時間軸 + Batch 推論 + 對話分派 + 中斷處理）
#
# 對應 ARCHITECTURE.md §6.3.2 + §4.2.1
#
# 核心職責：
#   1. 初始化所有角色（Character / STM / LTM / MemoryGraph / Agent）
#   2. run_tick() 執行一個完整 tick（Phase 1 執行 + Phase 2 決策）
#   3. run_autonomous_days() 跑多天
#   4. 對話發起、接受/拒絕、循環
#   5. 中斷分派
#   6. 收集觀察資料
#
# 誰會調用：
#   simulate.py     — run_autonomous_days
#   main.py         — run_tick（接 UE）
#   ws_server.py    — push_interrupt（後期）
# ================================================================

from typing import Optional
from PIL import Image
import random

from core.character     import Character
from core.memory_stm    import STM, make_turn_id
from core.memory_ltm    import LTM
from core.memory_graph  import MemoryGraph
from core.markov_engine import format_probs_display

from agent.agent     import Agent
from agent.interrupt import InterruptHandler
from model.prompt_builder import PromptBuilder

from utils.file_io import load_all_characters, save_character
from utils.logger  import get_logger, log_turn, log_consolidation

from config.world_config import (
    CHARACTER_NAMES, CHARACTER_CODES,
    DIALOGUE_MAX_TURNS,
    SLEEP_ACTION, WAKE_ACTION,
    MAX_TICKS_PER_DAY,
)
from config.triggers import DIALOGUE_REJECT_TEMPLATES

logger = get_logger("manager")


# ================================================================
# AgentManager
# ================================================================

class AgentManager:
    """
    多角色協調器。
    所有角色共用同一個 ModelLoader 與 InterruptHandler。
    """

    def __init__(self, loader, clock):
        self.loader = loader
        self.clock  = clock

        # 載入所有角色
        raw_data = load_all_characters()
        self._characters: dict = {}
        self._stms:       dict = {}
        self._ltms:       dict = {}
        self._graphs:     dict = {}
        self._agents:     dict = {}

        for code, data in raw_data.items():
            char = Character(data)
            stm  = STM(data)
            ltm  = LTM(data)
            graph = MemoryGraph(ltm)
            builder = PromptBuilder(char, stm, ltm, graph)
            agent = Agent(char, stm, ltm, graph, loader, builder)

            self._characters[code] = char
            self._stms[code]       = stm
            self._ltms[code]       = ltm
            self._graphs[code]     = graph
            self._agents[code]     = agent

        # 中斷處理器（所有角色共用）
        self.interrupts = InterruptHandler()

        # 對話記錄（每 tick 累積，pop 後清空）
        self._dialogue_history: list = []

        # 今天已入睡的角色
        self._sleeping_today: set = set()

        # 睡眠報告緩衝（一天結束時收集）
        self._sleep_reports_buffer: dict = {}

        logger.info(f"AgentManager 初始化，角色：{list(self._agents.keys())}")

    # ================================================================
    # A. 主迴圈：一個 tick
    # ================================================================

    def run_tick(self,
                  perception_input: dict = None,
                  external_input: dict = None) -> dict:
        """
        執行一個完整 tick。

        perception_input : {code: {"location", "yolo_desc", "scene_text"}}
                           若 None → 從角色當前位置生成預設 perception
        external_input   : {code: "input_text"} 外部訊息

        回傳 tick 報告 dict
        """
        perception_input = perception_input or {}
        external_input   = external_input or {}

        time_str = self.clock.time_str
        day      = self.clock.day
        logger.info(f"===== Tick {time_str} 第 {day} 天 開始 =====")

        # ─ 0. 重置 tick 暫存 ───────────────────────────────────────
        for char in self._characters.values():
            char.reset_slot_state()

        # ─ 1. 強制起床/睡覺檢查 ────────────────────────────────────
        self._check_force_wake_sleep()

        # ─ 2. 補 perception ────────────────────────────────────────
        for code, char in self._characters.items():
            if code in self._sleeping_today:
                continue
            if code not in perception_input:
                perception_input[code] = {
                    "location":   char.current_location,
                    "yolo_desc":  "",
                    "scene_text": self.clock.scene_prefix(),
                }

        # ─ 3. 中斷處理 ─────────────────────────────────────────────
        interrupt_results = self._handle_interrupts(perception_input)

        # ─ 4. Phase 1: 執行 pending_action ─────────────────────────
        execute_results = self._execute_phase(perception_input)

        # ─ 5. Phase 2: 決策下一 tick 行動 ──────────────────────────
        decide_results = self._decide_phase(perception_input, external_input)

        # ─ 6. STM 安全閥檢查 ───────────────────────────────────────
        self._check_safety_limit()

        # ─ 7. 推進時鐘 ─────────────────────────────────────────────
        self.clock.tick()

        # 收集對話歷史
        dialogues = self.pop_dialogue_history()

        logger.info(f"===== Tick {time_str} 結束 =====")

        return {
            "tick":           self.clock.ticks_today,
            "time":           time_str,
            "day":            day,
            "execute":        execute_results,
            "decide":         decide_results,
            "interrupts":     interrupt_results,
            "dialogues":      dialogues,
            "sleeping_today": list(self._sleeping_today),
        }

    # ================================================================
    # B. 多日自主模擬
    # ================================================================

    def run_autonomous_days(self, n_days: int) -> dict:
        """
        執行 n 天自主模擬，回傳完整結果（給觀察工具）。
        """
        all_days_data = []

        for d in range(n_days):
            day_data = self.run_one_day()
            all_days_data.append(day_data)

            # 確認所有角色都睡了 → 推進到下一天
            if self.all_sleeping_today():
                self.clock.advance_day()
                self._sleeping_today.clear()
                logger.info(f"推進至第 {self.clock.day} 天")

        return {
            "days":  all_days_data,
            "total_ticks": sum(len(d["ticks"]) for d in all_days_data),
        }

    def run_one_day(self) -> dict:
        """
        執行一天（直到所有角色入睡或達 force_sleep_time）。
        """
        day_n = self.clock.day
        ticks_data = []

        for _ in range(MAX_TICKS_PER_DAY + 2):
            if self.all_sleeping_today():
                break

            tick_data = self.run_tick()
            ticks_data.append(tick_data)

            if self.clock.is_forced_sleep_time():
                # 強制所有未睡的角色入睡
                for code in sorted(self._agents.keys()):
                    if code not in self._sleeping_today:
                        logger.info(f"[{code}] 強制入睡時間到")
                        self._do_sleep(code)

        return {
            "day":   day_n,
            "ticks": ticks_data,
            "sleep_reports": self._collect_sleep_reports(),
        }

    # ================================================================
    # C. Phase 1: 執行
    # ================================================================

    def _execute_phase(self, perception_input: dict) -> dict:
        """執行所有角色的 pending_action。"""
        results = {}

        # 找出對話配對
        conv_pairs = self._find_conversation_pairs()
        executed   = set()

        for code in sorted(self._agents.keys()):
            if code in self._sleeping_today:
                continue
            if code in executed:
                continue

            char = self._characters[code]
            pending = char.get_pending_action()
            action = pending.get("action", "")
            target = pending.get("target", "")

            if not action:
                # 從時間表取
                slot = char.get_current_slot()
                if slot:
                    action = slot["action"]
                    target = slot.get("location", "")
                else:
                    action = "休息"

            logger.info(f"[{code}] 執行：{action} {target}")

            # 對話 → 配對處理
            if action == "對話" and code in conv_pairs:
                partner = conv_pairs[code]
                if partner in conv_pairs and partner not in executed:
                    # 雙方都想對話 → 邀請接受/拒絕 → 可能進入對話
                    conv_result = self._handle_dialogue(
                        code, partner, perception_input
                    )
                    results[code]    = conv_result["initiator_result"]
                    results[partner] = conv_result["responder_result"]
                    executed.add(code)
                    executed.add(partner)
                    continue

            # 睡覺 → 檢查時間，再決定執行睡覺還是休息
            if action == SLEEP_ACTION:
                if self._is_sleep_time_for(char):
                    results[code] = {"action": "睡覺", "target": "",
                                       "completed": True}
                    self._do_sleep(code)
                    continue
                # 時間還早 → 改成休息
                action = "休息"
                target = ""
                char.set_pending_action("休息", "")

            # 一般行動 → 更新狀態
            char.current_action = action
            if action == "前往" and target:
                char.current_location = target
            char.add_today_action(action)

            results[code] = {
                "action": action, "target": target, "completed": True
            }

        return results

    # ================================================================
    # D. Phase 2: 決策
    # ================================================================

    def _decide_phase(self, perception_input, external_input) -> dict:
        """所有角色決策下一 tick 行動。"""
        results = {}

        for code in sorted(self._agents.keys()):
            if code in self._sleeping_today:
                continue

            char  = self._characters[code]
            agent = self._agents[code]

            co_located = self._get_co_located_codes(code)
            scene = self._build_scene_for(code, perception_input)

            try:
                result = agent.decide(
                    scene            = scene,
                    perception       = perception_input.get(code, {}),
                    co_located_codes = co_located,
                    input_text       = external_input.get(code, ""),
                )

                log_turn(
                    logger,
                    code    = code,
                    turn_id = f"D{char.day:03d}_T{self._stms[code].count():03d}",
                    action  = result.get("action", ""),
                    c_value = result.get("_meta", {}).get("confusion", {}).get("C", 0.0),
                    mode    = result.get("mode", "markov"),
                )

                # 睡覺時間檢查：不到 default_sleep_time 不允許睡
                if result.get("action") == SLEEP_ACTION:
                    if not self._is_sleep_time_for(char):
                        # 時間還早 → 改成「休息」
                        result["action"] = "休息"
                        result["target"] = ""
                        result["should_sleep"] = False
                        char.set_pending_action("休息", "")

                # 若決策是睡覺 → 觸發濃縮
                if result.get("should_sleep"):
                    self._do_sleep(code)
                    char.clear_pending_action()

                results[code] = result

            except Exception as e:
                logger.error(f"[{code}] decide 失敗：{e}")
                results[code] = {"error": str(e)}

        return results

    # ================================================================
    # E. 對話流程（邀請 → 接受/拒絕 → 循環）
    # ================================================================

    def _handle_dialogue(self, initiator_code, responder_code,
                          perception_input) -> dict:
        """處理一對對話：邀請 → 接受/拒絕 → 循環。"""
        initiator = self._agents[initiator_code]
        responder = self._agents[responder_code]
        init_char = self._characters[initiator_code]
        resp_char = self._characters[responder_code]

        # 鎖定雙方
        init_char.is_locked = True
        resp_char.is_locked = True

        # 邀請：發起方 pending_action 的 content 當作開場白
        invite_content = init_char.get_pending_action().get("target", "") or \
                         "（主動走近想聊聊）"

        # 接受判斷
        accepted = responder.should_accept_dialogue(initiator_code)

        if not accepted:
            # 拒絕
            reject_msg = random.choice(DIALOGUE_REJECT_TEMPLATES)
            logger.info(
                f"[{responder_code}] 拒絕 [{initiator_code}] 的對話邀請：{reject_msg}"
            )
            # 雙方寫 STM
            self._stms[initiator_code].add_turn(
                turn_id = make_turn_id(init_char.day,
                                        self._stms[initiator_code].next_turn_number(init_char.day)),
                time = self.clock.time_str,
                perception = perception_input.get(initiator_code, {}),
                event = {
                    "input_text": f"{resp_char.name}說：{reject_msg}",
                    "action":     "對話",
                    "target":     resp_char.name,
                    "content":    invite_content,
                },
                inner = {"thought": "對方好像不想聊", "emotion": init_char.emotion}
            )
            self._stms[responder_code].add_turn(
                turn_id = make_turn_id(resp_char.day,
                                        self._stms[responder_code].next_turn_number(resp_char.day)),
                time = self.clock.time_str,
                perception = perception_input.get(responder_code, {}),
                event = {
                    "input_text": f"{init_char.name}想跟我說話",
                    "action":     "對話",
                    "target":     init_char.name,
                    "content":    reject_msg,
                },
                inner = {"thought": "現在不想聊", "emotion": resp_char.emotion}
            )

            init_char.is_locked = False
            resp_char.is_locked = False

            self._dialogue_history.append({
                "initiator":  initiator_code,
                "responder":  responder_code,
                "accepted":   False,
                "turns":      [{"speaker": initiator_code, "msg": invite_content},
                                {"speaker": responder_code, "msg": reject_msg}],
            })

            return {
                "initiator_result": {"action": "對話", "target": resp_char.name,
                                      "content": invite_content, "accepted": False},
                "responder_result": {"action": "對話", "target": init_char.name,
                                      "content": reject_msg, "accepted": False},
            }

        # 接受 → 進入對話循環
        logger.info(f"[{initiator_code} ↔ {responder_code}] 對話開始")

        last_message = invite_content
        recent_dialogue_lines = []
        turns = []

        # 第一輪：發起方說 invite_content
        turns.append({"speaker": initiator_code, "msg": invite_content})

        scene = self._build_scene_for(initiator_code, perception_input)

        for round_idx in range(DIALOGUE_MAX_TURNS):
            recent_text = "\n".join(recent_dialogue_lines[-6:])

            # responder 回應
            resp_result = responder.generate_dialogue_response(
                scene           = scene,
                perception      = perception_input.get(responder_code, {}),
                partner_code    = initiator_code,
                partner_message = last_message,
                recent_dialogue = recent_text,
            )
            turns.append({
                "speaker": responder_code,
                "msg": resp_result["content"]
            })
            recent_dialogue_lines.append(
                f"{resp_char.name}：{resp_result['content']}"
            )

            # responder 決定結束
            if resp_result["action"] != "對話":
                break

            last_message = resp_result["content"]

            # initiator 回應
            init_result = initiator.generate_dialogue_response(
                scene           = scene,
                perception      = perception_input.get(initiator_code, {}),
                partner_code    = responder_code,
                partner_message = last_message,
                recent_dialogue = "\n".join(recent_dialogue_lines[-6:]),
            )
            turns.append({
                "speaker": initiator_code,
                "msg": init_result["content"]
            })
            recent_dialogue_lines.append(
                f"{init_char.name}：{init_result['content']}"
            )

            if init_result["action"] != "對話":
                break

            last_message = init_result["content"]

        init_char.is_locked = False
        resp_char.is_locked = False

        self._dialogue_history.append({
            "initiator":  initiator_code,
            "responder":  responder_code,
            "accepted":   True,
            "turns":      turns,
        })

        # 雙方今日行動紀錄
        init_char.add_today_action("對話")
        resp_char.add_today_action("對話")

        return {
            "initiator_result": {"action": "對話", "target": resp_char.name,
                                  "content": turns[0]["msg"], "accepted": True,
                                  "rounds": len(turns) // 2},
            "responder_result": {"action": "對話", "target": init_char.name,
                                  "content": turns[1]["msg"] if len(turns) > 1 else "",
                                  "accepted": True, "rounds": len(turns) // 2},
        }

    # ================================================================
    # F. 對話配對
    # ================================================================

    def _find_conversation_pairs(self) -> dict:
        """
        找出 pending_action 為對話且同地點的角色配對。
        回傳 {code: partner_code} 雙向 dict。
        """
        want_talk = []
        for code, char in self._characters.items():
            if code in self._sleeping_today:
                continue
            pending = char.get_pending_action()
            if pending.get("action") == "對話":
                want_talk.append(code)

        # 按地點分組
        by_location = {}
        for code, char in self._characters.items():
            if code in self._sleeping_today:
                continue
            loc = char.current_location
            by_location.setdefault(loc, []).append(code)

        pairs = {}
        used = set()

        for code_a in want_talk:
            if code_a in used:
                continue
            loc = self._characters[code_a].current_location
            candidates = [c for c in by_location.get(loc, []) if c != code_a and c not in used]
            if not candidates:
                continue
            # 優先選也想對話的
            best = next((c for c in candidates if c in want_talk), candidates[0])
            pairs[code_a] = best
            pairs[best]   = code_a
            used.add(code_a)
            used.add(best)

        return pairs

    # ================================================================
    # G. 中斷處理
    # ================================================================

    def _handle_interrupts(self, perception_input) -> dict:
        """檢查所有角色的中斷佇列，處理中斷。"""
        results = {}
        for code in sorted(self._agents.keys()):
            if code in self._sleeping_today:
                continue
            char = self._characters[code]
            if not self.interrupts.has_events(code):
                continue

            outcome = self.interrupts.process_interrupts(
                code, char.current_action
            )
            if outcome["should_interrupt"]:
                agent = self._agents[code]
                new_decision = agent.re_evaluate_on_interrupt(
                    interrupt_event  = outcome["triggered_event"],
                    perception       = perception_input.get(code, {}),
                    co_located_codes = self._get_co_located_codes(code),
                )
                results[code] = {
                    "interrupted":  True,
                    "new_action":   new_decision["action"],
                    "event":        outcome["triggered_event"],
                }
            else:
                results[code] = {
                    "interrupted":  False,
                    "events_noted": len(outcome["all_events"]),
                }

        return results

    def push_interrupt(self, code: str, event: dict):
        """外部（YOLO 層）寫入中斷事件。"""
        self.interrupts.push(code, event)

    # ================================================================
    # H. 強制起床/睡覺
    # ================================================================

    def _check_force_wake_sleep(self):
        """檢查所有角色是否到達強制起床/睡覺時間。"""
        current_minutes = self._current_minutes()

        for code, char in self._characters.items():
            sleep_pattern = char.get_sleep_pattern()

            # 強制睡覺
            if code not in self._sleeping_today:
                force_sleep = _parse_time(sleep_pattern.get("force_sleep_time", "02:00"))
                if _time_reached(current_minutes, force_sleep):
                    logger.info(f"[{code}] 達 force_sleep_time，強制入睡")
                    self._do_sleep(code)
                    continue

            # 強制起床（已睡角色不適用，那是隔天的事）

    # ================================================================
    # I. 睡眠
    # ================================================================

    def _do_sleep(self, code: str) -> dict:
        """觸發睡眠濃縮 + 存檔。"""
        if code in self._sleeping_today:
            return {}

        agent = self._agents[code]
        char  = self._characters[code]

        # 在 sleep() 清空 process_log 之前先快照
        process_log_snapshot = list(agent.process_log)

        result = agent.sleep()

        # 補充額外資訊供 dashboard 使用
        result["process_log"]    = process_log_snapshot
        result["character_name"] = char.name
        result["character_code"] = code

        log_consolidation(
            logger,
            code      = char.code,
            day       = char.day - 1,  # 已 advance_day，所以這裡是「剛結束的那天」
            stm_count = result["ham_extracted"],
            ltm_count = result["ltm_total"],
        )

        # 存檔
        try:
            save_character(code, char.to_dict())
            logger.info(f"[{code}] 存檔完成，進入第 {char.day} 天")
        except Exception as e:
            logger.error(f"[{code}] 存檔失敗：{e}")

        # 緩衝報告（run_one_day 結束時收集）
        self._sleep_reports_buffer[code] = result
        self._sleeping_today.add(code)
        return result

    def _collect_sleep_reports(self) -> dict:
        """收集本日所有角色的睡眠報告（給觀察工具用）。"""
        reports = dict(self._sleep_reports_buffer)
        self._sleep_reports_buffer.clear()
        return reports

    # ================================================================
    # J. 工具
    # ================================================================

    def _get_co_located_codes(self, code: str) -> list:
        """回傳同地點的其他角色代號列表。"""
        my_loc = self._characters[code].current_location
        return [
            other_code
            for other_code, other_char in self._characters.items()
            if other_code != code
            and other_code not in self._sleeping_today
            and other_char.current_location == my_loc
        ]

    def _build_scene_for(self, code: str, perception_input: dict) -> str:
        """組裝場景字串（時間 + 地點 + scene_text）。"""
        char = self._characters[code]
        perc = perception_input.get(code, {})
        scene_parts = [self.clock.scene_prefix()]
        if char.current_location:
            scene_parts.append(char.current_location)
        if perc.get("scene_text"):
            scene_parts.append(perc["scene_text"])
        return " ".join(scene_parts)

    def _current_minutes(self) -> int:
        """當前時間的分鐘數。"""
        h, m = self.clock.time_str.split(":")
        return int(h) * 60 + int(m)

    def _is_sleep_time_for(self, char) -> bool:
        """
        判斷該角色當前時間是否到達 default_sleep_time。
        未到 → markov 抽到「睡覺」會被改成「休息」
        """
        current = self._current_minutes()
        target = _parse_time(
            char.get_sleep_pattern().get("default_sleep_time", "22:00")
        )
        return _time_reached(current, target)

    def _check_safety_limit(self):
        """檢查 STM 是否超過安全閥，超過觸發中途濃縮。"""
        for code in sorted(self._agents.keys()):
            if code in self._sleeping_today:
                continue
            if self._stms[code].is_over_safety_limit():
                logger.warning(f"[{code}] STM 達安全閥，觸發中途濃縮")
                self._do_sleep(code)

    # ================================================================
    # K. 公開查詢介面（給觀察工具）
    # ================================================================

    def get_character(self, code: str):
        return self._characters[code]

    def get_agent(self, code: str):
        return self._agents[code]

    def all_codes(self) -> list:
        return list(self._agents.keys())

    def pop_dialogue_history(self) -> list:
        history = list(self._dialogue_history)
        self._dialogue_history.clear()
        return history

    def all_sleeping_today(self) -> bool:
        return self._sleeping_today >= set(self._agents.keys())

    def get_process_log(self, code: str) -> list:
        return self._agents[code].process_log

    def get_observation_data(self) -> dict:
        """收集所有觀察用資料（給 dashboard）。"""
        data = {}
        for code in sorted(self._agents.keys()):
            char  = self._characters[code]
            agent = self._agents[code]
            data[code] = {
                "name":           char.name,
                "current_location": char.current_location,
                "current_action":   char.current_action,
                "emotion":          char.emotion,
                "day":              char.day,
                "stm":              self._stms[code].get_all(),
                "ltm_nodes":        self._graphs[code].get_all_nodes(),
                "ltm_edges":        self._graphs[code].get_all_edges(),
                "ltm_summary":      self._ltms[code].get_summary(),
                "process_log":      agent.process_log,
                "schedule":         char.get_schedule(),
                "sleep_pattern":    char.get_sleep_pattern(),
                "is_sleeping":      code in self._sleeping_today,
            }
        return data


# ================================================================
# 模組級工具
# ================================================================

def _parse_time(time_str: str) -> int:
    """HH:MM → 分鐘數（0-1439）。"""
    try:
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def _minutes_since_day_start(minutes: int, day_start_hour: int = 6) -> int:
    """
    把絕對時間（0-1439）轉換為「從 day_start 算起的分鐘數」。
    day_start = 06:00 時：
      06:00 → 0
      12:00 → 360
      23:00 → 1020
      00:00 → 1080  ← 跨午夜後繼續累加
      02:00 → 1200  ← 一天的最末
    """
    day_start_minutes = day_start_hour * 60
    return (minutes - day_start_minutes) % (24 * 60)


def _time_reached(current_minutes: int, target_minutes: int,
                   day_start_hour: int = 6) -> bool:
    """
    判斷當前時間是否到達 target（基於 day_start 的順序）。

    例如 day_start=06:00：
      current=06:00, target=02:00 → 還沒到（02:00 在這天最後）
      current=23:00, target=02:00 → 還沒到
      current=02:00, target=02:00 → 到了
    """
    cur_since = _minutes_since_day_start(current_minutes, day_start_hour)
    tgt_since = _minutes_since_day_start(target_minutes, day_start_hour)
    return cur_since >= tgt_since
