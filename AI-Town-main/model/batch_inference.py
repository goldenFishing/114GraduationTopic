# ================================================================
# model/batch_inference.py
# Batch 推論工具（依顯存自動分批）
#
# 對應 ARCHITECTURE.md §6.4.7
#
# 設計：
#   1. 偵測 GPU 可用顯存
#   2. 依 VRAM 閾值決定 batch_size
#   3. 把多個 prompt 分批送進 fusion_decoder
#
# 注意：
#   Phi-3.5-Vision 的 batch 實作較複雜（不同 prompt 可能有不同
#   數量的圖片，需要 padding）。本版本先做「pseudo-batch」：
#   邏輯上接受 batch 介面，內部 sequential 跑。
#   未來可優化為真 batch（需要處理 attention mask + padding）。
#
# 誰會調用：
#   agent/manager.py — 收集多角色的 deliberate prompt 一起跑
# ================================================================

import torch

from config.model_config import (
    BATCH_SIZE_MAX_HIGH_VRAM,
    BATCH_SIZE_MAX_MID_VRAM,
    BATCH_SIZE_MAX_LOW_VRAM,
    VRAM_THRESHOLD_HIGH,
    VRAM_THRESHOLD_MID,
)


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
      images_list: 對應的圖片列表（每個元素是 PIL.Image 或 None）
      gen_cfg    : GenerationConfig

    回傳：結果字串列表（順序與 prompts 對應）

    內部邏輯：
      1. 算 batch_size
      2. 切分 prompts
      3. 對每批呼叫 fusion_decoder
      4. 合併結果
    """
    if not prompts:
        return []

    images_list = images_list or [None] * len(prompts)
    batch_size = decide_batch_size(len(prompts))

    results = []
    for i in range(0, len(prompts), batch_size):
        chunk_prompts = prompts[i:i + batch_size]
        chunk_images  = images_list[i:i + batch_size]

        fused_list = []
        for p, img in zip(chunk_prompts, chunk_images):
            num_images = 1 if img else 0
            text_prompt = loader.text.build_prompt(p, num_images=num_images)
            if img:
                vision_batch = loader.vision.encode([img])
                image_inputs = vision_batch.to_dict()
            else:
                image_inputs = {}
            fused = loader.fusion.fuse_inputs(
                text=text_prompt.prompt,
                image_inputs=image_inputs,
            )
            fused_list.append(fused)

        chunk_results = loader.fusion.generate_batch(fused_list, gen_cfg)
        results.extend(chunk_results)

    return results
