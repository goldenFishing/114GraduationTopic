# ================================================================
# model/inference_engine.py
# Gemma 4 推論引擎
#
# 架構說明：
#   - Gemma 4 是多模態模型（text / image / audio），此處只用 text 路徑
#   - TextEncoder   : 用 processor.tokenizer.apply_chat_template 組 chat prompt
#   - FusionDecoder : 包裝 model.generate()，處理 device placement
#   - VisionEncoder : 保留介面（未來可接圖片輸入），文字模式下為 no-op
#   - BatchInference: 依 VRAM 決定 batch size
#
# 與舊版（Phi-3.5）的差異：
#   - 移除所有 is_phi 判斷分支
#   - processor.tokenizer 負責 chat template；processor 負責 tokenize
#   - 啟用 KV cache（use_cache 不再強制設 False）
#   - 使用 _first_device() 相容 device_map / 量化模型
#   - temperature=0 時不傳入 temperature 參數，避免 HuggingFace 警告
# ================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

import torch
from PIL import Image

from config.model_config import (
    DELIBERATE_MAX_TOKENS, DELIBERATE_TEMPERATURE,
    DIALOGUE_MAX_TOKENS, DIALOGUE_TEMPERATURE,
    BATCH_SIZE_MAX_HIGH_VRAM,
    BATCH_SIZE_MAX_MID_VRAM,
    BATCH_SIZE_MAX_LOW_VRAM,
    VRAM_THRESHOLD_HIGH,
    VRAM_THRESHOLD_MID,
)

ImageLike = Union[str, Image.Image]


# ── VisionEncoder ──────────────────────────────────────────────────────────────

@dataclass
class VisionBatch:
    """圖片處理器輸出封裝（text-only 時 pixel_values=None）。"""
    pixel_values:   Any
    image_sizes:    Any = None
    num_img_tokens: Any = None

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        if self.pixel_values is not None:
            d["pixel_values"] = self.pixel_values
        if self.image_sizes is not None:
            d["image_sizes"] = self.image_sizes
        if self.num_img_tokens is not None:
            d["num_img_tokens"] = self.num_img_tokens
        return d


class VisionEncoder:
    """
    圖片前處理。
    Gemma 4 text-only 模式：直接回傳空 VisionBatch。
    保留介面供未來圖片輸入擴充。
    """

    def __init__(self, processor):
        self.processor       = processor
        self.image_processor = getattr(processor, "image_processor", None)

    @staticmethod
    def _load(img: ImageLike) -> Image.Image:
        return img.convert("RGB") if isinstance(img, Image.Image) \
               else Image.open(img).convert("RGB")

    def encode(self, images: Sequence[ImageLike],
               return_tensors: str = "pt") -> VisionBatch:
        """
        Text-only 模式：不做任何處理。
        若未來需要圖片輸入，在此呼叫 processor 的 image_processor。
        """
        return VisionBatch(pixel_values=None)


# ── TextEncoder ────────────────────────────────────────────────────────────────

@dataclass
class TextPrompt:
    prompt: str


class TextEncoder:
    """
    將 user_text 封裝為 Gemma 4 chat template 格式字串。

    Gemma 4 chat template 格式：
      <bos><start_of_turn>user\n{text}<end_of_turn>\n<start_of_turn>model\n
    由 processor.tokenizer.apply_chat_template 自動生成。
    """

    def __init__(self, processor):
        self.processor = processor
        self.tokenizer = processor.tokenizer

    def build_prompt(self, user_text: str,
                     num_images: int = 0,
                     system_text: Optional[str] = None) -> TextPrompt:
        """
        組合完整 chat prompt 字串（未 tokenize）。

        Gemma 4 text-only（num_images=0）：
          messages = [{"role": "user", "content": [{type: text}]}]
        含圖片（num_images > 0）：
          messages[0]["content"] 前面插入 {type: image} 佔位符
        """
        messages: List[dict] = []
        if system_text:
            messages.append({"role": "system", "content": [
                {"type": "text", "text": system_text}
            ]})

        user_content = []
        # 圖片佔位符（text-only 不加）
        for _ in range(num_images):
            user_content.append({"type": "image"})
        user_content.append({"type": "text", "text": user_text})

        messages.append({"role": "user", "content": user_content})

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        return TextPrompt(prompt=prompt)


# ── FusionDecoder / GenerationConfig ──────────────────────────────────────────

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
    """
    Gemma 4 推論包裝器。

    fuse_inputs  : processor tokenize → input_ids / attention_mask
    generate     : model.generate() with KV cache enabled
    _first_device: 取量化/device_map 後模型真正所在裝置
    """

    def __init__(self, model, processor, device: torch.device):
        self.model     = model
        self.processor = processor
        self.device    = device

    def _first_device(self) -> torch.device:
        """
        取模型第一個參數所在裝置。
        使用 device_map 量化時模型分散多個裝置，
        inputs 需送到 embedding 層的裝置（通常仍是 cuda:0）。
        """
        try:
            return next(self.model.parameters()).device
        except StopIteration:
            return self.device

    def fuse_inputs(self, text: str,
                    image_inputs: Dict[str, Any],
                    images: Optional[List[Image.Image]] = None,
                    return_tensors: str = "pt") -> Dict[str, Any]:
        """
        Tokenize 文字輸入（Gemma 4 text-only）。

        image_inputs / images 保留介面供未來擴充；text-only 模式忽略。
        回傳 dict：{"input_ids": Tensor, "attention_mask": Tensor}
        """
        if images:
            # 未來圖片支援路徑
            pil_images = [
                img.convert("RGB") if isinstance(img, Image.Image)
                else Image.open(img).convert("RGB")
                for img in images
            ]
            return self.processor(
                text=text,
                images=pil_images,
                return_tensors=return_tensors,
            )
        # Text-only（主要路徑）
        return self.processor(text=text, return_tensors=return_tensors)

    @torch.inference_mode()
    def generate(self, fused_inputs: Dict[str, Any],
                 gen_cfg: Optional[GenerationConfig] = None) -> str:
        """
        單筆推論。回傳純文字（已切除 prompt 部分）。

        - 使用 _first_device() 相容 device_map / 量化模型
        - KV cache 預設開啟（不傳 use_cache=False）
        - temperature=0 時不傳入 temperature，避免 HuggingFace 警告
        - pad_token_id 設為 eos_token_id，避免 open-end generation 警告
        """
        if gen_cfg is None:
            gen_cfg = GenerationConfig()

        target = self._first_device()
        fused_inputs = {
            k: (v.to(target) if hasattr(v, "to") else v)
            for k, v in fused_inputs.items()
        }

        eos_id = self.processor.tokenizer.eos_token_id
        pad_id = self.processor.tokenizer.pad_token_id or eos_id

        gen_kwargs: Dict[str, Any] = dict(
            eos_token_id   = eos_id,
            pad_token_id   = pad_id,
            max_new_tokens = gen_cfg.max_new_tokens,
            do_sample      = gen_cfg.do_sample,
        )
        # 只在 sampling 模式下傳 temperature
        if gen_cfg.do_sample and gen_cfg.temperature > 0:
            gen_kwargs["temperature"] = gen_cfg.temperature

        ids = self.model.generate(**fused_inputs, **gen_kwargs)

        # 切掉 prompt 部分，只保留生成內容
        prompt_len = fused_inputs["input_ids"].shape[1]
        ids = ids[:, prompt_len:]
        return self.processor.tokenizer.batch_decode(
            ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

    @torch.inference_mode()
    def generate_batch(self, fused_inputs_list: List[Dict[str, Any]],
                        gen_cfg: Optional[GenerationConfig] = None) -> List[str]:
        """
        Batch 推論（sequential fallback）。
        Gemma 4 的 padding 需統一長度，此處用 sequential 確保正確性。
        若 batch_size > 1 且記憶體充裕，可在此改為真正 batch padding。
        """
        if not fused_inputs_list:
            return []
        results = []
        for fused in fused_inputs_list:
            results.append(self.generate(fused, gen_cfg))
        return results


# ── BatchInference ─────────────────────────────────────────────────────────────

def detect_available_vram_mb() -> int:
    """偵測當前 GPU 可用顯存（MB）。非 CUDA 環境回傳 0。"""
    if not torch.cuda.is_available():
        return 0
    try:
        free_bytes, _ = torch.cuda.mem_get_info()
        return free_bytes // (1024 * 1024)
    except Exception:
        return 0


def decide_batch_size(num_prompts: int, vram_mb: int = None) -> int:
    """
    根據顯存決定 batch_size 上限。
    回傳：實際要用的 batch_size（≤ num_prompts）
    """
    if vram_mb is None:
        vram_mb = detect_available_vram_mb()

    if vram_mb >= VRAM_THRESHOLD_HIGH:
        max_batch = BATCH_SIZE_MAX_HIGH_VRAM
    elif vram_mb >= VRAM_THRESHOLD_MID:
        max_batch = BATCH_SIZE_MAX_MID_VRAM
    else:
        max_batch = BATCH_SIZE_MAX_LOW_VRAM

    return min(num_prompts, max_batch)


def batch_generate(
    loader,
    prompts: list,
    images_list: list = None,
    gen_cfg = None,
) -> list:
    """
    Batch 推論入口。

    參數：
      loader     : ModelLoader
      prompts    : prompt 字串列表
      images_list: 對應圖片（PIL.Image 或 None）
      gen_cfg    : GenerationConfig

    回傳：結果字串列表（順序與 prompts 對應）
    """
    if not prompts:
        return []

    images_list = images_list or [None] * len(prompts)
    batch_size  = decide_batch_size(len(prompts))

    results = []
    for i in range(0, len(prompts), batch_size):
        chunk_prompts = prompts[i:i + batch_size]
        chunk_images  = images_list[i:i + batch_size]

        fused_list = []
        for p, img in zip(chunk_prompts, chunk_images):
            num_images  = 1 if img else 0
            text_prompt = loader.text.build_prompt(p, num_images=num_images)
            image_inputs = {}
            if img:
                vision_batch = loader.vision.encode([img])
                image_inputs = vision_batch.to_dict()
            fused = loader.fusion.fuse_inputs(
                text=text_prompt.prompt,
                image_inputs=image_inputs,
                images=[img] if img else None,
            )
            fused_list.append(fused)

        chunk_results = loader.fusion.generate_batch(fused_list, gen_cfg)
        results.extend(chunk_results)

    return results
