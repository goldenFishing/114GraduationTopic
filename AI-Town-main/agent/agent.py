# ================================================================
# agent/agent.py
# 單一角色的決策與行動執行
#
# 對應 ARCHITECTURE.md §6.3.1
#
# 主要方法：
#   decide()                      — 一個 tick 的主決策（Markov / Deliberate）
#   generate_dialogue_response()  — 對話一輪生成
#   should_accept_dialogue()      — 對話接受判斷（純規則）
#   re_evaluate_on_interrupt()    — 中斷後重新評估
#   sleep()                       — 觸發濃縮
#
# 設計核心：
#   1. STM 寫入分離「記憶內容」vs「process_log」
#   2. Markov 路徑完全不呼叫模型
#   3. 對話拒絕純規則計算
#   4. 中斷重新決策走 Markov 重算
#   5. ActionValueTracker：tick 間 RL-style 價值繼承
#      每 tick 結束後計算 reward，更新 value_score，
#      下個 tick 的 Markov 計算帶入第四源（δ = 0.15）
# ================================================================

import random
from typing import Optional

from PIL import Image

from core.markov_engine import (
    compute_action_probabilities,
    sample_action,
    resolve_dialogue_target,
)
from core.confusion import evaluate as eval_confusion
from core.memory_stm import make_turn_id
from core.tick_value import ActionValueTracker
from model.output_parser import parse_decision_output
from model.fusion_decoder import GenerationConfig
from config.world_config import (
    SLEEP_ACTION,
    DIALOGUE_BASE_ACCEPT,
    DIALOGUE_RELATION_BONUS,
    DIALOGUE_LEISURE_BONUS,
    DIALOGUE_WORK_PENALTY,
    DIALOGUE_EMOTION_PENALTY,
    DIALOGUE_ACCEPT_MIN,
    DIALOGUE_ACCEPT_MAX,
)
from config.action_list import ACTION_TO_CATEGORY


class Agent:
    """
    單一角色的推論代理人。
    """

    def __init__(self, character, stm, ltm, memory_graph, loader,
                 prompt_builder):
        self.character = character
        self.stm       = stm
        self.ltm       = ltm
        self.graph     = memory_graph
        self.loader    = loader
        self.prompt_builder = prompt_builder

        # 處理元數據（每天累積，睡覺時清空）
        self.process_log: list = []

        # RL-style tick 間價值追蹤器
        # 每 tick 結束後更新，下 tick Markov 計算時帶入第四源
        self.value_tracker = ActionValueTracker()

        # 上一 tick 的情緒與 C 值，供 reward 計算用
        self._prev_emotion: str   = character.emotion
        self._prev_C:       float = 0.5

    # ================================================================
    # A. 主決策（一個 tick 呼叫一次）
    # ================================================================

    def decide(self,
                scene: str,
                perception: dict,
                co_located_codes: list = None,
                input_text: str = "",
                image: Optional[Image.Image] = None) -> dict:
        """
        決定下一 tick 要做什麼。

        回傳格式：
          {
            "action":  str,         # 動詞
            "target":  str,
            "content": str,         # 對話內容（其他行動空）
            "thought": str,
            "ham":     list,        # 模型自己提的（深思路徑才有，不一定用）
            "mode":    "markov" | "deliberate",
            "_meta":   {confusion, action_probs, is_major_event, ...}
          }
        """
        char = self.character
        co_located_codes = co_located_codes or []

        # 0. tick 開始：value_tracker 先衰減（上 tick 的影響乘以 DECAY）
        self.value_tracker.decay()

        # 1. 計算困惑度（先用 Markov 機率分布作為 U 的輸入）
        co_located_names = [
            char._data.get("name", c) if c == char.code else c
            for c in co_located_codes
        ]
        from config.world_config import CHARACTER_NAMES
        co_located_names = [
            CHARACTER_NAMES.get(c, c) for c in co_located_codes
        ]

        # 取 markov 機率分布作為 U 的輸入
        # 傳入 action_values：第四源帶入上 tick 的 value 繼承
        slot = char.get_current_slot()
        markov_breakdown = compute_action_probabilities(
            schedule_slot      = slot,
            stm_recent_verbs   = self.stm.get_recent_actions(8),
            perception         = perception,
            co_located         = co_located_names,
            emotion            = char.emotion,
            is_major_event     = False,
            action_values      = self.value_tracker.get_scores(),
            return_breakdown   = True,
        )
        action_probs = markov_breakdown["probs"]
        action_candidates = [
            {"action": a, "score": p} for a, p in action_probs.items()
        ]

        # 評估
        weights = char.get_confusion_weights()
        # threshold 用情緒調整後的版本
        weights = dict(weights)
        weights["threshold"] = char.get_confusion_threshold()

        confusion = eval_confusion(
            yolo_desc       = perception.get("yolo_desc", ""),
            input_text      = input_text,
            current_action  = char.current_action,
            scene_text      = perception.get("scene_text", ""),
            ltm_summary     = self.ltm.get_summary(),
            today_actions   = char.get_today_actions(),
            weights         = weights,
            action_candidates = action_candidates,
        )

        is_major = confusion["K"] >= 0.6  # MAJOR_EVENT_K_THRESHOLD
        mode = confusion["mode"]

        # 重大事件 → 用 EVENT 權重重算 markov（同樣帶入 action_values）
        if is_major:
            markov_breakdown = compute_action_probabilities(
                schedule_slot      = slot,
                stm_recent_verbs   = self.stm.get_recent_actions(8),
                perception         = perception,
                co_located         = co_located_names,
                emotion            = char.emotion,
                is_major_event     = True,
                action_values      = self.value_tracker.get_scores(),
                return_breakdown   = True,
            )
            action_probs = markov_breakdown["probs"]

        # 2. 走 Markov 或 Deliberate
        if mode == "intuitive":
            result = self._decide_markov(
                action_probs, co_located_names, scene, perception, char
            )
        else:
            result = self._decide_deliberate(
                scene, perception, co_located_codes, input_text, image
            )

        # 3. 寫入 STM
        self._write_stm_entry(perception, input_text, result)

        # 4. 寫入 process_log（不進 STM）
        self._write_process_log(
            confusion, mode, action_probs, is_major, result
        )

        # 5. 設定 pending_action
        char.set_pending_action(result["action"], result["target"])
        char.current_action = result["action"]
        if result["action"] == "前往" and result["target"]:
            # 注意：前往不立刻改變位置，下個 tick 執行時才改
            pass

        # 6. 更新 value_tracker（RL reward 計算）
        #    curr_C 用本 tick 算出的 confusion C 值
        curr_C = confusion.get("C", 0.5)
        turn_num = self.stm.next_turn_number(char.day) - 1
        tick_id  = f"D{char.day:03d}_T{turn_num:03d}"
        reward = self.value_tracker.compute_reward(
            action            = result["action"],
            prev_emotion      = self._prev_emotion,
            curr_emotion      = char.emotion,
            prev_C            = self._prev_C,
            curr_C            = curr_C,
            dialogue_accepted = False,  # 對話結果由 manager 在接受後補呼叫
            schedule_hit      = (result["action"] == slot.get("action", ""))
                                 if slot else False,
            tick_id           = tick_id,
        )
        self.value_tracker.update(result["action"], reward)

        # 記錄供下 tick 比較
        self._prev_emotion = char.emotion
        self._prev_C       = curr_C

        # 補充 meta
        result["_meta"] = {
            "confusion":     confusion,
            "action_probs":  action_probs,
            "is_major_event": is_major,
            "breakdown":     markov_breakdown.get("breakdown", {}),
            "value_scores":  self.value_tracker.get_scores(),   # 供 dashboard
            "tick_reward":   round(reward, 4),
        }
        result["mode"] = mode

        return result

    # ────────────────────────────────────────────────────────────

    def _decide_markov(self, action_probs, co_located_names,
                        scene, perception, char):
        """Markov 路徑：採樣行動。"""
        verb, target = resolve_dialogue_target(
            action_probs, co_located_names
        )

        # 「前往」目標補：時間表 → 職業預設 → 空
        if verb == "前往" and not target:
            target = self._next_schedule_location() or \
                     self._default_work_location() or ""
        # 沒目的地 → 改休息
        if verb == "前往" and not target:
            verb = "休息"

        return {
            "action":  verb,
            "target":  target,
            "content": "",
            "thought": "",
            "ham":     [],
            "should_sleep": verb == SLEEP_ACTION,
        }

    def _decide_deliberate(self, scene, perception, co_located_codes,
                            input_text, image):
        """Deliberate 路徑：呼叫模型。"""
        prompt_text = self.prompt_builder.build_deliberate(
            scene             = scene,
            perception        = perception,
            co_located_codes  = co_located_codes,
            input_text        = input_text,
        )

        raw = self._call_model(prompt_text, image, GenerationConfig.deliberate())
        parsed = parse_decision_output(raw)

        return {
            "action":  parsed["action"],
            "target":  parsed["target"],
            "content": parsed["content"],
            "thought": parsed["thought"],
            "ham":     parsed["ham"],
            "should_sleep": parsed["action"] == SLEEP_ACTION,
        }

    # ================================================================
    # B. 對話生成
    # ================================================================

    def generate_dialogue_response(self,
                                     scene: str,
                                     perception: dict,
                                     partner_code: str,
                                     partner_message: str,
                                     recent_dialogue: str = "",
                                     image: Optional[Image.Image] = None) -> dict:
        """
        對話一輪生成。被 manager 對話循環呼叫。
        """
        prompt_text = self.prompt_builder.build_dialogue(
            scene           = scene,
            partner_code    = partner_code,
            partner_message = partner_message,
            recent_dialogue = recent_dialogue,
        )

        raw = self._call_model(prompt_text, image, GenerationConfig.dialogue())
        parsed = parse_decision_output(raw)

        # 寫入 STM
        self._write_stm_entry(perception, partner_message, {
            "action":  parsed["action"],
            "target":  parsed["target"],
            "content": parsed["content"],
            "thought": parsed["thought"],
            "ham":     parsed["ham"],
        })

        return {
            "action":  parsed["action"],
            "target":  parsed["target"],
            "content": parsed["content"],
            "thought": parsed["thought"],
            "ham":     parsed["ham"],
            "mode":    "dialogue",
        }

    # ================================================================
    # C. 對話接受判斷（純規則）
    # ================================================================

    def should_accept_dialogue(self, inviter_code: str) -> bool:
        """
        判斷是否接受對方的對話邀請。
        純規則，不呼叫模型。
        """
        char = self.character
        acc = DIALOGUE_BASE_ACCEPT

        # 關係加成
        rel = char.get_relationship(inviter_code)
        summary = (rel.get("summary", "") + " " + rel.get("initial", ""))
        positive_kw = ["朋友", "好朋友", "信任", "喜歡", "在意", "親近", "熟"]
        if any(kw in summary for kw in positive_kw):
            acc += DIALOGUE_RELATION_BONUS

        # 當前行動類別
        cur_cat = ACTION_TO_CATEGORY.get(char.current_action, "")
        if cur_cat in ("rest", "daily"):
            acc += DIALOGUE_LEISURE_BONUS
        elif cur_cat == "work":
            acc += DIALOGUE_WORK_PENALTY

        # 情緒
        if char.emotion not in ("平靜", "開心", "興奮"):
            acc += DIALOGUE_EMOTION_PENALTY

        # Clamp
        acc = max(DIALOGUE_ACCEPT_MIN, min(DIALOGUE_ACCEPT_MAX, acc))

        return random.random() < acc

    # ================================================================
    # D. 中斷後重新評估（Markov 重算）
    # ================================================================

    def re_evaluate_on_interrupt(self,
                                   interrupt_event: dict,
                                   perception: dict,
                                   co_located_codes: list = None) -> dict:
        """
        中斷後重新算 Markov，可能改變 pending_action。

        強度大的事件當作 major_event。
        """
        char = self.character
        from config.world_config import CHARACTER_NAMES
        co_located_names = [
            CHARACTER_NAMES.get(c, c) for c in (co_located_codes or [])
        ]

        is_major = interrupt_event.get("strength") == "strong"

        breakdown = compute_action_probabilities(
            schedule_slot      = char.get_current_slot(),
            stm_recent_verbs   = self.stm.get_recent_actions(8),
            perception         = perception,
            co_located         = co_located_names,
            emotion            = char.emotion,
            is_major_event     = is_major,
            return_breakdown   = True,
        )
        probs = breakdown["probs"]

        verb, target = resolve_dialogue_target(probs, co_located_names)

        if verb == "前往" and not target:
            target = self._next_schedule_location() or \
                     self._default_work_location() or ""
        if verb == "前往" and not target:
            verb = "休息"

        # 設定新 pending
        char.set_pending_action(verb, target)
        char.current_action = verb

        # 寫 process_log
        self.process_log.append({
            "turn_id":          f"D{char.day:03d}_INTERRUPT",
            "decision_mode":    "interrupt",
            "interrupt_event":  interrupt_event,
            "action_probs":     probs,
            "is_major_event":   is_major,
        })

        return {
            "action":  verb,
            "target":  target,
            "mode":    "interrupt",
            "action_probs": probs,
        }

    # ================================================================
    # E. 睡眠
    # ================================================================

    def sleep(self) -> dict:
        """觸發睡眠濃縮，回傳濃縮報告。"""
        from core.consolidation import consolidate

        result = consolidate(
            character    = self.character,
            stm          = self.stm,
            ltm          = self.ltm,
            process_log  = self.process_log,
            loader       = self.loader,
        )

        # 清空當天 process_log
        self.process_log = []

        # 重置 value_tracker（情緒/困惑度跨天清零，避免舊 reward 汙染新天）
        self.value_tracker.reset()
        self._prev_emotion = self.character.emotion
        self._prev_C       = 0.5

        return result

    # ================================================================
    # 內部工具
    # ================================================================

    def _call_model(self, prompt_text, image, gen_cfg) -> str:
        """呼叫模型推論（單筆）。沒有 loader → 空字串。"""
        if self.loader is None or not self.loader.is_loaded():
            return ""

        # FakeLoader 或缺少 vision/text/fusion → 直接走 model_fn 簡化路徑
        if (getattr(self.loader, "text",   None) is None or
            getattr(self.loader, "fusion", None) is None):
            max_tokens = gen_cfg.max_new_tokens if gen_cfg else 256
            temp       = gen_cfg.temperature   if gen_cfg else 0.0
            model_fn = self.loader.make_model_fn(
                max_new_tokens=max_tokens, temperature=temp
            )
            return model_fn(prompt_text)

        # 真實模型：完整圖文 pipeline
        images = [image] if image else []
        num_images = len(images)
        text_prompt = self.loader.text.build_prompt(
            prompt_text, num_images=num_images
        )
        if images:
            vision_batch = self.loader.vision.encode(images)
            image_inputs = vision_batch.to_dict()
        else:
            image_inputs = {}

        fused = self.loader.fusion.fuse_inputs(
            text=text_prompt.prompt, image_inputs=image_inputs
        )
        return self.loader.fusion.generate(fused, gen_cfg)

    def _next_schedule_location(self) -> str:
        slot = self.character.get_current_slot()
        if slot and slot.get("location"):
            return slot["location"]
        return ""

    def _default_work_location(self) -> str:
        """根據職業回傳預設工作地點。"""
        role_map = {
            "咖啡師":    "咖啡廳",
            "餐廳員工":  "餐廳",
            "超市員工":  "超市",
            "辦公室員工":"辦公室",
            "公司老闆":  "辦公室",
            "廚師":      "餐廳",
            "律師":      "辦公室",
            "工程師":    "辦公室",
        }
        return role_map.get(self.character.role, "")

    def _write_stm_entry(self, perception: dict,
                          input_text: str, result: dict):
        """把這 tick 的決策寫入 STM（敘述形式）。"""
        char = self.character
        turn_num = self.stm.next_turn_number(char.day)
        turn_id = make_turn_id(char.day, turn_num)

        # 時間從時間表 / 時鐘取得（暫用當前時段的 time）
        slot = char.get_current_slot()
        time_str = slot["time"] if slot else "00:00"

        self.stm.add_turn(
            turn_id    = turn_id,
            time       = time_str,
            perception = perception or {
                "location":   char.current_location,
                "yolo_desc":  "",
                "scene_text": "",
            },
            event = {
                "input_text": input_text,
                "action":     result.get("action", ""),
                "target":     result.get("target", ""),
                "content":    result.get("content", ""),
            },
            inner = {
                "thought": result.get("thought", ""),
                "emotion": char.emotion,
            },
        )

    def _write_process_log(self, confusion, mode, action_probs,
                            is_major, result):
        """元數據另存 process_log，不進 STM。"""
        char = self.character
        self.process_log.append({
            "turn_id":        f"D{char.day:03d}_T{self.stm.next_turn_number(char.day) - 1:03d}",
            "decision_mode":  mode,
            "confusion":      confusion,
            "is_major_event": is_major,
            "action_probs":   action_probs,
            "action":         result.get("action", ""),
            "target":         result.get("target", ""),
        })
