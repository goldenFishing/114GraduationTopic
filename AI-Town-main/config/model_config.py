# ================================================================
# config/model_config.py
# Phi-3.5-Vision 模型的所有推論參數
#
# 對應 ARCHITECTURE.md §6.1.6 + §8.5
#
# 誰會調用這個檔案：
#   model/model_loader.py       — 載入模型、建立各路徑的 model_fn
#   model/fusion_decoder.py     — GenerationConfig 的預設值
#   model/prompt_builder.py     — 組 prompt 時截斷 STM/LTM 區塊
#   model/batch_inference.py    — 依顯存決定 batch size
#   agent/scheduler.py          — 時間表生成的 token 上限
#   core/consolidation.py       — 睡眠濃縮各步驟的 token 上限
# ================================================================


# ================================================================
# A. 模型載入設定
#
# 何時生效：程式啟動時 ModelLoader.load() 一次性使用
# ================================================================

MODEL_ID         = "microsoft/Phi-3.5-vision-instruct"
MODEL_NUM_CROPS  = 4        # 圖片切塊數，影響視覺處理精度
MODEL_CACHE_DIR  = None     # None = 用 HuggingFace 預設快取
                            # 可改成自訂路徑如 "D:/models/phi35"


# ================================================================
# B. 深思路徑（Agent.decide() 走 deliberate 時）
#
# 何時生效：每次需要深度思考決策時
# 影響：模型輸出長度上限、生成的確定性
#
# token 預算計算（中文 1 字 ≈ 1.5 tokens）：
#   [ACTION] + [TARGET] + [CONTENT]   ~30 字 = 50 tokens
#   [THOUGHT] 2-3 句                  ~80 字 = 130 tokens
#   [HAM] 5 條命題                    ~200 字 = 350 tokens
#   緩衝                              ~70 tokens
#                                     ─────────
#   總計                              ~600 tokens
# ================================================================

DELIBERATE_MAX_TOKENS  = 600
DELIBERATE_TEMPERATURE = 0.0    # 確定性輸出，重現性高


# ================================================================
# C. 對話生成（Agent.generate_dialogue_response()）
#
# 何時生效：對話循環中每一輪呼叫
# temperature 略提高，避免兩個角色講話像同一個模子刻出來
# ================================================================

DIALOGUE_MAX_TOKENS  = 400
DIALOGUE_TEMPERATURE = 0.3      # 對話需要多樣性，但不能太隨機


# ================================================================
# D. 睡眠濃縮（core/consolidation.py 各步驟）
#
# 何時生效：角色入睡時，依步驟順序逐個呼叫模型
# 每個步驟有自己的 token 預算（任務性質不同）
# ================================================================

# Step 2：從 STM 敘述抽 HAM 5 元組
CONSOLIDATE_HAM_EXTRACT_MAX_TOKENS = 500

# Step 3：從候選 HAM 中篩選重要的（最多 5 筆）
CONSOLIDATE_SELECT_MAX_TOKENS      = 200

# Step 5：生成新 LTM 摘要（1-2 句）
CONSOLIDATE_SUMMARY_MAX_TOKENS     = 80

# Step 6：更新與某角色的關係摘要（1 句）
CONSOLIDATE_RELATION_MAX_TOKENS    = 80

# Step 7：推斷新情緒（只回單詞）
CONSOLIDATE_EMOTION_MAX_TOKENS     = 10

# Step 8：生成隔天時間表（JSON list）
SCHEDULE_GEN_MAX_TOKENS            = 500


# ================================================================
# E. Prompt 注入預算
#
# 何時生效：PromptBuilder 組裝 prompt 時截斷 STM/LTM 區塊
# 防止 prompt 過長爆 context window
#
# 中文 1 字 ≈ 1.5 tokens
# Phi-3.5 context window = 128K tokens（綽綽有餘）
# 但 prompt 越長推論越慢，所以限制注入長度
# ================================================================

STM_TOKEN_BUDGET = 1500     # STM 敘述化文字上限（一天 30 筆敘述夠用）
LTM_TOKEN_BUDGET = 800      # LTM 命題反向組句後上限（2 跳擴散後命題量增加）


# ================================================================
# F. Batch 推論設定
#
# 何時生效：model/batch_inference.py 依顯存自動選擇 batch size
#   顯存 ≥ 16GB → 用 HIGH
#   顯存 ≥ 12GB → 用 MID
#   否則         → 用 LOW（sequential）
#
# 你的硬體：
#   4090 (24GB) → HIGH 模式
#   3060 (12GB) → MID 模式
# ================================================================

BATCH_SIZE_MAX_HIGH_VRAM = 5    # 5 角色一次跑完
BATCH_SIZE_MAX_MID_VRAM  = 3    # 3 角色一批
BATCH_SIZE_MAX_LOW_VRAM  = 1    # 一次一個

# 顯存判斷閾值（MB）
VRAM_THRESHOLD_HIGH = 16 * 1024    # 16 GB
VRAM_THRESHOLD_MID  = 12 * 1024    # 12 GB
