const PptxGenJS = require('C:/Users/Rayyu/AppData/Roaming/npm/node_modules/pptxgenjs/dist/pptxgen.cjs.js');
const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE';

const C = {
  bg: 'F8F9FA', dark: '1A1A2E', blue: '16213E', mid: '0F3460',
  acc: 'E94560', text: '2D3436', sub: '636E72', white: 'FFFFFF',
  code: 'F1F2F6', green: '00B894', yel: 'FDCB6E', gray: 'B2BEC3',
};

// ── Slide 18: Dialogue system ─────────────────────────────────────────
function slide18() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('對話系統（Dialogue Flow）— 接受/拒絕機率計算', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 24, bold: true, color: C.dark,
  });

  // Accept probability
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.82, w: 7.5, h: 3.5,
    fill: { color: C.mid, transparency: 90 }, line: { color: C.mid, width: 1.5 } });
  s.addText('對話接受機率公式', { x: 0.55, y: 0.85, w: 7.2, h: 0.35, fontSize: 13, bold: true, color: C.mid });
  s.addText('P_accept = base + relation_bonus + leisure_bonus + work_penalty', {
    x: 0.55, y: 1.28, w: 7.2, h: 0.32, fontSize: 13, bold: true, color: C.dark,
  });

  const terms = [
    { term: 'DIALOGUE_BASE_ACCEPT', val: '= 0.50', desc: '基礎接受機率（任何人都有50%接受）' },
    { term: 'DIALOGUE_RELATION_BONUS', val: '= +0.30', desc: '好感關係加成（認識的人）' },
    { term: 'DIALOGUE_LEISURE_BONUS', val: '= +0.20', desc: '休閒時間加成（不忙碌時）' },
    { term: 'DIALOGUE_WORK_PENALTY', val: '= −0.30', desc: '工作時間懲罰（忙碌中被打擾）' },
  ];
  terms.forEach((t, ti) => {
    s.addText(t.term, { x: 0.55, y: 1.7+ti*0.47, w: 3.4, h: 0.42, fontSize: 11, bold: true, color: C.mid });
    s.addText(t.val, { x: 3.95, y: 1.7+ti*0.47, w: 1.2, h: 0.42, fontSize: 12, bold: true, color: ti===3 ? C.acc : C.green });
    s.addText(t.desc, { x: 5.2, y: 1.7+ti*0.47, w: 2.6, h: 0.42, fontSize: 10.5, color: C.sub });
  });

  s.addText('DIALOGUE_MAX_TURNS = 10（每段對話最多10回合）', {
    x: 0.55, y: 3.63, w: 7.2, h: 0.3, fontSize: 11, color: C.sub,
  });

  // Examples
  s.addShape(pptx.ShapeType.rect, { x: 8.1, y: 0.82, w: 5.2, h: 3.5,
    fill: { color: C.yel, transparency: 85 }, line: { color: C.yel, width: 1.5 } });
  s.addText('計算範例', { x: 8.25, y: 0.85, w: 4.9, h: 0.35, fontSize: 13, bold: true, color: C.dark });
  const exs = [
    { scenario: 'Ben找Amy（休閒，有好感）', calc: '0.50 + 0.30 + 0.20 = 1.00', note: '必然接受' },
    { scenario: 'Ben找Amy（工作中，有好感）', calc: '0.50 + 0.30 − 0.30 = 0.50', note: '50%接受' },
    { scenario: '陌生人找Amy（休閒）', calc: '0.50 + 0.00 + 0.20 = 0.70', note: '70%接受' },
    { scenario: '陌生人找Amy（工作中）', calc: '0.50 + 0.00 − 0.30 = 0.20', note: '20%接受' },
  ];
  exs.forEach((ex, ei) => {
    s.addShape(pptx.ShapeType.rect, { x: 8.1, y: 1.3+ei*0.74, w: 5.2, h: 0.65,
      fill: { color: C.code } });
    s.addText(ex.scenario, { x: 8.2, y: 1.32+ei*0.74, w: 5.0, h: 0.25, fontSize: 10.5, bold: true, color: C.dark });
    s.addText(ex.calc + '  → ' + ex.note, { x: 8.2, y: 1.57+ei*0.74, w: 5.0, h: 0.25, fontSize: 11, color: C.text });
  });

  // Dialogue flow
  s.addShape(pptx.ShapeType.rect, { x: 0.4, y: 4.45, w: 12.9, h: 2.8,
    fill: { color: C.green, transparency: 90 }, line: { color: C.green, width: 1.5 } });
  s.addText('對話執行流程', { x: 0.55, y: 4.48, w: 12.6, h: 0.35, fontSize: 13, bold: true, color: C.green });
  const dflow = [
    '① 發起方（agent A）Markov採樣得到「對話」→ target = 同地點角色B',
    '② 計算 P_accept，隨機決定 B 是否接受',
    '③ 接受：設定雙方 action_lock=2（不可中斷），對話session開始',
    '④ 每回合：A生成內容（Markov或deliberate）→ STM寫入 → B回應 → STM寫入',
    '⑤ 達到 DIALOGUE_MAX_TURNS=10 或任一方主動結束 → 對話結束，action_lock清零',
    '⑥ 對話結束：reward += DIALOGUE_ACCEPT(+0.25)，寫入ValueTracker',
  ];
  dflow.forEach((ln, i) => {
    s.addText(ln, { x: 0.55, y: 4.9+i*0.35, w: 12.6, h: 0.32, fontSize: 11.5, color: C.text });
  });
}

// ── Slide 19: Complete end-to-end simulation trace ────────────────────
function slide19() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('完整模擬追蹤：Amy 第3天 08:30 一個完整 Tick', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 22, bold: true, color: C.dark,
  });

  const trace = [
    { phase: 'TICK 開始', color: C.mid, lines: [
      '時間：D3 08:30  角色：Amy  地點：咖啡廳',
      '上一tick行動：整理店面  情緒：平靜  當前pending_action：None',
    ]},
    { phase: 'YOLO感知', color: 'E17055', lines: [
      'YOLO偵測：咖啡廳有1個客人、1個杯子、1個咖啡機',
      'yolo_desc更新 → "咖啡廳有1個客人、1個杯子、1個咖啡機"',
      'interrupt_queue：無新事件',
    ]},
    { phase: 'Phase 1 執行', color: C.green, lines: [
      'pending_action = None → 跳過Phase 1',
    ]},
    { phase: 'Phase 2 決策（困惑度計算）', color: C.acc, lines: [
      'U=0.50（上tick賣咖啡0.55 vs 對話0.30，gap=0.25）',
      'K=0.00（無衝突、無情緒關鍵字）',
      'S=0.00（無驚訝關鍵字，且已有LTM）',
      'C = 0.4×0.50 + 0.3×0.00 + 0.3×0.00 = 0.20',
      '情緒平靜 → 最終閾值=0.45    K<0.5且C=0.20<0.45 → intuitive',
    ]},
    { phase: 'Markov 機率計算（intuitive）', color: '6C5CE7', lines: [
      'α=0.40: sched→賣咖啡≈0.62  β=0.30: iner→賣咖啡≈0.45',
      'γ=0.30: situ→賣咖啡≈0.38（客人+咖啡機命中）',
      '合併：0.4×0.62+0.3×0.45+0.3×0.38 = 0.497',
      '睡覺：ts=-1.5→scale≈0.05，被壓制  正規化→賣咖啡≈0.507',
      '採樣結果：賣咖啡（機率最高，加權隨機採樣）',
    ]},
    { phase: 'STM 寫入', color: C.mid, lines: [
      'turn_id: D003_T005  time: "08:30"',
      'perception: {咖啡廳, "1客人1杯子1咖啡機", ""}',
      'event: {input:"", action:"賣咖啡", target:"", content:""}',
      'inner: {thought:"繼續工作，今天客人挺多", emotion:"平靜"}',
    ]},
    { phase: 'RL獎勵計算', color: C.green, lines: [
      '時間表命中賣咖啡 → reward += SCHEDULE_HIT(+0.20)',
      '情緒無變化 → 無情緒獎勵   C變化<0.12 → 無困惑獎勵',
      'ValueTracker.update("賣咖啡", +0.20)  所有行動×VALUE_DECAY(0.85)',
    ]},
  ];

  let yy = 0.82;
  trace.forEach(block => {
    const h = 0.28 * block.lines.length + 0.42;
    s.addShape(pptx.ShapeType.rect, { x: 0.4, y: yy, w: 12.9, h: h,
      fill: { color: block.color, transparency: 92 }, line: { color: block.color, width: 1.5 } });
    s.addText(block.phase, { x: 0.55, y: yy+0.04, w: 12.6, h: 0.3, fontSize: 12, bold: true, color: block.color });
    block.lines.forEach((ln, li) => {
      s.addText(ln, { x: 0.7, y: yy+0.38+li*0.28, w: 12.5, h: 0.26, fontSize: 11, color: C.text });
    });
    yy += h + 0.06;
  });
}

// ── Slide 20: Complete parameter reference ────────────────────────────
function slide20() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('完整參數速查表（config/world_config.py + 各模組）', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 22, bold: true, color: C.dark,
  });

  const sections = [
    { title: 'STM / LTM 記憶', color: '6C5CE7', params: [
      ['STM_SAFETY_LIMIT', '50', 'STM超過觸發中途濃縮'],
      ['STM_KEEP_AFTER_CONS', '5', '睡眠後保留最近N筆'],
      ['LTM_DECAY_RATE', '0.05', '每天LTM衰減速率'],
      ['LTM_FORGET_THRESHOLD', '0.2', '低於此值刪除'],
    ]},
    { title: 'HAM 擴散激活', color: C.mid, params: [
      ['HAM_TRAVERSE_MAX_HOPS', '2', 'BFS最大跳數'],
      ['HAM_ACTIVATION_DECAY', '0.4', '每跳激活衰減率'],
      ['HAM_RETRIEVE_THRESHOLD', '0.3', '激活值低於此不取'],
    ]},
    { title: 'Markov 引擎', color: C.green, params: [
      ['MARKOV_WEIGHTS_NORMAL', 'α:0.4 β:0.3 γ:0.3', '正常模式（δ另計）'],
      ['MARKOV_WEIGHTS_EVENT', 'α:0.1 β:0.3 γ:0.6', 'K≥0.6時事件模式'],
      ['MAJOR_EVENT_K_THRESHOLD', '0.60', '切換事件權重的K門檻'],
      ['MIN_PROB_FLOOR', '0.005', '每行動最低機率保底'],
      ['KEYWORD_BOOST_PER_HIT', '0.15', '情境關鍵字每命中加分'],
    ]},
    { title: 'RL 價值追蹤', color: 'E17055', params: [
      ['VALUE_DECAY', '0.85', '每tick衰減係數'],
      ['REWARD_EMOTION_IMPROVE', '+0.50', '情緒改善獎勵'],
      ['REWARD_EMOTION_WORSEN', '−0.45', '情緒惡化懲罰'],
      ['REWARD_CONFUSION_DROP', '+0.30', 'C下降≥0.12獎勵'],
      ['REWARD_CONFUSION_SPIKE', '−0.35', 'C上升≥0.15懲罰'],
      ['REWARD_DIALOGUE_ACCEPT', '+0.25', '對話接受獎勵'],
      ['REWARD_SCHEDULE_HIT', '+0.20', '時間表命中獎勵'],
    ]},
    { title: '困惑度 / 模式切換', color: C.acc, params: [
      ['C公式', 'w1·U+w2·K+w3·S', 'w1=0.4 w2=0.3 w3=0.3'],
      ['DELIBERATE_K_OVERRIDE', '0.5', 'K≥此值強制deliberate'],
      ['EMOTION_RESET_THRESHOLD', '0.5', 'K峰值≥此才推斷情緒'],
    ]},
    { title: '對話系統', color: C.mid, params: [
      ['DIALOGUE_MAX_TURNS', '10', '每段對話最多回合'],
      ['DIALOGUE_BASE_ACCEPT', '0.50', '基礎接受機率'],
      ['DIALOGUE_RELATION_BONUS', '+0.30', '好感加成'],
      ['DIALOGUE_LEISURE_BONUS', '+0.20', '休閒加成'],
      ['DIALOGUE_WORK_PENALTY', '−0.30', '工作懲罰'],
    ]},
  ];

  const colW = 6.45;
  sections.forEach((sec, si) => {
    const col = si % 2;
    const row = Math.floor(si / 2);
    const x = 0.4 + col * 6.5;
    const h = 0.38 + sec.params.length * 0.38 + 0.1;
    const y = 0.85 + row * (h + 0.15);
    // Avoid overflow
    if (y + h > 7.5) return;
    s.addShape(pptx.ShapeType.rect, { x, y, w: colW, h,
      fill: { color: sec.color, transparency: 90 }, line: { color: sec.color, width: 1.5 } });
    s.addText(sec.title, { x: x+0.1, y: y+0.04, w: colW-0.2, h: 0.32, fontSize: 12, bold: true, color: sec.color });
    sec.params.forEach((p, pi) => {
      s.addText(p[0], { x: x+0.15, y: y+0.42+pi*0.38, w: 2.5, h: 0.34, fontSize: 10.5, bold: true, color: C.text });
      s.addText(p[1], { x: x+2.7, y: y+0.42+pi*0.38, w: 1.4, h: 0.34, fontSize: 11, bold: true, color: sec.color });
      s.addText(p[2], { x: x+4.15, y: y+0.42+pi*0.38, w: 2.2, h: 0.34, fontSize: 10, color: C.sub });
    });
  });
}

// ── Slide 21: Character profiles ──────────────────────────────────────
function slide21() {
  const s = pptx.addSlide();
  s.background = { color: C.bg };

  s.addText('角色設定表 — 5位角色的認知參數', {
    x: 0.4, y: 0.15, w: 12.5, h: 0.55, fontSize: 26, bold: true, color: C.dark,
  });

  const chars = [
    { name: 'Amy', role: '咖啡師', threshold: '0.45', traits: '暗戀David，被Ben追求', base_emotion: '平靜', color: C.acc },
    { name: 'Ben', role: '超市員工', threshold: '0.60', traits: '喜歡Amy，容易直覺行動', base_emotion: '平靜', color: C.green },
    { name: 'Claire', role: '學生', threshold: '0.35', traits: '愛讀書，最容易觸發deliberate', base_emotion: '平靜', color: '6C5CE7' },
    { name: 'David', role: '畫家', threshold: '0.55', traits: '感性，不知Amy暗戀他', base_emotion: '平靜', color: 'E17055' },
    { name: 'Emma', role: '老師', threshold: '0.50', traits: '理性，平衡直覺與深思', base_emotion: '平靜', color: C.mid },
  ];

  const headers = ['角色', '職業', '困惑閾值', '情緒對閾值影響範例', '特殊設定'];
  headers.forEach((h, hi) => {
    s.addText(h, {
      x: 0.4 + [0, 1.6, 3.2, 4.8, 8.8][hi],
      y: 0.88, w: [1.5, 1.5, 1.5, 3.8, 4.2][hi], h: 0.42,
      fontSize: 12, bold: true, color: C.white,
      fill: { color: C.dark },
    });
  });

  chars.forEach((ch, ci) => {
    const y = 1.38 + ci * 1.04;
    s.addShape(pptx.ShapeType.rect, { x: 0.4, y, w: 12.9, h: 0.95,
      fill: { color: ch.color, transparency: 92 }, line: { color: ch.color, width: 1 } });
    s.addText(ch.name, { x: 0.5, y: y+0.05, w: 1.4, h: 0.85, fontSize: 16, bold: true, color: ch.color, valign: 'middle' });
    s.addText(ch.role, { x: 2.1, y: y+0.25, w: 1.4, h: 0.45, fontSize: 12, color: C.text });
    s.addText(ch.threshold, { x: 3.4, y: y+0.1, w: 1.3, h: 0.75, fontSize: 20, bold: true, color: ch.color, valign: 'middle', align: 'center' });
    // Emotion threshold examples
    s.addText(`平靜→${ch.threshold}  緊張→${(parseFloat(ch.threshold)+0.10).toFixed(2)}  難過→${(parseFloat(ch.threshold)+0.15).toFixed(2)}`, {
      x: 4.9, y: y+0.28, w: 3.7, h: 0.38, fontSize: 11, color: C.text,
    });
    s.addText(ch.traits, { x: 8.9, y: y+0.25, w: 4.2, h: 0.45, fontSize: 11, color: C.text });
  });

  s.addText('所有角色情緒基線：「平靜」（BASELINE_EMOTION = "平靜"）\n觸發情緒更新：當天K值峰值 ≥ EMOTION_RESET_THRESHOLD(0.5) → 呼叫模型推斷新情緒', {
    x: 0.4, y: 6.6, w: 12.9, h: 0.65, fontSize: 11, color: C.sub, italic: true,
  });
}

// ── Slide 22: Summary ─────────────────────────────────────────────────
function slide22() {
  const s = pptx.addSlide();
  s.background = { color: C.dark };

  s.addText('AI-Town 系統總結', {
    x: 0.4, y: 0.3, w: 12.5, h: 0.7, fontSize: 34, bold: true, color: C.white, align: 'center',
  });

  const summary = [
    { label: '感知層', desc: 'YOLO → yolo_desc → interrupt_queue → action_lock（0/1/2）', color: 'E17055' },
    { label: '困惑度閘門', desc: 'C=w1U+w2K+w3S → intuitive(Markov) 或 deliberate(Phi-3.5)', color: C.acc },
    { label: 'Markov引擎', desc: '4來源加權（α時間表+β慣性+γ情境+δRL） → softmax → 保底 → 採樣', color: C.green },
    { label: 'RL價值', desc: '每tick衰減0.85 + 7種reward signal → Q值指導delta分支', color: 'E17055' },
    { label: 'Weight Adapter', desc: '每天SGD(LR=0.05)更新α/β/γ/δ → clip[0.05,0.85] → 正規化', color: C.yel },
    { label: 'STM（短期）', desc: '三層情節記憶（perception/event/inner） → 安全閥50 → 睡眠縮減保留5筆', color: '6C5CE7' },
    { label: 'LTM（長期）', desc: 'HAM 5元組 → 每天衰減 0.05/(1+ac×0.5) → 提取強化 → 低於0.2刪除', color: '6C5CE7' },
    { label: '擴散激活', desc: 'BFS 2跳，激活0.4^(hop-1)，門檻0.3，top20 → 組自然語言 → 注入deliberate', color: C.mid },
    { label: '睡眠鞏固', desc: '12步驟：STM→HAM→LTM→摘要→關係→情緒→時間表→衰減→縮減→更新權重', color: C.green },
  ];

  summary.forEach((item, i) => {
    const row = Math.floor(i / 3);
    const col = i % 3;
    const x = 0.4 + col * 4.3;
    const y = 1.15 + row * 1.95;
    s.addShape(pptx.ShapeType.rect, { x, y, w: 4.1, h: 1.8,
      fill: { color: item.color, transparency: 80 }, line: { color: item.color, width: 2 } });
    s.addText(item.label, { x: x+0.1, y: y+0.08, w: 3.9, h: 0.38, fontSize: 14, bold: true, color: item.color });
    s.addText(item.desc, { x: x+0.1, y: y+0.5, w: 3.9, h: 1.15, fontSize: 11, color: C.white });
  });

  s.addText('理論模型：Kahneman雙歷程 × Tulving情節/語意 × Anderson HAM × Anderson擴散激活 × Diekelmann睡眠鞏固', {
    x: 0.4, y: 7.05, w: 12.9, h: 0.35, fontSize: 10.5, color: C.gray, align: 'center',
  });
}

slide18();
slide19();
slide20();
slide21();
slide22();

const outPath = 'C:/Users/Rayyu/Desktop/agi/presentation/AI-Town-main/AI-Town-main/reports/AI-Town_complete_flows_part4.pptx';
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log('Part 4 done: slides 18-22 written to', outPath);
}).catch(e => { console.error(e); process.exit(1); });
