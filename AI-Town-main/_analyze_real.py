"""
跑 2 天真實模型模擬，逐 tick 記錄行動，寫入 _real_run.txt。
執行：python _analyze_real.py
"""
import sys, io, json, re, time
from collections import Counter, defaultdict

sys.path.insert(0, '.')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ── 攔截 log_turn ────────────────────────────────────────────────
import utils.logger as lg

_orig_log = lg.log_turn
_acts   = defaultdict(list)   # (code, 'D001') -> ['起床(d)', ...]
_times  = []                  # (wall_time, code, turn_id, action)
_t0     = time.time()

def _patch_log(logger, code, turn_id, action, c_value, mode):
    _orig_log(logger, code, turn_id, action, c_value, mode)
    day_key = turn_id[:4]   # 'D001' / 'D002'
    _acts[(code, day_key)].append(f"{action}({mode[0]})")
    _times.append((round(time.time() - _t0, 1), code, turn_id, action, mode[0]))

lg.log_turn = _patch_log

# ── 攔截 model_fn 計時（可選）────────────────────────────────────
_model_calls = []

# ── 載入模型 ─────────────────────────────────────────────────────
import torch
print(f"[Setup] VRAM free: {torch.cuda.mem_get_info()[0]/1024**3:.1f} GB")

from model.model_loader import ModelLoader
loader = ModelLoader()
loader.load()

vram_after = torch.cuda.memory_reserved() / 1024**3
print(f"[Setup] Model loaded. VRAM reserved: {vram_after:.2f} GB")

# ── reset 角色狀態 ────────────────────────────────────────────────
import simulate as _sim

print("[Setup] 重置角色狀態...")
_sim.reset_all_characters()

# ── 跑 2 天 ──────────────────────────────────────────────────────
from world.world_clock import WorldClock
from agent.manager import AgentManager

clock = WorldClock()
mgr   = AgentManager(loader, clock)

print("\n[Sim] 開始 2 天真實模型模擬...")
t_start = time.time()
mgr.run_autonomous_days(2)
elapsed = time.time() - t_start
print(f"[Sim] 完成！耗時 {elapsed/60:.1f} 分鐘")

# ── 分析 ──────────────────────────────────────────────────────────
NAMES  = {'A': 'Amy', 'B': 'Ben', 'C': 'Claire', 'D': 'David', 'E': 'Emma'}
DAYS   = ['D001', 'D002']
REST_ACTIONS = {'休息', '睡覺'}

lines = []
anomalies = []

for day in DAYS:
    lines.append(f"\n{'='*55}")
    lines.append(f"  {day}")
    lines.append(f"{'='*55}")
    for code, name in NAMES.items():
        acts = _acts.get((code, day), [])
        if not acts:
            lines.append(f"  {name}: (無資料)")
            continue
        rest  = sum(1 for a in acts if any(a.startswith(r) for r in REST_ACTIONS))
        total = len(acts)
        pct   = int(rest / total * 100) if total else 0
        seq   = ', '.join(acts)
        lines.append(f"  {name}: {total} ticks, {rest} rest ({pct}%)  ← {seq}")

        # 異常偵測
        if pct > 50:
            anomalies.append(f"[WARN] {day} {name}: 休息比例偏高 {pct}% ({rest}/{total})")
        consecutive = 0
        max_consec  = 0
        for a in acts:
            if any(a.startswith(r) for r in REST_ACTIONS):
                consecutive += 1
                max_consec = max(max_consec, consecutive)
            else:
                consecutive = 0
        if max_consec >= 5:
            anomalies.append(f"[WARN] {day} {name}: 連續休息 {max_consec} 次")
        # 只有起床或前往
        unique = set(a.split('(')[0] for a in acts)
        if unique <= {'起床', '前往', '休息', '睡覺'}:
            anomalies.append(f"[WARN] {day} {name}: 行動種類過少 {unique}")

lines.append("")

if anomalies:
    lines.append("【異常偵測結果】")
    for a in anomalies:
        lines.append(f"  {a}")
else:
    lines.append("【異常偵測結果】無異常 ✓")

# ── VRAM ─────────────────────────────────────────────────────────
lines.append(f"\n【GPU 使用】")
lines.append(f"  VRAM reserved: {torch.cuda.memory_reserved()/1024**3:.2f} GB")
lines.append(f"  VRAM allocated: {torch.cuda.memory_allocated()/1024**3:.2f} GB")
lines.append(f"  總耗時: {elapsed/60:.1f} min")

output = '\n'.join(lines)
print(output)

with open('_real_run.txt', 'w', encoding='utf-8') as f:
    f.write(output + '\n')
    f.write('\n【逐 tick 詳細記錄】\n')
    for t, code, tid, act, mode in _times:
        f.write(f"  t={t:6.1f}s  {NAMES.get(code,code):8s}  {tid}  {act}({mode})\n")

print(f"\n結果已寫入 _real_run.txt")
