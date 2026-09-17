const PptxGenJS = require('C:/Users/Rayyu/AppData/Roaming/npm/node_modules/pptxgenjs/dist/pptxgen.cjs.js');
const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE';

const C = {
  bg: 'F8F9FA', dark: '1A1A2E', blue: '16213E', mid: '0F3460',
  acc: 'E94560', text: '2D3436', sub: '636E72', white: 'FFFFFF',
  code: 'F1F2F6', green: '00B894', yel: 'FDCB6E', gray: 'B2BEC3',
};

// ══════════════════════════════════════════════════════
// SLIDE 1: Cover
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.dark };
  s.addText('AI-Town 完整系統流程與模擬', { x:0.5,y:1.4,w:12.3,h:1.2, fontSize:40,bold:true,color:C.white,align:'center' });
  s.addText('從感知到記憶的完整數據追蹤', { x:0.5,y:2.75,w:12.3,h:0.7, fontSize:22,color:C.acc,align:'center' });
  s.addText('設計靈感來自哪些人類心理學研究？', { x:1.5,y:3.55,w:10,h:0.38, fontSize:13,color:C.yel,bold:true });
  [
    'Kahneman (2011) 雙歷程理論 ─ 人類有兩種思考：快速直覺 vs 慢速深思，AI-Town 角色也用同樣模式',
    'Tulving (1972) 情節記憶 ─ 人記得「發生過什麼事」（STM）和「知識概念」（LTM）分開存放',
    'Anderson & Bower (1973) HAM ─ 記憶不是一句話，而是主語→關係→受語的三元組網路',
    'Anderson (1983) 擴散激活 ─ 想到一件事，腦中相關的記憶會自動被「點亮」',
    'Diekelmann & Born (2010) 睡眠鞏固 ─ 睡覺不是清空記憶，而是把今天的短期記憶整理成長期知識',
  ].forEach((t,i)=> s.addText(t,{x:1.5,y:4.0+i*0.52,w:10.5,h:0.46,fontSize:12.5,color:C.gray}));
}

// ══════════════════════════════════════════════════════
// SLIDE 2: Architecture
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('系統架構概覽 — 7 層分工',{x:0.4,y:0.2,w:12.5,h:0.6,fontSize:28,bold:true,color:C.dark});
  const layers=[
    {label:'Layer 1  進入層（負責啟動每個時間點）',mods:'clock.py  agent/manager.py  agent/interrupt.py',color:C.acc},
    {label:'Layer 2  協調層（決定角色要「想還是直覺反應」）',mods:'agent/agent.py  core/mental_state.py',color:C.mid},
    {label:'Layer 3a 直覺路徑（用 Markov 機率快速選行動）',mods:'core/markov_engine.py  core/tick_value.py',color:C.blue},
    {label:'Layer 3b 深思路徑（查記憶 + 呼叫 AI 模型推理）',mods:'core/memory_graph.py  model/prompt_builder.py  model/loader.py',color:C.blue},
    {label:'Layer 4  記憶核心（管理角色的短期與長期記憶）',mods:'core/character.py  core/memory_stm.py  core/memory_ltm.py  core/memory_graph.py  core/weight_adapter.py',color:C.green},
    {label:'Layer 5  語言模型層（AI 大腦：Phi-3.5）',mods:'model/loader.py  Phi-3.5-Vision-Instruct',color:'6C5CE7'},
    {label:'Layer 6  感知層（看見環境，像眼睛）',mods:'observe/yolo_perception.py  observe/scene.py',color:'E17055'},
    {label:'Layer 7  觀察層（輸出報告 / 視覺化）',mods:'observe/dashboard_html.py  reports/',color:C.sub},
  ];
  layers.forEach((l,i)=>{
    s.addShape(pptx.ShapeType.rect,{x:0.3,y:0.95+i*0.75,w:12.7,h:0.66,fill:{color:l.color,transparency:88},line:{color:l.color,width:2}});
    s.addText(l.label,{x:0.5,y:0.98+i*0.75,w:5.8,h:0.6,fontSize:11.5,bold:true,color:l.color});
    s.addText(l.mods,{x:6.5,y:0.98+i*0.75,w:6.4,h:0.6,fontSize:11,color:C.text});
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 3: Tick lifecycle
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 1｜每個「時間格（Tick）」裡發生什麼事？',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addText('角色的一天被切成很多個時間格，每格都按照以下順序走一遍：',{x:0.4,y:0.72,w:12.5,h:0.3,fontSize:12,color:C.sub});
  const steps=[
    {t:'① 時間格開始',d:'時鐘推進一格，通知所有角色「該行動了」'},
    {t:'② 時鐘強制檢查',d:'該起床就叫醒（force_wake），23:00後強制睡覺（force_sleep）'},
    {t:'③ 眼睛（感知）更新',d:'YOLO 掃描環境，更新場景描述，把「有事情發生」丟進待處理佇列'},
    {t:'④ 中斷評估',d:'評估剛收到的事件夠不夠重要，看能不能打斷正在做的事（行動鎖 0/1/2）'},
    {t:'⑤ 第一階段：執行',d:'把上一格決定好的行動做完（對話 / 走路 / 工作），結果寫進短期記憶'},
    {t:'⑥ 第二階段：決策',d:'計算現在有多困惑（C值），決定用直覺還是深思，選出下一格要做的事'},
    {t:'⑦ 記憶安全閥',d:'短期記憶超過 50 筆 → 立刻整理（中途濃縮），避免爆滿'},
    {t:'⑧ 進入下一格',d:'時鐘推進，重複整個流程'},
  ];
  steps.forEach((step,i)=>{
    const y=0.98+i*0.75;
    s.addShape(pptx.ShapeType.rect,{x:0.3,y,w:3.4,h:0.62,fill:{color:C.mid,transparency:85},line:{color:C.mid,width:1.5}});
    s.addText(step.t,{x:0.35,y:y+0.04,w:3.3,h:0.55,fontSize:12,bold:true,color:C.mid});
    s.addText(step.d,{x:3.9,y:y+0.04,w:9.4,h:0.55,fontSize:12,color:C.text});
    if(i<steps.length-1) s.addText('▼',{x:1.8,y:y+0.64,w:0.5,h:0.2,fontSize:10,color:C.gray,align:'center'});
  });
  s.addText('行動鎖等級說明：等級 2（不能被打斷）= 對話中、睡覺中 ｜ 等級 1（重要，不太好打斷）= 賣咖啡、工作中 ｜ 等級 0（隨時可打斷）= 散步、滑手機',
    {x:0.3,y:7.1,w:12.7,h:0.3,fontSize:10,color:C.sub,italic:true});
}

// ══════════════════════════════════════════════════════
// SLIDE 4: Confusion formula
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 2｜困惑度（C值）：角色有多不知道該怎麼辦？',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:23,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:12.5,h:0.7,fill:{color:C.dark,transparency:5},line:{color:C.acc,width:2}});
  s.addText('C = w1·U + w2·K + w3·S    （w1=0.4, w2=0.3, w3=0.3）    C 越高 → 越需要深思熟慮（呼叫 AI 模型）',
    {x:0.5,y:0.86,w:12.3,h:0.6,fontSize:15,bold:true,color:C.white,align:'center'});
  const cols=[
    {title:'U — 選擇有多猶豫？',color:C.green,lines:[
      '「Markov 給出的各行動機率差距太小」',
      '→ 代表不確定要選哪個',
      '',
      'gap = 第1名機率 − 第2名機率',
      'U = max(0.0, 1.0 − gap × 2.0)',
      '',
      '範例：gap=0.25 → U=0.50（有點猶豫）',
      '       gap=0.05 → U=0.90（很猶豫）',
      '       gap≥0.5  → U=0.0（很果斷）',
    ]},
    {title:'K — 有沒有衝突或情緒波動？',color:C.acc,lines:[
      '來源：YOLO描述 + 收到的話 + 行動 + 場景',
      '',
      '邏輯衝突（如「有人走了」卻還在「工作」）：+0.60',
      '強烈情緒關鍵字（思緒很亂、不知所措）：+0.45',
      '一般情緒關鍵字（心跳加速、告白、暗戀）：+0.25',
      '',
      'K 上限：1.0',
      '⚠ K ≥ 0.5 → 不管C值，直接強制深思',
    ]},
    {title:'S — 遇到預期外的事嗎？',color:'6C5CE7',lines:[
      '跟「長期記憶期望的樣子」差多少',
      '→ 差越多 S 越高',
      '',
      '第一天（長期記憶為空）→ S = 0.0',
      '陌生人/從沒見過：+0.60',
      '第一次/從未：+0.50',
      '意外/沒想到：+0.35',
      '突然：+0.25',
      'S 上限：1.0',
    ]},
  ];
  cols.forEach((col,ci)=>{
    const x=0.4+ci*4.3;
    s.addShape(pptx.ShapeType.rect,{x,y:1.65,w:4.1,h:5.55,fill:{color:col.color,transparency:90},line:{color:col.color,width:2}});
    s.addText(col.title,{x:x+0.1,y:1.68,w:3.9,h:0.42,fontSize:13,bold:true,color:col.color});
    col.lines.forEach((ln,li)=> s.addText(ln,{x:x+0.15,y:2.18+li*0.5,w:3.8,h:0.46,fontSize:11.5,color:ln===''?C.bg:C.text}));
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 5: Emotion threshold + mode decision
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 2｜心情不好時更難「深思熟慮」 — 閾值調整與路徑決策',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:21,bold:true,color:C.dark});
  s.addText('情緒如何影響「要深思還是直覺」的門檻？（adjust_threshold_by_emotion）',{x:0.4,y:0.82,w:8.5,h:0.4,fontSize:13,bold:true,color:C.mid});
  s.addText('邏輯：心情越差，閾值越高，越難觸發深思 → 更傾向快速直覺反應（就像人在情緒化時容易衝動）',{x:0.4,y:1.18,w:9,h:0.32,fontSize:11.5,color:C.sub,italic:true});
  const emotions=[
    {emo:'平靜',adj:'+0.00',final:'0.45（Amy基礎）',c:C.green},{emo:'開心',adj:'+0.00',final:'0.45',c:C.green},
    {emo:'興奮',adj:'+0.00',final:'0.45',c:C.green},{emo:'緊張',adj:'+0.10',final:'0.55',c:C.yel},
    {emo:'不安',adj:'+0.10',final:'0.55',c:C.yel},{emo:'困惑',adj:'+0.10',final:'0.55',c:C.yel},
    {emo:'難過',adj:'+0.15',final:'0.60',c:C.acc},{emo:'疲憊',adj:'+0.15',final:'0.60',c:C.acc},
  ];
  ['情緒狀態','閾值調整','Amy 的最終閾值'].forEach((h,hi)=>
    s.addText(h,{x:0.4+hi*2.5,y:1.58,w:2.4,h:0.38,fontSize:12,bold:true,color:C.white,fill:{color:C.mid}}));
  emotions.forEach((e,ei)=>{
    s.addText(e.emo,{x:0.4,y:2.04+ei*0.44,w:2.4,h:0.4,fontSize:12,color:e.c,bold:true});
    s.addText(e.adj,{x:2.9,y:2.04+ei*0.44,w:2.4,h:0.4,fontSize:12,color:C.text});
    s.addText(e.final,{x:5.4,y:2.04+ei*0.44,w:2.4,h:0.4,fontSize:12,color:C.text});
  });
  s.addText('怎麼決定要「深思」還是「直覺」？（decide_mode）',{x:8.5,y:0.82,w:4.8,h:0.4,fontSize:13,bold:true,color:C.mid});
  [{cond:'規則 1（最優先）',rule:'K ≥ 0.50',result:'→ 強制深思（deliberate）',note:'情緒衝突太大，不管 C 值直接叫模型',c:C.acc},
   {cond:'規則 2',rule:'C ≥ 最終閾值',result:'→ 深思（deliberate）',note:'整體困惑度超標，呼叫 Phi-3.5 推理',c:C.mid},
   {cond:'規則 3',rule:'C < 最終閾值',result:'→ 直覺（intuitive）',note:'夠確定了，直接走 Markov 機率決定',c:C.green},
  ].forEach((d,di)=>{
    s.addShape(pptx.ShapeType.rect,{x:8.5,y:1.35+di*1.28,w:4.8,h:1.15,fill:{color:d.c,transparency:88},line:{color:d.c,width:2}});
    s.addText(d.cond,{x:8.65,y:1.38+di*1.28,w:4.6,h:0.3,fontSize:10,color:d.c,bold:true});
    s.addText(d.rule,{x:8.65,y:1.68+di*1.28,w:4.6,h:0.32,fontSize:14,color:C.dark,bold:true});
    s.addText(d.result,{x:8.65,y:2.0+di*1.28,w:4.6,h:0.28,fontSize:12,bold:true,color:d.c});
    s.addText(d.note,{x:8.65,y:2.28+di*1.28,w:4.6,h:0.28,fontSize:10.5,color:C.sub});
  });
  s.addText('各角色基礎閾值：Amy=0.45　Ben=0.60　Claire=0.35（最容易深思）　David=0.55　Emma=0.50',
    {x:0.4,y:5.7,w:12.5,h:0.35,fontSize:11,color:C.sub});
  s.addText('DELIBERATE_K_OVERRIDE = 0.5 ← 這個值定義在 mental_state.py',
    {x:0.4,y:6.1,w:12.5,h:0.3,fontSize:11,color:C.sub,italic:true});
}

// ══════════════════════════════════════════════════════
// SLIDE 6: Sim example 1 — intuitive
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('實際計算範例①：Amy 遇到陌生客人 → 用直覺反應',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:23,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:5.8,h:2.85,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('當下情境',{x:0.55,y:0.85,w:5.5,h:0.35,fontSize:13,bold:true,color:C.mid});
  ['時間：第3天 09:30','地點：咖啡廳','現在在做：賣咖啡',
   'YOLO看到：「咖啡廳內有1個陌生人，從未見過」',
   '對方說：「陌生男子：請給我一杯美式」',
   '場景描述：「一個完全陌生的男人走進咖啡廳，Amy從未見過他」',
   'Amy 心情：平靜（基礎閾值 0.45）',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.25+i*0.33,w:5.5,h:0.3,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.4,y:0.82,w:6.9,h:5.8,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('C 值計算過程（一步步來）',{x:6.55,y:0.85,w:6.6,h:0.35,fontSize:13,bold:true,color:C.dark});
  let yy=1.28;
  [{label:'U（選擇有多猶豫）',c:C.green,lines:[
    '上一個時間格 Markov 給的機率：',
    '賣咖啡 0.55（第1名），對話 0.30（第2名）',
    'gap = 0.55 − 0.30 = 0.25',
    'U = max(0.0, 1.0 − 0.25×2) = 0.50',
  ]},
  {label:'K（有沒有衝突 / 情緒波動）',c:C.acc,lines:[
    '沒有邏輯衝突',
    '「陌生人」不在情緒關鍵字列表',
    '→ K = 0.00（沒有衝突）',
  ]},
  {label:'S（遇到預期外的事嗎）',c:'6C5CE7',lines:[
    '已有長期記憶（非第一天）',
    '場景描述含「從未見過」→ 命中驚訝關鍵字',
    '→ S = 0.50',
  ]},
  {label:'C 最終計算',c:C.mid,lines:[
    'C = 0.4×0.50 + 0.3×0.00 + 0.3×0.50',
    'C = 0.20 + 0.00 + 0.15 = 0.35',
  ]},
  ].forEach(blk=>{
    s.addText(blk.label+'：',{x:6.55,y:yy,w:6.6,h:0.3,fontSize:12,bold:true,color:blk.c}); yy+=0.32;
    blk.lines.forEach(ln=>{ s.addText(ln,{x:6.7,y:yy,w:6.4,h:0.28,fontSize:11,color:C.text}); yy+=0.3; }); yy+=0.1;
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:3.8,w:5.8,h:2.8,fill:{color:C.green,transparency:88},line:{color:C.green,width:2}});
  s.addText('結論',{x:0.55,y:3.83,w:5.5,h:0.35,fontSize:13,bold:true,color:C.green});
  ['心情平靜 → 閾值不調整，維持 0.45',
   'K = 0.00，沒有強制深思',
   'C = 0.35 < 閾值 0.45',
   '→ 走直覺路徑（intuitive）',
   '→ Markov 直接選出行動：賣咖啡',
   '→ 不需要叫 AI 模型思考',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:4.25+i*0.37,w:5.5,h:0.34,fontSize:i===3?13:11,bold:i===3,color:i===3?C.green:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 7: Sim example 2 — deliberate
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('實際計算範例②：Amy 收到 Ben 告白 → 觸發深思熟慮',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:23,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:5.8,h:2.55,fill:{color:C.acc,transparency:90},line:{color:C.acc,width:1.5}});
  s.addText('當下情境',{x:0.55,y:0.85,w:5.5,h:0.35,fontSize:13,bold:true,color:C.acc});
  ['時間：第3天 14:00','地點：咖啡廳','現在在做：休息',
   'Ben 說：「Amy，我一直很在意你，你願意和我交往嗎？」',
   '場景描述：「Ben神情認真，Amy心跳加速，思緒很亂」',
   '→ 心情從平靜變成緊張（閾值變 0.45+0.10 = 0.55）',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.25+i*0.33,w:5.5,h:0.3,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.4,y:0.82,w:6.9,h:5.5,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('C 值計算過程（一步步來）',{x:6.55,y:0.85,w:6.6,h:0.35,fontSize:13,bold:true,color:C.dark});
  let yy=1.28;
  [{label:'K（衝突 / 情緒波動）← 先算這個',c:C.acc,lines:[
    '邏輯衝突檢查：「休息」不在衝突行動列表 → +0',
    '場景含「心跳加速」→ 一般情緒關鍵字：+0.25',
    '場景含「思緒很亂」→ 強烈情緒關鍵字：+0.45',
    'K = min(0.25+0.45, 1.0) = 0.70',
  ]},
  {label:'S（遇到預期外嗎）',c:'6C5CE7',lines:[
    '場景沒有驚訝關鍵字 → S = 0.00',
  ]},
  {label:'U（選擇有多猶豫）',c:C.green,lines:[
    '機率很分散：對話 0.35，休息 0.30，gap=0.05',
    'U = max(0, 1.0 − 0.05×2) = 0.90',
  ]},
  {label:'C 最終計算',c:C.mid,lines:[
    'C = 0.4×0.90 + 0.3×0.70 + 0.3×0.00',
    'C = 0.36 + 0.21 + 0.00 = 0.57',
  ]},
  ].forEach(blk=>{
    s.addText(blk.label+'：',{x:6.55,y:yy,w:6.6,h:0.3,fontSize:12,bold:true,color:blk.c}); yy+=0.32;
    blk.lines.forEach(ln=>{ s.addText(ln,{x:6.7,y:yy,w:6.4,h:0.28,fontSize:11,color:C.text}); yy+=0.3; }); yy+=0.1;
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:3.5,w:5.8,h:3.1,fill:{color:C.acc,transparency:88},line:{color:C.acc,width:2}});
  s.addText('結論',{x:0.55,y:3.53,w:5.5,h:0.35,fontSize:13,bold:true,color:C.acc});
  ['心情緊張 → 閾值+0.10 → 最終閾值 0.55',
   'K = 0.70 ≥ 0.50',
   '→ 直接強制深思，不用看 C 值！',
   '→ 呼叫 Phi-3.5 AI 模型思考',
   '→ 模型讀取長期記憶 + 今日日記後回應',
   '（C=0.57 也 ≥ 0.55，兩個條件都成立）',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:3.96+i*0.37,w:5.5,h:0.34,fontSize:i===2?13:11,bold:i===2,color:i===2?C.acc:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 8: Markov 4-source overview
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜直覺路徑 — Markov 引擎怎麼決定要做什麼？',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:12.5,h:0.65,fill:{color:C.dark,transparency:5},line:{color:C.acc,width:2}});
  s.addText('P最終(行動) = α×P行程表(a) + β×P慣性(a) + γ×P情境(a) + δ×P學習(a)    ← 四個來源加權混合',
    {x:0.5,y:0.86,w:12.3,h:0.56,fontSize:14.5,bold:true,color:C.white,align:'center'});
  const sources=[
    {name:'α — 行程表分數（今天計畫做什麼？）',weight:'α = 0.40（正常情況）/ 0.10（重大事件發生時）',color:C.green,lines:[
      '來源：角色今天的時間規劃（每天睡覺時生成）',
      '完全符合行程 → 1.0分',
      '同類別的行動 → 0.5分（如：收銀算同類「工作」）',
      '無關行動 → 0.0分',
      '「前往」特例：還沒到目的地提升到0.6，已到了則×0.3',
      '使用 softmax（溫度 T=0.4）← 低溫讓高分更突出',
    ]},
    {name:'β — 行為慣性（最近一直在做什麼？）',weight:'β = 0.30（固定）',color:C.mid,lines:[
      '來源：最近 N 筆短期記憶的行動記錄',
      '歷史資料不足2筆 → 退回均勻分布（不偏好任何行動）',
      '統計：現在的動詞 → 接下來做各動詞的次數',
      'Laplace 平滑：count = 歷史次數 + 1（避免出現0）',
      'score = math.log(count)  ← 對數平滑',
      '使用 softmax（溫度 T=1.0）',
    ]},
    {name:'γ — 情境分數（現在環境在說什麼？）',weight:'γ = 0.30（正常）/ 0.60（重大事件 → 情境影響大增）',color:C.acc,lines:[
      '來源：YOLO 描述 + 場景文字 + 地點 + 周圍角色',
      '場景關鍵字命中：每個 +0.15（ACTION_KEYWORD_BOOST）',
      '情緒對特定行動的加成（EMOTION_TO_ACTION_BOOST）',
      '同地點有其他角色時：「對話」額外 +0.30',
      '使用 softmax（溫度 T=1.0）',
    ]},
    {name:'δ — 學習分數（過去哪些行動有好結果？）',weight:'δ = 0.15（有 RL 記錄時）/ 0.0（沒有記錄時，三源合一）',color:'E17055',lines:[
      '來源：ActionValueTracker 的 Q 值記錄',
      '過去帶來好結果的行動 → 分數偏高',
      '過去帶來壞結果的行動 → 分數偏低',
      '最小值移至0後再做 softmax',
      '沒有記錄時 δ=0，只靠前三個來源',
    ]},
  ];
  sources.forEach((src,si)=>{
    const x=0.4+(si%2)*6.4, y=1.6+Math.floor(si/2)*2.9;
    s.addShape(pptx.ShapeType.rect,{x,y,w:6.1,h:2.7,fill:{color:src.color,transparency:90},line:{color:src.color,width:1.5}});
    s.addText(src.name,{x:x+0.15,y:y+0.05,w:5.8,h:0.38,fontSize:12.5,bold:true,color:src.color});
    s.addText(src.weight,{x:x+0.15,y:y+0.45,w:5.8,h:0.28,fontSize:10.5,color:C.sub,italic:true});
    src.lines.forEach((ln,li)=> s.addText(ln,{x:x+0.2,y:y+0.78+li*0.3,w:5.75,h:0.28,fontSize:11,color:C.text}));
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 9: Markov special mechanisms
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜三個特殊設計：睡覺時間壓制 + 重大事件切換 + 保底正規化',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:20,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:7.6,h:3.05,fill:{color:C.blue,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('① 睡覺時間壓制曲線（_time_sleep_score）\n上班時不讓角色睡覺，深夜才讓機率回升',{x:0.55,y:0.85,w:7.3,h:0.55,fontSize:12.5,bold:true,color:C.mid});
  [['時間段','ts 值','scale = exp(ts×2)','實際效果'],
   ['07:00–18:00（上班時段）','ts = −1.5','exp(−3.0) ≈ 0.050','睡覺機率壓低至保底值 0.005'],
   ['18:00–23:00（下班後）','ts: 0.0→+0.5','exp(ts) ≈ 1.0→1.65','睡覺機率慢慢回升'],
   ['23:00 以後（深夜）','ts = +0.5','exp(0.5) ≈ 1.65','睡覺機率提升65%，角色傾向去睡覺'],
  ].forEach((row,ri)=> row.forEach((cell,ci)=>
    s.addText(cell,{x:0.55+ci*1.85,y:1.45+ri*0.47,w:1.8,h:0.43,fontSize:11,bold:ri===0,
      color:ri===0?C.mid:C.text, fill:ri===0?{color:C.mid,transparency:70}:undefined})));
  s.addShape(pptx.ShapeType.rect,{x:8.2,y:0.82,w:5.1,h:2.55,fill:{color:C.acc,transparency:88},line:{color:C.acc,width:1.5}});
  s.addText('② 重大事件時切換權重\n（模擬「地震時有人逃、有人繼續工作」的個體差異）',{x:8.35,y:0.85,w:4.8,h:0.55,fontSize:12.5,bold:true,color:C.acc});
  s.addText('觸發條件：K ≥ MAJOR_EVENT_K_THRESHOLD = 0.60',{x:8.35,y:1.45,w:4.8,h:0.3,fontSize:11,color:C.text});
  [['模式','α行程表','β慣性','γ情境'],['一般情況','0.40','0.30','0.30'],['重大事件','0.10','0.30','0.60']]
    .forEach((row,ri)=> row.forEach((cell,ci)=>
    s.addText(cell,{x:8.35+ci*1.2,y:1.8+ri*0.47,w:1.15,h:0.43,fontSize:11,bold:ri===0,
      color:ri===0?C.acc:(ri===2&&ci>0?C.acc:C.text)})));
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:4.05,w:12.9,h:2.5,fill:{color:C.green,transparency:92},line:{color:C.green,width:1.5}});
  s.addText('③ 最終保底 + 正規化（確保每個行動都有最低機率，所有機率加起來 = 1）',{x:0.55,y:4.08,w:12.6,h:0.38,fontSize:13,bold:true,color:C.green});
  ['步驟1 合併：P原始(a) = α×P行程 + β×P慣性 + γ×P情境 + δ×P學習',
   '步驟2 保底：final_prob(a) = max(P原始(a), MIN_PROB_FLOOR)   where MIN_PROB_FLOOR = 0.005',
   '          → 就算機率算出來是0，也給每個行動至少 0.5% 的機會',
   '步驟3 正規化：total = 所有行動機率加總，p(a) = round(p(a) / total, 4)   → 確保總和=1',
   '步驟4 對話目標：採樣到「對話」且有人在旁邊 → target = 第一個同地點角色；沒人 → 重新採樣',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:4.52+i*0.37,w:12.6,h:0.34,fontSize:11.5,color:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 10: Markov simulation
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜完整計算範例：Amy 早上 8:30 在咖啡廳',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:23,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:6.1,h:2.3,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('當下情境',{x:0.55,y:0.85,w:5.8,h:0.35,fontSize:12,bold:true,color:C.mid});
  ['時間：08:30（第3天）   地點：咖啡廳',
   '行程計畫：{08:30, 賣咖啡, 咖啡廳}',
   '最近做過的事：["前往","整理店面","賣咖啡","賣咖啡"]',
   'YOLO 看到：「1個客人、1個杯子、1個咖啡機」',
   '旁邊有誰：無   心情：平靜   有重大事件：否',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.23+i*0.34,w:5.8,h:0.31,fontSize:11,color:C.text}));
  [{name:'A. 行程表分數 (schedule)',color:C.green,rows:[
    ['賣咖啡','完全符合行程 → 1.0 → softmax(T=0.4)','≈ 0.62'],
    ['work類（收銀/補貨）','同類別 → 0.5 → softmax','各≈ 0.09'],
    ['其他行動','不相關 → 0.0 → softmax','各≈ 0.01'],
  ]},
  {name:'B. 行為慣性 (inertia)',color:C.mid,rows:[
    ['現在動詞 = "賣咖啡"','觀察轉移歷史',''],
    ['賣咖啡 → 賣咖啡 count=2','log(2)≈0.693','≈ 0.45'],
    ['其他行動 count=1','log(1)=0','≈ 0.028 各'],
  ]},
  {name:'C. 情境分數 (situation)',color:C.acc,rows:[
    ['賣咖啡','「客人」+「咖啡」命中 2次 → +0.30','≈ 0.38'],
    ['收銀','「客人」命中 1次 → +0.15','≈ 0.28'],
    ['對話','旁邊沒人 → 不加分','≈ 0.02'],
  ]},
  {name:'D. 學習分數 (value, δ=0)',color:'E17055',rows:[
    ['沒有 RL 記錄','均勻分布','無效'],
    ['δ = 0.0','不參與計算','—'],
  ]},
  ].forEach((src,si)=>{
    const x=0.4+(si%2)*6.4, y=3.25+Math.floor(si/2)*2.0;
    s.addShape(pptx.ShapeType.rect,{x,y,w:6.1,h:1.85,fill:{color:src.color,transparency:92},line:{color:src.color,width:1.5}});
    s.addText(src.name,{x:x+0.1,y:y+0.03,w:5.9,h:0.33,fontSize:12,bold:true,color:src.color});
    src.rows.forEach((row,ri)=>{
      s.addText(row[0],{x:x+0.1,y:y+0.4+ri*0.4,w:2.8,h:0.36,fontSize:10.5,color:C.text});
      s.addText(row[1],{x:x+2.95,y:y+0.4+ri*0.4,w:2.1,h:0.36,fontSize:10,color:C.sub});
      s.addText(row[2],{x:x+5.1,y:y+0.4+ri*0.4,w:0.95,h:0.36,fontSize:11,bold:true,color:src.color});
    });
  });
  s.addShape(pptx.ShapeType.rect,{x:6.7,y:0.82,w:6.6,h:2.3,fill:{color:C.dark,transparency:8},line:{color:C.yel,width:2}});
  s.addText('四個來源混合結果（α=0.4, β=0.3, γ=0.3, δ=0）',{x:6.85,y:0.85,w:6.3,h:0.35,fontSize:12,bold:true,color:C.yel});
  ['賣咖啡：0.4×0.62 + 0.3×0.45 + 0.3×0.38 = 0.248+0.135+0.114 = 0.497',
   '收 銀：0.4×0.09 + 0.3×0.028 + 0.3×0.28 ≈ 0.036+0.008+0.084 = 0.128',
   '對 話：0.4×0.01 + 0.3×0.028 + 0.3×0.00 ≈ 0.004+0.008+0 = 0.012',
   '睡 覺：上班時段壓制（ts=-1.5，scale≈0.05）→ 機率趨近保底',
   '正規化後前幾名：賣咖啡≈0.507, 收銀≈0.131, 補貨≈0.082...',
  ].forEach((ln,i)=> s.addText(ln,{x:6.85,y:1.25+i*0.35,w:6.3,h:0.32,fontSize:11,color:i===4?C.yel:C.white}));
}

// ══════════════════════════════════════════════════════
// SLIDE 11: Deliberate path
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3b｜深思路徑：先查記憶，再讓 AI 模型做決定',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  [{n:'①',title:'auto_query_nodes — 決定要去記憶裡查什麼',color:C.mid,lines:[
    '把「跟現在有關的關鍵詞」收集起來當查詢節點',
    '包含：角色自己 + 對話對象 + 同地點的人 + 當前位置 + 最近3筆記憶提到的名字',
    '範例：查詢節點 = ["Amy", "Ben", "咖啡廳"]',
  ]},
  {n:'②',title:'spreading_retrieve — 在記憶網路中「擴散查找」相關記憶',color:'6C5CE7',lines:[
    '起點節點的活化值 = 1.0，往外傳播時按 0.4^(跳數-1) 衰減',
    'hop=1（直接相關）: activation=1.0   hop=2（間接相關）: activation=0.4',
    '過濾掉：activation < 門檻值 0.3 的記憶（太模糊的不要）',
    '參數：最多跳 HAM_TRAVERSE_MAX_HOPS=2 跳，最多取 top_k=20 筆',
    '排序方式：活化值由高到低，相同時離起點近的優先',
  ]},
  {n:'③',title:'propositions_to_narrative — 把記憶翻譯成可讀的句子',color:C.green,lines:[
    '將記憶的「5元組結構」轉成自然語言',
    '範例：{Amy, 遇見, Ben, 咖啡廳, 第3天早上} → 「你在第3天早上在咖啡廳遇見Ben。」',
    '這段文字會被塞進給 AI 模型的提示（prompt）裡',
  ]},
  {n:'④',title:'build_deliberate → 呼叫 Phi-3.5 模型推理',color:C.acc,lines:[
    '組裝完整提示：角色人設 + 長期記憶摘要 + 今天的日記（最近5筆）+ 現在的困惑度 + 問題',
    'max_tokens 依場景設定（通常 200-500）',
    '模型輸出：action（做什麼）+ target（對誰）+ content（說什麼）+ thought（內心想法）',
  ]},
  ].forEach((step,si)=>{
    const y=0.82+si*1.65;
    s.addShape(pptx.ShapeType.rect,{x:0.4,y,w:12.9,h:1.55,fill:{color:step.color,transparency:90},line:{color:step.color,width:1.5}});
    s.addText(`${step.n} ${step.title}`,{x:0.55,y:y+0.05,w:12.6,h:0.38,fontSize:13,bold:true,color:step.color});
    step.lines.forEach((ln,li)=> s.addText(ln,{x:0.7,y:y+0.47+li*0.3,w:12.4,h:0.28,fontSize:11,color:C.text}));
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 12: STM structure
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜短期記憶（STM）— 每個時間格發生的事，分三層記錄',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:7.2,h:4.9,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('一筆記憶（Turn）的結構',{x:0.55,y:0.85,w:7.0,h:0.38,fontSize:13,bold:true,color:C.mid});
  s.addText('編號格式：D001_T003（第1天第3筆）  摘要編號：D002_T000（每天開頭的昨日摘要）',{x:0.55,y:1.28,w:7.0,h:0.35,fontSize:10.5,color:C.sub});
  let yy=1.72;
  [{name:'perception（感知層 — 我看到什麼）',color:C.green,fields:[
    'location    → 現在在哪',
    'yolo_desc   → YOLO 偵測到什麼東西',
    'scene_text  → 場景的文字描述',
  ]},
  {name:'event（事件層 — 發生了什麼 / 我做了什麼）',color:C.acc,fields:[
    'input_text  → 別人說的話或發生的事',
    'action      → 我做的行動',
    'target      → 行動的對象是誰',
    'content     → 我說了什麼',
  ]},
  {name:'inner（內在層 — 我心裡在想什麼）',color:'6C5CE7',fields:[
    'thought  → 內心的想法',
    'emotion  → 當下的情緒',
  ]},
  ].forEach(layer=>{
    s.addShape(pptx.ShapeType.rect,{x:0.55,y:yy,w:6.9,h:0.32,fill:{color:layer.color,transparency:70}});
    s.addText(layer.name,{x:0.65,y:yy+0.02,w:6.8,h:0.28,fontSize:12,bold:true,color:C.white}); yy+=0.35;
    layer.fields.forEach(f=>{ s.addText(f,{x:0.8,y:yy,w:6.7,h:0.3,fontSize:11,color:C.text}); yy+=0.32; }); yy+=0.1;
  });
  s.addShape(pptx.ShapeType.rect,{x:7.8,y:0.82,w:5.5,h:2.5,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('重要設定值',{x:7.95,y:0.85,w:5.2,h:0.35,fontSize:13,bold:true,color:C.green});
  ['STM_SAFETY_LIMIT = 50  → 超過就自動整理，防止塞爆',
   'STM_KEEP_AFTER_CONS = 5  → 每次睡覺只留最近5筆原始記錄',
   '（其餘壓縮成昨日摘要放在最前面）',
  ].forEach((p,pi)=> s.addText(p,{x:7.95,y:1.28+pi*0.45,w:5.2,h:0.42,fontSize:11.5,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:7.8,y:3.45,w:5.5,h:2.25,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('主要功能',{x:7.95,y:3.48,w:5.2,h:0.35,fontSize:13,bold:true,color:C.mid});
  ['add_turn()  — 記錄一筆新事件',
   'get_today_narrative()  — 把今天的記憶串成文章（給模型看）',
   'get_recent_actions(n)  — 取最近N個行動（給慣性計算用）',
   'shrink_to_summary()  — 睡覺時壓縮',
   'is_over_safety_limit()  — 檢查有沒有超過50筆',
  ].forEach((m,mi)=> s.addText(m,{x:7.95,y:3.9+mi*0.35,w:5.2,h:0.32,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:5.82,w:12.9,h:1.45,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('記憶轉成文章的範例（_turn_to_narrative）',{x:0.55,y:5.85,w:12.6,h:0.3,fontSize:11,bold:true,color:C.dark});
  s.addText('[08:00] 在咖啡廳，看到2個人、1個杯子。  聽到：Ben對你說：早安。  對Ben說：「早安，今天想喝什麼？」  內心想：Ben看起來心情不錯（情緒：平靜）',
    {x:0.55,y:6.2,w:12.6,h:0.55,fontSize:11,color:C.text});
}

// ══════════════════════════════════════════════════════
// SLIDE 13: LTM HAM + decay
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜長期記憶（LTM）— 每個「知識點」是一個5格子結構，會慢慢淡忘',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:20,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:6.2,h:4.55,fill:{color:'6C5CE7',transparency:90},line:{color:'6C5CE7',width:1.5}});
  s.addText('HAM 5元組結構（一筆長期記憶長這樣）',{x:0.55,y:0.85,w:6.0,h:0.35,fontSize:12,bold:true,color:'6C5CE7'});
  s.addText('靈感來源：Anderson & Bower (1973) 人類聯想記憶理論',{x:0.55,y:1.23,w:6.0,h:0.3,fontSize:10.5,color:C.sub,italic:true});
  [{f:'id',v:'"L001"  — 記憶的流水號'},
   {f:'subject',v:'"Amy"  — 主語（誰）'},
   {f:'relation',v:'"遇見"  — 關係或動作（做了什麼）'},
   {f:'object',v:'"Ben"  — 受語（對誰 / 什麼）'},
   {f:'location',v:'"咖啡廳"  — 發生在哪'},
   {f:'time',v:'"第3天 早上"  — 什麼時候'},
   {f:'strength',v:'1.0  — 記憶強度（每天會衰減，最低0→刪除）'},
   {f:'access_count',v:'0  — 被提取幾次（提取越多，衰減越慢）'},
   {f:'encoded_day',v:'3  — 這筆記憶是第幾天存進來的'},
  ].forEach((f,fi)=>{
    s.addText(f.f+':',{x:0.65,y:1.6+fi*0.38,w:1.6,h:0.35,fontSize:11,bold:true,color:'6C5CE7'});
    s.addText(f.v,{x:2.3,y:1.6+fi*0.38,w:4.2,h:0.35,fontSize:11,color:C.text});
  });
  s.addShape(pptx.ShapeType.rect,{x:6.8,y:0.82,w:6.5,h:3.25,fill:{color:C.acc,transparency:90},line:{color:C.acc,width:1.5}});
  s.addText('記憶每天會淡忘 — 但常用的忘得慢！',{x:6.95,y:0.85,w:6.2,h:0.35,fontSize:13,bold:true,color:C.acc});
  s.addText('公式：actual_decay = LTM_DECAY_RATE / (1 + access_count × 0.5)',{x:6.95,y:1.25,w:6.2,h:0.32,fontSize:12,bold:true,color:C.dark});
  s.addText('LTM_DECAY_RATE = 0.05（每天基礎衰減量）',{x:6.95,y:1.62,w:6.2,h:0.28,fontSize:11,color:C.sub});
  [['提取次數','每天衰減多少','說明'],
   ['0次','0.05 / 1.0 = 0.050','完全沒用到，正常忘記'],
   ['2次','0.05 / 2.0 = 0.025','用過2次，忘得慢一半'],
   ['10次','0.05 / 6.0 ≈ 0.008','常用記憶，幾乎不會忘'],
  ].forEach((row,ri)=> row.forEach((cell,ci)=>
    s.addText(cell,{x:6.95+ci*2.1,y:1.98+ri*0.42,w:2.0,h:0.38,fontSize:11,bold:ri===0,
      color:ri===0?C.acc:(ri===3?C.green:C.text)})));
  s.addShape(pptx.ShapeType.rect,{x:6.8,y:4.15,w:6.5,h:2.15,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('touch() 記憶強化 + prune() 清除舊記憶',{x:6.95,y:4.18,w:6.2,h:0.35,fontSize:13,bold:true,color:C.green});
  ['touch()：記憶被提取時自動呼叫',
   '  → access_count += 1（記錄又被用了一次）',
   '  → strength 直接重置回 1.0（記憶變清晰）',
   'prune()：每天睡覺後執行一次',
   '  → strength < LTM_FORGET_THRESHOLD(0.2) → 刪除這筆記憶',
   '  → 效果：很久沒想起的事情，終究會遺忘',
  ].forEach((m,mi)=> s.addText(m,{x:6.95,y:4.6+mi*0.3,w:6.2,h:0.28,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:5.5,w:6.2,h:1.25,fill:{color:C.yel,transparency:85},line:{color:C.yel,width:1}});
  s.addText('如果從來不用這筆記憶，多少天會被遺忘？',{x:0.55,y:5.53,w:6.0,h:0.3,fontSize:11,bold:true,color:C.dark});
  s.addText('strength 從 1.0 開始每天減 0.05\n→ 到 strength=0.2 需要 (1.0-0.2)/0.05 = 16 天後自動刪除',{x:0.55,y:5.87,w:6.0,h:0.55,fontSize:11,color:C.text});
}

// ══════════════════════════════════════════════════════
// SLIDE 14: Spreading activation
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜擴散激活 — 想到一件事，相關記憶自動被「點亮」',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  s.addText('靈感來源：Anderson (1983) ACT* 理論 — 就像在黑暗房間按燈，燈光會沿著電線傳到附近的燈',{x:0.4,y:0.75,w:12.5,h:0.3,fontSize:12,color:C.sub,italic:true});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:1.12,w:7.5,h:5.4,fill:{color:'6C5CE7',transparency:90},line:{color:'6C5CE7',width:1.5}});
  s.addText('BFS 擴散激活演算法（廣度優先搜尋）',{x:0.55,y:1.15,w:7.2,h:0.38,fontSize:13,bold:true,color:'6C5CE7'});
  ['① 起點：查詢節點的初始激活值 = 1.0',
   '② 建立 BFS 隊列：queue = [(節點, 跳數=1, 激活值=1.0)]',
   '③ 每次從隊列取出一個節點，計算它的傳播激活值：',
   '    傳播激活值 = activation_decay^(跳數-1) = 0.4^(跳數-1)',
   '    跳數=1（直接相關）: 傳播激活值 = 0.4^0 = 1.0',
   '    跳數=2（間接相關）: 傳播激活值 = 0.4^1 = 0.4',
   '④ 同時滿足以下條件才保留這筆記憶：',
   '    a. 傳播激活值 ≥ HAM_RETRIEVE_THRESHOLD = 0.3（不能太模糊）',
   '    b. 跳數 ≤ HAM_TRAVERSE_MAX_HOPS = 2（不能找太遠的記憶）',
   '    c. 這個節點還沒被訪問過',
   '⑤ 符合條件 → 加入結果：{命題內容, 激活值, 跳數}',
   '⑥ 繼續往外展開：把這個節點的鄰居加入隊列（跳數+1）',
   '⑦ 排序：激活值由高到低（越相關排越前面）',
   '⑧ 最多返回 top_k = 20 筆記憶',
  ].forEach((step,si)=> s.addText(step,{x:0.55,y:1.6+si*0.33,w:7.3,h:0.3,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:8.1,y:1.12,w:5.2,h:2.4,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('設定參數',{x:8.25,y:1.15,w:4.9,h:0.38,fontSize:13,bold:true,color:C.mid});
  [['HAM_TRAVERSE_MAX_HOPS','= 2（最多找2跳）'],['HAM_ACTIVATION_DECAY','= 0.4（每跳衰減40%）'],
   ['HAM_RETRIEVE_THRESHOLD','= 0.3（低於此不取）'],['top_k（最多返回幾筆）','= 20'],
  ].forEach((p,pi)=>{
    s.addText(p[0],{x:8.25,y:1.6+pi*0.45,w:3.5,h:0.4,fontSize:11,color:C.text});
    s.addText(p[1],{x:11.2,y:1.6+pi*0.45,w:2.0,h:0.4,fontSize:12,bold:true,color:C.mid});
  });
  s.addShape(pptx.ShapeType.rect,{x:8.1,y:3.65,w:5.2,h:2.85,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('範例（查 Amy + Ben + 咖啡廳）',{x:8.25,y:3.68,w:4.9,h:0.38,fontSize:12,bold:true,color:C.green});
  [['取到的記憶','跳數','激活值'],
   ['Amy 遇見 Ben（咖啡廳）','1','1.0 ✓ 保留'],
   ['Amy 暗戀 David','1','1.0 ✓ 保留'],
   ['Ben 送給 Amy 禮物','2','0.4 ✓ 保留'],
   ['Ben 在 超市 工作','2','0.4 ✓ 保留'],
   ['David 是 畫家','3','0.16 ✗ 太遠，過濾掉'],
  ].forEach((row,ri)=> row.forEach((cell,ci)=>
    s.addText(cell,{x:8.25+ci*1.7,y:4.12+ri*0.38,w:1.65,h:0.35,
      fontSize:ri===5&&ci===2?9.5:11,bold:ri===0,color:ri===0?C.green:(ri===5?C.acc:C.text)})));
}

// ══════════════════════════════════════════════════════
// SLIDE 15: RL Value Tracker
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜RL 學習機制 — 角色會從經驗中學習「哪些行動帶來好結果」',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:21,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:6.2,h:2.6,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('Q 值衰減 — 舊的記憶會自動淡化',{x:0.55,y:0.85,w:6.0,h:0.35,fontSize:13,bold:true,color:C.mid});
  s.addText('公式：V(行動) = V(行動) × VALUE_DECAY    每個時間格都執行',{x:0.55,y:1.25,w:6.0,h:0.32,fontSize:12,bold:true,color:C.dark});
  s.addText('VALUE_DECAY = 0.85（每格保留85%，15%淡忘）',{x:0.55,y:1.62,w:6.0,h:0.28,fontSize:11,color:C.sub});
  ['初始 V(賣咖啡) = 0.50',
   'Tick +1: 0.50 × 0.85 = 0.425',
   'Tick +2: 0.425 × 0.85 = 0.361',
   'Tick +5: 0.50 × 0.85⁵ ≈ 0.222',
   '→ 越近的行為對決策影響越大，舊的自然淡出',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.95+i*0.3,w:6.0,h:0.28,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.8,y:0.82,w:6.5,h:4.6,fill:{color:C.yel,transparency:88},line:{color:C.yel,width:1.5}});
  s.addText('什麼情況會獲得正/負獎勵？',{x:6.95,y:0.85,w:6.2,h:0.35,fontSize:13,bold:true,color:C.dark});
  [{event:'情緒變好（從壞情緒→好情緒）',r:'+0.50',c:C.green},
   {event:'情緒恢復平靜（從壞→平靜）',r:'+0.15',c:C.green},
   {event:'情緒變壞（從好/平靜→負面）',r:'−0.45',c:C.acc},
   {event:'困惑度明顯下降（C下降 ≥ 0.12）',r:'+0.30',c:C.green},
   {event:'困惑度突然飆高（C上升 ≥ 0.15）',r:'−0.35',c:C.acc},
   {event:'邀對話被接受（對方沒拒絕）',r:'+0.25',c:C.green},
   {event:'行動符合今天的行程計畫',r:'+0.20',c:C.green},
  ].forEach((rw,ri)=>{
    s.addText(rw.event,{x:6.95,y:1.3+ri*0.47,w:4.8,h:0.43,fontSize:11.5,color:C.text});
    s.addText(rw.r,{x:12.0,y:1.3+ri*0.47,w:1.2,h:0.43,fontSize:13,bold:true,color:rw.c,align:'right'});
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:3.55,w:6.2,h:2.1,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('Q 值是怎麼更新的？（類似 Q-learning）',{x:0.55,y:3.58,w:6.0,h:0.35,fontSize:12,bold:true,color:C.green});
  ['① 每格結束後計算本格的獎勵 r',
   '② 所有行動的 Q 值乘以 VALUE_DECAY（全部衰減）',
   '③ 本格選的行動：Q(行動) += r（好就加，壞就減）',
   '④ Markov 的 δ 分支直接用 Q 值當分數',
   '類似：Q(s,a) ← Q(s,a) + α[r − Q(s,a)]',
  ].forEach((q,qi)=> s.addText(q,{x:0.55,y:3.98+qi*0.3,w:6.0,h:0.28,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:5.78,w:12.9,h:1.45,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('範例：Amy 被告白事件後發生什麼',{x:0.55,y:5.81,w:12.6,h:0.3,fontSize:11,bold:true,color:C.dark});
  s.addText('情緒：平靜→緊張（變壞）→ reward=-0.45   困惑度上升0.22≥0.15 → reward=-0.35   本格總獎勵=-0.80\n→ Q(休息) += -0.80  →  下一格「休息」在 δ 分支的分數降低，Markov 更傾向選其他行動',
    {x:0.55,y:6.15,w:12.6,h:0.55,fontSize:11,color:C.text});
}

// ══════════════════════════════════════════════════════
// SLIDE 16: Weight Adapter
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜Weight Adapter — 角色每天睡覺後「調整自己的決策偏好」',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:21,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:5.5,h:2.0,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('每個角色的初始偏好（出廠設定）',{x:0.55,y:0.85,w:5.2,h:0.35,fontSize:13,bold:true,color:C.mid});
  [['α 行程表影響力','0.40'],['β 慣性影響力','0.30'],['γ 情境影響力','0.20'],['δ 學習影響力','0.10']]
    .forEach((d,di)=>{
      s.addText(d[0],{x:0.55,y:1.28+di*0.34,w:3.5,h:0.3,fontSize:12,color:C.text});
      s.addText(d[1],{x:4.2,y:1.28+di*0.34,w:1.5,h:0.3,fontSize:14,bold:true,color:C.mid});
    });
  s.addShape(pptx.ShapeType.rect,{x:6.1,y:0.82,w:7.2,h:2.8,fill:{color:C.dark,transparency:8},line:{color:C.acc,width:2}});
  s.addText('每天睡覺後的學習公式（SGD-like，梯度下降概念）',{x:6.25,y:0.85,w:7.0,h:0.35,fontSize:12,bold:true,color:C.yel});
  s.addText('α += LR × r × (sched_p − α)    ← 今天行程表準不準？獎勵越高、命中率越高 → α往上調\nβ += LR × r × (iner_p  − β)    ← 今天靠慣性選的對不對？\nγ += LR × r × (situ_p  − γ)    ← 今天情境判斷準不準？\nδ += LR × r × (val_p   − δ)    ← 今天學習分數準不準？\n\nLR = LEARNING_RATE = 0.05    r = 今天的總獎勵',
    {x:6.25,y:1.25,w:6.9,h:2.2,fontSize:11.5,color:C.white});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:2.98,w:5.5,h:2.2,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('更新完要做兩件事',{x:0.55,y:3.01,w:5.2,h:0.35,fontSize:13,bold:true,color:C.green});
  ['① 限制範圍（Clip）：每個權重只能在 [0.05, 0.85] 之間',
   '   MIN_WEIGHT = 0.05   MAX_WEIGHT = 0.85',
   '   → 不讓某個來源完全主導或完全消失',
   '② 正規化：total = α+β+γ+δ，每個除以 total',
   '   → 確保四個加起來 = 1.0，不會影響整體機率尺度',
  ].forEach((p,pi)=> s.addText(p,{x:0.55,y:3.44+pi*0.35,w:5.2,h:0.32,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.1,y:3.78,w:7.2,h:3.45,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('範例：Amy 第3天學習後的權重更新',{x:6.25,y:3.81,w:7.0,h:0.35,fontSize:12,bold:true,color:C.dark});
  ['出發點：α=0.40, β=0.30, γ=0.20, δ=0.10','',
   '今天記錄了 3 個時間格的數據：',
   'Tick1: r=+0.20, sched_p=0.62, iner_p=0.45, situ_p=0.38, val_p=0',
   'Tick2: r=-0.45, sched_p=0.30, iner_p=0.35, situ_p=0.55, val_p=0',
   'Tick3: r=+0.25, sched_p=0.50, iner_p=0.40, situ_p=0.42, val_p=0.2','',
   '更新後（clip+正規化）→ α≈0.39, β≈0.30, γ≈0.21, δ≈0.10',
   '→ Amy 稍微更相信「情境判斷」（γ微升），行程表影響力微降',
  ].forEach((ln,i)=> s.addText(ln,{x:6.25,y:4.22+i*0.33,w:7.0,h:0.3,fontSize:11,color:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 17: Sleep consolidation 12 steps
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜睡覺時做了什麼？— 12 步驟記憶鞏固',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addText('靈感來源：Diekelmann & Born (2010) — 人在睡覺時，大腦把今天的短期記憶「整理歸檔」成長期記憶',{x:0.4,y:0.73,w:12.5,h:0.3,fontSize:11,color:C.sub,italic:true});
  const steps12=[
    {n:'①',title:'讀取今天的日記',detail:'把今天所有的短期記憶（STM）合併成一篇完整的敘述文字',c:C.mid},
    {n:'②',title:'抽取記憶重點（HAM 5元組）',detail:'用 Phi-3.5 AI 讀今天的日記，抽出「誰做了什麼、在哪」等知識點（max_tokens=500）',c:C.mid},
    {n:'③',title:'篩選值得記住的',detail:'讓 AI 從抽出的知識點中選出最重要的（最多5筆），max_tokens=200',c:C.mid},
    {n:'④',title:'寫入長期記憶',detail:'ltm.encode_batch() 把篩選後的知識點加入記憶圖（MemoryGraph）',c:'6C5CE7'},
    {n:'⑤',title:'更新長期記憶摘要',detail:'讓 AI 重新寫一段「角色目前的人生狀態」摘要，max_tokens=80，上限200字',c:'6C5CE7'},
    {n:'⑥',title:'更新人際關係描述',detail:'找出今天日記裡提到的人，讓 AI 更新跟每個人的關係狀態，max_tokens=80',c:'6C5CE7'},
    {n:'⑦',title:'決定明天的情緒',detail:'今天 K 峰值 < 0.5 → 重置為平靜；≥0.5 → AI 推斷情緒（max_tokens=10）',c:C.acc},
    {n:'⑧',title:'生成明天的行程',detail:'根據職業模板 + 長期記憶摘要，讓 AI 安排明天的時間表，max_tokens=500',c:C.acc},
    {n:'⑨',title:'檢查行程合不合理',detail:'確認必要時段（起床、睡覺）有排到，時間順序要正確',c:C.acc},
    {n:'⑩',title:'長期記憶老化',detail:'apply_decay() 全部衰減一次；prune() 刪掉 strength < 0.2 的記憶',c:C.green},
    {n:'⑪',title:'壓縮短期記憶',detail:'shrink_to_summary()：只保留昨日摘要 + 最近5筆原始記錄，其他刪掉',c:C.green},
    {n:'⑫',title:'調整決策偏好 + 翻日曆',detail:'weight_adapter.update_weights() 學習今日；character.advance_day() 日期+1',c:C.green},
  ];
  steps12.slice(0,6).forEach((step,si)=>{
    const y=1.12+si*1.02;
    s.addShape(pptx.ShapeType.rect,{x:0.4,y,w:6.15,h:0.9,fill:{color:step.c,transparency:88},line:{color:step.c,width:1.5}});
    s.addText(`${step.n} ${step.title}`,{x:0.5,y:y+0.05,w:6.0,h:0.34,fontSize:12,bold:true,color:step.c});
    s.addText(step.detail,{x:0.55,y:y+0.42,w:5.9,h:0.4,fontSize:11,color:C.text});
  });
  steps12.slice(6,12).forEach((step,si)=>{
    const y=1.12+si*1.02;
    s.addShape(pptx.ShapeType.rect,{x:6.75,y,w:6.55,h:0.9,fill:{color:step.c,transparency:88},line:{color:step.c,width:1.5}});
    s.addText(`${step.n} ${step.title}`,{x:6.85,y:y+0.05,w:6.4,h:0.34,fontSize:12,bold:true,color:step.c});
    s.addText(step.detail,{x:6.9,y:y+0.42,w:6.3,h:0.4,fontSize:11,color:C.text});
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 18: Dialogue system
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('對話系統 — 別人來找你說話，要不要理他？',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:7.5,h:3.55,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('接受對話的機率計算公式',{x:0.55,y:0.85,w:7.2,h:0.35,fontSize:13,bold:true,color:C.mid});
  s.addText('P_accept = base + relation_bonus + leisure_bonus + work_penalty',{x:0.55,y:1.28,w:7.2,h:0.32,fontSize:13,bold:true,color:C.dark});
  [{term:'DIALOGUE_BASE_ACCEPT',val:'= 0.50',desc:'基礎接受率 — 不管是誰來，預設50%機率理他'},
   {term:'DIALOGUE_RELATION_BONUS',val:'= +0.30',desc:'認識的人 / 有好感 → 接受率 +30%'},
   {term:'DIALOGUE_LEISURE_BONUS',val:'= +0.20',desc:'正在休息中 → 接受率 +20%（沒在忙）'},
   {term:'DIALOGUE_WORK_PENALTY',val:'= −0.30',desc:'正在工作中 → 接受率 −30%（很忙不想理）'},
  ].forEach((t,ti)=>{
    s.addText(t.term,{x:0.55,y:1.7+ti*0.48,w:3.4,h:0.44,fontSize:11,bold:true,color:C.mid});
    s.addText(t.val,{x:3.95,y:1.7+ti*0.48,w:1.2,h:0.44,fontSize:12,bold:true,color:ti===3?C.acc:C.green});
    s.addText(t.desc,{x:5.2,y:1.7+ti*0.48,w:2.6,h:0.44,fontSize:10.5,color:C.sub});
  });
  s.addText('DIALOGUE_MAX_TURNS = 10 → 每段對話最多 10 個來回',{x:0.55,y:3.67,w:7.2,h:0.3,fontSize:11,color:C.sub});
  s.addShape(pptx.ShapeType.rect,{x:8.1,y:0.82,w:5.2,h:3.55,fill:{color:C.yel,transparency:85},line:{color:C.yel,width:1.5}});
  s.addText('實際場景計算',{x:8.25,y:0.85,w:4.9,h:0.35,fontSize:13,bold:true,color:C.dark});
  [{scenario:'Ben 找 Amy（休閒，有好感）',calc:'0.50 + 0.30 + 0.20 = 1.00',note:'100% → 一定接受'},
   {scenario:'Ben 找 Amy（工作中，有好感）',calc:'0.50 + 0.30 − 0.30 = 0.50',note:'50% → 可能接受'},
   {scenario:'陌生人找 Amy（休閒）',calc:'0.50 + 0.00 + 0.20 = 0.70',note:'70% → 大概接受'},
   {scenario:'陌生人找 Amy（工作中）',calc:'0.50 + 0.00 − 0.30 = 0.20',note:'20% → 大概拒絕'},
  ].forEach((ex,ei)=>{
    s.addShape(pptx.ShapeType.rect,{x:8.1,y:1.3+ei*0.74,w:5.2,h:0.65,fill:{color:C.code}});
    s.addText(ex.scenario,{x:8.2,y:1.32+ei*0.74,w:5.0,h:0.25,fontSize:10.5,bold:true,color:C.dark});
    s.addText(ex.calc+'  → '+ex.note,{x:8.2,y:1.57+ei*0.74,w:5.0,h:0.25,fontSize:11,color:C.text});
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:4.5,w:12.9,h:2.75,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('對話從開始到結束的流程',{x:0.55,y:4.53,w:12.6,h:0.35,fontSize:13,bold:true,color:C.green});
  ['① 角色 A 被 Markov 選出「對話」行動 → 目標 = 同地點的角色 B',
   '② 計算 P_accept，隨機決定 B 要不要接受',
   '③ B 接受：雙方的行動鎖設為 2（期間不能做其他事）',
   '④ 每個來回：A 說話 → 寫進短期記憶 → B 回應 → 寫進短期記憶',
   '⑤ 說滿 10 輪，或有人主動結束 → 行動鎖清除，各自繼續生活',
   '⑥ 結束後：reward += DIALOGUE_ACCEPT(+0.25)，寫入 RL 追蹤器',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:4.95+i*0.35,w:12.6,h:0.32,fontSize:11.5,color:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 19: Complete end-to-end trace
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('全程追蹤：Amy 第3天早上 8:30，一個時間格裡發生了什麼',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:21,bold:true,color:C.dark});
  const trace=[
    {phase:'時間格開始',color:C.mid,lines:['時間：D3 08:30  角色：Amy  所在地：咖啡廳','上一格做了：整理店面  情緒：平靜  手上沒有待執行的行動']},
    {phase:'眼睛更新（感知）',color:'E17055',lines:['YOLO 掃描：咖啡廳有1個客人、1個杯子、1個咖啡機','場景描述更新完成','打斷佇列：空（沒有突發事件）']},
    {phase:'第一階段：執行',color:C.green,lines:['沒有待執行的行動 → 跳過這個階段']},
    {phase:'第二階段：決策（計算 C 值）',color:C.acc,lines:['U=0.50（上格：賣咖啡0.55 vs 對話0.30，gap=0.25 → 有點猶豫）','K=0.00（沒有衝突，沒有情緒波動）','S=0.00（沒有驚訝的事，已有長期記憶）','C = 0.4×0.50 + 0.3×0.00 + 0.3×0.00 = 0.20','情緒平靜 → 閾值不調整，維持 0.45    K<0.5 且 C=0.20 < 0.45 → 走直覺路徑']},
    {phase:'直覺路徑：Markov 計算',color:'6C5CE7',lines:['α=0.40: 行程表→賣咖啡≈0.62  β=0.30: 慣性→賣咖啡≈0.45','γ=0.30: 情境→賣咖啡≈0.38（「客人」+「咖啡機」都命中）','混合：0.4×0.62+0.3×0.45+0.3×0.38 = 0.497','「睡覺」被早時段壓制（ts=-1.5，scale≈0.05）→ 趨近保底 0.005','正規化後：賣咖啡≈0.507 → 加權隨機採樣 → 選出「賣咖啡」']},
    {phase:'記憶寫入（STM）',color:C.mid,lines:['編號: D003_T005  時間: "08:30"','感知層: {咖啡廳, "1客人1杯子1咖啡機", ""}','事件層: {input:"", action:"賣咖啡", target:"", content:""}','內在層: {thought:"繼續工作，今天客人挺多", emotion:"平靜"}']},
    {phase:'計算獎勵（RL）',color:C.green,lines:['行動符合行程計畫「賣咖啡」 → reward += SCHEDULE_HIT(+0.20)','情緒沒變 → 無情緒獎勵    C 變化 < 0.12 → 無困惑度獎勵','ValueTracker.update("賣咖啡", +0.20)    全行動 × VALUE_DECAY(0.85)']},
  ];
  let yy=0.82;
  trace.forEach(block=>{
    const h=0.28*block.lines.length+0.42;
    s.addShape(pptx.ShapeType.rect,{x:0.4,y:yy,w:12.9,h,fill:{color:block.color,transparency:92},line:{color:block.color,width:1.5}});
    s.addText(block.phase,{x:0.55,y:yy+0.04,w:12.6,h:0.3,fontSize:12,bold:true,color:block.color});
    block.lines.forEach((ln,li)=> s.addText(ln,{x:0.7,y:yy+0.38+li*0.28,w:12.5,h:0.26,fontSize:11,color:C.text}));
    yy+=h+0.06;
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 20: Parameter reference
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('完整參數速查表（所有數值來源）',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  const sections=[
    {title:'記憶容量（STM / LTM）',color:'6C5CE7',params:[
      ['STM_SAFETY_LIMIT','50','短期記憶超過50筆就自動整理'],
      ['STM_KEEP_AFTER_CONS','5','睡覺後只保留最近5筆'],
      ['LTM_DECAY_RATE','0.05','每天基礎淡忘率'],
      ['LTM_FORGET_THRESHOLD','0.2','低於此強度就刪除記憶'],
    ]},
    {title:'記憶檢索（擴散激活）',color:C.mid,params:[
      ['HAM_TRAVERSE_MAX_HOPS','2','最多往外找2跳'],
      ['HAM_ACTIVATION_DECAY','0.4','每跳激活值×0.4衰減'],
      ['HAM_RETRIEVE_THRESHOLD','0.3','激活值低於此不取'],
    ]},
    {title:'Markov 決策引擎',color:C.green,params:[
      ['MARKOV_WEIGHTS_NORMAL','α:0.4 β:0.3 γ:0.3','平常的四源比例（δ另計）'],
      ['MARKOV_WEIGHTS_EVENT','α:0.1 β:0.3 γ:0.6','重大事件時情境影響大增'],
      ['MAJOR_EVENT_K_THRESHOLD','0.60','K超過0.6才切換事件模式'],
      ['MIN_PROB_FLOOR','0.005','每個行動至少0.5%機率'],
      ['KEYWORD_BOOST_PER_HIT','0.15','情境關鍵字每命中+0.15分'],
    ]},
    {title:'RL 學習系統',color:'E17055',params:[
      ['VALUE_DECAY','0.85','每格Q值保留85%'],
      ['REWARD_EMOTION_IMPROVE','+0.50','情緒變好的獎勵'],
      ['REWARD_EMOTION_WORSEN','−0.45','情緒變壞的懲罰'],
      ['REWARD_CONFUSION_DROP','+0.30','困惑度降低的獎勵（Δ≥0.12）'],
      ['REWARD_CONFUSION_SPIKE','−0.35','困惑度飆高的懲罰（Δ≥0.15）'],
      ['REWARD_DIALOGUE_ACCEPT','+0.25','對話被接受的獎勵'],
      ['REWARD_SCHEDULE_HIT','+0.20','行程計畫命中的獎勵'],
    ]},
    {title:'困惑度 & 思考切換',color:C.acc,params:[
      ['C 計算公式','w1·U+w2·K+w3·S','w1=0.4 w2=0.3 w3=0.3'],
      ['DELIBERATE_K_OVERRIDE','0.5','K≥0.5強制深思，不看C值'],
      ['EMOTION_RESET_THRESHOLD','0.5','K峰值≥0.5才讓AI推斷情緒'],
    ]},
    {title:'對話系統',color:C.mid,params:[
      ['DIALOGUE_MAX_TURNS','10','每段對話最多幾個來回'],
      ['DIALOGUE_BASE_ACCEPT','0.50','不管是誰，基礎接受率50%'],
      ['DIALOGUE_RELATION_BONUS','+0.30','有好感關係加成'],
      ['DIALOGUE_LEISURE_BONUS','+0.20','休閒時間加成'],
      ['DIALOGUE_WORK_PENALTY','−0.30','工作時間懲罰'],
    ]},
  ];
  sections.forEach((sec,si)=>{
    const col=si%2, row=Math.floor(si/2);
    const x=0.4+col*6.5;
    const h=0.38+sec.params.length*0.38+0.1;
    const y=0.85+row*(h+0.12);
    if(y+h>7.5) return;
    s.addShape(pptx.ShapeType.rect,{x,y,w:6.45,h,fill:{color:sec.color,transparency:90},line:{color:sec.color,width:1.5}});
    s.addText(sec.title,{x:x+0.1,y:y+0.04,w:6.25,h:0.32,fontSize:12,bold:true,color:sec.color});
    sec.params.forEach((p,pi)=>{
      s.addText(p[0],{x:x+0.15,y:y+0.42+pi*0.38,w:2.5,h:0.34,fontSize:10.5,bold:true,color:C.text});
      s.addText(p[1],{x:x+2.7,y:y+0.42+pi*0.38,w:1.4,h:0.34,fontSize:11,bold:true,color:sec.color});
      s.addText(p[2],{x:x+4.15,y:y+0.42+pi*0.38,w:2.2,h:0.34,fontSize:10,color:C.sub});
    });
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 21: Character profiles
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('5位角色的認知設定 — 每個人的「深思門檻」都不一樣',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  const chars=[
    {name:'Amy',role:'咖啡師',threshold:'0.45',traits:'暗戀David，被Ben追求。門檻適中，偶爾會深思。',color:C.acc},
    {name:'Ben',role:'超市員工',threshold:'0.60',traits:'喜歡Amy。門檻高，比較容易直覺反應，不愛想太多。',color:C.green},
    {name:'Claire',role:'學生',threshold:'0.35',traits:'愛讀書思考。門檻最低，最容易觸發深思，常常想半天。',color:'6C5CE7'},
    {name:'David',role:'畫家',threshold:'0.55',traits:'感性藝術家，不知Amy暗戀他。稍微愛深思。',color:'E17055'},
    {name:'Emma',role:'老師',threshold:'0.50',traits:'理性平衡，直覺與深思各佔一半。',color:C.mid},
  ];
  ['角色','職業','深思門檻','不同情緒下的實際閾值','個性特色'].forEach((h,hi)=>
    s.addText(h,{x:0.4+[0,1.6,3.2,4.8,8.8][hi],y:0.88,w:[1.5,1.5,1.5,3.8,4.2][hi],h:0.42,
      fontSize:12,bold:true,color:C.white,fill:{color:C.dark}}));
  chars.forEach((ch,ci)=>{
    const y=1.38+ci*1.04;
    s.addShape(pptx.ShapeType.rect,{x:0.4,y,w:12.9,h:0.95,fill:{color:ch.color,transparency:92},line:{color:ch.color,width:1}});
    s.addText(ch.name,{x:0.5,y:y+0.05,w:1.4,h:0.85,fontSize:16,bold:true,color:ch.color,valign:'middle'});
    s.addText(ch.role,{x:2.1,y:y+0.25,w:1.4,h:0.45,fontSize:12,color:C.text});
    s.addText(ch.threshold,{x:3.4,y:y+0.1,w:1.3,h:0.75,fontSize:20,bold:true,color:ch.color,valign:'middle',align:'center'});
    s.addText(`平靜→${ch.threshold}  緊張→${(parseFloat(ch.threshold)+0.10).toFixed(2)}  難過→${(parseFloat(ch.threshold)+0.15).toFixed(2)}`,
      {x:4.9,y:y+0.28,w:3.7,h:0.38,fontSize:11,color:C.text});
    s.addText(ch.traits,{x:8.9,y:y+0.2,w:4.2,h:0.55,fontSize:10.5,color:C.text});
  });
  s.addText('所有角色的預設情緒：「平靜」（BASELINE_EMOTION = "平靜"）',{x:0.4,y:6.55,w:8,h:0.3,fontSize:11,color:C.sub,italic:true});
  s.addText('情緒更新時機：當天 K 值峰值 ≥ 0.5 才讓 AI 推斷新情緒，否則直接回歸平靜',{x:0.4,y:6.9,w:12.9,h:0.3,fontSize:11,color:C.sub,italic:true});
}

// ══════════════════════════════════════════════════════
// SLIDE 22: Summary
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.dark };
  s.addText('AI-Town 系統一頁全覽',{x:0.4,y:0.3,w:12.5,h:0.7,fontSize:34,bold:true,color:C.white,align:'center'});
  [{label:'感知層（眼睛）',desc:'YOLO → yolo_desc → interrupt_queue → 行動鎖 0/1/2',color:'E17055'},
   {label:'C值閘門（要深思嗎？）',desc:'C=w1U+w2K+w3S → 直覺(Markov) 或 深思(Phi-3.5)',color:C.acc},
   {label:'Markov直覺引擎',desc:'α行程+β慣性+γ情境+δ學習 → softmax → 保底0.005 → 採樣',color:C.green},
   {label:'RL學習機制',desc:'每格衰減0.85 + 7種reward → Q值影響δ分支選擇',color:'E17055'},
   {label:'Weight Adapter（偏好調整）',desc:'每天SGD(LR=0.05)更新α/β/γ/δ → clip[0.05,0.85] → 正規化',color:C.yel},
   {label:'STM 短期記憶（日記）',desc:'3層記錄（感知/事件/內在） → 上限50筆 → 睡後保留5筆',color:'6C5CE7'},
   {label:'LTM 長期記憶（知識）',desc:'HAM 5元組 → 每天衰減 0.05/(1+ac×0.5) → 提取後強化 → 低於0.2刪除',color:'6C5CE7'},
   {label:'擴散激活（找記憶）',desc:'BFS 2跳，激活0.4^(hop-1)，門檻0.3，top20 → 翻譯成句子 → 餵給模型',color:C.mid},
   {label:'睡眠鞏固（整理歸檔）',desc:'12步驟：STM日記→抽重點→存長期→更新摘要→情緒→行程→衰減→壓縮→更新權重',color:C.green},
  ].forEach((item,i)=>{
    const row=Math.floor(i/3), col=i%3;
    const x=0.4+col*4.3, y=1.15+row*1.95;
    s.addShape(pptx.ShapeType.rect,{x,y,w:4.1,h:1.8,fill:{color:item.color,transparency:80},line:{color:item.color,width:2}});
    s.addText(item.label,{x:x+0.1,y:y+0.08,w:3.9,h:0.38,fontSize:13,bold:true,color:item.color});
    s.addText(item.desc,{x:x+0.1,y:y+0.5,w:3.9,h:1.15,fontSize:11,color:C.white});
  });
  s.addText('理論根基：Kahneman雙歷程 × Tulving情節/語意記憶 × Anderson HAM × Anderson擴散激活 × Diekelmann睡眠鞏固',
    {x:0.4,y:7.05,w:12.9,h:0.35,fontSize:10.5,color:C.gray,align:'center'});
}

const outPath = 'C:/Users/Rayyu/Desktop/agi/presentation/AI-Town-main/AI-Town-main/reports/AI-Town_complete_flows_v2.pptx';
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log('DONE: 22 slides (v2 plain language) written to', outPath);
}).catch(e => { console.error(e); process.exit(1); });
