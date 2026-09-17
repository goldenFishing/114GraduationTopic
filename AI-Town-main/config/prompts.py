# ================================================================
# config/prompts.py
# 所有送給 Phi-3.5 的 prompt 模板
#
# 對應 ARCHITECTURE.md §6.1.4
#
# 誰會調用這個檔案：
#   model/prompt_builder.py    — prompt_deliberate, prompt_dialogue
#   core/consolidation.py      — prompt_extract_ham, prompt_select_ltm,
#                                prompt_ltm_summary, prompt_update_relationship,
#                                prompt_infer_emotion
#   agent/scheduler.py         — prompt_generate_schedule
#
# 注意：
#   Markov 路徑完全不呼叫模型，所以沒有 prompt_intuitive。
#
# 輸出格式設計：
#   決策/對話用 block-style（[ACTION][TARGET][CONTENT][THOUGHT][HAM]）
#     - Phi-3.5 在 block 上比 JSON 穩定
#     - HAM 用 | 分隔，避免 JSON 中文引號問題
#   摘要/情緒用純文字
#   時間表用 JSON
# ================================================================

from config.action_list import VALID_ACTIONS, VALID_LOCATIONS
from config.world_config import VALID_EMOTIONS


# ================================================================
# 共用提示語（每個 prompt 都加）
# ================================================================

_LANGUAGE_REMINDER = "請務必使用繁體中文回應，不要夾雜英文。"


# ================================================================
# 共用區塊：可用行動與地點
# ================================================================

def _action_list_str() -> str:
    return "、".join(VALID_ACTIONS)


def _location_list_str() -> str:
    return "、".join(VALID_LOCATIONS)


# ================================================================
# A. 深思路徑（決策） — model/prompt_builder.build_deliberate()
# ================================================================

def prompt_deliberate(
    character_name: str,
    personality: str,
    habit: str,
    emotion: str,
    relationship_text: str,
    stm_narrative: str,
    ltm_narrative: str,
    scene: str,
    co_located_text: str = "",
    current_event: str = "",
) -> str:
    """
    深思路徑（System 2）的決策 prompt。

    輸入：
      character_name    : 角色名字
      personality       : 完整個性描述
      habit             : 習慣描述
      emotion           : 當前情緒
      relationship_text : 與當前可能互動對象的關係文字
      stm_narrative     : STM 敘述化文字（一天經歷的敘事）
      ltm_narrative     : LTM 圖譜反向組句後的相關記憶
      scene             : 當前場景（含時間+地點）
      co_located_text   : 同地點有誰
      current_event     : 當前發生的事件（對話輸入等）

    輸出：模型回應 [ACTION][TARGET][CONTENT][THOUGHT][HAM] 區塊
    """
    rel_part   = f"\n【與相關對象的關係】\n{relationship_text}" if relationship_text else ""
    co_part    = f"\n【附近的人】\n{co_located_text}" if co_located_text else ""
    event_part = f"\n\n【當下事件】\n{current_event}" if current_event else ""
    ltm_part   = f"\n【相關長期記憶】\n{ltm_narrative}" if ltm_narrative else ""

    return f"""{_LANGUAGE_REMINDER}

你正在扮演 {character_name}，依據你的記憶、個性與當下狀況，決定此刻最想做的事。

【個性】{personality}
【習慣】{habit}
【目前情緒】{emotion}{rel_part}{co_part}

【今天到現在發生的事】
{stm_narrative}{ltm_part}

【目前場景】
{scene}{event_part}

【可執行的行動】{_action_list_str()}
【可前往的地點】{_location_list_str()}

決策時請考慮：
- 現在幾點？是否需要工作、用餐、回家或休息？
- 附近有誰？如果想對話，對方在嗎？
- 還有什麼重要的事沒做完？
- 你是 {character_name}，自然依照你的方式回應（但不需過度強調，人是有彈性的）。

若選擇「對話」，[CONTENT] 必須寫出真正要說的完整一句話，不能寫「想說的話」這種抽象描述。
若選擇「前往」，[TARGET] 填地點名稱。
其他行動，[TARGET] 與 [CONTENT] 可留空。

請嚴格依照以下格式回應，標籤不可省略：

[ACTION] (從可執行行動清單選一個)
[TARGET] (地點名稱、人名、或留空)
[CONTENT] (對話時填要說的話、其他留空)

[THOUGHT] (內心想法，2-3 句)

[HAM]
- 主詞 | 關係 | 受詞 | 地點 | 時間
- (最多 5 筆，每筆一行，用 | 分隔)
[/HAM]"""


# ================================================================
# B. 對話路徑 — model/prompt_builder.build_dialogue()
# ================================================================

def prompt_dialogue(
    character_name: str,
    personality: str,
    emotion: str,
    partner_name: str,
    relationship_text: str,
    stm_narrative: str,
    ltm_narrative: str,
    scene: str,
    recent_dialogue: str,
    partner_message: str,
) -> str:
    """
    對話一輪的 prompt（會被對話循環多次呼叫）。

    輸入：
      character_name    : 自己名字
      personality       : 自己個性
      emotion           : 自己情緒
      partner_name      : 對話對象名字
      relationship_text : 與對方的關係
      stm_narrative     : 自己今天的經歷
      ltm_narrative     : 相關長期記憶
      scene             : 場景
      recent_dialogue   : 最近 3 輪對話歷史（雙方說了什麼）
      partner_message   : 對方剛剛說的話

    輸出：模型回應 [ACTION][TARGET][CONTENT][THOUGHT][HAM]
          通常 ACTION = 對話，除非角色決定結束對話
    """
    rel_part = f"\n【你與 {partner_name} 的關係】\n{relationship_text}" if relationship_text else ""
    ltm_part = f"\n【相關長期記憶】\n{ltm_narrative}" if ltm_narrative else ""
    history_part = f"\n【最近的對話】\n{recent_dialogue}" if recent_dialogue else ""

    return f"""{_LANGUAGE_REMINDER}

你正在扮演 {character_name}，現在正在和 {partner_name} 對話。

【你的個性】{personality}
【你目前的情緒】{emotion}{rel_part}

【你今天的經歷】
{stm_narrative}{ltm_part}

【目前場景】
{scene}{history_part}

【{partner_name} 剛剛對你說】
{partner_message}

請決定如何回應：
- 一般情況下選「對話」，[CONTENT] 寫出你要說的完整一句話
- 若想結束對話，可以說明確的結束話語（「我先走了」「待會聊」）
- 若話題已盡或想做其他事，可以選其他行動

請嚴格依照以下格式回應：

[ACTION] (從行動清單選一個)
[TARGET] {partner_name} (對話時填對方名字、其他填地點或留空)
[CONTENT] (對話內容、或留空)

[THOUGHT] (此刻內心想法，1-2 句)

[HAM]
- 主詞 | 關係 | 受詞 | 地點 | 時間
- (本輪對話的關鍵命題，1-3 筆即可)
[/HAM]"""


# ================================================================
# C. HAM 抽取 — core/consolidation.py Step 2
# ================================================================

def prompt_extract_ham(
    character_name: str,
    today_narrative: str,
) -> str:
    """
    從 STM 敘述化文字中抽取 HAM 5 元組命題。

    輸入：
      character_name  : 角色名字
      today_narrative : 當天 STM 全部敘述化的長文字

    輸出：HAM 命題列表（管道符分隔，每行一筆）
    """
    return f"""{_LANGUAGE_REMINDER}

請從 {character_name} 今天的經歷中，抽取出值得長期記憶的 HAM 5 元組命題。

【今天的經歷】
{today_narrative}

抽取規則：
- 每筆命題格式：主詞 | 關係 | 受詞 | 地點 | 時間
- 主詞通常是 {character_name} 或其他角色名
- 關係是動詞或描述（遇見、喜歡、看到、感到、工作、對話等）
- 受詞是人、物或事件
- 地點、時間可省略（填「無」）
- 優先抽取：人物互動、情感變化、新發現的事、有意義的事件
- 忽略：純粹日常瑣事（單純的吃飯、走路、滑手機）
- 最多抽 10 筆

只回傳命題列表，每行一筆，用 | 分隔，不要其他文字。範例：

{character_name} | 遇見 | Ben | 咖啡廳 | 早上
{character_name} | 感到 | 緊張 | 無 | 下午
Ben | 詢問 | {character_name} | 咖啡廳 | 早上"""


# ================================================================
# D. 篩選重要 HAM — core/consolidation.py Step 3
# ================================================================

def prompt_select_ltm(
    character_name: str,
    today_narrative: str,
    extracted_props: str,
) -> str:
    """
    從已抽取的 HAM 中篩選出值得長期保存的（最重要的）。

    輸入：
      character_name   : 角色名字
      today_narrative  : 當天經歷敘述
      extracted_props  : 上一步抽出的所有命題（| 分隔列表）

    輸出：精選後的命題列表（同樣格式）
    """
    return f"""{_LANGUAGE_REMINDER}

請從以下命題中，選出最值得 {character_name} 長期記憶的項目。

【今天的經歷】
{today_narrative}

【今天抽出的所有命題】
{extracted_props}

篩選規則：
- 保留涉及人物互動與情感變化的
- 保留改變了 {character_name} 認知或關係的
- 刪除瑣碎、重複、無意義的命題
- 最多保留 5 筆

只回傳精選後的命題列表（同樣 | 分隔格式），每行一筆。"""


# ================================================================
# E. LTM 摘要 — core/consolidation.py Step 5
# ================================================================

def prompt_ltm_summary(
    character_name: str,
    all_props_text: str,
) -> str:
    """
    根據所有 LTM 命題生成 1-2 句摘要。

    輸入：
      character_name : 角色名字
      all_props_text : 目前 LTM 所有命題的文字呈現

    輸出：1-2 句純文字摘要
    """
    return f"""{_LANGUAGE_REMINDER}

請用 1-2 句話總結 {character_name} 的長期記憶。

【LTM 所有命題】
{all_props_text}

以 {character_name} 的視角撰寫，聚焦在重要的人際關係與關鍵事件。
只回傳摘要文字，不要其他格式或說明。"""


# ================================================================
# F. 關係更新 — core/consolidation.py Step 6
# ================================================================

def prompt_update_relationship(
    character_name: str,
    target_name: str,
    initial: str,
    old_summary: str,
    today_narrative: str,
) -> str:
    """
    根據今天的事件更新與某角色的關係摘要。

    輸入：
      character_name   : 自己名字
      target_name      : 目標角色名字
      initial          : 兩人的初始關係（不變）
      old_summary      : 昨天的關係摘要
      today_narrative  : 今天的經歷

    輸出：一句話的新關係摘要
    """
    old_part = (
        f"先前的關係摘要：{old_summary}"
        if old_summary else "目前沒有先前的摘要紀錄。"
    )
    return f"""{_LANGUAGE_REMINDER}

請更新 {character_name} 與 {target_name} 之間的關係摘要。

【兩人的初始關係】{initial}
{old_part}

【今天 {character_name} 的經歷】
{today_narrative}

更新規則：
- 用一句話描述目前兩人關係的現狀
- 只有今天發生了重要變化才需要更新核心內容
- 若今天兩人沒有直接互動，但 {character_name} 想到 {target_name}，可微幅調整
- 若完全無相關，回傳「無變化」即可

只回傳一句話，不要其他格式。"""


# ================================================================
# G. 情緒推斷 — core/consolidation.py Step 7
# ================================================================

def prompt_infer_emotion(
    character_name: str,
    today_narrative: str,
    previous_emotion: str,
) -> str:
    """
    根據今天的事件推斷新情緒（僅在 today_max_K >= EMOTION_RESET_THRESHOLD 時調用，
    平時直接回歸「平靜」不呼叫模型）。

    輸入：
      character_name   : 角色名字
      today_narrative  : 今天的經歷
      previous_emotion : 昨天的情緒

    輸出：VALID_EMOTIONS 中的單一情緒詞
    """
    emotions_str = "、".join(VALID_EMOTIONS)
    return f"""{_LANGUAGE_REMINDER}

根據今天發生的事，{character_name} 目前的情緒是什麼？

【今天的經歷】
{today_narrative}

【昨天的情緒】{previous_emotion}

可選的情緒：{emotions_str}

判斷規則：
- 若沒有重大事件，請傾向回歸「平靜」
- 若昨天已是負面情緒（緊張/不安/難過/疲憊），今天傾向往「平靜」靠
- 只有今天真的發生了強烈事件，才選擇對應的非平靜情緒

只回傳一個情緒詞，不要其他文字。"""


# ================================================================
# H. 時間表生成 — agent/scheduler.py
# ================================================================

def prompt_generate_schedule(
    character_name: str,
    personality_short: str,
    habit: str,
    role: str,
    day: int,
    ltm_summary: str,
    today_important_events: str,
    yesterday_schedule_text: str,
    template_text: str,
) -> str:
    """
    睡眠濃縮的最後步驟：生成隔天的時間表。

    輸入：
      character_name           : 角色名字
      personality_short        : 個性簡述
      habit                    : 習慣
      role                     : 職業
      day                      : 明天是第幾天
      ltm_summary              : LTM 摘要
      today_important_events   : 今天的重要事件摘要
      yesterday_schedule_text  : 昨天的時間表（給模型參考連續性）
      template_text            : 該職業的範本

    輸出：JSON list，每個元素是 {time, action, location} 的時段
    """
    return f"""{_LANGUAGE_REMINDER}

你正在幫 {character_name}（{role}）規劃第 {day} 天的時間表。

【個性】{personality_short}
【習慣】{habit}
【長期記憶摘要】{ltm_summary if ltm_summary else "（尚無重要記憶）"}

【今天的重要事件】
{today_important_events if today_important_events else "（無特殊事件）"}

【昨天的時間表（參考連續性）】
{yesterday_schedule_text}

【職業範本（可大幅修改）】
{template_text}

【可執行行動】{_action_list_str()}
【可前往地點】{_location_list_str()}

規劃規則：
- 必須有「起床」「睡覺」時段
- 必須有該職業的核心工作時段
- 時間表以 1 小時為單位，使用 HH:MM 格式
- 起床時間在 06:00-10:00 之間
- 睡覺時間在 21:00-02:00 之間
- 可根據今天的事件動態調整（例如累了就早點睡、想找某人就安排去某地）

只回傳 JSON 陣列，不要其他文字。格式：

[
  {{"time": "07:00", "action": "起床", "location": "公寓三樓"}},
  {{"time": "08:30", "action": "前往", "location": "咖啡廳"}},
  {{"time": "09:00", "action": "賣咖啡", "location": "咖啡廳"}}
]"""
