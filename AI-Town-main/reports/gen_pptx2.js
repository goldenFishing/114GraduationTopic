const PptxGenJS = require('C:/Users/Rayyu/AppData/Roaming/npm/node_modules/pptxgenjs/dist/pptxgen.cjs.js');
const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE';

const C = {
  bg: 'F8F9FA', dark: '1A1A2E', blue: '16213E', mid: '0F3460',
  acc: 'E94560', text: '2D3436', sub: '636E72', white: 'FFFFFF',
  code: 'F1F2F6', green: '00B894', yel: 'FDCB6E', gray: 'B2BEC3',
};

// ── Slide 6: Simulation Example 1 — Intuitive path ──────────────────
function slide6() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 2｜模擬：Amy 遇到陌生客人（→ intuitive）', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  // Context box
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 5.8, h: 2.8,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('情境設定', { x: 0.55, y: 0.85, w: 5.5, h: 0.35, fontSize: 13, bold: true, color: C.mid });
  const ctx = [
    '時間：第3天 09:30',
    '地點：咖啡廳',
    '當前行動：賣咖啡',
    'YOLO：「咖啡廳內有1個陌生人，從未見過」',
    'scene_text：「一個完全陌生的男人走進咖啡廳，Amy從未見過他」',
    'input_text：「陌生男子：請給我一杯美式」',
    '情緒：平靜（基礎閾值0.45）',
  ];
  ctx.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 1.25 + i * 0.33, w: 5.5, h: 0.3, fontSize: 11, color: C.text });
  });

  // Calculation box
  s.addShape(pptx.ShapeType.rect, { x: 6.4, y: 0.82, w: 6.9, h: 5.8,
    fill: { color: C.code }, line: { color: C.gray, width: 1 } });
  s.addText('計算過程', { x: 6.55, y: 0.85, w: 6.6, h: 0.35, fontSize: 13, bold: true, color: C.dark });

  const calcs = [
    { label: 'U 計算', c: C.green, lines: [
      'Markov上一tick：賣咖啡 0.55（rank1），對話 0.30（rank2）',
      'gap = 0.55 − 0.30 = 0.25',
      'U = max(0.0, 1.0 − 0.25×2) = 0.50',
    ]},
    { label: 'K 計算', c: C.acc, lines: [
      '無邏輯衝突pair命中',
      '無強情緒關鍵字（「陌生人」不在K列表）',
      '無一般情緒關鍵字',
      'K = 0.00',
    ]},
    { label: 'S 計算', c: '6C5CE7', lines: [
      'LTM已有摘要（非第一天）',
      'scene_text 含「從未見過」→ _MID_HIGH_SURPRISE_KW',
      'S = 0.50',
    ]},
    { label: 'C 計算', c: C.mid, lines: [
      'C = 0.4×0.50 + 0.3×0.00 + 0.3×0.50',
      'C = 0.20 + 0.00 + 0.15 = 0.35',
    ]},
  ];
  let yy = 1.28;
  calcs.forEach(blk => {
    s.addText(blk.label + '：', { x: 6.55, y: yy, w: 6.6, h: 0.3, fontSize: 12, bold: true, color: blk.c });
    yy += 0.32;
    blk.lines.forEach(ln => {
      s.addText(ln, { x: 6.7, y: yy, w: 6.4, h: 0.28, fontSize: 11, color: C.text });
      yy += 0.3;
    });
    yy += 0.08;
  });

  // Result
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 3.75, w: 5.8, h: 2.85,
    fill: { color: C.green, transparency: 88 }, line: { color: C.green, width: 2 } });
  s.addText('決策結果', { x: 0.55, y: 3.78, w: 5.5, h: 0.35, fontSize: 13, bold: true, color: C.green });
  const results = [
    '情緒：平靜 → 調整 +0.00 → 最終閾值 0.45',
    'K = 0.00 < 0.50  →  不強制 deliberate',
    'C = 0.35 < 閾值 0.45',
    '→ 結果：intuitive（Markov 機率路徑）',
    '→ 行動：機率最高為「賣咖啡」',
    '→ 不呼叫 Phi-3.5 模型',
  ];
  results.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 4.22 + i * 0.37, w: 5.5, h: 0.34,
      fontSize: i === 3 ? 13 : 11, bold: i === 3, color: i === 3 ? C.green : C.text });
  });
}

// ── Slide 7: Simulation Example 2 — Deliberate path ─────────────────
function slide7() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 2｜模擬：Amy 收到 Ben 告白（→ deliberate）', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 5.8, h: 2.55,
    fill: { color: C.acc, transparency: 90 }, line: { color: C.acc, width: 1.5 } });
  s.addText('情境設定', { x: 0.55, y: 0.85, w: 5.5, h: 0.35, fontSize: 13, bold: true, color: C.acc });
  const ctx = [
    '時間：第3天 14:00',
    '地點：咖啡廳',
    '當前行動：休息',
    'input_text：「Ben：Amy，我一直很在意你，你願意和我交往嗎？」',
    'scene_text：「Ben神情認真，Amy心跳加速，思緒很亂」',
    '情緒：緊張（基礎閾值0.45 + 0.10 = 0.55）',
  ];
  ctx.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 1.25 + i * 0.33, w: 5.5, h: 0.3, fontSize: 11, color: C.text });
  });

  s.addShape(pptx.ShapeType.rect, { x: 6.4, y: 0.82, w: 6.9, h: 5.5,
    fill: { color: C.code }, line: { color: C.gray, width: 1 } });
  s.addText('計算過程', { x: 6.55, y: 0.85, w: 6.6, h: 0.35, fontSize: 13, bold: true, color: C.dark });

  const calcs2 = [
    { label: 'K 計算', c: C.acc, lines: [
      'combined = input_text + yolo_desc',
      '邏輯衝突：「休息」不在衝突行動列表 → +0',
      'scene_text 含「心跳加速」→ 一般情緒KW +0.25',
      'scene_text 含「思緒很亂」→ 強情緒KW +0.45',
      'K = min(0.25+0.45, 1.0) = 0.70',
    ]},
    { label: 'S 計算', c: '6C5CE7', lines: [
      '場景無驚訝關鍵字 → S = 0.00',
    ]},
    { label: 'U 計算', c: C.green, lines: [
      '機率均勻：對話0.35，休息0.30，gap=0.05',
      'U = max(0, 1.0 − 0.05×2) = 0.90',
    ]},
    { label: 'C 計算', c: C.mid, lines: [
      'C = 0.4×0.90 + 0.3×0.70 + 0.3×0.00',
      'C = 0.36 + 0.21 + 0.00 = 0.57',
    ]},
  ];
  let yy = 1.28;
  calcs2.forEach(blk => {
    s.addText(blk.label + '：', { x: 6.55, y: yy, w: 6.6, h: 0.3, fontSize: 12, bold: true, color: blk.c });
    yy += 0.32;
    blk.lines.forEach(ln => {
      s.addText(ln, { x: 6.7, y: yy, w: 6.4, h: 0.28, fontSize: 11, color: C.text });
      yy += 0.3;
    });
    yy += 0.08;
  });

  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 3.5, w: 5.8, h: 3.1,
    fill: { color: C.acc, transparency: 88 }, line: { color: C.acc, width: 2 } });
  s.addText('決策結果', { x: 0.55, y: 3.53, w: 5.5, h: 0.35, fontSize: 13, bold: true, color: C.acc });
  const results2 = [
    '情緒：緊張 → 調整 +0.10 → 最終閾值 0.55',
    'K = 0.70 ≥ 0.50',
    '→ 強制 deliberate（K override，不看C值）',
    '→ 呼叫 Phi-3.5-Vision-Instruct 模型',
    '→ 模型組 LTM + STM prompt 推理回應',
    'C = 0.57 也 ≥ 0.55（兩個條件都成立）',
  ];
  results2.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 3.96 + i * 0.37, w: 5.5, h: 0.34,
      fontSize: i === 2 ? 13 : 11, bold: i === 2, color: i === 2 ? C.acc : C.text });
  });
}

// ── Slide 8: Markov 4-source overview ────────────────────────────────
function slide8() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 3a｜Markov 引擎 — 四來源加權機率', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 12.5, h: 0.65,
    fill: { color: C.dark, transparency: 5 }, line: { color: C.acc, width: 2 } });
  s.addText('P_final(a) = α·P_sched(a) + β·P_iner(a) + γ·P_situ(a) + δ·P_value(a)', {
    x: 0.5, y: 0.86, w: 12.3, h: 0.56, fontSize: 16, bold: true, color: C.white, align: 'center',
  });

  const sources = [
    {
      name: 'α — schedule_score', weight: 'α = 0.40（正常）/ 0.10（重大事件）', color: C.green,
      lines: [
        '輸入：當前時間表時段 {time, action, location}',
        '完全匹配 action → 1.0',
        '同類別（同job_category）→ 0.5',
        '不相關 → 0.0',
        '「前往」特例：未到目的地提升0.6，已到×0.3',
        'Softmax 溫度 T=0.4（低溫使高分更突出）',
      ],
    },
    {
      name: 'β — inertia_score', weight: 'β = 0.30（固定）', color: C.mid,
      lines: [
        '輸入：最近N筆STM行動動詞序列',
        '歷史不足2筆 → 退回均勻分布',
        '統計：current_verb → 各行動的轉移次數',
        'Laplace平滑：count = transitions.get(a,0) + 1',
        'score[a] = math.log(count)',
        'Softmax 溫度 T=1.0',
      ],
    },
    {
      name: 'γ — situation_score', weight: 'γ = 0.30（正常）/ 0.60（重大事件）', color: C.acc,
      lines: [
        '輸入：yolo_desc + scene_text + location',
        'ACTION_KEYWORD_BOOST：每命中關鍵字 +0.15',
        'EMOTION_TO_ACTION_BOOST：情緒→特定行動加成',
        '同地點有人：對話 +0.30',
        'Softmax 溫度 T=1.0',
      ],
    },
    {
      name: 'δ — value_score', weight: 'δ = 0.15（需有action_values才啟用，否則=0）', color: 'E17055',
      lines: [
        '輸入：ActionValueTracker.get_scores()',
        '正值行動 → 傾向選擇',
        '負值行動 → 傾向迴避',
        'shift最小值歸0後 softmax',
        '無記錄時 δ=0，三源合一',
      ],
    },
  ];

  sources.forEach((src, si) => {
    const x = 0.4 + (si % 2) * 6.4;
    const y = 1.6 + Math.floor(si / 2) * 2.9;
    s.addShape(pptx.ShapeType.rect, { x, y, w: 6.1, h: 2.7,
      fill: { color: src.color, transparency: 90 }, line: { color: src.color, width: 1.5 } });
    s.addText(src.name, { x: x+0.15, y: y+0.05, w: 5.8, h: 0.38, fontSize: 13, bold: true, color: src.color });
    s.addText(src.weight, { x: x+0.15, y: y+0.43, w: 5.8, h: 0.3, fontSize: 10.5, color: C.sub, italic: true });
    src.lines.forEach((ln, li) => {
      s.addText(ln, { x: x+0.2, y: y+0.76 + li*0.3, w: 5.75, h: 0.28, fontSize: 11, color: C.text });
    });
  });
}

// ── Slide 9: Markov special mechanisms ───────────────────────────────
function slide9() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 3a｜特殊機制：睡覺時間曲線 + 重大事件 + 正規化', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 22, bold: true, color: C.dark,
  });

  // Sleep time curve
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 7.6, h: 3.0,
    fill: { color: C.blue, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('睡覺時間修正曲線（_time_sleep_score）', { x: 0.55, y: 0.85, w: 7.3, h: 0.38, fontSize: 13, bold: true, color: C.mid });
  const sleepRows = [
    ['時間段', 'ts 值', 'scale = exp(ts×2)', '效果'],
    ['07:00–18:00（工作）', 'ts = −1.5', 'exp(−3.0) ≈ 0.050', '睡覺機率 ≈ 保底0.005'],
    ['18:00–23:00（漸進）', 'ts: 0.0→+0.5', 'exp(ts) ≈ 1.0→1.65', '睡覺機率線性回升'],
    ['23:00+ （深夜）', 'ts = +0.5', 'exp(0.5) ≈ 1.65', '睡覺機率提升65%'],
  ];
  sleepRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      s.addText(cell, {
        x: 0.55 + ci*1.85, y: 1.28 + ri*0.47, w: 1.8, h: 0.43,
        fontSize: 11, bold: ri===0, color: ri===0 ? C.mid : C.text,
        fill: ri===0 ? { color: C.mid, transparency: 70 } : undefined,
      });
    });
  });

  // Major event weights
  s.addShape(pptx.ShapeType.rect, { x: 8.2, y: 0.82, w: 5.1, h: 2.5,
    fill: { color: C.acc, transparency: 88 }, line: { color: C.acc, width: 1.5 } });
  s.addText('重大事件權重切換', { x: 8.35, y: 0.85, w: 4.8, h: 0.38, fontSize: 13, bold: true, color: C.acc });
  s.addText('觸發條件：K ≥ MAJOR_EVENT_K_THRESHOLD = 0.60', { x: 8.35, y: 1.28, w: 4.8, h: 0.3, fontSize: 11, color: C.text });
  const modes = [
    ['', 'α(sched)', 'β(iner)', 'γ(situ)'],
    ['正常模式', '0.40', '0.30', '0.30'],
    ['事件模式', '0.10', '0.30', '0.60'],
  ];
  modes.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      s.addText(cell, {
        x: 8.35 + ci*1.2, y: 1.65 + ri*0.47, w: 1.15, h: 0.43,
        fontSize: 11, bold: ri===0, color: ri===0 ? C.acc : (ri===2 && ci>0 ? C.acc : C.text),
      });
    });
  });
  s.addText('目的：模擬「地震時有人繼續工作、有人逃跑」\n情境權重大增，時間表影響降低', {
    x: 8.35, y: 2.65, w: 4.8, h: 0.55, fontSize: 10.5, color: C.sub, italic: true,
  });

  // Normalization
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 4.0, w: 12.9, h: 2.4,
    fill: { color: C.green, transparency: 92 }, line: { color: C.green, width: 1.5 } });
  s.addText('最終正規化與保底機制', { x: 0.55, y: 4.03, w: 12.6, h: 0.38, fontSize: 13, bold: true, color: C.green });
  const norms = [
    '① 合併：P_raw(a) = α·P_sched + β·P_iner + γ·P_situ + δ·P_value',
    '② 保底：final_prob(a) = max(P_raw(a), MIN_PROB_FLOOR)  where MIN_PROB_FLOOR = 0.005',
    '③ 正規化：total = Σ final_prob(a)，p(a) = round(final_prob(a) / total, 4)',
    '④ 修正浮點誤差：確保所有行動機率總和精確 = 1.0',
    '⑤ 對話目標解析：選到「對話」且同地點有人 → target = 第一個同地點角色；無人可對話 → 重新採樣',
  ];
  norms.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 4.48 + i*0.35, w: 12.6, h: 0.32, fontSize: 11.5, color: C.text });
  });
}

// ── Slide 10: Markov simulation ───────────────────────────────────────
function slide10() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 3a｜模擬：Amy 咖啡廳 08:30 機率計算', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  // Context
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 6.1, h: 2.3,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('情境', { x: 0.55, y: 0.85, w: 5.8, h: 0.35, fontSize: 12, bold: true, color: C.mid });
  const ctx = [
    '時間：08:30（第3天）   地點：咖啡廳',
    '時間表：{08:30, 賣咖啡, 咖啡廳}',
    '最近STM行動：["前往","整理店面","賣咖啡","賣咖啡"]',
    'YOLO：「咖啡廳有1個客人、1個杯子、1個咖啡機」',
    '同地點角色：[]（無）   情緒：平靜   重大事件：否',
  ];
  ctx.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 1.23 + i*0.34, w: 5.8, h: 0.31, fontSize: 11, color: C.text });
  });

  // Four source results
  const sources = [
    { name: 'A. schedule', color: C.green, rows: [
      ['賣咖啡', '1.0 → softmax(T=0.4)', '≈ 0.62'],
      ['work類（收銀/補貨）', '0.5 → softmax', '各≈ 0.09'],
      ['其他', '0.0 → softmax', '各≈ 0.01'],
    ]},
    { name: 'B. inertia', color: C.mid, rows: [
      ['current_verb = "賣咖啡"', '', ''],
      ['賣咖啡→賣咖啡 count=2', 'log(2)≈0.693', '≈ 0.45'],
      ['其他 count=1', 'log(1)=0', '≈ 0.028各'],
    ]},
    { name: 'C. situation', color: C.acc, rows: [
      ['賣咖啡', '命中「客人」「咖啡」→+0.30', '≈ 0.38'],
      ['收銀', '命中「客人」→+0.15', '≈ 0.28'],
      ['對話', '無同地點角色→+0', '≈ 0.02'],
    ]},
    { name: 'D. value (δ=0)', color: 'E17055', rows: [
      ['無action_values記錄', '均勻分布', '無效'],
      ['δ = 0.0', '不參與合併', '—'],
    ]},
  ];

  sources.forEach((src, si) => {
    const x = 0.4 + (si%2)*6.4;
    const y = 3.25 + Math.floor(si/2)*2.0;
    s.addShape(pptx.ShapeType.rect, { x, y, w: 6.1, h: 1.85,
      fill: { color: src.color, transparency: 92 }, line: { color: src.color, width: 1.5 } });
    s.addText(src.name, { x: x+0.1, y: y+0.03, w: 5.9, h: 0.33, fontSize: 12, bold: true, color: src.color });
    src.rows.forEach((row, ri) => {
      s.addText(row[0], { x: x+0.1, y: y+0.4+ri*0.4, w: 2.8, h: 0.36, fontSize: 10.5, color: C.text });
      s.addText(row[1], { x: x+2.95, y: y+0.4+ri*0.4, w: 2.1, h: 0.36, fontSize: 10, color: C.sub });
      s.addText(row[2], { x: x+5.1, y: y+0.4+ri*0.4, w: 0.95, h: 0.36, fontSize: 11, bold: true, color: src.color });
    });
  });

  // Summary box
  s.addShape(pptx.ShapeType.rect, { x: 6.7, y: 0.82, w: 6.6, h: 2.3,
    fill: { color: C.dark, transparency: 8 }, line: { color: C.yel, width: 2 } });
  s.addText('最終合併（α=0.4, β=0.3, γ=0.3, δ=0）', { x: 6.85, y: 0.85, w: 6.3, h: 0.35, fontSize: 12, bold: true, color: C.yel });
  const finals = [
    '賣咖啡：0.4×0.62 + 0.3×0.45 + 0.3×0.38 = 0.248+0.135+0.114 = 0.497',
    '收 銀：0.4×0.09 + 0.3×0.028 + 0.3×0.28 ≈ 0.036+0.008+0.084 = 0.128',
    '對 話：0.4×0.01 + 0.3×0.028 + 0.3×0.00 ≈ 0.004+0.008+0 = 0.012',
    '睡 覺：08:30 屬工作時段，ts=-1.5，scale≈0.05 → 大幅壓制',
    '正規化後 TOP：賣咖啡≈0.507, 收銀≈0.131, 補貨≈0.082...',
  ];
  finals.forEach((ln, i) => {
    s.addText(ln, { x: 6.85, y: 1.25 + i*0.35, w: 6.3, h: 0.32, fontSize: 11, color: i===4 ? C.yel : C.white });
  });
}

// ── Slide 11: Deliberate path — LTM retrieval ─────────────────────────
function slide11() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 3b｜Deliberate 路徑 — LTM 擴散激活 + Phi-3.5 推理', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 22, bold: true, color: C.dark,
  });

  const steps = [
    {
      n: '①', title: 'auto_query_nodes', color: C.mid,
      lines: [
        '組合查詢節點：角色自己 + 對話對象 + 同地點角色 + 當前位置',
        '+ 最近3筆STM中出現的角色名字',
        '範例：["Amy", "Ben", "咖啡廳"]',
      ],
    },
    {
      n: '②', title: 'spreading_retrieve（BFS 擴散激活）', color: '6C5CE7',
      lines: [
        '起始節點活化值 = 1.0',
        'prop_activation_at_hop = activation_decay^(hop-1) = 0.4^(hop-1)',
        'hop=1: activation=1.0   hop=2: activation=0.4',
        '過濾：activation < HAM_RETRIEVE_THRESHOLD(0.3) → 不取',
        'HAM_TRAVERSE_MAX_HOPS = 2  HAM_ACTIVATION_DECAY = 0.4',
        '排序：activation降序，相同則hops升序，取 top_k=20',
      ],
    },
    {
      n: '③', title: 'propositions_to_narrative', color: C.green,
      lines: [
        '將 HAM 5元組轉換為自然語言敘述',
        '範例：{Amy, 遇見, Ben, 咖啡廳, 第3天早上}',
        '→  「你在第3天早上在咖啡廳遇見Ben。」',
        '組成多段 LTM 上下文文字',
      ],
    },
    {
      n: '④', title: 'build_deliberate → 呼叫 Phi-3.5', color: C.acc,
      lines: [
        '組裝完整 prompt：角色設定 + LTM敘述 + STM最近5筆',
        '+ 困惑度數值 + 當前情境 + 問題',
        'max_tokens 依場景設定（通常200-500）',
        '輸出：action + target + content + thought',
      ],
    },
  ];

  steps.forEach((step, si) => {
    const y = 0.82 + si * 1.65;
    s.addShape(pptx.ShapeType.rect, { x: 0.4, y, w: 12.9, h: 1.55,
      fill: { color: step.color, transparency: 90 }, line: { color: step.color, width: 1.5 } });
    s.addText(`${step.n} ${step.title}`, { x: 0.55, y: y+0.05, w: 12.6, h: 0.38, fontSize: 13, bold: true, color: step.color });
    step.lines.forEach((ln, li) => {
      s.addText(ln, { x: 0.7, y: y+0.47+li*0.3, w: 12.4, h: 0.28, fontSize: 11, color: C.text });
    });
  });
}

slide6();
slide7();
slide8();
slide9();
slide10();
slide11();

const outPath = 'C:/Users/Rayyu/Desktop/agi/presentation/AI-Town-main/AI-Town-main/reports/AI-Town_complete_flows_part2.pptx';
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log('Part 2 done: slides 6-11 written to', outPath);
}).catch(e => { console.error(e); process.exit(1); });
