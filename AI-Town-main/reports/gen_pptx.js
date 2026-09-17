const PptxGenJS = require('C:/Users/Rayyu/AppData/Roaming/npm/node_modules/pptxgenjs/dist/pptxgen.cjs.js');
const pptx = new PptxGenJS();

// ── Layout ──────────────────────────────────────────────────────────
pptx.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5 inches

// ── Theme colors ──────────────────────────────────────────────────
const C = {
  bg:    'F8F9FA',
  dark:  '1A1A2E',
  blue:  '16213E',
  mid:   '0F3460',
  acc:   'E94560',
  text:  '2D3436',
  sub:   '636E72',
  white: 'FFFFFF',
  code:  'F1F2F6',
  green: '00B894',
  yel:   'FDCB6E',
  gray:  'B2BEC3',
};

function slide1() {
  const s = pptx.addSlide();
  s.background = { color: C.dark };

  s.addText('AI-Town 完整系統流程與模擬', {
    x: 0.5, y: 1.5, w: 12.3, h: 1.2,
    fontSize: 40, bold: true, color: C.white, align: 'center',
  });
  s.addText('從感知到記憶的完整數據追蹤', {
    x: 0.5, y: 2.9, w: 12.3, h: 0.7,
    fontSize: 22, color: C.acc, align: 'center',
  });

  const theories = [
    'Kahneman (2011)  雙歷程理論 — System 1 直覺 / System 2 深思',
    'Tulving (1972)   情節記憶與語意記憶 — STM 敘述 / LTM HAM命題',
    'Anderson & Bower (1973)  HAM — 人類聯想記憶 5元組',
    'Anderson (1983)  擴散激活理論 — 記憶節點 BFS 傳播',
    'Diekelmann & Born (2010)  睡眠鞏固 — STM→LTM 轉移整合',
  ];
  theories.forEach((t, i) => {
    s.addText(t, {
      x: 1.5, y: 4.0 + i * 0.52, w: 10.3, h: 0.46,
      fontSize: 13, color: C.gray, align: 'left',
    });
  });

  s.addText('認知科學理論基礎', {
    x: 1.5, y: 3.6, w: 4, h: 0.36,
    fontSize: 12, color: C.yel, bold: true,
  });
}

function slide2() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('系統架構概覽', {
    x: 0.4, y: 0.2, w: 12.5, h: 0.6,
    fontSize: 28, bold: true, color: C.dark,
  });

  const layers = [
    { label: 'Layer 1  進入層', mods: 'clock.py  agent/manager.py  agent/interrupt.py', color: C.acc },
    { label: 'Layer 2  協調層', mods: 'agent/agent.py  core/mental_state.py', color: C.mid },
    { label: 'Layer 3a 推論層（直覺）', mods: 'core/markov_engine.py  core/tick_value.py', color: C.blue },
    { label: 'Layer 3b 推論層（深思）', mods: 'core/memory_graph.py  model/prompt_builder.py  model/loader.py', color: C.blue },
    { label: 'Layer 4  認知層', mods: 'core/character.py  core/memory_stm.py  core/memory_ltm.py  core/memory_graph.py  core/weight_adapter.py', color: C.green },
    { label: 'Layer 5  模型層', mods: 'model/loader.py  Phi-3.5-Vision-Instruct', color: '6C5CE7' },
    { label: 'Layer 6  感知層', mods: 'observe/yolo_perception.py  observe/scene.py', color: 'E17055' },
    { label: 'Layer 7  觀察層', mods: 'observe/dashboard_html.py  reports/', color: C.sub },
  ];

  layers.forEach((l, i) => {
    s.addShape(pptx.ShapeType.rect, {
      x: 0.3, y: 0.95 + i * 0.75, w: 12.7, h: 0.66,
      fill: { color: l.color, transparency: 88 },
      line: { color: l.color, width: 2 },
    });
    s.addText(l.label, {
      x: 0.5, y: 0.98 + i * 0.75, w: 3.8, h: 0.6,
      fontSize: 12, bold: true, color: l.color,
    });
    s.addText(l.mods, {
      x: 4.4, y: 0.98 + i * 0.75, w: 8.4, h: 0.6,
      fontSize: 11, color: C.text,
    });
  });
}

function slide3() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 1｜Tick 完整生命週期', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55,
    fontSize: 26, bold: true, color: C.dark,
  });

  const steps = [
    { t: '① Tick T 開始', d: 'clock.py 推進時間，觸發所有角色處理' },
    { t: '② 時鐘檢查', d: 'force_wake（起床時間）/ force_sleep（23:00後）判斷' },
    { t: '③ 感知層更新', d: 'YOLO偵測場景 → yolo_desc更新，interrupt_queue排入事件' },
    { t: '④ 中斷處理', d: 'interrupt.py 評估事件強度 vs 行動鎖等級（0/1/2）' },
    { t: '⑤ Phase 1 執行', d: 'pending_action執行（對話/一般/多tick行動） → 寫STM turn' },
    { t: '⑥ Phase 2 決策', d: '計算困惑度C → 選路徑（intuitive/deliberate） → 設定下一pending_action → 寫STM' },
    { t: '⑦ STM 安全閥', d: 'STM turns > 50 → 觸發中途濃縮（midday consolidation）' },
    { t: '⑧ Tick T+1', d: '時鐘推進，回到①' },
  ];

  steps.forEach((step, i) => {
    const y = 0.85 + i * 0.75;
    s.addShape(pptx.ShapeType.rect, {
      x: 0.3, y, w: 3.2, h: 0.62,
      fill: { color: C.mid, transparency: 85 },
      line: { color: C.mid, width: 1.5 },
    });
    s.addText(step.t, { x: 0.35, y: y + 0.04, w: 3.1, h: 0.55, fontSize: 12, bold: true, color: C.mid });
    s.addText(step.d, { x: 3.7, y: y + 0.04, w: 9.3, h: 0.55, fontSize: 12, color: C.text });
    if (i < steps.length - 1) {
      s.addText('▼', { x: 1.7, y: y + 0.64, w: 0.5, h: 0.2, fontSize: 10, color: C.gray, align: 'center' });
    }
  });

  s.addText('行動鎖等級：等級2（不可中斷）= 對話、睡覺 ｜ 等級1（重要）= 賣咖啡、工作 ｜ 等級0（容易中斷）= 前往、散步、滑手機', {
    x: 0.3, y: 7.1, w: 12.7, h: 0.3,
    fontSize: 10, color: C.sub, italic: true,
  });
}

function slide4() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 2｜困惑度計算 — 公式與參數來源', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55,
    fontSize: 24, bold: true, color: C.dark,
  });

  // Main formula
  s.addShape(pptx.ShapeType.rect, {
    x: 0.4, y: 0.82, w: 12.5, h: 0.7,
    fill: { color: C.dark, transparency: 5 },
    line: { color: C.acc, width: 2 },
  });
  s.addText('C = w1·U + w2·K + w3·S    （w1=0.4, w2=0.3, w3=0.3）    來源：mental_state.py → compute_C()', {
    x: 0.5, y: 0.86, w: 12.3, h: 0.6,
    fontSize: 15, bold: true, color: C.white, align: 'center',
  });

  const cols = [
    {
      title: 'U — 不確定性', color: C.green,
      lines: [
        '來源：Markov機率分布前兩名差距',
        'gap = prob_rank1 − prob_rank2',
        'U = max(0.0, 1.0 − gap × 2.0)',
        '範圍：0.0（確定）~ 1.0（不確定）',
        '範例：gap=0.25 → U=0.50',
        '       gap=0.05 → U=0.90',
        '       gap≥0.5  → U=0.0',
      ],
    },
    {
      title: 'K — 衝突程度', color: C.acc,
      lines: [
        '來源：YOLO + 對話 + 行動 + 場景',
        '邏輯衝突pair命中：+0.60',
        '  （如「離開/走了」+正在「工作」）',
        '強情緒關鍵字命中：+0.45',
        '  （混亂、不知所措、思緒紊亂）',
        '一般情緒關鍵字命中：+0.25',
        '  （心跳、暗戀、告白、情緒複雜）',
        'K上限：1.0',
        'K ≥ 0.5 → 強制 deliberate',
      ],
    },
    {
      title: 'S — 驚訝程度', color: '6C5CE7',
      lines: [
        '來源：scene_text vs LTM預期',
        'LTM為空（第一天）→ S=0.0',
        '陌生人/從沒見過：+0.60',
        '第一次/從未：+0.50',
        '意外/沒想到/不可思議：+0.35',
        '突然：+0.25',
        'S上限：1.0',
      ],
    },
  ];

  cols.forEach((col, ci) => {
    const x = 0.4 + ci * 4.3;
    s.addShape(pptx.ShapeType.rect, {
      x, y: 1.65, w: 4.1, h: 5.55,
      fill: { color: col.color, transparency: 90 },
      line: { color: col.color, width: 2 },
    });
    s.addText(col.title, { x: x + 0.1, y: 1.68, w: 3.9, h: 0.42, fontSize: 14, bold: true, color: col.color });
    col.lines.forEach((ln, li) => {
      s.addText(ln, { x: x + 0.15, y: 2.18 + li * 0.52, w: 3.8, h: 0.48, fontSize: 11.5, color: C.text });
    });
  });
}

function slide5() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 2｜情緒調整閾值 + 模式決策邏輯', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55,
    fontSize: 24, bold: true, color: C.dark,
  });

  // Emotion table
  s.addText('情緒對困惑度閾值的調整（adjust_threshold_by_emotion）', {
    x: 0.4, y: 0.82, w: 8, h: 0.4,
    fontSize: 14, bold: true, color: C.mid,
  });
  s.addText('設計邏輯：心情差時容易直覺反應，更難深思', {
    x: 0.4, y: 1.18, w: 8, h: 0.32,
    fontSize: 12, color: C.sub, italic: true,
  });

  const emotions = [
    { emo: '平靜', adj: '+0.00', final: '0.45（Amy基礎）', c: C.green },
    { emo: '開心', adj: '+0.00', final: '0.45', c: C.green },
    { emo: '興奮', adj: '+0.00', final: '0.45', c: C.green },
    { emo: '緊張', adj: '+0.10', final: '0.55', c: C.yel },
    { emo: '不安', adj: '+0.10', final: '0.55', c: C.yel },
    { emo: '困惑', adj: '+0.10', final: '0.55', c: C.yel },
    { emo: '難過', adj: '+0.15', final: '0.60', c: C.acc },
    { emo: '疲憊', adj: '+0.15', final: '0.60', c: C.acc },
  ];

  const headers = ['情緒', '閾值調整', 'Amy最終閾值'];
  headers.forEach((h, hi) => {
    s.addText(h, {
      x: 0.4 + hi * 2.5, y: 1.58, w: 2.4, h: 0.36,
      fontSize: 12, bold: true, color: C.white,
      fill: { color: C.mid },
    });
  });
  emotions.forEach((e, ei) => {
    s.addText(e.emo, { x: 0.4, y: 2.0 + ei * 0.44, w: 2.4, h: 0.4, fontSize: 12, color: e.c, bold: true });
    s.addText(e.adj, { x: 2.9, y: 2.0 + ei * 0.44, w: 2.4, h: 0.4, fontSize: 12, color: C.text });
    s.addText(e.final, { x: 5.4, y: 2.0 + ei * 0.44, w: 2.4, h: 0.4, fontSize: 12, color: C.text });
  });

  // Decision logic
  s.addText('模式決策邏輯（decide_mode 函式）', {
    x: 8.5, y: 0.82, w: 4.7, h: 0.4,
    fontSize: 14, bold: true, color: C.mid,
  });

  const decisions = [
    { cond: '條件 1', rule: 'K ≥ 0.50', result: '→ 強制 deliberate', note: '（不看C值，情緒衝突 override）', c: C.acc },
    { cond: '條件 2', rule: 'C ≥ 最終閾值', result: '→ deliberate', note: '（呼叫 Phi-3.5 模型推理）', c: C.mid },
    { cond: '條件 3', rule: 'C < 最終閾值', result: '→ intuitive', note: '（走 Markov 機率路徑）', c: C.green },
  ];

  decisions.forEach((d, di) => {
    s.addShape(pptx.ShapeType.rect, {
      x: 8.5, y: 1.35 + di * 1.2, w: 4.7, h: 1.05,
      fill: { color: d.c, transparency: 88 },
      line: { color: d.c, width: 2 },
    });
    s.addText(d.cond, { x: 8.65, y: 1.37 + di * 1.2, w: 4.4, h: 0.3, fontSize: 10, color: d.c, bold: true });
    s.addText(d.rule, { x: 8.65, y: 1.67 + di * 1.2, w: 4.4, h: 0.3, fontSize: 13, color: C.dark, bold: true });
    s.addText(d.result + '  ' + d.note, { x: 8.65, y: 1.97 + di * 1.2, w: 4.4, h: 0.35, fontSize: 11, color: C.text });
  });

  s.addText('Amy 角色設定：困惑閾值基礎值 = 0.45　　Ben：0.60　　Claire：0.35　　David：0.55　　Emma：0.50', {
    x: 0.4, y: 5.65, w: 12.5, h: 0.35,
    fontSize: 11, color: C.sub,
  });

  s.addText('DELIBERATE_K_OVERRIDE = 0.5  （來源：mental_state.py）', {
    x: 0.4, y: 6.1, w: 12.5, h: 0.3,
    fontSize: 11, color: C.sub, italic: true,
  });
}

slide1();
slide2();
slide3();
slide4();
slide5();

// Placeholder for more slides - will be added in next part
const outPath = 'C:/Users/Rayyu/Desktop/agi/presentation/AI-Town-main/AI-Town-main/reports/AI-Town_complete_flows_part1.pptx';
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log('Part 1 done: slides 1-5 written to', outPath);
}).catch(e => { console.error(e); process.exit(1); });
