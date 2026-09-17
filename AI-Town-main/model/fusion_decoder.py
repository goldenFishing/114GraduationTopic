# ================================================================
# model/fusion_decoder.py
# 圖文融合推論 + batch 推論支援
#
# 對應 ARCHITECTURE.md §6.4.4
#
# 修改重點：
#   1. 加入 GenerationConfig.dialogue() 工廠
#   2. 加入 generate_batch() 方法
#   3. 移除舊版 GenerationConfig.intuitive()（不再呼叫模型）
# ================================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch

from config.model_config import (
    DELIBERATE_MAX_TOKENS, DELIBERATE_TEMPERATURE,
    DIALOGUE_MAX_TOKENS, DIALOGUE_TEMPERATURE,
)


@dataclass
class GenerationConfig:
    max_new_tokens: int   = 256
    temperature:    float = 0.0
    do_sample:      bool  = False

    @classmethod
    def deliberate(cls) -> "GenerationConfig":
        return cls(
            max_new_tokens = DELIBERATE_MAX_TOKENS,
            temperature    = DELIBERATE_TEMPERATURE,
            do_sample      = False,
        )

    @classmethod
    def dialogue(cls) -> "GenerationConfig":
        return cls(
            max_new_tokens = DIALOGUE_MAX_TOKENS,
            temperature    = DIALOGUE_TEMPERATURE,
            do_sample      = (DIALOGUE_TEMPERATURE > 0),
        )


class FusionDecoder:
    """圖文融合推論。"""

    def __init__(self, model, processor, device: torch.device):
        self.model     = model
        self.processor = processor
        self.device    = device

    # ────────────────────────────────────────────────────────────

    def fuse_inputs(self, text: str,
                    image_inputs: Dict[str, Any],
                    return_tensors: str = "pt") -> Dict[str, Any]:
        """合併圖文輸入。"""
        return self.processor._convert_images_texts_to_inputs(
            image_inputs, text, return_tensors=return_tensors
        )

    @torch.inference_mode()
    def generate(self, fused_inputs: Dict[str, Any],
                 gen_cfg: Optional[GenerationConfig] = None) -> str:
        """單筆推論。回傳純文字（已切除 prompt 部分）。"""
        if gen_cfg is None:
            gen_cfg = GenerationConfig()

        fused_inputs = {
            k: (v.to(self.device) if hasattr(v, "to") else v)
            for k, v in fused_inputs.items()
        }

        ids = self.model.generate(
            **fused_inputs,
            eos_token_id   = self.processor.tokenizer.eos_token_id,
            max_new_tokens = gen_cfg.max_new_tokens,
            temperature    = gen_cfg.temperature,
            do_sample      = gen_cfg.do_sample,
        )

        ids = ids[:, fused_inputs["input_ids"].shape[1]:]
        return self.processor.batch_decode(
            ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

    @torch.inference_mode()
    def generate_batch(self, fused_inputs_list: List[Dict[str, Any]],
                        gen_cfg: Optional[GenerationConfig] = None) -> List[str]:
        """
        Batch 推論。
        所有 prompt 一起跑，提升 GPU 利用率。

        注意：每個 prompt 透過 attention_mask 隔離，不會互相影響。

        若 batch_inference.py 計算後決定不 batch，會逐個呼叫 generate()。
        這個方法假設 caller 已經處理過 batch_size。
        """
        if not fused_inputs_list:
            return []

        if len(fused_inputs_list) == 1:
            return [self.generate(fused_inputs_list[0], gen_cfg)]

        if gen_cfg is None:
            gen_cfg = GenerationConfig()

        # 由於 Phi-3.5-Vision 的 input 結構特殊（image_sizes 等）
        # 簡單可靠的做法是 fallback 為 sequential。
        # 真正的 batch padding 留給 batch_inference.py 處理。
        results = []
        for fused in fused_inputs_list:
            results.append(self.generate(fused, gen_cfg))
        return results
