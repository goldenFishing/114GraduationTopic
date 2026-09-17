# ================================================================
# observe/memory_viewer.py
# LTM 圖譜視覺化資料準備
#
# 對應 ARCHITECTURE.md §6.5.2
#
# 主要功能：
#   1. ltm_to_vis_graph    — 把 MemoryGraph 轉成 vis.js 格式
#   2. stm_to_timeline     — STM 轉時間軸資料
#   3. process_log_to_curves — process_log 轉折線圖資料（U/K/S/C）
# ================================================================


def ltm_to_vis_graph(memory_graph) -> dict:
    """
    把 MemoryGraph 轉成 vis.js / cytoscape.js 格式。

    回傳：
      {
        "nodes": [{id, label, group, value, title}, ...],
        "edges": [{from, to, label, value, title}, ...]
      }
    """
    raw_nodes = memory_graph.get_all_nodes()
    raw_edges = memory_graph.get_all_edges()

    # 節點：依 type 分組（vis.js 用 group 區分顏色）
    nodes = []
    for n in raw_nodes:
        nodes.append({
            "id":    n["id"],
            "label": n["label"],
            "group": n["type"],                  # person/location/concept
            "value": n["value"],                 # 大小依平均 strength
            "title": (f"{n['label']}\n"
                       f"類型：{n['type']}\n"
                       f"涉及命題：{n['prop_count']} 筆\n"
                       f"平均強度：{n['value']}"),
        })

    # 邊：strength 決定線粗
    edges = []
    for e in raw_edges:
        title_parts = [f"{e['from']} → {e['label']} → {e['to']}"]
        if e.get("location"):
            title_parts.append(f"地點：{e['location']}")
        if e.get("time"):
            title_parts.append(f"時間：{e['time']}")
        title_parts.append(f"強度：{e['strength']}")
        title_parts.append(f"ID：{e['prop_id']}")

        edges.append({
            "from":  e["from"],
            "to":    e["to"],
            "label": e["label"],
            "value": max(1, int(e["strength"] * 5)),  # 線粗 1~5
            "title": "\n".join(title_parts),
            "arrows": "to",
        })

    return {"nodes": nodes, "edges": edges}


def stm_to_timeline(stm_turns: list) -> list:
    """
    STM 轉時間軸資料（給 dashboard 顯示）。
    """
    timeline = []
    for turn in stm_turns:
        timeline.append({
            "turn_id":    turn.get("turn_id", ""),
            "time":       turn.get("time", ""),
            "location":   turn.get("perception", {}).get("location", ""),
            "yolo_desc":  turn.get("perception", {}).get("yolo_desc", ""),
            "input":      turn.get("event", {}).get("input_text", ""),
            "action":     turn.get("event", {}).get("action", ""),
            "target":     turn.get("event", {}).get("target", ""),
            "content":    turn.get("event", {}).get("content", ""),
            "thought":    turn.get("inner", {}).get("thought", ""),
            "emotion":    turn.get("inner", {}).get("emotion", ""),
        })
    return timeline


def process_log_to_curves(process_log: list) -> dict:
    """
    把 process_log 轉成折線圖資料。

    回傳：
      {
        "labels":     [turn_id, ...],
        "U_values":   [...],
        "K_values":   [...],
        "S_values":   [...],
        "C_values":   [...],
        "thresholds": [...],
        "modes":      [...]  # 'markov' / 'deliberate'
      }
    """
    labels, U, K, S, C, modes = [], [], [], [], [], []
    for entry in process_log:
        labels.append(entry.get("turn_id", ""))
        conf = entry.get("confusion", {})
        U.append(conf.get("U", 0.0))
        K.append(conf.get("K", 0.0))
        S.append(conf.get("S", 0.0))
        C.append(conf.get("C", 0.0))
        modes.append(entry.get("decision_mode", ""))

    return {
        "labels":   labels,
        "U_values": U,
        "K_values": K,
        "S_values": S,
        "C_values": C,
        "modes":    modes,
    }
