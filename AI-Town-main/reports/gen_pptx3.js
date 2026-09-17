const PptxGenJS = require('C:/Users/Rayyu/AppData/Roaming/npm/node_modules/pptxgenjs/dist/pptxgen.cjs.js');
const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE';

const C = {
  bg: 'F8F9FA', dark: '1A1A2E', blue: '16213E', mid: '0F3460',
  acc: 'E94560', text: '2D3436', sub: '636E72', white: 'FFFFFF',
  code: 'F1F2F6', green: '00B894', yel: 'FDCB6E', gray: 'B2BEC3',
};

// ── Slide 12: STM structure ───────────────────────────────────────────
function slide12() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 4｜短期記憶（STM）— 三層情節結構', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  // Structure diagram
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 7.2, h: 4.8,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('STM Turn 結構（一筆記錄）', { x: 0.55, y: 0.85, w: 7.0, h: 0.38, fontSize: 13, bold: true, color: C.mid });
  s.addText('turn_id 格式：D001_T003  （第1天第3個turn）\n摘要turn：D002_T000（T000保留給昨日摘要）', {
    x: 0.55, y: 1.28, w: 7.0, h: 0.55, fontSize: 11, color: C.sub,
  });

  const layers = [
    { name: 'perception', color: C.green, fields: [
      'location    → 當前地點',
      'yolo_desc   → YOLO偵測描述',
      'scene_text  → 場景文字描述',
    ]},
    { name: 'event', color: C.acc, fields: [
      'input_text  → 接收的對話/事件',
      'action      → 執行的行動動詞',
      'target      → 對象角色',
      'content     → 對話內容',
    ]},
    { name: 'inner', color: '6C5CE7', fields: [
      'thought  → 內心想法',
      'emotion  → 當前情緒',
    ]},
  ];

  let yy = 1.9;
  layers.forEach(layer => {
    s.addShape(pptx.ShapeType.rect, { x: 0.55, y: yy, w: 6.9, h: 0.32,
      fill: { color: layer.color, transparency: 70 } });
    s.addText(layer.name, { x: 0.65, y: yy+0.02, w: 6.8, h: 0.28, fontSize: 12, bold: true, color: C.white });
    yy += 0.35;
    layer.fields.forEach(f => {
      s.addText(f, { x: 0.8, y: yy, w: 6.7, h: 0.3, fontSize: 11, color: C.text });
      yy += 0.32;
    });
    yy += 0.1;
  });

  // Config & methods
  s.addShape(pptx.ShapeType.rect, { x: 7.8, y: 0.82, w: 5.5, h: 2.5,
    fill: { color: C.green, transparency: 90 }, line: { color: C.green, width: 1.5 } });
  s.addText('關鍵參數', { x: 7.95, y: 0.85, w: 5.2, h: 0.35, fontSize: 13, bold: true, color: C.green });
  const params = [
    'STM_SAFETY_LIMIT = 50（超過觸發中途濃縮）',
    'STM_KEEP_AFTER_CONS = 5（睡眠後保留最近5筆）',
    '安全閥觸發：midday consolidation（中途濃縮）',
  ];
  params.forEach((p, pi) => {
    s.addText(p, { x: 7.95, y: 1.28+pi*0.42, w: 5.2, h: 0.38, fontSize: 11.5, color: C.text });
  });

  s.addShape(pptx.ShapeType.rect, { x: 7.8, y: 3.45, w: 5.5, h: 2.2,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('主要方法', { x: 7.95, y: 3.48, w: 5.2, h: 0.35, fontSize: 13, bold: true, color: C.mid });
  const methods = [
    'add_turn()  — 寫入一筆3層記錄',
    'get_today_narrative()  — 輸出敘述化文字',
    'get_recent_actions(n)  — 取最近n筆行動（給inertia）',
    'shrink_to_summary()  — 睡眠後縮減STM',
    'is_over_safety_limit()  — 安全閥檢查',
  ];
  methods.forEach((m, mi) => {
    s.addText(m, { x: 7.95, y: 3.9+mi*0.35, w: 5.2, h: 0.32, fontSize: 11, color: C.text });
  });

  // Narrative example
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 5.75, w: 12.9, h: 1.5,
    fill: { color: C.code }, line: { color: C.gray, width: 1 } });
  s.addText('敘述化輸出範例（_turn_to_narrative）', { x: 0.55, y: 5.78, w: 12.6, h: 0.3, fontSize: 11, bold: true, color: C.dark });
  s.addText('[08:00] 在咖啡廳，看到2個人、1個杯子。  聽到：Ben對你說：早安。  對Ben說：「早安，今天想喝什麼？」  內心想：Ben看起來心情不錯（情緒：平靜）', {
    x: 0.55, y: 6.12, w: 12.6, h: 0.55, fontSize: 11, color: C.text,
  });
}

// ── Slide 13: LTM — HAM structure + decay ────────────────────────────
function slide13() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 4｜長期記憶（LTM）— HAM 5元組 + 衰減機制', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  // HAM structure
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 6.2, h: 4.5,
    fill: { color: '6C5CE7', transparency: 90 }, line: { color: '6C5CE7', width: 1.5 } });
  s.addText('HAM 5元組結構（Human Associative Memory）', { x: 0.55, y: 0.85, w: 6.0, h: 0.35, fontSize: 12, bold: true, color: '6C5CE7' });
  s.addText('理論基礎：Anderson & Bower (1973)', { x: 0.55, y: 1.23, w: 6.0, h: 0.3, fontSize: 10.5, color: C.sub, italic: true });

  const fields = [
    { f: 'id', v: '"L001"  — 唯一識別碼' },
    { f: 'subject', v: '"Amy"  — 主語' },
    { f: 'relation', v: '"遇見"  — 關係/動詞' },
    { f: 'object', v: '"Ben"  — 受語' },
    { f: 'location', v: '"咖啡廳"  — 地點上下文' },
    { f: 'time', v: '"第3天 早上"  — 時間上下文' },
    { f: 'strength', v: '1.0  — 記憶強度（0.0~1.0）' },
    { f: 'access_count', v: '0  — 被提取次數' },
    { f: 'encoded_day', v: '3  — 寫入的天數' },
  ];
  fields.forEach((f, fi) => {
    s.addText(f.f + ':', { x: 0.65, y: 1.6+fi*0.38, w: 1.6, h: 0.35, fontSize: 11, bold: true, color: '6C5CE7' });
    s.addText(f.v, { x: 2.3, y: 1.6+fi*0.38, w: 4.2, h: 0.35, fontSize: 11, color: C.text });
  });

  // Decay mechanism
  s.addShape(pptx.ShapeType.rect, { x: 6.8, y: 0.82, w: 6.5, h: 3.2,
    fill: { color: C.acc, transparency: 90 }, line: { color: C.acc, width: 1.5 } });
  s.addText('衰減機制（apply_decay）', { x: 6.95, y: 0.85, w: 6.2, h: 0.35, fontSize: 13, bold: true, color: C.acc });
  s.addText('公式：actual_decay = LTM_DECAY_RATE / (1 + access_count × 0.5)', {
    x: 6.95, y: 1.25, w: 6.2, h: 0.32, fontSize: 12, bold: true, color: C.dark,
  });
  s.addText('LTM_DECAY_RATE = 0.05（每天）', { x: 6.95, y: 1.62, w: 6.2, h: 0.28, fontSize: 11, color: C.sub });

  const decayRows = [
    ['access_count', 'actual_decay/天', '說明'],
    ['0', '0.05 / 1.0 = 0.050', '未被使用，正常衰減'],
    ['2', '0.05 / 2.0 = 0.025', '提取2次，衰減減半'],
    ['10', '0.05 / 6.0 ≈ 0.008', '常用記憶，幾乎不衰減'],
  ];
  decayRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      s.addText(cell, {
        x: 6.95 + ci*2.1, y: 1.98+ri*0.42, w: 2.0, h: 0.38,
        fontSize: 11, bold: ri===0, color: ri===0 ? C.acc : (ri===3 ? C.green : C.text),
      });
    });
  });

  // touch & prune
  s.addShape(pptx.ShapeType.rect, { x: 6.8, y: 4.15, w: 6.5, h: 2.15,
    fill: { color: C.green, transparency: 90 }, line: { color: C.green, width: 1.5 } });
  s.addText('touch() 提取加強 + prune() 遺忘修剪', { x: 6.95, y: 4.18, w: 6.2, h: 0.35, fontSize: 13, bold: true, color: C.green });
  const methods = [
    'touch()：被 spreading_retrieve 命中時呼叫',
    '  → access_count += 1',
    '  → strength 重置為 1.0（記憶強化）',
    'prune()：每天睡眠後執行',
    '  → strength < LTM_FORGET_THRESHOLD(0.2) → 刪除',
    '  → 效果：久未使用的記憶自然消失',
  ];
  methods.forEach((m, mi) => {
    s.addText(m, { x: 6.95, y: 4.6+mi*0.3, w: 6.2, h: 0.28, fontSize: 11, color: C.text });
  });

  // Days until forget
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 5.45, w: 6.2, h: 1.3,
    fill: { color: C.yel, transparency: 85 }, line: { color: C.yel, width: 1 } });
  s.addText('記憶存活天數估算（未被提取）', { x: 0.55, y: 5.48, w: 6.0, h: 0.3, fontSize: 11, bold: true, color: C.dark });
  s.addText('strength從1.0開始，每天減0.05\n→ 到 strength=0.2 需要 (1.0-0.2)/0.05 = 16 天後自動刪除', {
    x: 0.55, y: 5.82, w: 6.0, h: 0.55, fontSize: 11, color: C.text,
  });
}

// ── Slide 14: Spreading activation ───────────────────────────────────
function slide14() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 4｜擴散激活（Spreading Activation）— BFS 記憶檢索', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 22, bold: true, color: C.dark,
  });

  s.addText('理論基礎：Anderson (1983) ACT* — 記憶節點在語意網絡中擴散傳播', {
    x: 0.4, y: 0.75, w: 12.5, h: 0.3, fontSize: 12, color: C.sub, italic: true,
  });

  // Algorithm
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 1.12, w: 7.5, h: 5.4,
    fill: { color: '6C5CE7', transparency: 90 }, line: { color: '6C5CE7', width: 1.5 } });
  s.addText('BFS 擴散激活演算法', { x: 0.55, y: 1.15, w: 7.2, h: 0.38, fontSize: 13, bold: true, color: '6C5CE7' });

  const algoSteps = [
    '① 初始化：起始節點集合（query_nodes 中每個節點 activation=1.0）',
    '② BFS 隊列：queue = [(node, hop=1, activation=1.0)]',
    '③ 每次取出節點：',
    '    prop_activation = activation_decay^(hop-1) = 0.4^(hop-1)',
    '    hop=1: prop_activation = 0.4^0 = 1.0',
    '    hop=2: prop_activation = 0.4^1 = 0.4',
    '④ 過濾條件（同時滿足）：',
    '    a. prop_activation ≥ HAM_RETRIEVE_THRESHOLD = 0.3',
    '    b. hop ≤ HAM_TRAVERSE_MAX_HOPS = 2',
    '    c. 節點未被訪問過',
    '⑤ 加入結果：{proposition, activation, hops}',
    '⑥ 繼續展開：把鄰居節點加入隊列（hop+1）',
    '⑦ 排序：activation 降序，相同則 hops 升序',
    '⑧ 取 top_k = 20 筆返回',
  ];
  algoSteps.forEach((step, si) => {
    s.addText(step, { x: 0.55, y: 1.6+si*0.33, w: 7.3, h: 0.3, fontSize: 11, color: C.text });
  });

  // Key parameters
  s.addShape(pptx.ShapeType.rect, { x: 8.1, y: 1.12, w: 5.2, h: 2.4,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('關鍵參數', { x: 8.25, y: 1.15, w: 4.9, h: 0.38, fontSize: 13, bold: true, color: C.mid });
  const params = [
    ['HAM_TRAVERSE_MAX_HOPS', '= 2'],
    ['HAM_ACTIVATION_DECAY', '= 0.4'],
    ['HAM_RETRIEVE_THRESHOLD', '= 0.3'],
    ['top_k（返回上限）', '= 20'],
  ];
  params.forEach((p, pi) => {
    s.addText(p[0], { x: 8.25, y: 1.6+pi*0.45, w: 3.5, h: 0.4, fontSize: 11, color: C.text });
    s.addText(p[1], { x: 11.8, y: 1.6+pi*0.45, w: 1.4, h: 0.4, fontSize: 12, bold: true, color: C.mid });
  });

  // Example
  s.addShape(pptx.ShapeType.rect, { x: 8.1, y: 3.65, w: 5.2, h: 2.85,
    fill: { color: C.green, transparency: 90 }, line: { color: C.green, width: 1.5 } });
  s.addText('範例（Amy + Ben + 咖啡廳 為起始節點）', { x: 8.25, y: 3.68, w: 4.9, h: 0.38, fontSize: 12, bold: true, color: C.green });
  const exRows = [
    ['命題', 'hop', 'activation'],
    ['Amy 遇見 Ben（咖啡廳）', '1', '1.0 ✓'],
    ['Amy 暗戀 David', '1', '1.0 ✓'],
    ['Ben 送給 Amy 禮物', '2', '0.4 ✓'],
    ['Ben 在 超市 工作', '2', '0.4 ✓'],
    ['David 是 畫家', '3', '0.16 ✗過濾'],
  ];
  exRows.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      s.addText(cell, {
        x: 8.25 + ci*1.7, y: 4.12+ri*0.38, w: 1.65, h: 0.35,
        fontSize: ri===5 && ci===2 ? 10 : 11,
        bold: ri===0,
        color: ri===0 ? C.green : (ri===5 ? C.acc : C.text),
      });
    });
  });
}

// ── Slide 15: RL Value Tracker ────────────────────────────────────────
function slide15() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 3a｜RL 價值追蹤器（ActionValueTracker）', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  // Decay mechanism
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 6.2, h: 2.5,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('價值衰減機制（每 tick 執行）', { x: 0.55, y: 0.85, w: 6.0, h: 0.35, fontSize: 13, bold: true, color: C.mid });
  s.addText('公式：V(a) = V(a) × VALUE_DECAY  （VALUE_DECAY = 0.85）', {
    x: 0.55, y: 1.25, w: 6.0, h: 0.32, fontSize: 12, bold: true, color: C.dark,
  });
  const decayEx = [
    '初始 V(賣咖啡) = 0.50',
    'tick +1: 0.50 × 0.85 = 0.425',
    'tick +2: 0.425 × 0.85 = 0.361',
    'tick +5: 0.50 × 0.85⁵ ≈ 0.222',
    '→ 舊記憶自然淡化，近期行為影響更大',
  ];
  decayEx.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 1.62+i*0.32, w: 6.0, h: 0.28, fontSize: 11, color: C.text });
  });

  // Reward table
  s.addShape(pptx.ShapeType.rect, { x: 6.8, y: 0.82, w: 6.5, h: 4.6,
    fill: { color: C.yel, transparency: 88 }, line: { color: C.yel, width: 1.5 } });
  s.addText('獎勵信號定義（reward constants）', { x: 6.95, y: 0.85, w: 6.2, h: 0.35, fontSize: 13, bold: true, color: C.dark });

  const rewards = [
    { event: '情緒改善（負→正）', r: '+0.50', c: C.green },
    { event: '情緒回歸中性（負→平靜）', r: '+0.15', c: C.green },
    { event: '情緒惡化（正/平靜→負）', r: '−0.45', c: C.acc },
    { event: 'C下降 ≥ 0.12（困惑度降低）', r: '+0.30', c: C.green },
    { event: 'C上升 ≥ 0.15（困惑度飆升）', r: '−0.35', c: C.acc },
    { event: '對話被接受（DIALOGUE_ACCEPT）', r: '+0.25', c: C.green },
    { event: '時間表命中（SCHEDULE_HIT）', r: '+0.20', c: C.green },
  ];
  rewards.forEach((rw, ri) => {
    s.addText(rw.event, { x: 6.95, y: 1.3+ri*0.47, w: 4.8, h: 0.43, fontSize: 11.5, color: C.text });
    s.addText(rw.r, { x: 12.0, y: 1.3+ri*0.47, w: 1.2, h: 0.43, fontSize: 13, bold: true, color: rw.c, align: 'right' });
  });

  // Q-value update
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 3.45, w: 6.2, h: 2.2,
    fill: { color: C.green, transparency: 90 }, line: { color: C.green, width: 1.5 } });
  s.addText('Q值更新機制（類 Q-learning + Eligibility Trace）', { x: 0.55, y: 3.48, w: 6.0, h: 0.35, fontSize: 12, bold: true, color: C.green });
  const qsteps = [
    '① 每tick結束後計算當前獎勵 r',
    '② 所有行動的 Q 值 × VALUE_DECAY（衰減）',
    '③ Q(chosen_action) += r（當前行動加獎勵）',
    '④ Markov delta分支使用 get_scores() 作為 P_value',
    '⑤ 效果：好行動累積正值，壞行動累積負值',
    '   類似 Q(s,a) ← Q(s,a) + α[r - Q(s,a)]',
  ];
  qsteps.forEach((q, qi) => {
    s.addText(q, { x: 0.55, y: 3.88+qi*0.3, w: 6.0, h: 0.28, fontSize: 11, color: C.text });
  });

  // Example simulation
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 5.75, w: 12.9, h: 1.45,
    fill: { color: C.code }, line: { color: C.gray, width: 1 } });
  s.addText('模擬範例：Amy 告白事件後', { x: 0.55, y: 5.78, w: 12.6, h: 0.3, fontSize: 11, bold: true, color: C.dark });
  s.addText('情緒：平靜→緊張（惡化）→ reward=-0.45   C上升0.22≥0.15 → reward=-0.35   合計reward=-0.80\n→ Q(休息) += -0.80  →  下一tick休息的機率（delta分支）降低，Markov更傾向對話或前往', {
    x: 0.55, y: 6.12, w: 12.6, h: 0.55, fontSize: 11, color: C.text,
  });
}

// ── Slide 16: Weight Adapter ──────────────────────────────────────────
function slide16() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 4｜Weight Adapter — 每日 SGD-like 自適應學習', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  // Default weights
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 5.5, h: 1.9,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('初始預設權重', { x: 0.55, y: 0.85, w: 5.2, h: 0.35, fontSize: 13, bold: true, color: C.mid });
  const defaults = [
    ['α (schedule)', '0.40'],
    ['β (inertia)', '0.30'],
    ['γ (situation)', '0.20'],
    ['δ (value)', '0.10'],
  ];
  defaults.forEach((d, di) => {
    s.addText(d[0], { x: 0.55, y: 1.28+di*0.34, w: 3.5, h: 0.3, fontSize: 12, color: C.text });
    s.addText(d[1], { x: 4.2, y: 1.28+di*0.34, w: 1.5, h: 0.3, fontSize: 13, bold: true, color: C.mid });
  });

  // SGD formula
  s.addShape(pptx.ShapeType.rect, { x: 6.1, y: 0.82, w: 7.2, h: 2.8,
    fill: { color: C.dark, transparency: 8 }, line: { color: C.acc, width: 2 } });
  s.addText('SGD-like 更新公式（update_weights，每天睡覺時執行）', { x: 6.25, y: 0.85, w: 7.0, h: 0.35, fontSize: 12, bold: true, color: C.yel });
  s.addText('α += LR × r × (sched_p − α)\nβ += LR × r × (iner_p  − β)\nγ += LR × r × (situ_p  − γ)\nδ += LR × r × (val_p   − δ)\n\nLR = LEARNING_RATE = 0.05\nr = 當日平均reward   sched_p/iner_p/situ_p/val_p = 各來源在該tick的機率', {
    x: 6.25, y: 1.25, w: 6.9, h: 2.2, fontSize: 12, color: C.white,
  });

  // Clip + normalize
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 2.85, w: 5.5, h: 2.2,
    fill: { color: C.green, transparency: 90 }, line: { color: C.green, width: 1.5 } });
  s.addText('後處理', { x: 0.55, y: 2.88, w: 5.2, h: 0.35, fontSize: 13, bold: true, color: C.green });
  const post = [
    '① Clip：每個權重 clamp 到 [0.05, 0.85]',
    '   MIN_WEIGHT = 0.05   MAX_WEIGHT = 0.85',
    '② 正規化：total = α+β+γ+δ',
    '   每個權重 /= total（總和=1）',
    '③ 浮點修正：餘差加回 α（確保精確=1.0）',
  ];
  post.forEach((p, pi) => {
    s.addText(p, { x: 0.55, y: 3.3+pi*0.35, w: 5.2, h: 0.32, fontSize: 11, color: C.text });
  });

  // Simulation
  s.addShape(pptx.ShapeType.rect, { x: 6.1, y: 3.75, w: 7.2, h: 3.5,
    fill: { color: C.code }, line: { color: C.gray, width: 1 } });
  s.addText('模擬範例：Amy 第3天學習後的權重更新', { x: 6.25, y: 3.78, w: 7.0, h: 0.35, fontSize: 12, bold: true, color: C.dark });
  const simRows = [
    '初始：α=0.40, β=0.30, γ=0.20, δ=0.10',
    '',
    '當日記錄（3 ticks）：',
    'tick1: r=+0.20, sched_p=0.62, iner_p=0.45, situ_p=0.38, val_p=0',
    'tick2: r=-0.45, sched_p=0.30, iner_p=0.35, situ_p=0.55, val_p=0',
    'tick3: r=+0.25, sched_p=0.50, iner_p=0.40, situ_p=0.42, val_p=0.2',
    '',
    '更新後（clip+正規化）→ α≈0.39, β≈0.30, γ≈0.21, δ≈0.10',
    '→ Amy 略微增加對「情境」的依賴（γ上升）',
  ];
  simRows.forEach((ln, i) => {
    s.addText(ln, { x: 6.25, y: 4.2+i*0.33, w: 7.0, h: 0.3, fontSize: 11, color: C.text });
  });
}

// ── Slide 17: Sleep consolidation ────────────────────────────────────
function slide17() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('Layer 4｜睡眠鞏固 12 步驟（consolidation.py）', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });
  s.addText('理論基礎：Diekelmann & Born (2010) — 睡眠不清空記憶，而是「轉移與整合」STM→LTM', {
    x: 0.4, y: 0.73, w: 12.5, h: 0.3, fontSize: 11, color: C.sub, italic: true,
  });

  const steps12 = [
    { n: '①', title: '取出今日STM敘述', detail: 'stm.get_today_narrative() → narrative文字', c: C.mid },
    { n: '②', title: '抽取HAM 5元組', detail: 'prompt_extract_ham(narrative)，Phi-3.5，max_tokens=500 → HAM列表', c: C.mid },
    { n: '③', title: '篩選重要HAM', detail: 'prompt_select_ltm，max_tokens=200，最多5筆寫入LTM', c: C.mid },
    { n: '④', title: '寫入LTM', detail: 'ltm.encode_batch(selected_hams) → 新增節點+邊到MemoryGraph', c: '6C5CE7' },
    { n: '⑤', title: '更新LTM摘要', detail: '模型生成新摘要，max_tokens=80，上限200字', c: '6C5CE7' },
    { n: '⑥', title: '更新關係摘要', detail: '找出narrative中出現的角色，模型更新各對關係描述，max_tokens=80', c: '6C5CE7' },
    { n: '⑦', title: '情緒判斷', detail: 'today_max_K<0.5→直接平靜；≥0.5→模型推斷，max_tokens=10', c: C.acc },
    { n: '⑧', title: '生成隔天時間表', detail: '職業範本+LTM摘要，模型生成，max_tokens=500', c: C.acc },
    { n: '⑨', title: '時間表規則檢查', detail: '確認必要時段（睡覺/起床）、時間順序正確', c: C.acc },
    { n: '⑩', title: 'LTM衰減+修剪', detail: 'apply_decay() 全體衰減；prune() 刪除 strength<0.2', c: C.green },
    { n: '⑪', title: 'STM縮減', detail: 'shrink_to_summary()：保留摘要turn + 最近5筆（STM_KEEP_AFTER_CONS=5）', c: C.green },
    { n: '⑫', title: '更新權重+推進天數', detail: 'weight_adapter.update_weights()；character.advance_day()', c: C.green },
  ];

  const leftSteps = steps12.slice(0, 6);
  const rightSteps = steps12.slice(6, 12);

  [[leftSteps, 0.4], [rightSteps, 6.75]].forEach(([steps, xBase]) => {
    steps.forEach((step, si) => {
      const y = 1.12 + si * 1.02;
      s.addShape(pptx.ShapeType.rect, { x: xBase, y, w: 6.15, h: 0.9,
        fill: { color: step.c, transparency: 88 }, line: { color: step.c, width: 1.5 } });
      s.addText(`${step.n} ${step.title}`, { x: xBase+0.1, y: y+0.05, w: 6.0, h: 0.34, fontSize: 12, bold: true, color: step.c });
      s.addText(step.detail, { x: xBase+0.15, y: y+0.42, w: 5.9, h: 0.4, fontSize: 11, color: C.text });
    });
  });
}

slide12();
slide13();
slide14();
slide15();
slide16();
slide17();

const outPath = 'C:/Users/Rayyu/Desktop/agi/presentation/AI-Town-main/AI-Town-main/reports/AI-Town_complete_flows_part3.pptx';
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log('Part 3 done: slides 12-17 written to', outPath);
}).catch(e => { console.error(e); process.exit(1); });
