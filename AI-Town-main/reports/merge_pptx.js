// Merge all 4 parts into one PPTX by re-generating all slides in a single run
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
  s.addText('AI-Town 完整系統流程與模擬', { x:0.5,y:1.5,w:12.3,h:1.2, fontSize:40,bold:true,color:C.white,align:'center' });
  s.addText('從感知到記憶的完整數據追蹤', { x:0.5,y:2.9,w:12.3,h:0.7, fontSize:22,color:C.acc,align:'center' });
  s.addText('認知科學理論基礎', { x:1.5,y:3.6,w:4,h:0.36, fontSize:12,color:C.yel,bold:true });
  ['Kahneman (2011)  雙歷程理論 — System 1 直覺 / System 2 深思',
   'Tulving (1972)   情節記憶與語意記憶 — STM 敘述 / LTM HAM命題',
   'Anderson & Bower (1973)  HAM — 人類聯想記憶 5元組',
   'Anderson (1983)  擴散激活理論 — 記憶節點 BFS 傳播',
   'Diekelmann & Born (2010)  睡眠鞏固 — STM→LTM 轉移整合',
  ].forEach((t,i)=> s.addText(t,{x:1.5,y:4.0+i*0.52,w:10.3,h:0.46,fontSize:13,color:C.gray}));
}

// ══════════════════════════════════════════════════════
// SLIDE 2: Architecture
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('系統架構概覽',{x:0.4,y:0.2,w:12.5,h:0.6,fontSize:28,bold:true,color:C.dark});
  const layers=[
    {label:'Layer 1  進入層',mods:'clock.py  agent/manager.py  agent/interrupt.py',color:C.acc},
    {label:'Layer 2  協調層',mods:'agent/agent.py  core/mental_state.py',color:C.mid},
    {label:'Layer 3a 推論層（直覺）',mods:'core/markov_engine.py  core/tick_value.py',color:C.blue},
    {label:'Layer 3b 推論層（深思）',mods:'core/memory_graph.py  model/prompt_builder.py  model/loader.py',color:C.blue},
    {label:'Layer 4  認知層',mods:'core/character.py  core/memory_stm.py  core/memory_ltm.py  core/memory_graph.py  core/weight_adapter.py',color:C.green},
    {label:'Layer 5  模型層',mods:'model/loader.py  Phi-3.5-Vision-Instruct',color:'6C5CE7'},
    {label:'Layer 6  感知層',mods:'observe/yolo_perception.py  observe/scene.py',color:'E17055'},
    {label:'Layer 7  觀察層',mods:'observe/dashboard_html.py  reports/',color:C.sub},
  ];
  layers.forEach((l,i)=>{
    s.addShape(pptx.ShapeType.rect,{x:0.3,y:0.95+i*0.75,w:12.7,h:0.66,fill:{color:l.color,transparency:88},line:{color:l.color,width:2}});
    s.addText(l.label,{x:0.5,y:0.98+i*0.75,w:3.8,h:0.6,fontSize:12,bold:true,color:l.color});
    s.addText(l.mods,{x:4.4,y:0.98+i*0.75,w:8.4,h:0.6,fontSize:11,color:C.text});
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 3: Tick lifecycle
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 1｜Tick 完整生命週期',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:26,bold:true,color:C.dark});
  const steps=[
    {t:'① Tick T 開始',d:'clock.py 推進時間，觸發所有角色處理'},
    {t:'② 時鐘檢查',d:'force_wake（起床時間）/ force_sleep（23:00後）判斷'},
    {t:'③ 感知層更新',d:'YOLO偵測場景 → yolo_desc更新，interrupt_queue排入事件'},
    {t:'④ 中斷處理',d:'interrupt.py 評估事件強度 vs 行動鎖等級（0/1/2）'},
    {t:'⑤ Phase 1 執行',d:'pending_action執行（對話/一般/多tick行動） → 寫STM turn'},
    {t:'⑥ Phase 2 決策',d:'計算困惑度C → 選路徑（intuitive/deliberate） → 設定pending_action → 寫STM'},
    {t:'⑦ STM 安全閥',d:'STM turns > 50 → 觸發中途濃縮（midday consolidation）'},
    {t:'⑧ Tick T+1',d:'時鐘推進，回到①'},
  ];
  steps.forEach((step,i)=>{
    const y=0.85+i*0.75;
    s.addShape(pptx.ShapeType.rect,{x:0.3,y,w:3.2,h:0.62,fill:{color:C.mid,transparency:85},line:{color:C.mid,width:1.5}});
    s.addText(step.t,{x:0.35,y:y+0.04,w:3.1,h:0.55,fontSize:12,bold:true,color:C.mid});
    s.addText(step.d,{x:3.7,y:y+0.04,w:9.3,h:0.55,fontSize:12,color:C.text});
    if(i<steps.length-1) s.addText('▼',{x:1.7,y:y+0.64,w:0.5,h:0.2,fontSize:10,color:C.gray,align:'center'});
  });
  s.addText('行動鎖等級：等級2（不可中斷）= 對話、睡覺 ｜ 等級1（重要）= 賣咖啡、工作 ｜ 等級0（容易中斷）= 前往、散步、滑手機',
    {x:0.3,y:7.1,w:12.7,h:0.3,fontSize:10,color:C.sub,italic:true});
}

// ══════════════════════════════════════════════════════
// SLIDE 4: Confusion formula
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 2｜困惑度計算 — 公式與參數來源',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:12.5,h:0.7,fill:{color:C.dark,transparency:5},line:{color:C.acc,width:2}});
  s.addText('C = w1·U + w2·K + w3·S    （w1=0.4, w2=0.3, w3=0.3）    來源：mental_state.py → compute_C()',
    {x:0.5,y:0.86,w:12.3,h:0.6,fontSize:15,bold:true,color:C.white,align:'center'});
  const cols=[
    {title:'U — 不確定性',color:C.green,lines:['來源：Markov機率分布前兩名差距','gap = prob_rank1 − prob_rank2','U = max(0.0, 1.0 − gap × 2.0)','範圍：0.0（確定）~ 1.0（不確定）','範例：gap=0.25 → U=0.50','       gap=0.05 → U=0.90','       gap≥0.5  → U=0.0']},
    {title:'K — 衝突程度',color:C.acc,lines:['來源：YOLO + 對話 + 行動 + 場景','邏輯衝突pair命中：+0.60','  （如「離開/走了」+正在「工作」）','強情緒關鍵字命中：+0.45','  （混亂、不知所措、思緒紊亂）','一般情緒關鍵字命中：+0.25','  （心跳、暗戀、告白、情緒複雜）','K上限：1.0','K ≥ 0.5 → 強制 deliberate']},
    {title:'S — 驚訝程度',color:'6C5CE7',lines:['來源：scene_text vs LTM預期','LTM為空（第一天）→ S=0.0','陌生人/從沒見過：+0.60','第一次/從未：+0.50','意外/沒想到/不可思議：+0.35','突然：+0.25','S上限：1.0']},
  ];
  cols.forEach((col,ci)=>{
    const x=0.4+ci*4.3;
    s.addShape(pptx.ShapeType.rect,{x,y:1.65,w:4.1,h:5.55,fill:{color:col.color,transparency:90},line:{color:col.color,width:2}});
    s.addText(col.title,{x:x+0.1,y:1.68,w:3.9,h:0.42,fontSize:14,bold:true,color:col.color});
    col.lines.forEach((ln,li)=> s.addText(ln,{x:x+0.15,y:2.18+li*0.52,w:3.8,h:0.48,fontSize:11.5,color:C.text}));
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 5: Emotion threshold + mode decision
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 2｜情緒調整閾值 + 模式決策邏輯',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addText('情緒對困惑度閾值的調整（adjust_threshold_by_emotion）',{x:0.4,y:0.82,w:8,h:0.4,fontSize:14,bold:true,color:C.mid});
  s.addText('設計邏輯：心情差時容易直覺反應，更難深思',{x:0.4,y:1.18,w:8,h:0.32,fontSize:12,color:C.sub,italic:true});
  const emotions=[
    {emo:'平靜',adj:'+0.00',final:'0.45（Amy基礎）',c:C.green},{emo:'開心',adj:'+0.00',final:'0.45',c:C.green},
    {emo:'興奮',adj:'+0.00',final:'0.45',c:C.green},{emo:'緊張',adj:'+0.10',final:'0.55',c:C.yel},
    {emo:'不安',adj:'+0.10',final:'0.55',c:C.yel},{emo:'困惑',adj:'+0.10',final:'0.55',c:C.yel},
    {emo:'難過',adj:'+0.15',final:'0.60',c:C.acc},{emo:'疲憊',adj:'+0.15',final:'0.60',c:C.acc},
  ];
  ['情緒','閾值調整','Amy最終閾值'].forEach((h,hi)=>
    s.addText(h,{x:0.4+hi*2.5,y:1.58,w:2.4,h:0.36,fontSize:12,bold:true,color:C.white,fill:{color:C.mid}}));
  emotions.forEach((e,ei)=>{
    s.addText(e.emo,{x:0.4,y:2.0+ei*0.44,w:2.4,h:0.4,fontSize:12,color:e.c,bold:true});
    s.addText(e.adj,{x:2.9,y:2.0+ei*0.44,w:2.4,h:0.4,fontSize:12,color:C.text});
    s.addText(e.final,{x:5.4,y:2.0+ei*0.44,w:2.4,h:0.4,fontSize:12,color:C.text});
  });
  s.addText('模式決策邏輯（decide_mode 函式）',{x:8.5,y:0.82,w:4.7,h:0.4,fontSize:14,bold:true,color:C.mid});
  [{cond:'條件 1',rule:'K ≥ 0.50',result:'→ 強制 deliberate',note:'（不看C值，情緒衝突 override）',c:C.acc},
   {cond:'條件 2',rule:'C ≥ 最終閾值',result:'→ deliberate',note:'（呼叫 Phi-3.5 模型推理）',c:C.mid},
   {cond:'條件 3',rule:'C < 最終閾值',result:'→ intuitive',note:'（走 Markov 機率路徑）',c:C.green},
  ].forEach((d,di)=>{
    s.addShape(pptx.ShapeType.rect,{x:8.5,y:1.35+di*1.2,w:4.7,h:1.05,fill:{color:d.c,transparency:88},line:{color:d.c,width:2}});
    s.addText(d.cond,{x:8.65,y:1.37+di*1.2,w:4.4,h:0.3,fontSize:10,color:d.c,bold:true});
    s.addText(d.rule,{x:8.65,y:1.67+di*1.2,w:4.4,h:0.3,fontSize:13,color:C.dark,bold:true});
    s.addText(d.result+'  '+d.note,{x:8.65,y:1.97+di*1.2,w:4.4,h:0.35,fontSize:11,color:C.text});
  });
  s.addText('Amy 角色設定：困惑閾值基礎值 = 0.45　　Ben：0.60　　Claire：0.35　　David：0.55　　Emma：0.50',
    {x:0.4,y:5.65,w:12.5,h:0.35,fontSize:11,color:C.sub});
  s.addText('DELIBERATE_K_OVERRIDE = 0.5  （來源：mental_state.py）',
    {x:0.4,y:6.1,w:12.5,h:0.3,fontSize:11,color:C.sub,italic:true});
}

// ══════════════════════════════════════════════════════
// SLIDE 6: Sim example 1 — intuitive
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 2｜模擬：Amy 遇到陌生客人（→ intuitive）',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:5.8,h:2.8,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('情境設定',{x:0.55,y:0.85,w:5.5,h:0.35,fontSize:13,bold:true,color:C.mid});
  ['時間：第3天 09:30','地點：咖啡廳','當前行動：賣咖啡',
   'YOLO：「咖啡廳內有1個陌生人，從未見過」',
   'scene_text：「一個完全陌生的男人走進咖啡廳，Amy從未見過他」',
   'input_text：「陌生男子：請給我一杯美式」','情緒：平靜（基礎閾值0.45）',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.25+i*0.33,w:5.5,h:0.3,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.4,y:0.82,w:6.9,h:5.8,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('計算過程',{x:6.55,y:0.85,w:6.6,h:0.35,fontSize:13,bold:true,color:C.dark});
  let yy=1.28;
  [{label:'U 計算',c:C.green,lines:['Markov上一tick：賣咖啡 0.55（rank1），對話 0.30（rank2）','gap = 0.55 − 0.30 = 0.25','U = max(0.0, 1.0 − 0.25×2) = 0.50']},
   {label:'K 計算',c:C.acc,lines:['無邏輯衝突pair命中','無強情緒關鍵字（「陌生人」不在K列表）','無一般情緒關鍵字','K = 0.00']},
   {label:'S 計算',c:'6C5CE7',lines:['LTM已有摘要（非第一天）','scene_text 含「從未見過」→ _MID_HIGH_SURPRISE_KW','S = 0.50']},
   {label:'C 計算',c:C.mid,lines:['C = 0.4×0.50 + 0.3×0.00 + 0.3×0.50','C = 0.20 + 0.00 + 0.15 = 0.35']},
  ].forEach(blk=>{
    s.addText(blk.label+'：',{x:6.55,y:yy,w:6.6,h:0.3,fontSize:12,bold:true,color:blk.c}); yy+=0.32;
    blk.lines.forEach(ln=>{ s.addText(ln,{x:6.7,y:yy,w:6.4,h:0.28,fontSize:11,color:C.text}); yy+=0.3; }); yy+=0.08;
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:3.75,w:5.8,h:2.85,fill:{color:C.green,transparency:88},line:{color:C.green,width:2}});
  s.addText('決策結果',{x:0.55,y:3.78,w:5.5,h:0.35,fontSize:13,bold:true,color:C.green});
  ['情緒：平靜 → 調整 +0.00 → 最終閾值 0.45','K = 0.00 < 0.50  →  不強制 deliberate',
   'C = 0.35 < 閾值 0.45','→ 結果：intuitive（Markov 機率路徑）',
   '→ 行動：機率最高為「賣咖啡」','→ 不呼叫 Phi-3.5 模型',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:4.22+i*0.37,w:5.5,h:0.34,fontSize:i===3?13:11,bold:i===3,color:i===3?C.green:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 7: Sim example 2 — deliberate
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 2｜模擬：Amy 收到 Ben 告白（→ deliberate）',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:5.8,h:2.55,fill:{color:C.acc,transparency:90},line:{color:C.acc,width:1.5}});
  s.addText('情境設定',{x:0.55,y:0.85,w:5.5,h:0.35,fontSize:13,bold:true,color:C.acc});
  ['時間：第3天 14:00','地點：咖啡廳','當前行動：休息',
   'input_text：「Ben：Amy，我一直很在意你，你願意和我交往嗎？」',
   'scene_text：「Ben神情認真，Amy心跳加速，思緒很亂」',
   '情緒：緊張（基礎閾值0.45 + 0.10 = 0.55）',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.25+i*0.33,w:5.5,h:0.3,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.4,y:0.82,w:6.9,h:5.5,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('計算過程',{x:6.55,y:0.85,w:6.6,h:0.35,fontSize:13,bold:true,color:C.dark});
  let yy=1.28;
  [{label:'K 計算',c:C.acc,lines:['combined = input_text + yolo_desc','邏輯衝突：「休息」不在衝突行動列表 → +0','scene_text 含「心跳加速」→ 一般情緒KW +0.25','scene_text 含「思緒很亂」→ 強情緒KW +0.45','K = min(0.25+0.45, 1.0) = 0.70']},
   {label:'S 計算',c:'6C5CE7',lines:['場景無驚訝關鍵字 → S = 0.00']},
   {label:'U 計算',c:C.green,lines:['機率均勻：對話0.35，休息0.30，gap=0.05','U = max(0, 1.0 − 0.05×2) = 0.90']},
   {label:'C 計算',c:C.mid,lines:['C = 0.4×0.90 + 0.3×0.70 + 0.3×0.00','C = 0.36 + 0.21 + 0.00 = 0.57']},
  ].forEach(blk=>{
    s.addText(blk.label+'：',{x:6.55,y:yy,w:6.6,h:0.3,fontSize:12,bold:true,color:blk.c}); yy+=0.32;
    blk.lines.forEach(ln=>{ s.addText(ln,{x:6.7,y:yy,w:6.4,h:0.28,fontSize:11,color:C.text}); yy+=0.3; }); yy+=0.08;
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:3.5,w:5.8,h:3.1,fill:{color:C.acc,transparency:88},line:{color:C.acc,width:2}});
  s.addText('決策結果',{x:0.55,y:3.53,w:5.5,h:0.35,fontSize:13,bold:true,color:C.acc});
  ['情緒：緊張 → 調整 +0.10 → 最終閾值 0.55','K = 0.70 ≥ 0.50',
   '→ 強制 deliberate（K override，不看C值）','→ 呼叫 Phi-3.5-Vision-Instruct 模型',
   '→ 模型組 LTM + STM prompt 推理回應','C = 0.57 也 ≥ 0.55（兩個條件都成立）',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:3.96+i*0.37,w:5.5,h:0.34,fontSize:i===2?13:11,bold:i===2,color:i===2?C.acc:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 8: Markov 4-source overview
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜Markov 引擎 — 四來源加權機率',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:12.5,h:0.65,fill:{color:C.dark,transparency:5},line:{color:C.acc,width:2}});
  s.addText('P_final(a) = α·P_sched(a) + β·P_iner(a) + γ·P_situ(a) + δ·P_value(a)',
    {x:0.5,y:0.86,w:12.3,h:0.56,fontSize:16,bold:true,color:C.white,align:'center'});
  const sources=[
    {name:'α — schedule_score',weight:'α = 0.40（正常）/ 0.10（重大事件）',color:C.green,lines:['輸入：當前時間表時段 {time, action, location}','完全匹配 action → 1.0','同類別（同job_category）→ 0.5','不相關 → 0.0','「前往」特例：未到目的地提升0.6，已到×0.3','Softmax 溫度 T=0.4（低溫使高分更突出）']},
    {name:'β — inertia_score',weight:'β = 0.30（固定）',color:C.mid,lines:['輸入：最近N筆STM行動動詞序列','歷史不足2筆 → 退回均勻分布','統計：current_verb → 各行動的轉移次數','Laplace平滑：count = transitions.get(a,0) + 1','score[a] = math.log(count)','Softmax 溫度 T=1.0']},
    {name:'γ — situation_score',weight:'γ = 0.30（正常）/ 0.60（重大事件）',color:C.acc,lines:['輸入：yolo_desc + scene_text + location','ACTION_KEYWORD_BOOST：每命中關鍵字 +0.15','EMOTION_TO_ACTION_BOOST：情緒→特定行動加成','同地點有人：對話 +0.30','Softmax 溫度 T=1.0']},
    {name:'δ — value_score',weight:'δ = 0.15（需有action_values才啟用，否則=0）',color:'E17055',lines:['輸入：ActionValueTracker.get_scores()','正值行動 → 傾向選擇','負值行動 → 傾向迴避','shift最小值歸0後 softmax','無記錄時 δ=0，三源合一']},
  ];
  sources.forEach((src,si)=>{
    const x=0.4+(si%2)*6.4, y=1.6+Math.floor(si/2)*2.9;
    s.addShape(pptx.ShapeType.rect,{x,y,w:6.1,h:2.7,fill:{color:src.color,transparency:90},line:{color:src.color,width:1.5}});
    s.addText(src.name,{x:x+0.15,y:y+0.05,w:5.8,h:0.38,fontSize:13,bold:true,color:src.color});
    s.addText(src.weight,{x:x+0.15,y:y+0.43,w:5.8,h:0.3,fontSize:10.5,color:C.sub,italic:true});
    src.lines.forEach((ln,li)=> s.addText(ln,{x:x+0.2,y:y+0.76+li*0.3,w:5.75,h:0.28,fontSize:11,color:C.text}));
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 9: Markov special mechanisms
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜特殊機制：睡覺時間曲線 + 重大事件 + 正規化',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:7.6,h:3.0,fill:{color:C.blue,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('睡覺時間修正曲線（_time_sleep_score）',{x:0.55,y:0.85,w:7.3,h:0.38,fontSize:13,bold:true,color:C.mid});
  [['時間段','ts 值','scale = exp(ts×2)','效果'],
   ['07:00–18:00（工作）','ts = −1.5','exp(−3.0) ≈ 0.050','睡覺機率 ≈ 保底0.005'],
   ['18:00–23:00（漸進）','ts: 0.0→+0.5','exp(ts) ≈ 1.0→1.65','睡覺機率線性回升'],
   ['23:00+ （深夜）','ts = +0.5','exp(0.5) ≈ 1.65','睡覺機率提升65%'],
  ].forEach((row,ri)=> row.forEach((cell,ci)=>
    s.addText(cell,{x:0.55+ci*1.85,y:1.28+ri*0.47,w:1.8,h:0.43,fontSize:11,bold:ri===0,
      color:ri===0?C.mid:C.text, fill:ri===0?{color:C.mid,transparency:70}:undefined})));
  s.addShape(pptx.ShapeType.rect,{x:8.2,y:0.82,w:5.1,h:2.5,fill:{color:C.acc,transparency:88},line:{color:C.acc,width:1.5}});
  s.addText('重大事件權重切換',{x:8.35,y:0.85,w:4.8,h:0.38,fontSize:13,bold:true,color:C.acc});
  s.addText('觸發條件：K ≥ MAJOR_EVENT_K_THRESHOLD = 0.60',{x:8.35,y:1.28,w:4.8,h:0.3,fontSize:11,color:C.text});
  [['','α(sched)','β(iner)','γ(situ)'],['正常模式','0.40','0.30','0.30'],['事件模式','0.10','0.30','0.60']].forEach((row,ri)=>
    row.forEach((cell,ci)=> s.addText(cell,{x:8.35+ci*1.2,y:1.65+ri*0.47,w:1.15,h:0.43,fontSize:11,bold:ri===0,
      color:ri===0?C.acc:(ri===2&&ci>0?C.acc:C.text)})));
  s.addText('目的：模擬「地震時有人繼續工作、有人逃跑」\n情境權重大增，時間表影響降低',{x:8.35,y:2.65,w:4.8,h:0.55,fontSize:10.5,color:C.sub,italic:true});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:4.0,w:12.9,h:2.4,fill:{color:C.green,transparency:92},line:{color:C.green,width:1.5}});
  s.addText('最終正規化與保底機制',{x:0.55,y:4.03,w:12.6,h:0.38,fontSize:13,bold:true,color:C.green});
  ['① 合併：P_raw(a) = α·P_sched + β·P_iner + γ·P_situ + δ·P_value',
   '② 保底：final_prob(a) = max(P_raw(a), MIN_PROB_FLOOR)  where MIN_PROB_FLOOR = 0.005',
   '③ 正規化：total = Σ final_prob(a)，p(a) = round(final_prob(a) / total, 4)',
   '④ 修正浮點誤差：確保所有行動機率總和精確 = 1.0',
   '⑤ 對話目標解析：選到「對話」且同地點有人 → target = 第一個同地點角色；無人 → 重新採樣',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:4.48+i*0.35,w:12.6,h:0.32,fontSize:11.5,color:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 10: Markov simulation
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜模擬：Amy 咖啡廳 08:30 機率計算',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:6.1,h:2.3,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('情境',{x:0.55,y:0.85,w:5.8,h:0.35,fontSize:12,bold:true,color:C.mid});
  ['時間：08:30（第3天）   地點：咖啡廳',
   '時間表：{08:30, 賣咖啡, 咖啡廳}',
   '最近STM行動：["前往","整理店面","賣咖啡","賣咖啡"]',
   'YOLO：「咖啡廳有1個客人、1個杯子、1個咖啡機」',
   '同地點角色：[]（無）   情緒：平靜   重大事件：否',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.23+i*0.34,w:5.8,h:0.31,fontSize:11,color:C.text}));
  [{name:'A. schedule',color:C.green,rows:[['賣咖啡','1.0 → softmax(T=0.4)','≈ 0.62'],['work類（收銀/補貨）','0.5 → softmax','各≈ 0.09'],['其他','0.0 → softmax','各≈ 0.01']]},
   {name:'B. inertia',color:C.mid,rows:[['current_verb = "賣咖啡"','',''],['賣咖啡→賣咖啡 count=2','log(2)≈0.693','≈ 0.45'],['其他 count=1','log(1)=0','≈ 0.028各']]},
   {name:'C. situation',color:C.acc,rows:[['賣咖啡','命中「客人」「咖啡」→+0.30','≈ 0.38'],['收銀','命中「客人」→+0.15','≈ 0.28'],['對話','無同地點角色→+0','≈ 0.02']]},
   {name:'D. value (δ=0)',color:'E17055',rows:[['無action_values記錄','均勻分布','無效'],['δ = 0.0','不參與合併','—']]},
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
  s.addText('最終合併（α=0.4, β=0.3, γ=0.3, δ=0）',{x:6.85,y:0.85,w:6.3,h:0.35,fontSize:12,bold:true,color:C.yel});
  ['賣咖啡：0.4×0.62 + 0.3×0.45 + 0.3×0.38 = 0.248+0.135+0.114 = 0.497',
   '收 銀：0.4×0.09 + 0.3×0.028 + 0.3×0.28 ≈ 0.036+0.008+0.084 = 0.128',
   '對 話：0.4×0.01 + 0.3×0.028 + 0.3×0.00 ≈ 0.004+0.008+0 = 0.012',
   '睡 覺：08:30 屬工作時段，ts=-1.5，scale≈0.05 → 大幅壓制',
   '正規化後 TOP：賣咖啡≈0.507, 收銀≈0.131, 補貨≈0.082...',
  ].forEach((ln,i)=> s.addText(ln,{x:6.85,y:1.25+i*0.35,w:6.3,h:0.32,fontSize:11,color:i===4?C.yel:C.white}));
}

// ══════════════════════════════════════════════════════
// SLIDE 11: Deliberate path
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3b｜Deliberate 路徑 — LTM 擴散激活 + Phi-3.5 推理',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  [{n:'①',title:'auto_query_nodes',color:C.mid,lines:['組合查詢節點：角色自己 + 對話對象 + 同地點角色 + 當前位置','+ 最近3筆STM中出現的角色名字','範例：["Amy", "Ben", "咖啡廳"]']},
   {n:'②',title:'spreading_retrieve（BFS 擴散激活）',color:'6C5CE7',lines:['起始節點活化值 = 1.0','prop_activation_at_hop = activation_decay^(hop-1) = 0.4^(hop-1)','hop=1: activation=1.0   hop=2: activation=0.4','過濾：activation < HAM_RETRIEVE_THRESHOLD(0.3) → 不取','HAM_TRAVERSE_MAX_HOPS = 2  HAM_ACTIVATION_DECAY = 0.4','排序：activation降序，相同則hops升序，取 top_k=20']},
   {n:'③',title:'propositions_to_narrative',color:C.green,lines:['將 HAM 5元組轉換為自然語言敘述','範例：{Amy, 遇見, Ben, 咖啡廳, 第3天早上}','→  「你在第3天早上在咖啡廳遇見Ben。」','組成多段 LTM 上下文文字']},
   {n:'④',title:'build_deliberate → 呼叫 Phi-3.5',color:C.acc,lines:['組裝完整 prompt：角色設定 + LTM敘述 + STM最近5筆','+ 困惑度數值 + 當前情境 + 問題','max_tokens 依場景設定（通常200-500）','輸出：action + target + content + thought']},
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
  s.addText('Layer 4｜短期記憶（STM）— 三層情節結構',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:7.2,h:4.8,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('STM Turn 結構（一筆記錄）',{x:0.55,y:0.85,w:7.0,h:0.38,fontSize:13,bold:true,color:C.mid});
  s.addText('turn_id 格式：D001_T003  （第1天第3個turn）\n摘要turn：D002_T000（T000保留給昨日摘要）',{x:0.55,y:1.28,w:7.0,h:0.55,fontSize:11,color:C.sub});
  let yy=1.9;
  [{name:'perception',color:C.green,fields:['location    → 當前地點','yolo_desc   → YOLO偵測描述','scene_text  → 場景文字描述']},
   {name:'event',color:C.acc,fields:['input_text  → 接收的對話/事件','action      → 執行的行動動詞','target      → 對象角色','content     → 對話內容']},
   {name:'inner',color:'6C5CE7',fields:['thought  → 內心想法','emotion  → 當前情緒']},
  ].forEach(layer=>{
    s.addShape(pptx.ShapeType.rect,{x:0.55,y:yy,w:6.9,h:0.32,fill:{color:layer.color,transparency:70}});
    s.addText(layer.name,{x:0.65,y:yy+0.02,w:6.8,h:0.28,fontSize:12,bold:true,color:C.white}); yy+=0.35;
    layer.fields.forEach(f=>{ s.addText(f,{x:0.8,y:yy,w:6.7,h:0.3,fontSize:11,color:C.text}); yy+=0.32; }); yy+=0.1;
  });
  s.addShape(pptx.ShapeType.rect,{x:7.8,y:0.82,w:5.5,h:2.5,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('關鍵參數',{x:7.95,y:0.85,w:5.2,h:0.35,fontSize:13,bold:true,color:C.green});
  ['STM_SAFETY_LIMIT = 50（超過觸發中途濃縮）','STM_KEEP_AFTER_CONS = 5（睡眠後保留最近5筆）','安全閥觸發：midday consolidation（中途濃縮）']
    .forEach((p,pi)=> s.addText(p,{x:7.95,y:1.28+pi*0.42,w:5.2,h:0.38,fontSize:11.5,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:7.8,y:3.45,w:5.5,h:2.2,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('主要方法',{x:7.95,y:3.48,w:5.2,h:0.35,fontSize:13,bold:true,color:C.mid});
  ['add_turn()  — 寫入一筆3層記錄','get_today_narrative()  — 輸出敘述化文字',
   'get_recent_actions(n)  — 取最近n筆行動（給inertia）','shrink_to_summary()  — 睡眠後縮減STM','is_over_safety_limit()  — 安全閥檢查']
    .forEach((m,mi)=> s.addText(m,{x:7.95,y:3.9+mi*0.35,w:5.2,h:0.32,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:5.75,w:12.9,h:1.5,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('敘述化輸出範例（_turn_to_narrative）',{x:0.55,y:5.78,w:12.6,h:0.3,fontSize:11,bold:true,color:C.dark});
  s.addText('[08:00] 在咖啡廳，看到2個人、1個杯子。  聽到：Ben對你說：早安。  對Ben說：「早安，今天想喝什麼？」  內心想：Ben看起來心情不錯（情緒：平靜）',
    {x:0.55,y:6.12,w:12.6,h:0.55,fontSize:11,color:C.text});
}

// ══════════════════════════════════════════════════════
// SLIDE 13: LTM HAM + decay
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜長期記憶（LTM）— HAM 5元組 + 衰減機制',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:6.2,h:4.5,fill:{color:'6C5CE7',transparency:90},line:{color:'6C5CE7',width:1.5}});
  s.addText('HAM 5元組結構（Human Associative Memory）',{x:0.55,y:0.85,w:6.0,h:0.35,fontSize:12,bold:true,color:'6C5CE7'});
  s.addText('理論基礎：Anderson & Bower (1973)',{x:0.55,y:1.23,w:6.0,h:0.3,fontSize:10.5,color:C.sub,italic:true});
  [{f:'id',v:'"L001"  — 唯一識別碼'},{f:'subject',v:'"Amy"  — 主語'},{f:'relation',v:'"遇見"  — 關係/動詞'},
   {f:'object',v:'"Ben"  — 受語'},{f:'location',v:'"咖啡廳"  — 地點上下文'},{f:'time',v:'"第3天 早上"  — 時間上下文'},
   {f:'strength',v:'1.0  — 記憶強度（0.0~1.0）'},{f:'access_count',v:'0  — 被提取次數'},{f:'encoded_day',v:'3  — 寫入的天數'},
  ].forEach((f,fi)=>{
    s.addText(f.f+':',{x:0.65,y:1.6+fi*0.38,w:1.6,h:0.35,fontSize:11,bold:true,color:'6C5CE7'});
    s.addText(f.v,{x:2.3,y:1.6+fi*0.38,w:4.2,h:0.35,fontSize:11,color:C.text});
  });
  s.addShape(pptx.ShapeType.rect,{x:6.8,y:0.82,w:6.5,h:3.2,fill:{color:C.acc,transparency:90},line:{color:C.acc,width:1.5}});
  s.addText('衰減機制（apply_decay）',{x:6.95,y:0.85,w:6.2,h:0.35,fontSize:13,bold:true,color:C.acc});
  s.addText('公式：actual_decay = LTM_DECAY_RATE / (1 + access_count × 0.5)',{x:6.95,y:1.25,w:6.2,h:0.32,fontSize:12,bold:true,color:C.dark});
  s.addText('LTM_DECAY_RATE = 0.05（每天）',{x:6.95,y:1.62,w:6.2,h:0.28,fontSize:11,color:C.sub});
  [['access_count','actual_decay/天','說明'],['0','0.05 / 1.0 = 0.050','未被使用，正常衰減'],
   ['2','0.05 / 2.0 = 0.025','提取2次，衰減減半'],['10','0.05 / 6.0 ≈ 0.008','常用記憶，幾乎不衰減'],
  ].forEach((row,ri)=> row.forEach((cell,ci)=>
    s.addText(cell,{x:6.95+ci*2.1,y:1.98+ri*0.42,w:2.0,h:0.38,fontSize:11,bold:ri===0,color:ri===0?C.acc:(ri===3?C.green:C.text)})));
  s.addShape(pptx.ShapeType.rect,{x:6.8,y:4.15,w:6.5,h:2.15,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('touch() 提取加強 + prune() 遺忘修剪',{x:6.95,y:4.18,w:6.2,h:0.35,fontSize:13,bold:true,color:C.green});
  ['touch()：被 spreading_retrieve 命中時呼叫','  → access_count += 1','  → strength 重置為 1.0（記憶強化）',
   'prune()：每天睡眠後執行','  → strength < LTM_FORGET_THRESHOLD(0.2) → 刪除','  → 效果：久未使用的記憶自然消失',
  ].forEach((m,mi)=> s.addText(m,{x:6.95,y:4.6+mi*0.3,w:6.2,h:0.28,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:5.45,w:6.2,h:1.3,fill:{color:C.yel,transparency:85},line:{color:C.yel,width:1}});
  s.addText('記憶存活天數估算（未被提取）',{x:0.55,y:5.48,w:6.0,h:0.3,fontSize:11,bold:true,color:C.dark});
  s.addText('strength從1.0開始，每天減0.05\n→ 到 strength=0.2 需要 (1.0-0.2)/0.05 = 16 天後自動刪除',{x:0.55,y:5.82,w:6.0,h:0.55,fontSize:11,color:C.text});
}

// ══════════════════════════════════════════════════════
// SLIDE 14: Spreading activation
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜擴散激活（Spreading Activation）— BFS 記憶檢索',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  s.addText('理論基礎：Anderson (1983) ACT* — 記憶節點在語意網絡中擴散傳播',{x:0.4,y:0.75,w:12.5,h:0.3,fontSize:12,color:C.sub,italic:true});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:1.12,w:7.5,h:5.4,fill:{color:'6C5CE7',transparency:90},line:{color:'6C5CE7',width:1.5}});
  s.addText('BFS 擴散激活演算法',{x:0.55,y:1.15,w:7.2,h:0.38,fontSize:13,bold:true,color:'6C5CE7'});
  ['① 初始化：起始節點集合（query_nodes 中每個節點 activation=1.0）',
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
  ].forEach((step,si)=> s.addText(step,{x:0.55,y:1.6+si*0.33,w:7.3,h:0.3,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:8.1,y:1.12,w:5.2,h:2.4,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('關鍵參數',{x:8.25,y:1.15,w:4.9,h:0.38,fontSize:13,bold:true,color:C.mid});
  [['HAM_TRAVERSE_MAX_HOPS','= 2'],['HAM_ACTIVATION_DECAY','= 0.4'],['HAM_RETRIEVE_THRESHOLD','= 0.3'],['top_k（返回上限）','= 20']]
    .forEach((p,pi)=>{
      s.addText(p[0],{x:8.25,y:1.6+pi*0.45,w:3.5,h:0.4,fontSize:11,color:C.text});
      s.addText(p[1],{x:11.8,y:1.6+pi*0.45,w:1.4,h:0.4,fontSize:12,bold:true,color:C.mid});
    });
  s.addShape(pptx.ShapeType.rect,{x:8.1,y:3.65,w:5.2,h:2.85,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('範例（Amy + Ben + 咖啡廳 為起始節點）',{x:8.25,y:3.68,w:4.9,h:0.38,fontSize:12,bold:true,color:C.green});
  [['命題','hop','activation'],['Amy 遇見 Ben（咖啡廳）','1','1.0 ✓'],['Amy 暗戀 David','1','1.0 ✓'],
   ['Ben 送給 Amy 禮物','2','0.4 ✓'],['Ben 在 超市 工作','2','0.4 ✓'],['David 是 畫家','3','0.16 ✗過濾'],
  ].forEach((row,ri)=> row.forEach((cell,ci)=>
    s.addText(cell,{x:8.25+ci*1.7,y:4.12+ri*0.38,w:1.65,h:0.35,fontSize:ri===5&&ci===2?10:11,bold:ri===0,color:ri===0?C.green:(ri===5?C.acc:C.text)})));
}

// ══════════════════════════════════════════════════════
// SLIDE 15: RL Value Tracker
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 3a｜RL 價值追蹤器（ActionValueTracker）',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:6.2,h:2.5,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('價值衰減機制（每 tick 執行）',{x:0.55,y:0.85,w:6.0,h:0.35,fontSize:13,bold:true,color:C.mid});
  s.addText('公式：V(a) = V(a) × VALUE_DECAY  （VALUE_DECAY = 0.85）',{x:0.55,y:1.25,w:6.0,h:0.32,fontSize:12,bold:true,color:C.dark});
  ['初始 V(賣咖啡) = 0.50','tick +1: 0.50 × 0.85 = 0.425','tick +2: 0.425 × 0.85 = 0.361',
   'tick +5: 0.50 × 0.85⁵ ≈ 0.222','→ 舊記憶自然淡化，近期行為影響更大',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:1.62+i*0.32,w:6.0,h:0.28,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.8,y:0.82,w:6.5,h:4.6,fill:{color:C.yel,transparency:88},line:{color:C.yel,width:1.5}});
  s.addText('獎勵信號定義（reward constants）',{x:6.95,y:0.85,w:6.2,h:0.35,fontSize:13,bold:true,color:C.dark});
  [{event:'情緒改善（負→正）',r:'+0.50',c:C.green},{event:'情緒回歸中性（負→平靜）',r:'+0.15',c:C.green},
   {event:'情緒惡化（正/平靜→負）',r:'−0.45',c:C.acc},{event:'C下降 ≥ 0.12（困惑度降低）',r:'+0.30',c:C.green},
   {event:'C上升 ≥ 0.15（困惑度飆升）',r:'−0.35',c:C.acc},{event:'對話被接受（DIALOGUE_ACCEPT）',r:'+0.25',c:C.green},
   {event:'時間表命中（SCHEDULE_HIT）',r:'+0.20',c:C.green},
  ].forEach((rw,ri)=>{
    s.addText(rw.event,{x:6.95,y:1.3+ri*0.47,w:4.8,h:0.43,fontSize:11.5,color:C.text});
    s.addText(rw.r,{x:12.0,y:1.3+ri*0.47,w:1.2,h:0.43,fontSize:13,bold:true,color:rw.c,align:'right'});
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:3.45,w:6.2,h:2.2,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('Q值更新機制（類 Q-learning + Eligibility Trace）',{x:0.55,y:3.48,w:6.0,h:0.35,fontSize:12,bold:true,color:C.green});
  ['① 每tick結束後計算當前獎勵 r','② 所有行動的 Q 值 × VALUE_DECAY（衰減）',
   '③ Q(chosen_action) += r（當前行動加獎勵）','④ Markov delta分支使用 get_scores() 作為 P_value',
   '⑤ 效果：好行動累積正值，壞行動累積負值','   類似 Q(s,a) ← Q(s,a) + α[r - Q(s,a)]',
  ].forEach((q,qi)=> s.addText(q,{x:0.55,y:3.88+qi*0.3,w:6.0,h:0.28,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:5.75,w:12.9,h:1.45,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('模擬範例：Amy 告白事件後',{x:0.55,y:5.78,w:12.6,h:0.3,fontSize:11,bold:true,color:C.dark});
  s.addText('情緒：平靜→緊張（惡化）→ reward=-0.45   C上升0.22≥0.15 → reward=-0.35   合計reward=-0.80\n→ Q(休息) += -0.80  →  下一tick休息的機率（delta分支）降低，Markov更傾向對話或前往',
    {x:0.55,y:6.12,w:12.6,h:0.55,fontSize:11,color:C.text});
}

// ══════════════════════════════════════════════════════
// SLIDE 16: Weight Adapter
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜Weight Adapter — 每日 SGD-like 自適應學習',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:5.5,h:1.9,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('初始預設權重',{x:0.55,y:0.85,w:5.2,h:0.35,fontSize:13,bold:true,color:C.mid});
  [['α (schedule)','0.40'],['β (inertia)','0.30'],['γ (situation)','0.20'],['δ (value)','0.10']]
    .forEach((d,di)=>{
      s.addText(d[0],{x:0.55,y:1.28+di*0.34,w:3.5,h:0.3,fontSize:12,color:C.text});
      s.addText(d[1],{x:4.2,y:1.28+di*0.34,w:1.5,h:0.3,fontSize:13,bold:true,color:C.mid});
    });
  s.addShape(pptx.ShapeType.rect,{x:6.1,y:0.82,w:7.2,h:2.8,fill:{color:C.dark,transparency:8},line:{color:C.acc,width:2}});
  s.addText('SGD-like 更新公式（update_weights，每天睡覺時執行）',{x:6.25,y:0.85,w:7.0,h:0.35,fontSize:12,bold:true,color:C.yel});
  s.addText('α += LR × r × (sched_p − α)\nβ += LR × r × (iner_p  − β)\nγ += LR × r × (situ_p  − γ)\nδ += LR × r × (val_p   − δ)\n\nLR = LEARNING_RATE = 0.05\nr = 當日平均reward   sched_p/iner_p/situ_p/val_p = 各來源在該tick的機率',
    {x:6.25,y:1.25,w:6.9,h:2.2,fontSize:12,color:C.white});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:2.85,w:5.5,h:2.2,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('後處理',{x:0.55,y:2.88,w:5.2,h:0.35,fontSize:13,bold:true,color:C.green});
  ['① Clip：每個權重 clamp 到 [0.05, 0.85]','   MIN_WEIGHT = 0.05   MAX_WEIGHT = 0.85',
   '② 正規化：total = α+β+γ+δ','   每個權重 /= total（總和=1）','③ 浮點修正：餘差加回 α（確保精確=1.0）',
  ].forEach((p,pi)=> s.addText(p,{x:0.55,y:3.3+pi*0.35,w:5.2,h:0.32,fontSize:11,color:C.text}));
  s.addShape(pptx.ShapeType.rect,{x:6.1,y:3.75,w:7.2,h:3.5,fill:{color:C.code},line:{color:C.gray,width:1}});
  s.addText('模擬範例：Amy 第3天學習後的權重更新',{x:6.25,y:3.78,w:7.0,h:0.35,fontSize:12,bold:true,color:C.dark});
  ['初始：α=0.40, β=0.30, γ=0.20, δ=0.10','',
   '當日記錄（3 ticks）：',
   'tick1: r=+0.20, sched_p=0.62, iner_p=0.45, situ_p=0.38, val_p=0',
   'tick2: r=-0.45, sched_p=0.30, iner_p=0.35, situ_p=0.55, val_p=0',
   'tick3: r=+0.25, sched_p=0.50, iner_p=0.40, situ_p=0.42, val_p=0.2','',
   '更新後（clip+正規化）→ α≈0.39, β≈0.30, γ≈0.21, δ≈0.10',
   '→ Amy 略微增加對「情境」的依賴（γ上升）',
  ].forEach((ln,i)=> s.addText(ln,{x:6.25,y:4.2+i*0.33,w:7.0,h:0.3,fontSize:11,color:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 17: Sleep consolidation 12 steps
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('Layer 4｜睡眠鞏固 12 步驟（consolidation.py）',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addText('理論基礎：Diekelmann & Born (2010) — 睡眠不清空記憶，而是「轉移與整合」STM→LTM',{x:0.4,y:0.73,w:12.5,h:0.3,fontSize:11,color:C.sub,italic:true});
  const steps12=[
    {n:'①',title:'取出今日STM敘述',detail:'stm.get_today_narrative() → narrative文字',c:C.mid},
    {n:'②',title:'抽取HAM 5元組',detail:'prompt_extract_ham(narrative)，Phi-3.5，max_tokens=500 → HAM列表',c:C.mid},
    {n:'③',title:'篩選重要HAM',detail:'prompt_select_ltm，max_tokens=200，最多5筆寫入LTM',c:C.mid},
    {n:'④',title:'寫入LTM',detail:'ltm.encode_batch(selected_hams) → 新增節點+邊到MemoryGraph',c:'6C5CE7'},
    {n:'⑤',title:'更新LTM摘要',detail:'模型生成新摘要，max_tokens=80，上限200字',c:'6C5CE7'},
    {n:'⑥',title:'更新關係摘要',detail:'找出narrative中出現的角色，模型更新各對關係描述，max_tokens=80',c:'6C5CE7'},
    {n:'⑦',title:'情緒判斷',detail:'today_max_K<0.5→直接平靜；≥0.5→模型推斷，max_tokens=10',c:C.acc},
    {n:'⑧',title:'生成隔天時間表',detail:'職業範本+LTM摘要，模型生成，max_tokens=500',c:C.acc},
    {n:'⑨',title:'時間表規則檢查',detail:'確認必要時段（睡覺/起床）、時間順序正確',c:C.acc},
    {n:'⑩',title:'LTM衰減+修剪',detail:'apply_decay() 全體衰減；prune() 刪除 strength<0.2',c:C.green},
    {n:'⑪',title:'STM縮減',detail:'shrink_to_summary()：保留摘要turn + 最近5筆（STM_KEEP_AFTER_CONS=5）',c:C.green},
    {n:'⑫',title:'更新權重+推進天數',detail:'weight_adapter.update_weights()；character.advance_day()',c:C.green},
  ];
  steps12.slice(0,6).forEach((step,si)=>{
    const y=1.12+si*1.02;
    s.addShape(pptx.ShapeType.rect,{x:0.4,y,w:6.15,h:0.9,fill:{color:step.c,transparency:88},line:{color:step.c,width:1.5}});
    s.addText(`${step.n} ${step.title}`,{x:0.5,y:y+0.05,w:6.0,h:0.34,fontSize:12,bold:true,color:step.c});
    s.addText(step.detail,{x:0.55,y:y+0.42,w:5.9,h:0.4,fontSize:11,color:C.text});
  });
  steps12.slice(6,12).forEach((step,si)=>{
    const y=1.12+si*1.02;
    s.addShape(pptx.ShapeType.rect,{x:6.75,y,w:6.15,h:0.9,fill:{color:step.c,transparency:88},line:{color:step.c,width:1.5}});
    s.addText(`${step.n} ${step.title}`,{x:6.85,y:y+0.05,w:6.0,h:0.34,fontSize:12,bold:true,color:step.c});
    s.addText(step.detail,{x:6.9,y:y+0.42,w:5.9,h:0.4,fontSize:11,color:C.text});
  });
}

// ══════════════════════════════════════════════════════
// SLIDE 18: Dialogue system
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('對話系統（Dialogue Flow）— 接受/拒絕機率計算',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:24,bold:true,color:C.dark});
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:0.82,w:7.5,h:3.5,fill:{color:C.mid,transparency:90},line:{color:C.mid,width:1.5}});
  s.addText('對話接受機率公式',{x:0.55,y:0.85,w:7.2,h:0.35,fontSize:13,bold:true,color:C.mid});
  s.addText('P_accept = base + relation_bonus + leisure_bonus + work_penalty',{x:0.55,y:1.28,w:7.2,h:0.32,fontSize:13,bold:true,color:C.dark});
  [{term:'DIALOGUE_BASE_ACCEPT',val:'= 0.50',desc:'基礎接受機率（任何人都有50%接受）'},
   {term:'DIALOGUE_RELATION_BONUS',val:'= +0.30',desc:'好感關係加成（認識的人）'},
   {term:'DIALOGUE_LEISURE_BONUS',val:'= +0.20',desc:'休閒時間加成（不忙碌時）'},
   {term:'DIALOGUE_WORK_PENALTY',val:'= −0.30',desc:'工作時間懲罰（忙碌中被打擾）'},
  ].forEach((t,ti)=>{
    s.addText(t.term,{x:0.55,y:1.7+ti*0.47,w:3.4,h:0.42,fontSize:11,bold:true,color:C.mid});
    s.addText(t.val,{x:3.95,y:1.7+ti*0.47,w:1.2,h:0.42,fontSize:12,bold:true,color:ti===3?C.acc:C.green});
    s.addText(t.desc,{x:5.2,y:1.7+ti*0.47,w:2.6,h:0.42,fontSize:10.5,color:C.sub});
  });
  s.addText('DIALOGUE_MAX_TURNS = 10（每段對話最多10回合）',{x:0.55,y:3.63,w:7.2,h:0.3,fontSize:11,color:C.sub});
  s.addShape(pptx.ShapeType.rect,{x:8.1,y:0.82,w:5.2,h:3.5,fill:{color:C.yel,transparency:85},line:{color:C.yel,width:1.5}});
  s.addText('計算範例',{x:8.25,y:0.85,w:4.9,h:0.35,fontSize:13,bold:true,color:C.dark});
  [{scenario:'Ben找Amy（休閒，有好感）',calc:'0.50 + 0.30 + 0.20 = 1.00',note:'必然接受'},
   {scenario:'Ben找Amy（工作中，有好感）',calc:'0.50 + 0.30 − 0.30 = 0.50',note:'50%接受'},
   {scenario:'陌生人找Amy（休閒）',calc:'0.50 + 0.00 + 0.20 = 0.70',note:'70%接受'},
   {scenario:'陌生人找Amy（工作中）',calc:'0.50 + 0.00 − 0.30 = 0.20',note:'20%接受'},
  ].forEach((ex,ei)=>{
    s.addShape(pptx.ShapeType.rect,{x:8.1,y:1.3+ei*0.74,w:5.2,h:0.65,fill:{color:C.code}});
    s.addText(ex.scenario,{x:8.2,y:1.32+ei*0.74,w:5.0,h:0.25,fontSize:10.5,bold:true,color:C.dark});
    s.addText(ex.calc+'  → '+ex.note,{x:8.2,y:1.57+ei*0.74,w:5.0,h:0.25,fontSize:11,color:C.text});
  });
  s.addShape(pptx.ShapeType.rect,{x:0.4,y:4.45,w:12.9,h:2.8,fill:{color:C.green,transparency:90},line:{color:C.green,width:1.5}});
  s.addText('對話執行流程',{x:0.55,y:4.48,w:12.6,h:0.35,fontSize:13,bold:true,color:C.green});
  ['① 發起方（agent A）Markov採樣得到「對話」→ target = 同地點角色B',
   '② 計算 P_accept，隨機決定 B 是否接受',
   '③ 接受：設定雙方 action_lock=2（不可中斷），對話session開始',
   '④ 每回合：A生成內容（Markov或deliberate）→ STM寫入 → B回應 → STM寫入',
   '⑤ 達到 DIALOGUE_MAX_TURNS=10 或任一方主動結束 → 對話結束，action_lock清零',
   '⑥ 對話結束：reward += DIALOGUE_ACCEPT(+0.25)，寫入ValueTracker',
  ].forEach((ln,i)=> s.addText(ln,{x:0.55,y:4.9+i*0.35,w:12.6,h:0.32,fontSize:11.5,color:C.text}));
}

// ══════════════════════════════════════════════════════
// SLIDE 19: Complete end-to-end trace
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.bg };
  s.addText('完整模擬追蹤：Amy 第3天 08:30 一個完整 Tick',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  const trace=[
    {phase:'TICK 開始',color:C.mid,lines:['時間：D3 08:30  角色：Amy  地點：咖啡廳','上一tick行動：整理店面  情緒：平靜  當前pending_action：None']},
    {phase:'YOLO感知',color:'E17055',lines:['YOLO偵測：咖啡廳有1個客人、1個杯子、1個咖啡機','yolo_desc更新 → "咖啡廳有1個客人、1個杯子、1個咖啡機"','interrupt_queue：無新事件']},
    {phase:'Phase 1 執行',color:C.green,lines:['pending_action = None → 跳過Phase 1']},
    {phase:'Phase 2 決策（困惑度計算）',color:C.acc,lines:['U=0.50（上tick賣咖啡0.55 vs 對話0.30，gap=0.25）','K=0.00（無衝突、無情緒關鍵字）','S=0.00（無驚訝關鍵字，且已有LTM）','C = 0.4×0.50 + 0.3×0.00 + 0.3×0.00 = 0.20','情緒平靜 → 最終閾值=0.45    K<0.5且C=0.20<0.45 → intuitive']},
    {phase:'Markov 機率計算（intuitive）',color:'6C5CE7',lines:['α=0.40: sched→賣咖啡≈0.62  β=0.30: iner→賣咖啡≈0.45','γ=0.30: situ→賣咖啡≈0.38（客人+咖啡機命中）','合併：0.4×0.62+0.3×0.45+0.3×0.38 = 0.497','睡覺：ts=-1.5→scale≈0.05，被壓制  正規化→賣咖啡≈0.507','採樣結果：賣咖啡（機率最高，加權隨機採樣）']},
    {phase:'STM 寫入',color:C.mid,lines:['turn_id: D003_T005  time: "08:30"','perception: {咖啡廳, "1客人1杯子1咖啡機", ""}','event: {input:"", action:"賣咖啡", target:"", content:""}','inner: {thought:"繼續工作，今天客人挺多", emotion:"平靜"}']},
    {phase:'RL獎勵計算',color:C.green,lines:['時間表命中賣咖啡 → reward += SCHEDULE_HIT(+0.20)','情緒無變化 → 無情緒獎勵   C變化<0.12 → 無困惑獎勵','ValueTracker.update("賣咖啡", +0.20)  所有行動×VALUE_DECAY(0.85)']},
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
  s.addText('完整參數速查表（config/world_config.py + 各模組）',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:22,bold:true,color:C.dark});
  const sections=[
    {title:'STM / LTM 記憶',color:'6C5CE7',params:[['STM_SAFETY_LIMIT','50','STM超過觸發中途濃縮'],['STM_KEEP_AFTER_CONS','5','睡眠後保留最近N筆'],['LTM_DECAY_RATE','0.05','每天LTM衰減速率'],['LTM_FORGET_THRESHOLD','0.2','低於此值刪除']]},
    {title:'HAM 擴散激活',color:C.mid,params:[['HAM_TRAVERSE_MAX_HOPS','2','BFS最大跳數'],['HAM_ACTIVATION_DECAY','0.4','每跳激活衰減率'],['HAM_RETRIEVE_THRESHOLD','0.3','激活值低於此不取']]},
    {title:'Markov 引擎',color:C.green,params:[['MARKOV_WEIGHTS_NORMAL','α:0.4 β:0.3 γ:0.3','正常模式（δ另計）'],['MARKOV_WEIGHTS_EVENT','α:0.1 β:0.3 γ:0.6','K≥0.6時事件模式'],['MAJOR_EVENT_K_THRESHOLD','0.60','切換事件權重的K門檻'],['MIN_PROB_FLOOR','0.005','每行動最低機率保底'],['KEYWORD_BOOST_PER_HIT','0.15','情境關鍵字每命中加分']]},
    {title:'RL 價值追蹤',color:'E17055',params:[['VALUE_DECAY','0.85','每tick衰減係數'],['REWARD_EMOTION_IMPROVE','+0.50','情緒改善獎勵'],['REWARD_EMOTION_WORSEN','−0.45','情緒惡化懲罰'],['REWARD_CONFUSION_DROP','+0.30','C下降≥0.12獎勵'],['REWARD_CONFUSION_SPIKE','−0.35','C上升≥0.15懲罰'],['REWARD_DIALOGUE_ACCEPT','+0.25','對話接受獎勵'],['REWARD_SCHEDULE_HIT','+0.20','時間表命中獎勵']]},
    {title:'困惑度 / 模式切換',color:C.acc,params:[['C公式','w1·U+w2·K+w3·S','w1=0.4 w2=0.3 w3=0.3'],['DELIBERATE_K_OVERRIDE','0.5','K≥此值強制deliberate'],['EMOTION_RESET_THRESHOLD','0.5','K峰值≥此才推斷情緒']]},
    {title:'對話系統',color:C.mid,params:[['DIALOGUE_MAX_TURNS','10','每段對話最多回合'],['DIALOGUE_BASE_ACCEPT','0.50','基礎接受機率'],['DIALOGUE_RELATION_BONUS','+0.30','好感加成'],['DIALOGUE_LEISURE_BONUS','+0.20','休閒加成'],['DIALOGUE_WORK_PENALTY','−0.30','工作懲罰']]},
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
  s.addText('角色設定表 — 5位角色的認知參數',{x:0.4,y:0.15,w:12.5,h:0.55,fontSize:26,bold:true,color:C.dark});
  const chars=[
    {name:'Amy',role:'咖啡師',threshold:'0.45',traits:'暗戀David，被Ben追求',color:C.acc},
    {name:'Ben',role:'超市員工',threshold:'0.60',traits:'喜歡Amy，容易直覺行動',color:C.green},
    {name:'Claire',role:'學生',threshold:'0.35',traits:'愛讀書，最容易觸發deliberate',color:'6C5CE7'},
    {name:'David',role:'畫家',threshold:'0.55',traits:'感性，不知Amy暗戀他',color:'E17055'},
    {name:'Emma',role:'老師',threshold:'0.50',traits:'理性，平衡直覺與深思',color:C.mid},
  ];
  ['角色','職業','困惑閾值','情緒對閾值影響範例','特殊設定'].forEach((h,hi)=>
    s.addText(h,{x:0.4+[0,1.6,3.2,4.8,8.8][hi],y:0.88,w:[1.5,1.5,1.5,3.8,4.2][hi],h:0.42,fontSize:12,bold:true,color:C.white,fill:{color:C.dark}}));
  chars.forEach((ch,ci)=>{
    const y=1.38+ci*1.04;
    s.addShape(pptx.ShapeType.rect,{x:0.4,y,w:12.9,h:0.95,fill:{color:ch.color,transparency:92},line:{color:ch.color,width:1}});
    s.addText(ch.name,{x:0.5,y:y+0.05,w:1.4,h:0.85,fontSize:16,bold:true,color:ch.color,valign:'middle'});
    s.addText(ch.role,{x:2.1,y:y+0.25,w:1.4,h:0.45,fontSize:12,color:C.text});
    s.addText(ch.threshold,{x:3.4,y:y+0.1,w:1.3,h:0.75,fontSize:20,bold:true,color:ch.color,valign:'middle',align:'center'});
    s.addText(`平靜→${ch.threshold}  緊張→${(parseFloat(ch.threshold)+0.10).toFixed(2)}  難過→${(parseFloat(ch.threshold)+0.15).toFixed(2)}`,{x:4.9,y:y+0.28,w:3.7,h:0.38,fontSize:11,color:C.text});
    s.addText(ch.traits,{x:8.9,y:y+0.25,w:4.2,h:0.45,fontSize:11,color:C.text});
  });
  s.addText('所有角色情緒基線：「平靜」（BASELINE_EMOTION = "平靜"）\n觸發情緒更新：當天K值峰值 ≥ EMOTION_RESET_THRESHOLD(0.5) → 呼叫模型推斷新情緒',
    {x:0.4,y:6.6,w:12.9,h:0.65,fontSize:11,color:C.sub,italic:true});
}

// ══════════════════════════════════════════════════════
// SLIDE 22: Summary
// ══════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.background = { color: C.dark };
  s.addText('AI-Town 系統總結',{x:0.4,y:0.3,w:12.5,h:0.7,fontSize:34,bold:true,color:C.white,align:'center'});
  [{label:'感知層',desc:'YOLO → yolo_desc → interrupt_queue → action_lock（0/1/2）',color:'E17055'},
   {label:'困惑度閘門',desc:'C=w1U+w2K+w3S → intuitive(Markov) 或 deliberate(Phi-3.5)',color:C.acc},
   {label:'Markov引擎',desc:'4來源加權（α時間表+β慣性+γ情境+δRL） → softmax → 保底 → 採樣',color:C.green},
   {label:'RL價值',desc:'每tick衰減0.85 + 7種reward signal → Q值指導delta分支',color:'E17055'},
   {label:'Weight Adapter',desc:'每天SGD(LR=0.05)更新α/β/γ/δ → clip[0.05,0.85] → 正規化',color:C.yel},
   {label:'STM（短期）',desc:'三層情節記憶（perception/event/inner） → 安全閥50 → 睡眠縮減保留5筆',color:'6C5CE7'},
   {label:'LTM（長期）',desc:'HAM 5元組 → 每天衰減 0.05/(1+ac×0.5) → 提取強化 → 低於0.2刪除',color:'6C5CE7'},
   {label:'擴散激活',desc:'BFS 2跳，激活0.4^(hop-1)，門檻0.3，top20 → 組自然語言 → 注入deliberate',color:C.mid},
   {label:'睡眠鞏固',desc:'12步驟：STM→HAM→LTM→摘要→關係→情緒→時間表→衰減→縮減→更新權重',color:C.green},
  ].forEach((item,i)=>{
    const row=Math.floor(i/3), col=i%3;
    const x=0.4+col*4.3, y=1.15+row*1.95;
    s.addShape(pptx.ShapeType.rect,{x,y,w:4.1,h:1.8,fill:{color:item.color,transparency:80},line:{color:item.color,width:2}});
    s.addText(item.label,{x:x+0.1,y:y+0.08,w:3.9,h:0.38,fontSize:14,bold:true,color:item.color});
    s.addText(item.desc,{x:x+0.1,y:y+0.5,w:3.9,h:1.15,fontSize:11,color:C.white});
  });
  s.addText('理論模型：Kahneman雙歷程 × Tulving情節/語意 × Anderson HAM × Anderson擴散激活 × Diekelmann睡眠鞏固',
    {x:0.4,y:7.05,w:12.9,h:0.35,fontSize:10.5,color:C.gray,align:'center'});
}

const outPath = 'C:/Users/Rayyu/Desktop/agi/presentation/AI-Town-main/AI-Town-main/reports/AI-Town_complete_flows.pptx';
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log('DONE: 22 slides written to', outPath);
}).catch(e => { console.error(e); process.exit(1); });
