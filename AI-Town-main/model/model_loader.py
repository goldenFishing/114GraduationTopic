# ================================================================
# model/model_loader.py
# Phi-3.5-Vision 模型載入與工廠
#
# 對應 ARCHITECTURE.md §6.4.1
#
# 設計：
#   1. 單例模式：模型只載入一次，所有 agent 共用
#   2. 工廠方法：依用途回傳不同 token 預算的 model_fn
#   3. 支援自訂快取路徑（MODEL_CACHE_DIR）
#
# 誰會調用：
#   main.py / simulate.py — 啟動時 load()
#   agent/manager.py      — 取 loader 傳給 agent
#   agent/agent.py        — make_deliberate_fn, make_dialogue_fn
#   core/consolidation.py — make_consolidation_fn(step)
#   agent/scheduler.py    — make_model_fn(SCHEDULE_GEN_MAX_TOKENS)
# ================================================================

import torch
from transformers import AutoModelForCausalLM, AutoProcessor

from config.model_config import (
    MODEL_ID, MODEL_NUM_CROPS, MODEL_CACHE_DIR,
    DELIBERATE_MAX_TOKENS, DELIBERATE_TEMPERATURE,
    DIALOGUE_MAX_TOKENS, DIALOGUE_TEMPERATURE,
    CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS,
    CONSOLIDATE_SELECT_MAX_TOKENS,
    CONSOLIDATE_SUMMARY_MAX_TOKENS,
    CONSOLIDATE_RELATION_MAX_TOKENS,
    CONSOLIDATE_EMOTION_MAX_TOKENS,
    SCHEDULE_GEN_MAX_TOKENS,
)
from model.vision_encoder import VisionEncoder
from model.text_encoder import TextEncoder
from model.fusion_decoder import FusionDecoder, GenerationConfig


def pick_device() -> torch.device:
    """自動選最佳裝置：CUDA > MPS > CPU"""
    if torch.cuda.is_available():
        return torch.device("cuda:0")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class ModelLoader:
    """Phi-3.5-Vision 單例載入器。"""

    def __init__(self):
        self.device    = pick_device()
        self.model     = None
        self.processor = None
        self.vision    = None
        self.text      = None
        self.fusion    = None
        self._loaded   = False

    # ────────────────────────────────────────────────────────────

    def load(self):
        """載入模型（首次會下載，之後從快取）。"""
        if self._loaded:
            return

        print(f"[ModelLoader] 載入模型：{MODEL_ID}")
        print(f"[ModelLoader] 裝置：{self.device}")

        kwargs = {
            "trust_remote_code": True,
            "torch_dtype":       "auto",
            "_attn_implementation": "eager",
        }
        if MODEL_CACHE_DIR:
            kwargs["cache_dir"] = MODEL_CACHE_DIR

        self.model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **kwargs)
        self.model = self.model.to(self.device)

        proc_kwargs = {"trust_remote_code": True, "num_crops": MODEL_NUM_CROPS}
        if MODEL_CACHE_DIR:
            proc_kwargs["cache_dir"] = MODEL_CACHE_DIR
        self.processor = AutoProcessor.from_pretrained(MODEL_ID, **proc_kwargs)

        self.vision = VisionEncoder(self.processor)
        self.text   = TextEncoder(self.processor)
        self.fusion = FusionDecoder(self.model, self.processor, self.device)

        self._loaded = True
        print("[ModelLoader] 模型載入完成。")

    def is_loaded(self) -> bool:
        return self._loaded

    # ────────────────────────────────────────────────────────────
    # 工廠方法：各用途的 model_fn
    # ────────────────────────────────────────────────────────────

    def make_model_fn(self, max_new_tokens: int = 256,
                       temperature: float = 0.0):
        """
        回傳一個純文字推論 callable。
        signature: model_fn(prompt: str) -> str
        """
        if not self._loaded:
            raise RuntimeError("請先呼叫 load() 載入模型。")

        def model_fn(prompt: str) -> str:
            text_prompt = self.text.build_prompt(prompt, num_images=0)
            fused = self.fusion.fuse_inputs(
                text=text_prompt.prompt, image_inputs={}
            )
            fused["use_cache"] = False
            return self.fusion.generate(
                fused_inputs=fused,
                gen_cfg=GenerationConfig(
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=(temperature > 0),
                ),
            )

        return model_fn

    def make_deliberate_fn(self):
        """深思路徑專用 model_fn。"""
        return self.make_model_fn(
            max_new_tokens=DELIBERATE_MAX_TOKENS,
            temperature=DELIBERATE_TEMPERATURE,
        )

    def make_dialogue_fn(self):
        """對話生成專用 model_fn。"""
        return self.make_model_fn(
            max_new_tokens=DIALOGUE_MAX_TOKENS,
            temperature=DIALOGUE_TEMPERATURE,
        )

    def make_consolidation_fn(self, step: str):
        """
        睡眠濃縮各步驟專用 model_fn。

        step ∈ {"ham_extract", "select", "summary",
                 "relation", "emotion", "schedule"}
        """
        token_map = {
            "ham_extract": CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS,
            "select":      CONSOLIDATE_SELECT_MAX_TOKENS,
            "summary":     CONSOLIDATE_SUMMARY_MAX_TOKENS,
            "relation":    CONSOLIDATE_RELATION_MAX_TOKENS,
            "emotion":     CONSOLIDATE_EMOTION_MAX_TOKENS,
            "schedule":    SCHEDULE_GEN_MAX_TOKENS,
        }
        return self.make_model_fn(
            max_new_tokens=token_map.get(step, 256),
            temperature=0.0,
        )
