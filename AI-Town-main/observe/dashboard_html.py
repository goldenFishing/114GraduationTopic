# ================================================================
# observe/dashboard_html.py
# 完整 HTML 儀表板生成 v2（修復版）
#
# 對應 ARCHITECTURE.md §6.5.1
#
# 七個分頁：
#   1. 總覽       — 角色最終狀態 + 統計
#   2. 每日日誌   — 每個時段的決策（直覺 Markov 機率 / 深思模型輸出）
#   3. 時間表     — 每個角色的時間表（含睡眠後生成的隔天計畫）
#   4. LTM 圖譜   — vis.js 互動圖（修復物理參數）
#   5. 困惑度曲線 — chart.js 折線（修復初始化問題）
#   6. 對話記錄   — 接受/拒絕對話
#   7. 睡眠濃縮   — HAM 抽取 / LTM 變化 / 情緒 / 隔天時間表
#
# 資料來源：
#   sim_data（run_autonomous_days 回傳）— 主要時序資料
#   final_state（manager.get_observation_data）— 最終 LTM/狀態
# ================================================================

import json
import os
from datetime import datetime

from config.world_config import REPORT_DIR, CHARACTER_NAMES
from observe.dialogue_log import format_dialogue_history


# ================================================================
# A. 主入口
# ================================================================

def generate_report(manager, simulation_data: dict,
                     output_path: str = None) -> str:
    """
    生成完整 HTML 儀表板。

    參數：
      manager         : AgentManager（取最終 LTM / 狀態）
      simulation_data : run_autonomous_days() 的回傳值
      output_path     : 自訂路徑，None 用 reports/ 自動命名

    回傳：實際寫入的檔案路徑
    """
    os.makedirs(REPORT_DIR, exist_ok=True)
    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(REPORT_DIR, f"simulation_{ts}.html")

    # 最終狀態（LTM 圖、STM 殘餘、schedule）
    final_state = manager.get_observation_data()

    # 從 sim_data 建立各分頁所需資料
    char_tick_log  = _build_char_tick_log(simulation_data)
    char_confusion = _build_char_confusion(simulation_data)
    dialogue_list  = _build_dialogue_list(simulation_data)
    sleep_reports  = _build_sleep_reports(simulation_data)
    stats          = _compute_stats(simulation_data, final_state, dialogue_list)

    # LTM vis.js 資料（只需 JS 端）
    ltm_js = {
        code: _ltm_to_vis(d["ltm_nodes"], d["ltm_edges"])
        for code, d in final_state.items()
    }

    html = _render_html(
        final_state, stats,
        char_tick_log, char_confusion,
        dialogue_list, sleep_reports,
        ltm_js,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Dashboard] 報告輸出：{output_path}")
    return output_path


# ================================================================
# B. 資料建構（從 sim_data 提取，不依賴 final_state）
# ================================================================

def _build_char_tick_log(sim_data: dict) -> dict:
    """
    從 sim_data 建立每個角色的每 tick 決策紀錄。
    回傳：{code: [{day,time,action,target,mode,C,K,top_probs,thought,content,is_major}, ...]}
    """
    result: dict = {}

    for day_data in sim_data.get("days", []):
        day_n = day_data.get("day", 1)
        for tick_data in day_data.get("ticks", []):
            t_str = tick_data.get("time", "")
            for code, dec in tick_data.get("decide", {}).items():
                if "error" in dec:
                    continue
                if code not in result:
                    result[code] = []

                meta  = dec.get("_meta") or {}
                conf  = meta.get("confusion") or {}
                probs = meta.get("action_probs") or {}

                # 前 6 個最高機率行動（轉成 %）
                top_probs = sorted(
                    [(a, round(p * 100, 1)) for a, p in probs.items()],
                    key=lambda x: -x[1]
                )[:6]

                result[code].append({
                    "day":      day_n,
                    "time":     t_str,
                    "action":   dec.get("action", ""),
                    "target":   dec.get("target", ""),
                    "content":  dec.get("content", ""),
                    "thought":  dec.get("thought", ""),
                    "mode":     dec.get("mode", "intuitive"),
                    "C":        round(conf.get("C", 0.0), 2),
                    "K":        round(conf.get("K", 0.0), 2),
                    "top_probs":  top_probs,
                    "is_major":   bool(meta.get("is_major_event", False)),
                })

    return result


def _build_char_confusion(sim_data: dict) -> dict:
    """
    從 sim_data 建立每個角色的困惑度曲線資料（給 chart.js 用）。
    回傳：{code: {labels, U, K, S, C, modes, thresholds}}
    """
    result: dict = {}

    for day_data in sim_data.get("days", []):
        for tick_data in day_data.get("ticks", []):
            t_str = tick_data.get("time", "")
            for code, dec in tick_data.get("decide", {}).items():
                if "error" in dec:
                    continue
                if code not in result:
                    result[code] = {
                        "labels": [], "U": [], "K": [], "S": [], "C": [],
                        "modes": [], "thresholds": [],
                    }

                meta = dec.get("_meta") or {}
                conf = meta.get("confusion") or {}

                result[code]["labels"].append(t_str)
                result[code]["U"].append(round(conf.get("U", 0.0), 3))
                result[code]["K"].append(round(conf.get("K", 0.0), 3))
                result[code]["S"].append(round(conf.get("S", 0.0), 3))
                result[code]["C"].append(round(conf.get("C", 0.0), 3))
                result[code]["modes"].append(dec.get("mode", "intuitive"))
                result[code]["thresholds"].append(
                    round(conf.get("threshold", 0.5), 3)
                )

    return result


def _build_dialogue_list(sim_data: dict) -> list:
    """
    攤平所有 tick 的對話記錄，加上 day/time 資訊。
    """
    result = []
    for day_data in sim_data.get("days", []):
        day_n = day_data.get("day", 1)
        for tick_data in day_data.get("ticks", []):
            t_str = tick_data.get("time", "")
            for raw in tick_data.get("dialogues", []):
                formatted = format_dialogue_history([raw])
                if formatted:
                    d = formatted[0]
                    d["day"]  = day_n
                    d["time"] = t_str
                    result.append(d)
    return result


def _build_sleep_reports(sim_data: dict) -> list:
    """
    收集所有天的睡眠報告。
    回傳：[{day, code, character_name, ham_extracted, ...}, ...]
    """
    result = []
    for day_data in sim_data.get("days", []):
        day_n   = day_data.get("day", 1)
        reports = day_data.get("sleep_reports", {})
        for code, rep in reports.items():
            entry = dict(rep)
            entry["day"]  = day_n
            entry["code"] = code
            result.append(entry)
    return result


def _compute_stats(sim_data, final_state, dialogue_list) -> dict:
    total_days  = len(sim_data.get("days", []))
    total_ticks = sum(
        len(d.get("ticks", [])) for d in sim_data.get("days", [])
    )
    model_calls = 0
    for day_data in sim_data.get("days", []):
        for tick_data in day_data.get("ticks", []):
            for dec in tick_data.get("decide", {}).values():
                if dec.get("mode") == "deliberate":
                    model_calls += 1
    accepted = sum(1 for d in dialogue_list if d.get("accepted"))
    return {
        "total_days":      total_days,
        "total_ticks":     total_ticks,
        "model_calls":     model_calls,
        "dialogue_total":  len(dialogue_list),
        "dialogue_accept": accepted,
    }


# ================================================================
# C. LTM vis.js 格式轉換
# ================================================================

def _ltm_to_vis(nodes: list, edges: list) -> dict:
    """把 raw LTM nodes/edges 轉成 vis.js Dataset 格式。"""
    vis_nodes = [
        {
            "id":    n["id"],
            "label": n["label"],
            "group": n.get("type", "concept"),
            "value": n.get("value", 1),
            "title": f"{n['label']}（{n.get('type','')}）",
        }
        for n in nodes
    ]
    vis_edges = [
        {
            "from":   e["from"],
            "to":     e["to"],
            "label":  e["label"],
            "value":  max(1, int(e.get("strength", 0.5) * 5)),
            "title":  f"{e['label']}（強度 {e.get('strength', 0):.2f}）",
            "arrows": "to",
        }
        for e in edges
    ]
    return {"nodes": vis_nodes, "edges": vis_edges}


# Keep public alias for backward compatibility
def ltm_to_vis_graph_from_data(nodes: list, edges: list) -> dict:
    return _ltm_to_vis(nodes, edges)


# ================================================================
# D. HTML 頂層渲染
# ================================================================

def _render_html(final_state, stats,
                 char_tick_log, char_confusion,
                 dialogue_list, sleep_reports,
                 ltm_js) -> str:
    codes = sorted(final_state.keys())

    ltm_js_str  = json.dumps(ltm_js,         ensure_ascii=False)
    conf_js_str = json.dumps(char_confusion,  ensure_ascii=False)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>AI-Town 模擬報告</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
{_css()}
</style>
</head>
<body>
<header>
  <h1>🏘 AI-Town 模擬報告</h1>
  <div class="meta">
    生成時間：{ts} ｜
    天數：{stats['total_days']} ｜
    Ticks：{stats['total_ticks']} ｜
    模型呼叫（深思）：{stats['model_calls']} ｜
    對話嘗試：{stats['dialogue_total']}（接受 {stats['dialogue_accept']}）
  </div>
</header>

<nav id="main-nav">
  <button class="tab-btn active" data-tab="overview">📊 總覽</button>
  <button class="tab-btn" data-tab="daily-log">📅 每日日誌</button>
  <button class="tab-btn" data-tab="schedule">🗓 時間表</button>
  <button class="tab-btn" data-tab="ltm">🕸 LTM 圖譜</button>
  <button class="tab-btn" data-tab="confusion">📈 困惑度曲線</button>
  <button class="tab-btn" data-tab="dialogue">💬 對話記錄</button>
  <button class="tab-btn" data-tab="sleep">🌙 睡眠濃縮</button>
</nav>

<main>
{_render_overview(final_state, stats)}
{_render_daily_log(final_state, char_tick_log, codes)}
{_render_schedule(final_state, sleep_reports, codes)}
{_render_ltm(final_state, codes)}
{_render_confusion(final_state, codes)}
{_render_dialogue(dialogue_list)}
{_render_sleep(sleep_reports, final_state)}
</main>

<script>
const LTM_DATA  = {ltm_js_str};
const CONF_DATA = {conf_js_str};
{_js()}
</script>
</body>
</html>"""


# ================================================================
# E. 各分頁渲染
# ================================================================

def _render_overview(final_state, stats) -> str:
    rows = []
    for code in sorted(final_state.keys()):
        d = final_state[code]
        stm_count = len(d.get("stm", []))
        ltm_count = len(d.get("ltm_edges", []))
        status    = "💤 睡眠中" if d["is_sleeping"] else "🟢 活動中"
        rows.append(f"""<tr>
          <td><b>{d['name']}</b></td><td>{code}</td><td>第 {d['day']} 天</td>
          <td>{d['current_location']}</td><td>{d['current_action']}</td>
          <td>{d['emotion']}</td>
          <td>{stm_count}</td><td>{ltm_count}</td><td>{status}</td>
        </tr>""")

    stat_cards = "".join([
        f'<div class="stat-card"><div class="stat-num">{stats[k]}</div>'
        f'<div class="stat-label">{label}</div></div>'
        for k, label in [
            ("total_ticks",     "總 Ticks"),
            ("model_calls",     "深思模式次數"),
            ("dialogue_total",  "對話嘗試"),
            ("dialogue_accept", "對話接受"),
        ]
    ])

    return f"""
<section id="overview" class="tab active">
  <h2>角色總覽（最終狀態）</h2>
  <table class="overview-table">
    <thead><tr>
      <th>名字</th><th>代號</th><th>日期</th>
      <th>位置</th><th>行動</th><th>情緒</th>
      <th>STM</th><th>LTM 命題</th><th>狀態</th>
    </tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <div class="stat-row">{stat_cards}</div>
</section>"""


def _render_daily_log(final_state, char_tick_log, codes) -> str:
    """每日決策日誌——每個時段的決策結果（直覺/深思）。"""
    char_tabs  = _char_tab_buttons(final_state, codes, "log-panel-")
    panels_html = []

    for idx, code in enumerate(codes):
        active = "active" if idx == 0 else ""
        ticks  = char_tick_log.get(code, [])

        if not ticks:
            body = '<div class="empty">（無決策記錄）</div>'
        else:
            # 按天分組
            by_day: dict = {}
            for t in ticks:
                by_day.setdefault(t["day"], []).append(t)

            body = ""
            for day_n in sorted(by_day.keys()):
                body += f'<div class="day-header">第 {day_n} 天</div>'
                for tick in by_day[day_n]:
                    body += _render_tick_entry(tick)

        panels_html.append(
            f'<div class="char-panel {active}" id="log-panel-{code}">'
            f'{body}</div>'
        )

    return f"""
<section id="daily-log" class="tab">
  <h2>每日決策日誌</h2>
  <p class="section-desc">
    🟢 直覺模式（Markov / System 1）顯示行動機率分布；
    🟠 深思模式（Model / System 2）顯示模型思考與輸出。
    ⚡ 代表重大事件（K≥0.6）。
  </p>
  <div class="char-tabs">{''.join(char_tabs)}</div>
  <div class="char-panels">{''.join(panels_html)}</div>
</section>"""


def _render_tick_entry(tick: dict) -> str:
    """渲染單一 tick 的決策卡片。"""
    mode       = tick.get("mode", "intuitive")
    is_major   = tick.get("is_major", False)
    mode_label = "直覺" if mode == "intuitive" else "深思"
    mode_cls   = "intuitive" if mode == "intuitive" else "deliberate"

    action_str = tick.get("action", "—")
    target     = tick.get("target", "")
    if target:
        action_str += f" → {target}"

    major_html = '<span class="major-badge">⚡ 重大</span>' if is_major else ""
    c_val      = tick.get("C", 0.0)
    k_val      = tick.get("K", 0.0)

    # ── Markov 機率（直覺模式）
    probs_html = ""
    if mode == "intuitive" and tick.get("top_probs"):
        chosen = tick.get("action", "")
        bars = []
        for act, pct in tick["top_probs"]:
            sel_cls  = " selected" if act == chosen else ""
            bar_w    = min(pct, 100)
            bars.append(
                f'<div class="prob-item{sel_cls}">'
                f'<span class="prob-action">{act}</span>'
                f'<div class="prob-bar-wrap">'
                f'<div class="prob-bar-fill" style="width:{bar_w}%"></div>'
                f'</div>'
                f'<span class="prob-pct">{pct:.0f}%</span>'
                f'</div>'
            )
        probs_html = f'<div class="tick-probs">{"".join(bars)}</div>'

    # ── 模型輸出（深思模式）
    thought_html = content_html = ""
    if mode == "deliberate":
        thought = tick.get("thought", "")
        content = tick.get("content", "")
        if thought:
            thought_html = f'<div class="tick-thought">💭 {thought}</div>'
        if content:
            content_html = f'<div class="tick-content">💬 「{content}」</div>'

    return (
        f'<div class="tick-entry {mode_cls}">'
        f'  <div class="tick-hdr">'
        f'    <span class="tick-time">{tick.get("time","")}</span>'
        f'    <span class="mode-badge {mode_cls}">{mode_label}</span>'
        f'    {major_html}'
        f'    <span class="tick-action">{action_str}</span>'
        f'    <span class="tick-cv" title="C={c_val:.2f} K={k_val:.2f}">'
        f'C={c_val:.2f}</span>'
        f'  </div>'
        f'  {probs_html}'
        f'  {thought_html}'
        f'  {content_html}'
        f'</div>'
    )


def _render_schedule(final_state, sleep_reports, codes) -> str:
    """時間表分頁：原始時間表 + 每日實際決策摘要。"""
    char_tabs   = _char_tab_buttons(final_state, codes, "sched-panel-")
    panels_html = []

    # 按 code 索引睡眠報告（取最後一筆）
    sleep_by_code: dict = {}
    for rep in sleep_reports:
        c = rep.get("code") or rep.get("character_code", "")
        if c:
            sleep_by_code[c] = rep

    for idx, code in enumerate(codes):
        active = "active" if idx == 0 else ""
        sched  = final_state[code].get("schedule", [])
        name   = final_state[code]["name"]

        # ── 當前時間表（從 final_state，睡眠濃縮後生成的計畫）
        sched_rows = ""
        for slot in sorted(sched, key=lambda s: s.get("time", "")):
            done_cls  = "completed" if slot.get("completed") else ""
            done_mark = "✓" if slot.get("completed") else "·"
            sched_rows += (
                f'<tr class="{done_cls}">'
                f'<td class="sched-time">{slot.get("time","")}</td>'
                f'<td>{slot.get("action","")}</td>'
                f'<td>{slot.get("location","")}</td>'
                f'<td class="done-mark">{done_mark}</td>'
                f'</tr>'
            )
        if not sched_rows:
            sched_rows = '<tr><td colspan="4" style="color:#86868b">（無時間表資料）</td></tr>'

        # ── 睡眠報告裡的情緒 / 摘要（簡要）
        sleep_summary_html = ""
        rep = sleep_by_code.get(code)
        if rep:
            emo_from = rep.get("emotion_change", {}).get("from", "")
            emo_to   = rep.get("emotion_change", {}).get("to", "")
            emo_str  = f"{emo_from} → {emo_to}" if emo_from != emo_to else emo_from
            ltm_sum  = (rep.get("ltm_summary") or "")[:120]
            sleep_summary_html = f"""
<div class="sched-sleep-info">
  <span>😶 情緒：{emo_str}</span>
  <span>📝 {ltm_sum}</span>
</div>"""

        panels_html.append(f"""
<div class="char-panel {active}" id="sched-panel-{code}">
  {sleep_summary_html}
  <table class="sched-table">
    <thead>
      <tr><th>時間</th><th>行動</th><th>地點</th><th>完成</th></tr>
    </thead>
    <tbody>{sched_rows}</tbody>
  </table>
  <div class="sched-note">※ 此為睡眠濃縮後生成的計畫（已重置完成狀態）。完整每時決策請查「每日日誌」分頁。</div>
</div>""")

    return f"""
<section id="schedule" class="tab">
  <h2>角色時間表</h2>
  <p class="section-desc">
    每個角色的作息計畫。由模型在睡眠濃縮時依當天事件重新生成，
    或使用職業預設模板。
  </p>
  <div class="char-tabs">{''.join(char_tabs)}</div>
  <div class="char-panels">{''.join(panels_html)}</div>
</section>"""


def _render_ltm(final_state, codes) -> str:
    """LTM 圖譜（vis.js，修復物理參數避免節點擠壓）。"""
    char_tabs   = _char_tab_buttons(final_state, codes, "ltm-panel-")
    panels_html = []

    for idx, code in enumerate(codes):
        active     = "active" if idx == 0 else ""
        ltm_summary = final_state[code].get("ltm_summary", "") or "（尚無摘要）"
        ltm_count   = len(final_state[code].get("ltm_edges", []))

        panels_html.append(f"""
<div class="char-panel {active}" id="ltm-panel-{code}">
  <div class="ltm-summary">📝 {ltm_summary} <span class="ltm-count">({ltm_count} 條命題)</span></div>
  <div id="ltm-graph-{code}" style="height:540px;background:white;border-radius:8px;"></div>
</div>""")

    return f"""
<section id="ltm" class="tab">
  <h2>LTM 記憶圖譜（互動：拖移 / 縮放 / 懸停查看詳情）</h2>
  <div class="legend">
    <span class="lg-node person">● 角色</span>
    <span class="lg-node location">● 地點</span>
    <span class="lg-node concept">● 概念</span>
  </div>
  <div class="char-tabs">{''.join(char_tabs)}</div>
  <div class="char-panels">{''.join(panels_html)}</div>
</section>"""


def _render_confusion(final_state, codes) -> str:
    """困惑度曲線（chart.js，DOMContentLoaded 初始化修復版）。"""
    char_tabs   = _char_tab_buttons(final_state, codes, "conf-panel-")
    panels_html = []

    for idx, code in enumerate(codes):
        active = "active" if idx == 0 else ""
        panels_html.append(f"""
<div class="char-panel {active}" id="conf-panel-{code}">
  <canvas id="conf-chart-{code}" width="900" height="300"
          style="max-width:100%;"></canvas>
  <div class="conf-legend">
    <span class="lg-u">— U 不確定性</span>
    <span class="lg-k">— K 困惑度峰值</span>
    <span class="lg-s">— S 情境複雜度</span>
    <span class="lg-c">— C 最終值（粗線）</span>
    <span class="lg-th">-- 閾值（虛線）</span>
  </div>
  <div class="conf-note">
    🟠 三角形點 = 該時段觸發深思模式（C 超過閾值，呼叫模型）
  </div>
</div>""")

    return f"""
<section id="confusion" class="tab">
  <h2>困惑度曲線（雙歷程理論 Kahneman 2011）</h2>
  <p class="section-desc">
    C 值超過閾值 → 深思（System 2）；以下 → 直覺（System 1 / Markov）。
    情緒不好時閾值升高（更傾向直覺）。
  </p>
  <div class="char-tabs">{''.join(char_tabs)}</div>
  <div class="char-panels">{''.join(panels_html)}</div>
</section>"""


def _render_dialogue(dialogue_list: list) -> str:
    """對話記錄分頁。"""
    if not dialogue_list:
        body = '<div class="empty">（無對話記錄）</div>'
    else:
        accepted_cards = []
        rejected_cards = []

        for d in dialogue_list:
            accepted  = d.get("accepted", False)
            acc_label = "✅ 接受" if accepted else "❌ 拒絕"
            acc_cls   = "accepted" if accepted else "rejected"

            turns_html = ""
            for t in d.get("turns", []):
                spk  = t.get("speaker_name", "?")
                msg  = t.get("msg", "")
                turns_html += f'<div class="dlg-turn"><b>{spk}：</b>{msg}</div>'
            if not turns_html:
                turns_html = '<div class="dlg-empty">（無對話內容）</div>'

            card = (
                f'<div class="dlg-card {acc_cls}">'
                f'  <div class="dlg-head">'
                f'    第 {d.get("day","")} 天 {d.get("time","")} ｜ '
                f'    {d["initiator_name"]} → {d["responder_name"]} ｜ '
                f'    {acc_label} ｜ {d.get("rounds",0)} 來回'
                f'  </div>'
                f'  <div class="dlg-body">{turns_html}</div>'
                f'</div>'
            )
            if accepted:
                accepted_cards.append(card)
            else:
                rejected_cards.append(card)

        # 接受的先顯示
        body = ""
        if accepted_cards:
            body += f'<h3 class="dlg-group-header">✅ 接受的對話（{len(accepted_cards)} 次）</h3>'
            body += "".join(accepted_cards)
        if rejected_cards:
            body += f'<h3 class="dlg-group-header">❌ 拒絕的邀請（{len(rejected_cards)} 次）</h3>'
            body += "".join(rejected_cards)

    return f"""
<section id="dialogue" class="tab">
  <h2>對話記錄</h2>
  <div class="dialogue-list">{body}</div>
</section>"""


def _render_sleep(sleep_reports: list, final_state: dict) -> str:
    """睡眠濃縮報告分頁。"""
    if not sleep_reports:
        body = (
            '<div class="empty">'
            '（無睡眠濃縮紀錄）<br>'
            '<small>可能原因：模擬未完成一整天、或模擬天數設定不足</small>'
            '</div>'
        )
    else:
        cards = []
        for rep in sleep_reports:
            code = rep.get("code") or rep.get("character_code", "?")
            name = rep.get("character_name",
                           final_state.get(code, {}).get("name", code))
            day  = rep.get("day", "?")

            emo_from = rep.get("emotion_change", {}).get("from", "?")
            emo_to   = rep.get("emotion_change", {}).get("to", "?")
            emo_arrow = " → " if emo_from != emo_to else " ＝ "
            emo_html = f"😶 情緒：{emo_from}{emo_arrow}{emo_to}"

            # 摘要
            summary  = (rep.get("ltm_summary", "") or "（無）")[:200]
            max_k    = rep.get("today_max_K", 0.0)

            # 隔天時間表摘要
            next_sched = rep.get("next_day_schedule", [])
            sched_str  = "（無）"
            if next_sched:
                sched_str = "  ".join(
                    f'{s.get("time","")}{s.get("action","")}'
                    for s in sorted(next_sched, key=lambda s: s.get("time",""))[:8]
                )

            # 關係更新
            rel_changes = rep.get("relationship_updates", {})
            rel_html    = ""
            if rel_changes:
                rel_items = "；".join(
                    f'{CHARACTER_NAMES.get(c, c)}: {v[:30]}'
                    for c, v in list(rel_changes.items())[:4]
                )
                rel_html = f'<div class="sleep-rel">🤝 關係更新：{rel_items}</div>'

            # 統計徽章
            stats_badges = " ".join([
                f'<span class="sleep-badge">HAM 抽取 {rep.get("ham_extracted",0)}</span>',
                f'<span class="sleep-badge">HAM 保留 {rep.get("ham_kept",0)}</span>',
                f'<span class="sleep-badge">LTM 總量 {rep.get("ltm_total",0)}</span>',
                f'<span class="sleep-badge">LTM 修剪 {rep.get("ltm_pruned",0)}</span>',
                f'<span class="sleep-badge">STM 保留 {rep.get("stm_kept",0)}</span>',
                f'<span class="sleep-badge">今日峰值 K={max_k:.2f}</span>',
            ])

            cards.append(f"""
<div class="sleep-card">
  <div class="sleep-head">
    <span class="sleep-who">{name}</span>
    <span class="sleep-day">第 {day} 天 睡眠濃縮</span>
  </div>
  <div class="sleep-badges">{stats_badges}</div>
  <div class="sleep-row">{emo_html}</div>
  <div class="sleep-row">📝 LTM 摘要：{summary}</div>
  <div class="sleep-row">📅 隔天計畫：{sched_str}</div>
  {rel_html}
</div>""")

        body = "".join(cards)

    return f"""
<section id="sleep" class="tab">
  <h2>睡眠濃縮報告</h2>
  <p class="section-desc">
    睡眠時進行 STM→LTM 轉移（Diekelmann & Born 2010）。
    HAM 命題從當天敘述中抽取，重要的存入長期記憶。
  </p>
  <div class="sleep-list">{body}</div>
</section>"""


# ================================================================
# F. 共用 HTML 元件
# ================================================================

def _char_tab_buttons(final_state, codes, panel_prefix) -> list:
    """產生角色切換按鈕清單。"""
    buttons = []
    for idx, code in enumerate(codes):
        active = "active" if idx == 0 else ""
        name   = final_state[code]["name"]
        buttons.append(
            f'<button class="char-tab-btn {active}" '
            f'onclick="showCharTab(\'{panel_prefix}\', \'{code}\', this)">'
            f'{name}</button>'
        )
    return buttons


# ================================================================
# G. CSS
# ================================================================

def _css() -> str:
    return """
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont,
               "Microsoft JhengHei", "Segoe UI", sans-serif;
  background: #f0f0f5; color: #1d1d1f; margin: 0;
}
header {
  background: #1d1d1f; color: white; padding: 16px 28px;
}
header h1 { margin: 0 0 6px; font-size: 22px; }
.meta { font-size: 12px; color: #a1a1a6; }

/* ── Nav ───────────────────────────────────────────── */
nav#main-nav {
  background: white; padding: 8px 28px;
  border-bottom: 1px solid #d2d2d7;
  display: flex; gap: 6px; flex-wrap: wrap;
  position: sticky; top: 0; z-index: 100;
}
.tab-btn {
  padding: 7px 14px; border: none; background: #f0f0f5;
  border-radius: 6px; cursor: pointer; font-size: 13px; color: #1d1d1f;
  transition: background 0.15s;
}
.tab-btn:hover { background: #e0e0e8; }
.tab-btn.active { background: #007aff; color: white; }

/* ── Main ──────────────────────────────────────────── */
main { padding: 20px 28px; }
.tab { display: none; }
.tab.active { display: block; }
h2 { font-size: 19px; margin: 0 0 4px; }
h3 { font-size: 16px; margin: 0 0 10px; }
h4 { font-size: 14px; margin: 0 0 8px; }
.section-desc { font-size: 13px; color: #6e6e73; margin: 0 0 14px; line-height: 1.5; }

/* ── Overview ──────────────────────────────────────── */
.overview-table {
  border-collapse: collapse; background: white;
  border-radius: 8px; overflow: hidden; width: 100%; margin-bottom: 20px;
}
.overview-table th, .overview-table td {
  padding: 9px 12px; text-align: left;
  border-bottom: 1px solid #e5e5ea; font-size: 13px;
}
.overview-table th { background: #fafafa; font-weight: 600; font-size: 12px; }
.stat-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
.stat-card {
  background: white; border-radius: 8px; padding: 14px 20px;
  flex: 1; min-width: 130px; text-align: center;
}
.stat-num { font-size: 30px; font-weight: 700; color: #007aff; }
.stat-label { font-size: 12px; color: #86868b; margin-top: 4px; }

/* ── Char tabs (common) ────────────────────────────── */
.char-tabs {
  display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap;
}
.char-tab-btn {
  padding: 5px 12px; border: 1px solid #d2d2d7; background: white;
  border-radius: 5px; cursor: pointer; font-size: 13px;
}
.char-tab-btn.active { background: #007aff; color: white; border-color: #007aff; }
.char-panel { display: none; }
.char-panel.active { display: block; }

/* ── Daily Log ─────────────────────────────────────── */
.day-header {
  font-size: 13px; font-weight: 700; color: #007aff;
  background: #e8f0fe; padding: 5px 12px;
  border-radius: 4px; margin: 16px 0 8px;
}
.tick-entry {
  background: white; border-radius: 8px; margin-bottom: 7px;
  padding: 9px 13px; border-left: 4px solid #d2d2d7;
}
.tick-entry.intuitive { border-left-color: #34c759; }
.tick-entry.deliberate { border-left-color: #ff9500; }

.tick-hdr {
  display: flex; align-items: center; gap: 8px;
  flex-wrap: wrap; margin-bottom: 2px;
}
.tick-time {
  font-size: 13px; font-weight: 700; color: #007aff; min-width: 46px;
}
.mode-badge {
  font-size: 11px; padding: 2px 7px; border-radius: 10px;
  font-weight: 600; white-space: nowrap;
}
.mode-badge.intuitive  { background: #d4f5de; color: #1a7a3e; }
.mode-badge.deliberate { background: #ffecd0; color: #b06800; }
.major-badge {
  font-size: 11px; padding: 2px 7px; border-radius: 10px;
  background: #ffd2d2; color: #900; font-weight: 600;
}
.tick-action { flex: 1; font-size: 14px; font-weight: 500; color: #1d1d1f; }
.tick-cv { font-size: 12px; color: #86868b; margin-left: auto; white-space: nowrap; }

/* Markov probability bars */
.tick-probs {
  margin-top: 7px; display: flex; flex-direction: column; gap: 3px;
}
.prob-item { display: flex; align-items: center; gap: 6px; }
.prob-item.selected .prob-action { font-weight: 700; color: #007aff; }
.prob-action {
  font-size: 11px; width: 58px; text-align: right;
  color: #424245; flex-shrink: 0;
}
.prob-bar-wrap {
  flex: 1; height: 7px; background: #eee;
  border-radius: 4px; overflow: hidden;
}
.prob-bar-fill {
  height: 100%; background: #b0ddc0; border-radius: 4px;
}
.prob-item.selected .prob-bar-fill { background: #34c759; }
.prob-pct {
  font-size: 11px; color: #86868b; width: 34px; flex-shrink: 0;
}

/* Model output */
.tick-thought {
  font-size: 13px; color: #5856d6; margin-top: 6px; font-style: italic;
}
.tick-content {
  font-size: 13px; background: #f5f5f7; padding: 5px 10px;
  border-radius: 4px; margin-top: 4px;
}

/* ── Schedule ──────────────────────────────────────── */
.sched-table {
  border-collapse: collapse; width: 100%; background: white;
  border-radius: 8px; overflow: hidden; margin-bottom: 12px;
}
.sched-table th, .sched-table td {
  padding: 8px 14px; text-align: left;
  border-bottom: 1px solid #f0f0f5; font-size: 13px;
}
.sched-table th { background: #fafafa; font-weight: 600; font-size: 12px; }
.sched-table tr.completed td { color: #86868b; }
.sched-time { font-weight: 600; color: #007aff; }
.done-mark { color: #34c759; font-weight: bold; }
.sched-sleep-info {
  display: flex; gap: 16px; font-size: 13px; color: #424245;
  background: #f5f5f7; padding: 8px 12px; border-radius: 6px;
  margin-bottom: 10px; flex-wrap: wrap;
}
.sched-note { font-size: 12px; color: #86868b; margin-top: 6px; }

/* ── LTM ───────────────────────────────────────────── */
.ltm-summary {
  background: white; padding: 10px 14px; border-radius: 6px;
  margin-bottom: 10px; font-size: 13px; color: #424245;
}
.ltm-count { color: #86868b; font-size: 12px; }
.legend { display: flex; gap: 12px; margin-bottom: 12px; font-size: 13px; }
.lg-node {
  padding: 2px 10px; border-radius: 10px; font-weight: 600;
}
.lg-node.person   { background: #cce5ff; color: #0055bb; }
.lg-node.location { background: #d4f5de; color: #1a7a3e; }
.lg-node.concept  { background: #fff3d0; color: #a05e00; }

/* ── Confusion Chart ───────────────────────────────── */
.conf-legend {
  display: flex; gap: 16px; margin-top: 8px; font-size: 12px;
  flex-wrap: wrap;
}
.conf-note { font-size: 12px; color: #86868b; margin-top: 4px; }
.lg-u { color: #007aff; }
.lg-k { color: #ff3b30; }
.lg-s { color: #ff9500; }
.lg-c { color: #34c759; font-weight: 700; }
.lg-th { color: #86868b; }

/* ── Dialogue ──────────────────────────────────────── */
.dialogue-list { max-height: 80vh; overflow-y: auto; }
.dlg-group-header {
  font-size: 14px; margin: 16px 0 8px; color: #424245;
}
.dlg-card {
  background: white; padding: 12px 14px; margin-bottom: 8px;
  border-radius: 8px; border-left: 4px solid #34c759;
}
.dlg-card.rejected { border-left-color: #ff3b30; opacity: 0.70; }
.dlg-head { font-size: 12px; color: #86868b; margin-bottom: 8px; }
.dlg-turn { padding: 3px 0; font-size: 14px; }
.dlg-empty { color: #86868b; font-size: 13px; }

/* ── Sleep ─────────────────────────────────────────── */
.sleep-card {
  background: white; padding: 14px 16px;
  margin-bottom: 12px; border-radius: 8px;
  border-left: 4px solid #5856d6;
}
.sleep-head {
  display: flex; justify-content: space-between;
  align-items: baseline; margin-bottom: 10px;
}
.sleep-who { font-weight: 700; font-size: 16px; }
.sleep-day { color: #86868b; font-size: 13px; }
.sleep-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.sleep-badge {
  background: #f0f0f5; padding: 3px 8px;
  border-radius: 4px; font-size: 12px; color: #424245;
}
.sleep-row { font-size: 13px; margin-top: 6px; color: #424245; line-height: 1.5; }
.sleep-rel { font-size: 13px; margin-top: 6px; color: #5856d6; }
.sleep-list { }

/* ── Utilities ─────────────────────────────────────── */
.empty {
  color: #86868b; padding: 30px; text-align: center;
  font-size: 14px; line-height: 2;
}
"""


# ================================================================
# H. JavaScript
# ================================================================

def _js() -> str:
    return r"""
// ── Tab switching ──────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    var name = this.dataset.tab;
    document.querySelectorAll('.tab').forEach(function(t) {
      t.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(function(b) {
      b.classList.remove('active');
    });
    document.getElementById(name).classList.add('active');
    this.classList.add('active');

    // 觸發需要可見容器的元件
    if (name === 'ltm')      { initActiveLTMGraph(); }
    if (name === 'confusion') { resizeConfusionCharts(); }
  });
});

// ── Character panel switching ──────────────────────────────────
function showCharTab(panelPrefix, code, btn) {
  var section = btn.closest('.tab');
  section.querySelectorAll('.char-panel').forEach(function(p) {
    p.classList.remove('active');
  });
  btn.closest('.char-tabs').querySelectorAll('.char-tab-btn').forEach(function(b) {
    b.classList.remove('active');
  });
  document.getElementById(panelPrefix + code).classList.add('active');
  btn.classList.add('active');

  // LTM：切換角色時初始化該角色的圖
  if (panelPrefix === 'ltm-panel-') {
    initLTMGraph(code);
  }
}

// ── LTM vis.js Graphs ──────────────────────────────────────────
var ltmNetworks = {};
var ltmInitDone = false;

function initActiveLTMGraph() {
  if (ltmInitDone) return;
  ltmInitDone = true;
  // 只初始化當前可見的
  var active = document.querySelector('#ltm .char-panel.active');
  if (active) {
    var code = active.id.replace('ltm-panel-', '');
    initLTMGraph(code);
  }
}

function initLTMGraph(code) {
  if (ltmNetworks[code]) {
    ltmNetworks[code].redraw();
    ltmNetworks[code].fit();
    return;
  }
  var container = document.getElementById('ltm-graph-' + code);
  if (!container) return;

  var data = LTM_DATA[code];
  if (!data || !data.nodes || data.nodes.length === 0) {
    container.innerHTML =
      '<div style="padding:30px;color:#86868b;text-align:center">' +
      '（尚無 LTM 命題）</div>';
    return;
  }

  var options = {
    nodes: {
      shape: 'dot',
      scaling: {
        min: 14, max: 42,
        label: { enabled: true, min: 12, max: 18 }
      },
      font: { size: 14, face: 'Microsoft JhengHei, Arial, sans-serif' },
      borderWidth: 2,
    },
    edges: {
      font: { size: 11, align: 'middle',
              face: 'Microsoft JhengHei, Arial, sans-serif' },
      smooth: { type: 'continuous' },
      arrows: { to: { enabled: true, scaleFactor: 0.65 } },
      color: { color: '#848484', opacity: 0.8 },
    },
    groups: {
      person:   { color: { background: '#cce5ff', border: '#0055bb',
                            highlight: { background: '#99ccff', border: '#003388' } } },
      location: { color: { background: '#d4f5de', border: '#1a7a3e',
                            highlight: { background: '#a8edbe', border: '#0d5c29' } } },
      concept:  { color: { background: '#fff3d0', border: '#a05e00',
                            highlight: { background: '#ffe8a0', border: '#7a4700' } } },
    },
    physics: {
      enabled: true,
      barnesHut: {
        gravitationalConstant: -4000,
        centralGravity: 0.25,
        springLength: 200,
        springConstant: 0.03,
        damping: 0.12,
        avoidOverlap: 1.0,
      },
      stabilization: {
        enabled: true,
        iterations: 400,
        updateInterval: 25,
        fit: true,
      },
    },
    layout: {
      improvedLayout: true,
      randomSeed: 42,
    },
    interaction: {
      hover: true,
      tooltipDelay: 150,
      zoomView: true,
      dragView: true,
      navigationButtons: true,
    },
  };

  ltmNetworks[code] = new vis.Network(
    container,
    { nodes: new vis.DataSet(data.nodes),
      edges: new vis.DataSet(data.edges) },
    options
  );
}

// ── Confusion Charts (chart.js) ────────────────────────────────
var confCharts = {};

function initConfusionCharts() {
  Object.keys(CONF_DATA).forEach(function(code) {
    if (confCharts[code]) return;
    var canvas = document.getElementById('conf-chart-' + code);
    if (!canvas) return;

    var c = CONF_DATA[code];
    if (!c || !c.labels || c.labels.length === 0) {
      canvas.insertAdjacentHTML('afterend',
        '<div style="padding:10px;color:#86868b">（無困惑度數據）</div>');
      return;
    }

    // C 點：深思時用橘色三角形，直覺時用綠色圓點
    var cPointStyle  = c.modes.map(function(m) {
      return m === 'deliberate' ? 'triangle' : 'circle';
    });
    var cPointColor  = c.modes.map(function(m) {
      return m === 'deliberate' ? '#ff9500' : '#34c759';
    });
    var cPointRadius = c.modes.map(function(m) {
      return m === 'deliberate' ? 9 : 4;
    });

    confCharts[code] = new Chart(canvas, {
      type: 'line',
      data: {
        labels: c.labels,
        datasets: [
          { label: 'U 不確定性', data: c.U,
            borderColor: '#007aff', backgroundColor: 'transparent',
            pointRadius: 3, tension: 0.3 },
          { label: 'K 困惑度',   data: c.K,
            borderColor: '#ff3b30', backgroundColor: 'transparent',
            pointRadius: 3, tension: 0.3 },
          { label: 'S 情境複雜', data: c.S,
            borderColor: '#ff9500', backgroundColor: 'transparent',
            pointRadius: 3, tension: 0.3 },
          { label: 'C 最終值',   data: c.C,
            borderColor: '#34c759', borderWidth: 3,
            backgroundColor: 'transparent',
            pointRadius: cPointRadius,
            pointStyle:  cPointStyle,
            pointBackgroundColor: cPointColor,
            tension: 0.3 },
          { label: '閾值', data: c.thresholds,
            borderColor: '#86868b', borderDash: [7, 4],
            backgroundColor: 'transparent',
            pointRadius: 0, tension: 0 },
        ],
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 1.05, grid: { color: '#e5e5ea' } },
          x: { grid: { display: false },
               ticks: { maxRotation: 45, font: { size: 11 } } },
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { boxWidth: 12, font: { size: 12 } }
          },
          tooltip: { mode: 'index', intersect: false },
        },
        animation: { duration: 0 },
      },
    });
  });
}

function resizeConfusionCharts() {
  Object.values(confCharts).forEach(function(ch) {
    if (ch) ch.resize();
  });
}

// 頁面載入後立即初始化所有 confusion 圖表
// （canvas 有明確的 width/height，不依賴容器可見性）
document.addEventListener('DOMContentLoaded', function() {
  initConfusionCharts();
});
"""
