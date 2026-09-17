# ================================================================
# make_ppt.py
# AI-Town 專案完整簡報生成腳本
# 使用 python-pptx 1.0.2
# ================================================================

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import os

# ================================================================
# 色彩定義
# ================================================================
DARK_BLUE   = RGBColor(0x1a, 0x2e, 0x52)   # 深藍（主色、標題列）
BLUE        = RGBColor(0x00, 0x5c, 0xb5)   # 中藍（重點區塊）
LIGHT_BLUE  = RGBColor(0xd6, 0xe8, 0xff)   # 淺藍（背景/填充）
GREEN       = RGBColor(0x0d, 0x6e, 0x3a)   # 綠（System 1 / intuitive）
LIGHT_GREEN = RGBColor(0xd6, 0xf0, 0xe0)   # 淺綠
ORANGE      = RGBColor(0xb8, 0x6a, 0x00)   # 橘（System 2 / deliberate）
LIGHT_ORANGE= RGBColor(0xff, 0xee, 0xcc)   # 淺橘
RED         = RGBColor(0xa8, 0x1c, 0x1c)   # 紅
LIGHT_RED   = RGBColor(0xff, 0xe0, 0xe0)   # 淺紅
PURPLE      = RGBColor(0x5b, 0x00, 0x8f)   # 紫
LIGHT_PURPLE= RGBColor(0xef, 0xd9, 0xff)   # 淺紫
TEAL        = RGBColor(0x00, 0x6d, 0x77)   # 青
LIGHT_TEAL  = RGBColor(0xcc, 0xf0, 0xf3)   # 淺青
GRAY        = RGBColor(0x55, 0x55, 0x55)   # 深灰
LIGHT_GRAY  = RGBColor(0xf2, 0xf4, 0xf8)   # 淺灰
WHITE       = RGBColor(0xff, 0xff, 0xff)
BLACK       = RGBColor(0x00, 0x00, 0x00)
YELLOW      = RGBColor(0xff, 0xd7, 0x00)   # 金黃

# ================================================================
# 簡報尺寸（16:9）
# ================================================================
SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.50)


# ================================================================
# 工具函數
# ================================================================

def new_prs():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    blank_layout = prs.slide_layouts[6]  # completely blank
    return prs.slides.add_slide(blank_layout)


def add_rect(slide, x, y, w, h,
             fill_color=None, line_color=None, line_width=Pt(1.5)):
    """新增矩形（inches 或 Emu）"""
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(x) if isinstance(x, float) else x,
        Inches(y) if isinstance(y, float) else y,
        Inches(w) if isinstance(w, float) else w,
        Inches(h) if isinstance(h, float) else h,
    )
    fill = shape.fill
    if fill_color:
        fill.solid()
        fill.fore_color.rgb = fill_color
    else:
        fill.background()

    line = shape.line
    if line_color:
        line.color.rgb = line_color
        line.width     = line_width
    else:
        line.fill.background()

    return shape


def add_text_box(slide, text, x, y, w, h,
                 font_size=Pt(14), bold=False, italic=False,
                 color=BLACK, align=PP_ALIGN.LEFT,
                 wrap=True, v_anchor=None):
    """新增文字框"""
    txBox = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    tf = txBox.text_frame
    tf.word_wrap = wrap
    if v_anchor:
        from pptx.enum.text import MSO_ANCHOR
        tf.vertical_anchor = v_anchor
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = font_size
    run.font.bold  = bold
    run.font.color.rgb = color
    if italic:
        run.font.italic = True
    return txBox


def add_label_in_rect(slide, shape, text,
                       font_size=Pt(13), bold=False,
                       color=WHITE, align=PP_ALIGN.CENTER):
    """在已有 shape 上覆蓋文字（使用文字框置中）"""
    l = shape.left
    t = shape.top
    w = shape.width
    h = shape.height
    txBox = slide.shapes.add_textbox(l, t, w, h)
    tf = txBox.text_frame
    tf.word_wrap = True
    from pptx.enum.text import MSO_ANCHOR
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = font_size
    run.font.bold  = bold
    run.font.color.rgb = color
    return txBox


def header_bar(slide, title, subtitle=""):
    """每張投影片頂端深藍色標題列"""
    # 深藍背景
    bar = add_rect(slide, 0, 0, 13.33, 1.1, fill_color=DARK_BLUE)
    # 標題
    add_text_box(slide, title,
                 0.3, 0.08, 9.5, 0.6,
                 font_size=Pt(28), bold=True,
                 color=WHITE, align=PP_ALIGN.LEFT)
    # 副標題
    if subtitle:
        add_text_box(slide, subtitle,
                     0.3, 0.65, 9.5, 0.38,
                     font_size=Pt(14), color=LIGHT_BLUE,
                     align=PP_ALIGN.LEFT)
    # 右上角 Logo 文字
    add_text_box(slide, "AI-Town",
                 11.2, 0.2, 1.9, 0.55,
                 font_size=Pt(20), bold=True,
                 color=YELLOW, align=PP_ALIGN.RIGHT)


def bullet_list(slide, items, x, y, w, h,
                font_size=Pt(13), color=DARK_BLUE,
                indent="  • ", line_spacing=1.2):
    """多行項目清單"""
    txBox = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(3)
        run = p.add_run()
        run.text = indent + item
        run.font.size  = font_size
        run.font.color.rgb = color
    return txBox


def arrow_right(slide, x, y, w=0.5, h=0.35, color=GRAY):
    """向右箭頭（用文字▶替代）"""
    add_text_box(slide, "▶", x, y, w, h,
                 font_size=Pt(18), color=color,
                 align=PP_ALIGN.CENTER)


def arrow_down(slide, x, y, w=0.5, h=0.35, color=GRAY):
    """向下箭頭"""
    add_text_box(slide, "▼", x, y, w, h,
                 font_size=Pt(18), color=color,
                 align=PP_ALIGN.CENTER)


def colored_box(slide, text, x, y, w, h,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(12), bold=False, font_color=DARK_BLUE,
                align=PP_ALIGN.CENTER):
    """帶底色邊框的文字方塊"""
    shape = add_rect(slide, x, y, w, h,
                     fill_color=fill, line_color=border, line_width=Pt(1.5))
    add_label_in_rect(slide, shape, text,
                      font_size=font_size, bold=bold,
                      color=font_color, align=align)
    return shape


# ================================================================
# Slide 1: 封面
# ================================================================
def slide_cover(prs):
    slide = blank_slide(prs)

    # 深藍漸層背景（用兩個矩形模擬）
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=DARK_BLUE)
    add_rect(slide, 0, 4.5, 13.33, 3.0, fill_color=RGBColor(0x0d, 0x1c, 0x38))

    # 金色橫線裝飾
    for i in range(3):
        add_rect(slide, 0.5, 1.5 + i*0.12, 12.33, 0.06,
                 fill_color=YELLOW)

    # 主標題
    add_text_box(slide, "AI-Town",
                 0.5, 1.9, 12.33, 1.2,
                 font_size=Pt(64), bold=True,
                 color=WHITE, align=PP_ALIGN.CENTER)

    # 英文副標題
    add_text_box(slide,
                 "Cognitive Agent Simulation System",
                 0.5, 3.0, 12.33, 0.7,
                 font_size=Pt(26),
                 color=LIGHT_BLUE, align=PP_ALIGN.CENTER)

    # 中文副標題
    add_text_box(slide,
                 "基於認知科學的多智能體模擬系統",
                 0.5, 3.65, 12.33, 0.6,
                 font_size=Pt(20),
                 color=LIGHT_BLUE, align=PP_ALIGN.CENTER)

    # 特色標籤
    tags = ["雙歷程決策", "HAM 記憶", "三源 Markov", "睡眠濃縮", "視覺感知"]
    tag_w = 2.0
    start_x = (13.33 - len(tags) * (tag_w + 0.2)) / 2
    for i, tag in enumerate(tags):
        tx = start_x + i * (tag_w + 0.2)
        colored_box(slide, tag, tx, 4.5, tag_w, 0.5,
                    fill=RGBColor(0x00, 0x3a, 0x7a),
                    border=LIGHT_BLUE,
                    font_size=Pt(13), bold=True,
                    font_color=WHITE)

    # 底部資訊
    add_text_box(slide,
                 "AI Town  ·  2026",
                 0.5, 6.7, 12.33, 0.5,
                 font_size=Pt(14),
                 color=LIGHT_BLUE, align=PP_ALIGN.CENTER)


# ================================================================
# Slide 2: 系統目標與特色
# ================================================================
def slide_goals(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "系統目標與特色",
               "模擬具備認知能力的 AI 角色在虛擬小鎮中生活")

    # 左側：目標
    colored_box(slide, "系統目標", 0.3, 1.25, 5.8, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(15), bold=True, font_color=WHITE)

    goals = [
        "模擬 5 個角色在虛擬小鎮中的日常生活",
        "角色具備記憶、情緒、個性差異",
        "決策融合認知科學理論（雙歷程理論）",
        "支援視覺感知輸入（YOLO + 語言模型）",
        "完整記憶生命週期：STM → 睡眠濃縮 → LTM",
    ]
    bullet_list(slide, goals, 0.3, 1.85, 5.9, 3.0,
                font_size=Pt(13.5), color=DARK_BLUE)

    # 右側：角色卡片
    colored_box(slide, "五位角色", 7.0, 1.25, 5.8, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(15), bold=True, font_color=WHITE)

    chars = [
        ("A  Amy",   "咖啡師",     LIGHT_BLUE,  BLUE),
        ("B  Ben",   "辦公室員工", LIGHT_GREEN, GREEN),
        ("C  Claire","律師",       LIGHT_ORANGE,ORANGE),
        ("D  David", "廚師",       LIGHT_PURPLE,PURPLE),
        ("E  Emma",  "超市員工",   LIGHT_TEAL,  TEAL),
    ]
    for i, (name, role, lc, bc) in enumerate(chars):
        row = i // 2
        col = i % 2
        cx = 7.05 + col * 2.95
        cy = 1.88 + row * 1.0
        if i == 4:
            cx = 8.5  # 最後一個居中
        colored_box(slide, f"{name}\n{role}",
                    cx, cy, 2.65, 0.82,
                    fill=lc, border=bc,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE)

    # 底部關鍵參數
    colored_box(slide, "關鍵參數：每天 20 ticks  ·  每 tick = 60 分鐘  ·  模擬時段 06:00–02:00",
                0.3, 5.1, 12.7, 0.65,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(14), bold=True, font_color=DARK_BLUE)

    # 分隔線
    add_rect(slide, 6.2, 1.25, 0.04, 4.3, fill_color=BLUE)

    # 下方：三大設計亮點
    highlights = [
        ("🧠 雙歷程決策", "Markov(直覺) vs 模型(深思)"),
        ("🗄 三層記憶", "STM ↔ LTM ↔ MemoryGraph"),
        ("💤 睡眠濃縮", "12步記憶固化流程"),
    ]
    for i, (title, desc) in enumerate(highlights):
        hx = 0.35 + i * 4.35
        colored_box(slide, f"{title}\n{desc}",
                    hx, 5.9, 4.0, 1.3,
                    fill=WHITE, border=BLUE,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE)


# ================================================================
# Slide 3: 系統架構全景
# ================================================================
def slide_architecture(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "系統架構全景",
               "感知層 → 決策層 → 記憶層 → 協調層 → 觀察層")

    # 五層架構圖
    layers = [
        ("感知層  Perception", "YOLO目標偵測 · PerceptionWatcher · 場景文字", LIGHT_TEAL,  TEAL),
        ("決策層  Decision",   "Agent.decide() · Markov引擎 · 困惑度評估 · LLM",  LIGHT_ORANGE,ORANGE),
        ("記憶層  Memory",     "STM(敘述) · LTM(HAM命題) · MemoryGraph(圖)",       LIGHT_BLUE,  BLUE),
        ("協調層  Coordination","AgentManager · WorldClock · 對話協調 · 中斷佇列", LIGHT_GREEN, GREEN),
        ("觀察層  Observation", "Dashboard(7分頁) · MemoryViewer · 模擬報告",      LIGHT_PURPLE,PURPLE),
    ]
    for i, (name, content, lc, bc) in enumerate(layers):
        iy = 1.25 + i * 1.05
        # 左側標籤
        colored_box(slide, name, 0.3, iy, 3.0, 0.82,
                    fill=bc, border=bc,
                    font_size=Pt(12), bold=True, font_color=WHITE)
        # 箭頭
        arrow_right(slide, 3.35, iy+0.2, 0.5, 0.4, color=bc)
        # 內容
        colored_box(slide, content, 3.9, iy, 8.9, 0.82,
                    fill=lc, border=bc,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    # 雙向箭頭連結提示
    for i in range(4):
        iy = 2.0 + i * 1.05
        add_text_box(slide, "⇅", 1.55, iy, 0.8, 0.25,
                     font_size=Pt(11), color=GRAY,
                     align=PP_ALIGN.CENTER)

    # 右側：資料流圖
    add_text_box(slide, "核心資料流",
                 9.3, 1.22, 3.7, 0.35,
                 font_size=Pt(13), bold=True,
                 color=DARK_BLUE, align=PP_ALIGN.CENTER)


# ================================================================
# Slide 4: 認知科學理論基礎
# ================================================================
def slide_theories(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "認知科學理論基礎",
               "系統設計對應 6 大心理學 / 認知科學理論")

    theories = [
        ("雙歷程理論",   "Kahneman (2011)",
         "System 1（直覺快思）vs System 2（深思慢想）\n→ Markov直覺路徑 vs LLM深思路徑",
         LIGHT_ORANGE, ORANGE),
        ("HAM 記憶模型", "Anderson & Bower (1973)",
         "命題記憶以五元組存儲：\n主體｜關係｜客體｜地點｜時間",
         LIGHT_BLUE, BLUE),
        ("擴散激活",     "Anderson (1983)",
         "BFS 2-hop 激活 · 衰減係數 0.4 · 閾值 0.3\n→ 相關記憶自動聯想浮現",
         LIGHT_TEAL, TEAL),
        ("情節 vs 語意記憶", "Tulving (1972)",
         "STM = 情節記憶（敘述）\nLTM = 語意記憶（命題）",
         LIGHT_GREEN, GREEN),
        ("睡眠記憶固化", "Diekelmann & Born (2010)",
         "睡眠中系統性提取 STM → HAM → LTM\n增強重要記憶，修剪低權重命題",
         LIGHT_PURPLE, PURPLE),
        ("情緒基線重置", "Frijda (1988)",
         "睡眠後情緒趨向基線（平靜）\n若困惑度 K < 0.5 則重置情緒",
         LIGHT_RED, RED),
    ]

    for i, (name, ref, desc, lc, bc) in enumerate(theories):
        col = i % 3
        row = i // 3
        tx = 0.3 + col * 4.35
        ty = 1.25 + row * 2.85

        # 頂部標題
        colored_box(slide, f"{name}\n{ref}",
                    tx, ty, 4.0, 0.8,
                    fill=bc, border=bc,
                    font_size=Pt(12), bold=True, font_color=WHITE)
        # 說明
        colored_box(slide, desc,
                    tx, ty+0.85, 4.0, 1.85,
                    fill=lc, border=bc,
                    font_size=Pt(11.5), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)


# ================================================================
# Slide 5: 記憶系統三層架構
# ================================================================
def slide_memory_system(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "記憶系統三層架構",
               "STM（工作記憶）→ 睡眠濃縮 → LTM（長期記憶）+ MemoryGraph（激活網路）")

    # ── STM 區塊 ──
    colored_box(slide, "STM  短期記憶", 0.3, 1.25, 3.8, 0.55,
                fill=BLUE, border=BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)
    stm_items = [
        "結構：turn_id / time / perception",
        "       event / inner（thought+emotion）",
        "安全上限：50 筆 turns",
        "睡後保留：摘要 + 最近 5 筆",
        "格式：自然語言敘述（情節記憶）",
    ]
    bullet_list(slide, stm_items, 0.3, 1.9, 3.85, 2.5,
                font_size=Pt(12), color=DARK_BLUE, indent="  · ")

    # ── 睡眠濃縮箭頭 ──
    colored_box(slide, "睡眠濃縮\nconsolidate()", 4.4, 2.4, 2.2, 0.85,
                fill=LIGHT_PURPLE, border=PURPLE,
                font_size=Pt(12), bold=True, font_color=DARK_BLUE)
    arrow_right(slide, 4.25, 2.6, 0.3, 0.4, color=PURPLE)
    arrow_right(slide, 6.6,  2.6, 0.3, 0.4, color=PURPLE)

    # ── LTM 區塊 ──
    colored_box(slide, "LTM  長期記憶", 6.95, 1.25, 3.8, 0.55,
                fill=GREEN, border=GREEN,
                font_size=Pt(14), bold=True, font_color=WHITE)
    ltm_items = [
        "格式：HAM 五元組命題",
        "  主體｜關係｜客體｜地點｜時間",
        "權重：初始 0.5，強化 × 1.3",
        "剪枝：weight < 0.2 時淘汰",
        "查詢：擴散激活（BFS 2-hop）",
    ]
    bullet_list(slide, ltm_items, 6.95, 1.9, 3.85, 2.5,
                font_size=Pt(12), color=DARK_BLUE, indent="  · ")

    # ── MemoryGraph ──
    colored_box(slide, "MemoryGraph（激活網路）", 0.3, 5.0, 12.0, 0.5,
                fill=TEAL, border=TEAL,
                font_size=Pt(14), bold=True, font_color=WHITE)
    mg_items = [
        "主體 / 客體 → 節點；命題 → 有向邊（帶權重）",
        "擴散激活：seed → BFS 2跳 → 衰減 0.4 → 閾值 0.3 過濾",
        "用途：decide() 時檢索相關記憶 供 prompt 使用",
    ]
    bullet_list(slide, mg_items, 0.3, 5.6, 12.0, 1.6,
                font_size=Pt(12.5), color=DARK_BLUE, indent="  ▸ ")

    # ── MemoryGraph 示意圖 ──
    # 中心節點
    colored_box(slide, "Amy", 5.8, 2.6, 1.0, 0.5,
                fill=LIGHT_ORANGE, border=ORANGE,
                font_size=Pt(11), bold=True, font_color=DARK_BLUE)
    # 周圍節點
    nodes = [
        ("Ben",    5.1, 1.75),
        ("疲憊",   7.0, 1.75),
        ("咖啡廳", 4.5, 3.1),
        ("工作",   7.2, 3.1),
    ]
    for label, nx, ny in nodes:
        colored_box(slide, label, nx, ny, 1.0, 0.42,
                    fill=LIGHT_TEAL, border=TEAL,
                    font_size=Pt(10), bold=False, font_color=DARK_BLUE)

    # 說明標籤
    add_text_box(slide, "MemoryGraph 示意",
                 4.4, 4.1, 3.5, 0.4,
                 font_size=Pt(11), color=GRAY,
                 align=PP_ALIGN.CENTER, italic=True)


# ================================================================
# Slide 6: 短期記憶 STM 詳解
# ================================================================
def slide_stm(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "短期記憶（STM）詳解",
               "情節式工作記憶 · 每 tick 寫入 · 安全上限 50 筆")

    # 左側：STM 結構
    colored_box(slide, "STM Turn 結構", 0.3, 1.25, 5.8, 0.5,
                fill=BLUE, border=BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    fields = [
        ("turn_id",    "D001_T003  （天 + 輪次編號）"),
        ("time",       "14:00  （當前模擬時刻）"),
        ("perception", "location / yolo_desc / scene_text"),
        ("event",      "input_text / action / target / content"),
        ("inner",      "thought / emotion"),
    ]
    for i, (field, desc) in enumerate(fields):
        fy = 1.85 + i * 0.72
        colored_box(slide, field,  0.3, fy, 1.8, 0.58,
                    fill=LIGHT_BLUE, border=BLUE,
                    font_size=Pt(12), bold=True, font_color=DARK_BLUE)
        colored_box(slide, desc,   2.2, fy, 3.9, 0.58,
                    fill=WHITE, border=LIGHT_BLUE,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    # 右側：生命週期
    colored_box(slide, "STM 生命週期", 6.5, 1.25, 6.5, 0.5,
                fill=BLUE, border=BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    lifecycle = [
        ("每 tick 寫入",  "decide() 與 generate_dialogue_response()\n結束後呼叫 _write_stm_entry()",
         LIGHT_BLUE, BLUE),
        ("容量控制",      "add_turn() 最多保留 50 筆\n超過自動淘汰最舊記錄",
         LIGHT_GREEN, GREEN),
        ("睡眠時濃縮",    "consolidate() 提取 HAM 命題\n寫入 LTM & MemoryGraph",
         LIGHT_PURPLE, PURPLE),
        ("睡後清理",      "shrink_to_summary() 保留\n摘要 + 最近 5 筆（節省上下文）",
         LIGHT_ORANGE, ORANGE),
    ]
    for i, (title, desc, lc, bc) in enumerate(lifecycle):
        row = i // 2
        col = i % 2
        lx = 6.55 + col * 3.3
        ly = 1.88 + row * 2.4
        colored_box(slide, f"◆ {title}\n\n{desc}",
                    lx, ly, 3.1, 2.1,
                    fill=lc, border=bc,
                    font_size=Pt(11.5), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    # 底部關鍵設計
    colored_box(slide,
                "設計原則：STM 只記「體驗」（敘述），process_log 另存「決策元數據」（困惑度/機率），兩者分離",
                0.3, 6.8, 12.7, 0.55,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(13), bold=True, font_color=DARK_BLUE)


# ================================================================
# Slide 7: 長期記憶 LTM / HAM
# ================================================================
def slide_ltm(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "長期記憶（LTM）& HAM 模型",
               "Human Associative Memory（Anderson & Bower, 1973）· 命題五元組")

    # HAM 五元組示意
    colored_box(slide, "HAM 命題格式", 0.3, 1.25, 5.8, 0.5,
                fill=GREEN, border=GREEN,
                font_size=Pt(14), bold=True, font_color=WHITE)

    tuple_fields = ["主體\nSubject", "關係\nRelation", "客體\nObject", "地點\nLocation", "時間\nTime"]
    tuple_colors = [LIGHT_BLUE, LIGHT_GREEN, LIGHT_ORANGE, LIGHT_TEAL, LIGHT_PURPLE]
    tuple_borders = [BLUE, GREEN, ORANGE, TEAL, PURPLE]
    for i, (f, lc, bc) in enumerate(zip(tuple_fields, tuple_colors, tuple_borders)):
        tx = 0.35 + i * 1.15
        colored_box(slide, f, tx, 1.88, 1.0, 0.82,
                    fill=lc, border=bc,
                    font_size=Pt(11), bold=True, font_color=DARK_BLUE)
        if i < 4:
            add_text_box(slide, "|", tx+1.03, 2.05, 0.1, 0.4,
                         font_size=Pt(14), color=GRAY,
                         align=PP_ALIGN.CENTER)

    # 例子
    colored_box(slide, "範例：Amy  ｜  感到  ｜  疲憊  ｜  咖啡廳  ｜  下午",
                0.3, 2.85, 5.8, 0.55,
                fill=WHITE, border=GREEN,
                font_size=Pt(12), bold=False, font_color=DARK_BLUE)

    # LTM 操作
    colored_box(slide, "LTM 核心操作", 0.3, 3.55, 5.8, 0.5,
                fill=GREEN, border=GREEN,
                font_size=Pt(14), bold=True, font_color=WHITE)
    ops = [
        "add_proposition()     — 新增／強化（× 1.3）",
        "query()               — 語意查詢（關鍵詞比對）",
        "spreading_activate()  — 擴散激活",
        "prune()               — 剪枝（weight < 0.2）",
        "get_summary()         — 生成文字摘要供 prompt",
    ]
    bullet_list(slide, ops, 0.3, 4.15, 5.9, 2.5,
                font_size=Pt(12), color=DARK_BLUE, indent="  ○ ")

    # 右側：擴散激活流程
    colored_box(slide, "擴散激活（Spreading Activation）", 6.5, 1.25, 6.5, 0.5,
                fill=TEAL, border=TEAL,
                font_size=Pt(14), bold=True, font_color=WHITE)

    sa_steps = [
        ("Step 1", "輸入種子節點（seed）\n從 STM/perception 提取關鍵詞", LIGHT_TEAL, TEAL),
        ("Step 2", "BFS 第 1 跳：相鄰命題\n激活分 = 節點分 × 命題權重", LIGHT_BLUE, BLUE),
        ("Step 3", "BFS 第 2 跳：衰減 × 0.4\n防止過度泛化", LIGHT_GREEN, GREEN),
        ("Step 4", "閾值 0.3 過濾\n回傳高相關命題列表", LIGHT_ORANGE, ORANGE),
    ]
    for i, (step, desc, lc, bc) in enumerate(sa_steps):
        sy = 1.88 + i * 1.3
        colored_box(slide, step, 6.55, sy, 1.2, 1.1,
                    fill=bc, border=bc,
                    font_size=Pt(13), bold=True, font_color=WHITE)
        arrow_right(slide, 7.8, sy+0.25, 0.4, 0.4, color=bc)
        colored_box(slide, desc, 8.3, sy, 4.55, 1.1,
                    fill=lc, border=bc,
                    font_size=Pt(11.5), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)
        if i < 3:
            arrow_down(slide, 6.9, sy+1.15, 0.5, 0.2, color=bc)


# ================================================================
# Slide 8: 雙歷程決策架構
# ================================================================
def slide_dual_process(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "雙歷程決策架構（Dual Process Theory）",
               "Kahneman (2011)：System 1 直覺快思 vs System 2 深思慢想")

    # 中間分隔
    add_rect(slide, 6.5, 1.2, 0.04, 5.7, fill_color=GRAY)

    # System 1 標題
    colored_box(slide, "System 1  直覺路徑（Markov）",
                0.3, 1.2, 6.0, 0.7,
                fill=GREEN, border=GREEN,
                font_size=Pt(16), bold=True, font_color=WHITE)

    # System 2 標題
    colored_box(slide, "System 2  深思路徑（LLM）",
                6.7, 1.2, 6.3, 0.7,
                fill=ORANGE, border=ORANGE,
                font_size=Pt(16), bold=True, font_color=WHITE)

    # System 1 特徵
    s1_items = [
        "觸發條件：C 值 < threshold（低困惑）",
        "輸入：三源 Markov 機率分布",
        "輸出：直接採樣行動（sample_action）",
        "不呼叫語言模型",
        "速度快、資源消耗低",
        "適合日常慣例行為",
    ]
    bullet_list(slide, s1_items, 0.3, 2.05, 6.0, 2.5,
                font_size=Pt(13), color=GREEN, indent="  ✓ ")

    # System 2 特徵
    s2_items = [
        "觸發條件：C 值 ≥ threshold（高困惑）",
        "輸入：完整 prompt（記憶+感知+情境）",
        "輸出：LLM 生成 ACTION/TARGET/CONTENT",
        "含 THOUGHT 內心想法",
        "含 HAM 命題（記憶更新素材）",
        "處理新奇、衝突、社交等複雜情境",
    ]
    bullet_list(slide, s2_items, 6.7, 2.05, 6.2, 2.5,
                font_size=Pt(13), color=ORANGE, indent="  ✓ ")

    # 中間：切換機制
    colored_box(slide, "決策模式切換機制",
                3.5, 4.65, 6.3, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    colored_box(slide,
                "C 值 = f(U, K, S)  ←困惑度評估引擎\n"
                "U = 行動不確定性  ·  K = 情境異常程度  ·  S = 情境壓力",
                3.5, 5.22, 6.3, 1.05,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(12.5), bold=False, font_color=DARK_BLUE)

    arrow_right(slide, 3.0, 5.1, 0.6, 0.45, color=GREEN)
    add_text_box(slide, "C < θ", 2.0, 4.9, 1.2, 0.5,
                 font_size=Pt(12), bold=True, color=GREEN,
                 align=PP_ALIGN.CENTER)

    arrow_right(slide, 9.85, 5.1, 0.6, 0.45, color=ORANGE)
    add_text_box(slide, "C ≥ θ", 10.3, 4.9, 1.2, 0.5,
                 font_size=Pt(12), bold=True, color=ORANGE,
                 align=PP_ALIGN.CENTER)

    # 底部：情緒調整 threshold
    colored_box(slide,
                "⚙  Threshold 動態調整：基礎值 0.5 · 情緒不穩 ±0.1 · 重大事件 ↓ threshold → 更容易觸發 System 2",
                0.3, 6.5, 12.7, 0.72,
                fill=LIGHT_ORANGE, border=ORANGE,
                font_size=Pt(12.5), bold=False, font_color=DARK_BLUE)


# ================================================================
# Slide 9: Markov 引擎（三源加權）
# ================================================================
def slide_markov(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "Markov 引擎：三源加權行動機率",
               "三源分布線性疊加 → 加入情緒 / 感知 修正 → 採樣行動")

    # 公式區
    colored_box(slide, "核心公式",
                0.3, 1.25, 12.7, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    colored_box(slide,
                "P(action) = α × P_schedule + β × P_inertia + γ × P_situation",
                0.3, 1.82, 12.7, 0.72,
                fill=WHITE, border=BLUE,
                font_size=Pt(20), bold=True, font_color=DARK_BLUE)

    # 三源說明
    sources = [
        ("α × P_schedule\n（時間表）",
         "α = 0.4（一般）/ 0.1（重大事件）\n"
         "依當前時間段查角色時間表\n"
         "取對應行動分布",
         LIGHT_BLUE, BLUE),
        ("β × P_inertia\n（行動慣性）",
         "β = 0.3\n"
         "加強最近 N 筆行動的機率\n"
         "模擬行為連續性",
         LIGHT_GREEN, GREEN),
        ("γ × P_situation\n（情境）",
         "γ = 0.3（一般）/ 0.6（重大事件）\n"
         "共同在場人物 → 加強對話機率\n"
         "感知到特殊事物 → 調整行動",
         LIGHT_ORANGE, ORANGE),
    ]
    for i, (title, desc, lc, bc) in enumerate(sources):
        sx = 0.3 + i * 4.35
        colored_box(slide, title, sx, 2.72, 4.0, 0.82,
                    fill=bc, border=bc,
                    font_size=Pt(13), bold=True, font_color=WHITE)
        colored_box(slide, desc, sx, 3.6, 4.0, 1.5,
                    fill=lc, border=bc,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    # 箭頭
    arrow_down(slide, 2.1, 5.15, 0.5, 0.35, color=BLUE)
    arrow_down(slide, 6.4, 5.15, 0.5, 0.35, color=GREEN)
    arrow_down(slide, 10.7, 5.15, 0.5, 0.35, color=ORANGE)

    # 加權疊加
    colored_box(slide, "加權疊加 → 正規化",
                4.5, 5.5, 4.3, 0.55,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    # 修正項目
    mods = [
        ("情緒修正", "情緒偵測 → 調整特定行動分布"),
        ("感知修正", "YOLO / 場景文字 → 加成/減分"),
        ("地板機率", "MIN_PROB_FLOOR = 0.005（每個行動保持最低機率）"),
    ]
    for i, (k, v) in enumerate(mods):
        mx = 0.3 + i * 4.35
        colored_box(slide, f"{k}：{v}", mx, 6.15, 4.1, 0.65,
                    fill=LIGHT_GRAY, border=GRAY,
                    font_size=Pt(11.5), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    # 重大事件切換說明
    colored_box(slide,
                "重大事件（K ≥ 0.6）：α↓0.1  γ↑0.6  →  更依賴當下情境，更少依賴時間表",
                0.3, 6.88, 12.7, 0.5,
                fill=LIGHT_ORANGE, border=ORANGE,
                font_size=Pt(12.5), bold=True, font_color=DARK_BLUE)


# ================================================================
# Slide 10: 困惑度評估系統
# ================================================================
def slide_confusion(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "困惑度評估系統（C 值）",
               "決定走 System 1（直覺）還是 System 2（深思）的核心機制")

    # 三個輸入指標
    metrics = [
        ("U\n行動不確定性", "Markov 機率分布的熵值\n行動分布越分散 → U 越高\n越難「直觀」決定", LIGHT_BLUE, BLUE),
        ("K\n情境異常程度", "感知與 LTM 的偏差\n「出現陌生人」「異常場景」\nK ≥ 0.6 → 重大事件", LIGHT_ORANGE, ORANGE),
        ("S\n情境壓力",      "時間壓力 + 情緒強度\n負面情緒 → S 上升\n影響 C 的絕對值", LIGHT_RED, RED),
    ]
    for i, (title, desc, lc, bc) in enumerate(metrics):
        mx = 0.3 + i * 4.35
        colored_box(slide, title, mx, 1.25, 3.8, 0.82,
                    fill=bc, border=bc,
                    font_size=Pt(15), bold=True, font_color=WHITE)
        colored_box(slide, desc, mx, 2.13, 3.8, 1.5,
                    fill=lc, border=bc,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)
        arrow_down(slide, mx+1.6, 3.68, 0.5, 0.3, color=bc)

    # C 值計算
    colored_box(slide, "C = w_U × U + w_K × K + w_S × S",
                1.5, 4.05, 10.3, 0.72,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(20), bold=True, font_color=WHITE)

    arrow_down(slide, 6.2, 4.83, 0.5, 0.35, color=DARK_BLUE)

    # 判斷邏輯
    colored_box(slide, "與 threshold 比較",
                4.5, 5.25, 4.3, 0.5,
                fill=GRAY, border=GRAY,
                font_size=Pt(14), bold=True, font_color=WHITE)

    colored_box(slide, "C < threshold\n→ intuitive\n→ System 1 / Markov",
                0.5, 6.0, 4.8, 1.18,
                fill=LIGHT_GREEN, border=GREEN,
                font_size=Pt(13), bold=False, font_color=GREEN)
    add_text_box(slide, "vs", 5.5, 6.3, 0.8, 0.5,
                 font_size=Pt(16), bold=True, color=GRAY,
                 align=PP_ALIGN.CENTER)
    colored_box(slide, "C ≥ threshold\n→ deliberate\n→ System 2 / LLM",
                7.0, 6.0, 4.8, 1.18,
                fill=LIGHT_ORANGE, border=ORANGE,
                font_size=Pt(13), bold=False, font_color=ORANGE)

    # threshold 調整說明
    colored_box(slide,
                "Threshold = 0.5（基礎）+ 情緒調整量 ∈ [0.3, 0.7]",
                0.3, 5.25, 4.0, 0.5,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(11), bold=False, font_color=DARK_BLUE)


# ================================================================
# Slide 11: 每 Tick 決策流程圖
# ================================================================
def slide_tick_flow(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "每 Tick 決策流程",
               "Agent.decide() 的完整執行步驟（每 60 分鐘執行一次）")

    # 流程步驟（縱向）
    steps = [
        ("① 取當前時段",       "character.get_current_slot()\n→ 時間表查詢",                 LIGHT_TEAL, TEAL),
        ("② 計算 Markov 分布", "compute_action_probabilities()\nα·schedule+β·inertia+γ·sit", LIGHT_BLUE, BLUE),
        ("③ 評估困惑度 C",     "eval_confusion(U, K, S)\n→ mode: intuitive / deliberate",    LIGHT_ORANGE, ORANGE),
        ("④ 若重大事件",       "K ≥ 0.6 → 切換 EVENT 權重\n重新計算 Markov 分布",            LIGHT_RED, RED),
        ("⑤ 路徑分岔",         "intuitive → Markov 採樣\ndeliberate → 呼叫 LLM",              LIGHT_GREEN, GREEN),
        ("⑥ 寫入 STM",         "_write_stm_entry()\n敘述式記憶",                              LIGHT_PURPLE, PURPLE),
        ("⑦ 寫入 process_log", "_write_process_log()\n決策元數據",                            LIGHT_GRAY, GRAY),
    ]

    col1_x = 0.3
    col2_x = 7.1
    for i, (title, desc, lc, bc) in enumerate(steps):
        col = i % 2
        row = i // 2
        if col == 0:
            sx = col1_x
            sy = 1.25 + row * 1.45
        else:
            sx = col2_x
            sy = 1.25 + (row) * 1.45

        # 對最後一個（7th）特殊處理
        if i == 6:
            sx = 0.3
            sy = 1.25 + 3 * 1.45

        colored_box(slide, title, sx, sy, 3.0, 0.55,
                    fill=bc, border=bc,
                    font_size=Pt(12), bold=True, font_color=WHITE)
        colored_box(slide, desc, sx+3.05, sy, 3.45, 0.55,
                    fill=lc, border=bc,
                    font_size=Pt(11), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

        # 箭頭
        if i < 5 and i != 3:
            if col == 0 and i + 2 <= 6:
                arrow_down(slide, sx + 1.4, sy + 0.6, 0.5, 0.3, color=bc)
            elif col == 1:
                arrow_down(slide, sx + 1.4, sy + 0.6, 0.5, 0.3, color=bc)

    # 右側：set_pending_action 補充
    colored_box(slide,
                "⑧ 設定 pending_action\n→ character.set_pending_action()\n→ Manager 下個 tick 執行",
                7.1, 5.6, 5.9, 1.55,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(12.5), bold=False, font_color=DARK_BLUE,
                align=PP_ALIGN.LEFT)


# ================================================================
# Slide 12: 睡眠濃縮 12 步驟
# ================================================================
def slide_sleep(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "睡眠記憶濃縮（12 步驟）",
               "Diekelmann & Born (2010)  ·  每日模擬結束後執行  ·  consolidate()")

    steps_col1 = [
        ("01", "STM → 文字快照",  "將當天所有 STM turns 轉成純文字敘述"),
        ("02", "HAM 命題提取",    "用 LLM 或規則從敘述中提取五元組命題"),
        ("03", "命題去重",        "相同五元組 → 強化權重（× 1.3）"),
        ("04", "LTM 寫入",        "新命題加入長期記憶，初始 weight = 0.5"),
        ("05", "LTM 剪枝",        "weight < 0.2 的命題淘汰"),
        ("06", "MemoryGraph 更新","節點和邊同步更新"),
    ]
    steps_col2 = [
        ("07", "LTM 摘要生成",    "get_summary() 更新供下日 prompt 使用"),
        ("08", "關係更新",        "從互動記憶更新 relationship 描述"),
        ("09", "情緒評估",        "今日最高 K 值 → 決定是否重置情緒"),
        ("10", "情緒重置",        "K < 0.5 → 情緒歸 '平靜' (Frijda, 1988)"),
        ("11", "時間表生成",      "依角色角色生成次日行程"),
        ("12", "STM 清理",        "shrink_to_summary()：保留摘要 + 5 筆"),
    ]

    for i, (num, title, desc) in enumerate(steps_col1):
        sy = 1.25 + i * 0.95
        colored_box(slide, num, 0.3, sy, 0.55, 0.75,
                    fill=DARK_BLUE, border=DARK_BLUE,
                    font_size=Pt(14), bold=True, font_color=YELLOW)
        colored_box(slide, title, 0.92, sy, 2.2, 0.75,
                    fill=BLUE, border=BLUE,
                    font_size=Pt(11.5), bold=True, font_color=WHITE)
        colored_box(slide, desc, 3.18, sy, 3.2, 0.75,
                    fill=LIGHT_BLUE, border=BLUE,
                    font_size=Pt(11), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    for i, (num, title, desc) in enumerate(steps_col2):
        sy = 1.25 + i * 0.95
        colored_box(slide, num, 6.7, sy, 0.55, 0.75,
                    fill=DARK_BLUE, border=DARK_BLUE,
                    font_size=Pt(14), bold=True, font_color=YELLOW)
        colored_box(slide, title, 7.32, sy, 2.2, 0.75,
                    fill=GREEN, border=GREEN,
                    font_size=Pt(11.5), bold=True, font_color=WHITE)
        colored_box(slide, desc, 9.58, sy, 3.5, 0.75,
                    fill=LIGHT_GREEN, border=GREEN,
                    font_size=Pt(11), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    # 分隔線
    add_rect(slide, 6.4, 1.2, 0.04, 5.8, fill_color=GRAY)


# ================================================================
# Slide 13: 對話系統
# ================================================================
def slide_dialogue(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "對話系統",
               "邀請 → 接受判斷 → 多輪對話 → 記憶更新")

    # 流程圖（橫向）
    flow_items = [
        ("邀請發起\nInviter decides\n'對話'", LIGHT_BLUE, BLUE),
        ("接受判斷\nshould_accept\n_dialogue()", LIGHT_GREEN, GREEN),
        ("多輪對話\ngenerate_dialogue\n_response()", LIGHT_ORANGE, ORANGE),
        ("結束對話\n寫入雙方 STM\nHAM 命題更新", LIGHT_TEAL, TEAL),
    ]
    for i, (text, lc, bc) in enumerate(flow_items):
        fx = 0.35 + i * 3.25
        colored_box(slide, text, fx, 1.25, 2.9, 1.4,
                    fill=lc, border=bc,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE)
        if i < 3:
            arrow_right(slide, fx+2.93, 1.75, 0.4, 0.4, color=bc)

    # 接受判斷公式
    colored_box(slide, "接受機率計算（純規則，不呼叫模型）",
                0.3, 2.82, 12.7, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    factors = [
        ("基礎機率", "DIALOGUE_BASE_ACCEPT = 0.5",    LIGHT_BLUE, BLUE),
        ("關係加成", "+0.15（朋友/信任/喜歡等關鍵詞）", LIGHT_GREEN, GREEN),
        ("行動加成", "+0.10（rest/daily 類行動）",     LIGHT_TEAL, TEAL),
        ("工作懲罰", "-0.15（work 類行動）",           LIGHT_RED, RED),
        ("情緒懲罰", "-0.10（非平靜/開心/興奮情緒）",  LIGHT_ORANGE, ORANGE),
    ]
    for i, (k, v, lc, bc) in enumerate(factors):
        col = i % 3
        row = i // 3
        fx = 0.3 + col * 4.35
        fy = 3.42 + row * 1.0
        colored_box(slide, k, fx, fy, 1.6, 0.75,
                    fill=bc, border=bc,
                    font_size=Pt(12), bold=True, font_color=WHITE)
        colored_box(slide, v, fx+1.65, fy, 2.6, 0.75,
                    fill=lc, border=bc,
                    font_size=Pt(11.5), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    colored_box(slide, "Clamp: [0.1, 0.95]  →  random() < acc → 接受",
                0.3, 5.55, 12.7, 0.55,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(13), bold=True, font_color=DARK_BLUE)

    # 對話輸出格式
    colored_box(slide, "LLM 對話輸出格式",
                0.3, 6.2, 12.7, 0.4,
                fill=GRAY, border=GRAY,
                font_size=Pt(13), bold=True, font_color=WHITE)
    colored_box(slide,
                "[ACTION] 對話   [TARGET] Amy   [CONTENT] 你今天看起來累累的   [THOUGHT] 我想關心她   [HAM] subject|relation|object|loc|time",
                0.3, 6.67, 12.7, 0.62,
                fill=WHITE, border=GRAY,
                font_size=Pt(11.5), bold=False, font_color=DARK_BLUE,
                align=PP_ALIGN.LEFT)


# ================================================================
# Slide 14: 角色與世界時鐘
# ================================================================
def slide_world(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "角色與世界時鐘",
               "5 角色  ·  20 ticks/day  ·  06:00–02:00  ·  可多天模擬")

    # WorldClock
    colored_box(slide, "WorldClock", 0.3, 1.25, 5.8, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)
    clock_items = [
        "DAY_START_HOUR = 6（早上 6 點開始）",
        "MAX_TICKS_PER_DAY = 20",
        "MINUTES_PER_TICK = 60",
        "time_str：HH:MM 格式（如 14:00）",
        "tick()：每次推進 60 分鐘",
        "day / hour / minute 屬性",
    ]
    bullet_list(slide, clock_items, 0.3, 1.85, 5.9, 2.8,
                font_size=Pt(13), color=DARK_BLUE, indent="  · ")

    # Character 屬性
    colored_box(slide, "Character 核心屬性", 6.5, 1.25, 6.5, 0.5,
                fill=BLUE, border=BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)
    char_items = [
        "code / name / role（角色代碼/名稱/職業）",
        "current_location（當前位置）",
        "current_action（當前行動動詞）",
        "emotion（情緒：平靜/開心/憤怒/…）",
        "schedule（每日時間表列表）",
        "relationships（dict：對其他角色的關係）",
        "pending_action（已決策待執行）",
        "day（當前模擬天數）",
    ]
    bullet_list(slide, char_items, 6.5, 1.85, 6.6, 3.2,
                font_size=Pt(12.5), color=DARK_BLUE, indent="  · ")

    # 時間軸示意圖
    colored_box(slide, "每天 20 Ticks 時間軸",
                0.3, 4.8, 12.7, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    hours = ["06", "07", "08", "09", "10", "11", "12", "13", "14",
             "15", "16", "17", "18", "19", "20", "21", "22", "23", "00", "01"]
    tick_colors = [LIGHT_BLUE, LIGHT_GREEN, LIGHT_ORANGE,
                   LIGHT_TEAL, LIGHT_PURPLE]
    for i, h in enumerate(hours):
        bx = 0.32 + i * 0.638
        colored_box(slide, h, bx, 5.42, 0.58, 0.55,
                    fill=tick_colors[i % 5],
                    border=BLUE,
                    font_size=Pt(9), bold=False, font_color=DARK_BLUE)

    add_text_box(slide, "Tick 0      Tick 1      Tick 2      ···      Tick 19",
                 0.3, 6.05, 12.7, 0.4,
                 font_size=Pt(11), color=GRAY,
                 align=PP_ALIGN.CENTER, italic=True)

    colored_box(slide,
                "每 Tick：感知 → decide() → 執行行動 → 更新位置/情緒 → 對話協調",
                0.3, 6.52, 12.7, 0.6,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(12.5), bold=True, font_color=DARK_BLUE)


# ================================================================
# Slide 15: AgentManager 協調機制
# ================================================================
def slide_manager(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "AgentManager 協調機制",
               "多角色並行管理  ·  Two-Phase Tick  ·  中斷佇列  ·  對話協調")

    # 兩個主要 Phase
    colored_box(slide, "Phase 1：決策階段",
                0.3, 1.25, 6.0, 0.55,
                fill=BLUE, border=BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    p1_items = [
        "所有角色依序呼叫 agent.decide()",
        "傳入 scene / perception / co_located",
        "結果暫存至 pending_action",
        "（此時不執行，避免競態）",
    ]
    bullet_list(slide, p1_items, 0.3, 1.9, 6.0, 2.0,
                font_size=Pt(13), color=DARK_BLUE, indent="  ▸ ")

    colored_box(slide, "Phase 2：執行階段",
                6.5, 1.25, 6.5, 0.55,
                fill=GREEN, border=GREEN,
                font_size=Pt(14), bold=True, font_color=WHITE)

    p2_items = [
        "執行所有 pending_action",
        "前往 → 更新 current_location",
        "對話 → 啟動對話協調邏輯",
        "睡覺 → 觸發 agent.sleep() 濃縮",
    ]
    bullet_list(slide, p2_items, 6.5, 1.9, 6.5, 2.0,
                font_size=Pt(13), color=DARK_BLUE, indent="  ▸ ")

    # 中斷機制
    colored_box(slide, "中斷佇列（Interrupt Queue）",
                0.3, 4.1, 12.7, 0.5,
                fill=ORANGE, border=ORANGE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    intr_items = [
        "push_interrupt(code, event)：任何時間點推入中斷事件",
        "事件屬性：type / strength（weak/medium/strong）/ data / timestamp",
        "Agent.re_evaluate_on_interrupt()：Markov 重算 → 可能改變 pending_action",
        "PerceptionWatcher：YOLO 偵測到場景變化時自動觸發",
    ]
    bullet_list(slide, intr_items, 0.3, 4.72, 12.7, 2.0,
                font_size=Pt(13), color=DARK_BLUE, indent="  ◆ ")

    # 對話協調
    colored_box(slide,
                "對話協調：發起者決定'對話' → Manager 判斷對象是否在場 → 呼叫 should_accept_dialogue() → 啟動 dialogue loop",
                0.3, 6.8, 12.7, 0.58,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(12.5), bold=True, font_color=DARK_BLUE)


# ================================================================
# Slide 16: 模型整合（Phi-3.5 / FusionDecoder）
# ================================================================
def slide_model(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "模型整合（Phi-3.5 Vision）",
               "文字 + 視覺融合推論  ·  GenerationConfig  ·  FakeLoader 模式")

    # 架構圖
    components = [
        ("TextEncoder\nPhi-3.5 tokenizer\nbuild_prompt()", LIGHT_BLUE, BLUE),
        ("VisionEncoder\nCLIP / ViT\nencode(images)", LIGHT_GREEN, GREEN),
        ("FusionDecoder\nfuse_inputs()\ngenerate()", LIGHT_ORANGE, ORANGE),
        ("Output Parser\nparse_decision\n_output()", LIGHT_PURPLE, PURPLE),
    ]
    for i, (text, lc, bc) in enumerate(components):
        cx = 0.4 + i * 3.22
        colored_box(slide, text, cx, 1.25, 2.9, 1.5,
                    fill=lc, border=bc,
                    font_size=Pt(12), bold=False, font_color=DARK_BLUE)
        if i < 3:
            arrow_right(slide, cx+2.93, 1.82, 0.38, 0.4, color=bc)

    # GenerationConfig
    colored_box(slide, "GenerationConfig 參數",
                0.3, 2.95, 6.0, 0.5,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(14), bold=True, font_color=WHITE)

    gen_items = [
        "deliberate()：max_new_tokens=512, temperature=0.7",
        "dialogue()：  max_new_tokens=256, temperature=0.8",
        "溫度越高 → 輸出越多樣（對話場景）",
        "深思路徑需要較長輸出（含 THOUGHT+HAM）",
    ]
    bullet_list(slide, gen_items, 0.3, 3.55, 6.0, 2.5,
                font_size=Pt(13), color=DARK_BLUE, indent="  · ")

    # FakeLoader
    colored_box(slide, "FakeLoader（測試 / 無 GPU 環境）",
                6.5, 2.95, 6.5, 0.5,
                fill=TEAL, border=TEAL,
                font_size=Pt(14), bold=True, font_color=WHITE)

    fake_items = [
        "make_model_fn() → 返回規則生成函數",
        "自動選擇合法動詞（VALID_ACTIONS）",
        "完整走完所有決策流程（C 值、STM、LTM）",
        "不需要 GPU，適合開發與演示",
        "is_loaded() 回傳 True",
    ]
    bullet_list(slide, fake_items, 6.5, 3.55, 6.5, 2.5,
                font_size=Pt(13), color=DARK_BLUE, indent="  · ")

    # 輸出格式
    colored_box(slide, "模型輸出格式（Block Format）",
                0.3, 6.1, 12.7, 0.4,
                fill=GRAY, border=GRAY,
                font_size=Pt(13), bold=True, font_color=WHITE)
    colored_box(slide,
                "[ACTION] 對話  [TARGET] Amy  [CONTENT] 你今天好嗎  [THOUGHT] 我在意她的狀況  [HAM]  - Amy|感到|疲憊|咖啡廳|下午  [/HAM]",
                0.3, 6.57, 12.7, 0.7,
                fill=WHITE, border=GRAY,
                font_size=Pt(11), bold=False, font_color=DARK_BLUE,
                align=PP_ALIGN.LEFT)


# ================================================================
# Slide 17: 觀察儀表板（7 分頁）
# ================================================================
def slide_dashboard(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "觀察儀表板（7 分頁）",
               "dashboard_html.py  ·  模擬結束後生成完整 HTML 報告")

    tabs = [
        ("📋 每日日誌",     "每筆決策記錄（時刻/行動/模式/C值）\nMarkov 機率橫條圖",     LIGHT_BLUE,   BLUE),
        ("📊 混淆度圖表",   "U/K/S/C 折線圖（per tick）\n直覺/深思 決策點標示",          LIGHT_ORANGE, ORANGE),
        ("🗄 STM 時間線",   "每角色短期記憶 turn-by-turn\n按天/時間展開",                 LIGHT_GREEN,  GREEN),
        ("🧠 LTM 知識圖",   "vis.js 力導向圖\nBarnesHut 物理引擎·節點代表概念",          LIGHT_PURPLE, PURPLE),
        ("💬 對話紀錄",     "接受 vs 拒絕分開顯示\n完整多輪對話內容",                    LIGHT_TEAL,   TEAL),
        ("💤 睡眠報告",     "每角色每天睡眠濃縮結果\nHAM 提取數·情緒變化·時間表",        LIGHT_RED,    RED),
        ("📅 時間表",       "每角色完整每日行程\n時段/地點/活動一覽",                    LIGHT_GRAY,   GRAY),
    ]

    for i, (name, desc, lc, bc) in enumerate(tabs):
        col = i % 4
        row = i // 4
        tx = 0.3 + col * 3.26
        ty = 1.3 + row * 2.8

        if i == 6:  # 最後一個置中
            tx = 4.6

        colored_box(slide, name,
                    tx, ty, 2.95, 0.65,
                    fill=bc, border=bc,
                    font_size=Pt(13), bold=True, font_color=WHITE)
        colored_box(slide, desc,
                    tx, ty+0.7, 2.95, 1.85,
                    fill=lc, border=bc,
                    font_size=Pt(11), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)

    # 底部說明
    colored_box(slide,
                "實作：純 Python + Chart.js + vis.js  ·  無需後端  ·  單一 HTML 檔案  ·  ~200KB",
                0.3, 7.0, 12.7, 0.42,
                fill=LIGHT_BLUE, border=BLUE,
                font_size=Pt(12), bold=True, font_color=DARK_BLUE)


# ================================================================
# Slide 18: 模擬結果
# ================================================================
def slide_results(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "模擬結果與量化指標",
               "FakeLoader 模式  ·  5 角色  ·  1 天  ·  20 ticks/人")

    # 量化指標卡片
    metrics = [
        ("決策記錄",  "98 筆",    "5 角色 × 約 20 ticks/天", LIGHT_BLUE,   BLUE),
        ("Markov 條",  "590 個",   "每 tick 顯示 top 行動機率", LIGHT_GREEN,  GREEN),
        ("睡眠報告",  "5 張",     "每角色完整固化結果",        LIGHT_ORANGE, ORANGE),
        ("對話卡片",  "15 筆",    "14 接受 + 1 拒絕",          LIGHT_PURPLE, PURPLE),
        ("時間表",    "5 張",     "每角色完整行程",             LIGHT_TEAL,   TEAL),
        ("報告大小",  "~200 KB",  "單 HTML 含所有資料",         LIGHT_RED,    RED),
    ]
    for i, (label, value, note, lc, bc) in enumerate(metrics):
        col = i % 3
        row = i // 3
        mx = 0.35 + col * 4.3
        my = 1.3 + row * 2.35

        colored_box(slide, label, mx, my, 3.9, 0.55,
                    fill=bc, border=bc,
                    font_size=Pt(13), bold=True, font_color=WHITE)
        colored_box(slide, value, mx, my+0.6, 3.9, 0.85,
                    fill=lc, border=bc,
                    font_size=Pt(26), bold=True, font_color=DARK_BLUE)
        colored_box(slide, note, mx, my+1.5, 3.9, 0.62,
                    fill=WHITE, border=bc,
                    font_size=Pt(11.5), bold=False, font_color=GRAY)

    # 關鍵觀察
    colored_box(slide, "關鍵觀察",
                0.3, 6.05, 12.7, 0.4,
                fill=DARK_BLUE, border=DARK_BLUE,
                font_size=Pt(13), bold=True, font_color=WHITE)
    obs = [
        "System 1 佔主導（~80%）：日常慣例行為直接採樣",
        "對話接受率高（93%）：FakeLoader 情緒皆'平靜'",
        "睡眠濃縮驗證：STM 50筆 → 5筆，LTM 命題增加",
    ]
    bullet_list(slide, obs, 0.3, 6.52, 12.7, 0.9,
                font_size=Pt(12), color=DARK_BLUE, indent="  ✓ ")


# ================================================================
# Slide 19: 未來擴展方向
# ================================================================
def slide_future(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=LIGHT_GRAY)
    header_bar(slide, "未來擴展方向",
               "真實模型 · 即時 YOLO · UE5 整合 · 多角色協作")

    future_items = [
        ("真實 LLM 推論",
         "Phi-3.5-Vision 本地部署\n真正走 vision/text/fusion pipeline\n每個 deliberate tick 呼叫模型",
         LIGHT_ORANGE, ORANGE),
        ("即時 YOLO 感知",
         "PerceptionWatcher async loop\n每秒偵測場景變化\n自動觸發 push_interrupt()",
         LIGHT_GREEN, GREEN),
        ("Unreal Engine 5 整合",
         "ws_server WebSocket 介面\n角色渲染 + 動作播放\n雙向通訊（行動 ↔ 感知）",
         LIGHT_BLUE, BLUE),
        ("多天連續模擬",
         "記憶跨天累積演化\n關係動態變化\n情緒長期影響決策",
         LIGHT_PURPLE, PURPLE),
        ("社交網路分析",
         "MemoryGraph 可視化演進\n角色間影響力分析\nHAM 命題網路統計",
         LIGHT_TEAL, TEAL),
        ("真實評估指標",
         "人類評估對話自然度\nBelief-Desire-Intention 驗證\nAblation study（去除各模組）",
         LIGHT_RED, RED),
    ]

    for i, (title, desc, lc, bc) in enumerate(future_items):
        col = i % 3
        row = i // 3
        fx = 0.3 + col * 4.35
        fy = 1.3 + row * 2.8

        colored_box(slide, title, fx, fy, 4.0, 0.6,
                    fill=bc, border=bc,
                    font_size=Pt(14), bold=True, font_color=WHITE)
        colored_box(slide, desc, fx, fy+0.65, 4.0, 2.0,
                    fill=lc, border=bc,
                    font_size=Pt(12.5), bold=False, font_color=DARK_BLUE,
                    align=PP_ALIGN.LEFT)


# ================================================================
# Slide 20: 結語
# ================================================================
def slide_conclusion(prs):
    slide = blank_slide(prs)
    add_rect(slide, 0, 0, 13.33, 7.5, fill_color=DARK_BLUE)
    add_rect(slide, 0, 5.5, 13.33, 2.0, fill_color=RGBColor(0x0d, 0x1c, 0x38))

    # 金色裝飾
    add_rect(slide, 0.5, 1.2, 12.33, 0.07, fill_color=YELLOW)
    add_rect(slide, 0.5, 5.4, 12.33, 0.07, fill_color=YELLOW)

    add_text_box(slide, "總結",
                 0.5, 1.4, 12.33, 0.75,
                 font_size=Pt(36), bold=True,
                 color=YELLOW, align=PP_ALIGN.CENTER)

    summary_lines = [
        "▸  雙歷程決策  ：Markov 直覺 + LLM 深思，C 值動態切換",
        "▸  三層記憶    ：STM（工作記憶）→ 睡眠濃縮 → LTM + MemoryGraph",
        "▸  認知科學    ：HAM / 擴散激活 / 情節-語意 / 睡眠固化 / 情緒基線",
        "▸  世界模擬    ：20 ticks/天 · 5 角色 · 視覺感知 · 中斷機制",
        "▸  觀察工具    ：7 分頁 HTML Dashboard · 完整決策可視化",
    ]
    for i, line in enumerate(summary_lines):
        add_text_box(slide, line,
                     0.8, 2.35 + i * 0.6, 11.8, 0.52,
                     font_size=Pt(15.5),
                     color=WHITE, align=PP_ALIGN.LEFT)

    add_text_box(slide, "AI-Town  ·  基於認知科學的多智能體模擬系統",
                 0.5, 6.05, 12.33, 0.55,
                 font_size=Pt(16), bold=True,
                 color=LIGHT_BLUE, align=PP_ALIGN.CENTER)

    add_text_box(slide, "2026",
                 0.5, 6.7, 12.33, 0.5,
                 font_size=Pt(13),
                 color=LIGHT_BLUE, align=PP_ALIGN.CENTER)


# ================================================================
# 主程式
# ================================================================

def main():
    out_path = r"C:\Users\Rayyu\Desktop\agi\presentation\AI-Town-main\AI-Town-main\reports\AI-Town_presentation.pptx"

    prs = new_prs()

    print("Building slides...")
    slide_cover(prs);       print("  01/20  Cover")
    slide_goals(prs);       print("  02/20  Goals")
    slide_architecture(prs);print("  03/20  Architecture")
    slide_theories(prs);    print("  04/20  Theories")
    slide_memory_system(prs);print(" 05/20  Memory System")
    slide_stm(prs);         print("  06/20  STM")
    slide_ltm(prs);         print("  07/20  LTM + HAM")
    slide_dual_process(prs);print("  08/20  Dual Process")
    slide_markov(prs);      print("  09/20  Markov Engine")
    slide_confusion(prs);   print("  10/20  Confusion C")
    slide_tick_flow(prs);   print("  11/20  Tick Flow")
    slide_sleep(prs);       print("  12/20  Sleep 12-step")
    slide_dialogue(prs);    print("  13/20  Dialogue")
    slide_world(prs);       print("  14/20  World Clock")
    slide_manager(prs);     print("  15/20  Manager")
    slide_model(prs);       print("  16/20  Model")
    slide_dashboard(prs);   print("  17/20  Dashboard")
    slide_results(prs);     print("  18/20  Results")
    slide_future(prs);      print("  19/20  Future")
    slide_conclusion(prs);  print("  20/20  Conclusion")

    prs.save(out_path)
    print(f"\nSaved: {out_path}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    main()
