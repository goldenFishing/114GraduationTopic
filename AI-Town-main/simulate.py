# ================================================================
# simulate.py
# 離線模擬進入點（不需要 UE）
#
# 對應 ARCHITECTURE.md §6.8.1
#
# 用法：
#   python simulate.py                 # 跑預設天數
#   python simulate.py --days 3
#   python simulate.py --no-model      # 假模型快速驗證
#   python simulate.py --report-only   # 只重新產生報告
# ================================================================

import argparse
import sys
import io
import time
import traceback

# Windows 主控台 UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, '.')

from world.world_clock import WorldClock
from agent.manager     import AgentManager
from observe.dashboard_html import generate_report
from utils.logger      import get_logger
from config.world_config import SIMULATION_DEFAULT_DAYS

logger = get_logger("simulate")


# ================================================================
# Fake loader（--no-model 模式）
# ================================================================

class FakeLoader:
    """假模型 loader，所有 model_fn 回傳預設值。"""

    def __init__(self):
        self._loaded = True
        self.vision = None
        self.text   = None
        self.fusion = None

    def load(self):
        pass

    def is_loaded(self):
        return True

    def make_model_fn(self, max_new_tokens=256, temperature=0.0):
        def model_fn(prompt: str) -> str:
            return _fake_response(prompt)
        return model_fn

    def make_deliberate_fn(self):
        return self.make_model_fn()

    def make_dialogue_fn(self):
        return self.make_model_fn()

    def make_consolidation_fn(self, step: str):
        return self.make_model_fn()


def _fake_response(prompt: str) -> str:
    """根據 prompt 內容回傳合理的假輸出。"""
    if "目前的情緒是什麼" in prompt:
        return "平靜"
    if "用 1-2 句話總結" in prompt:
        return "今天度過了平凡的一天，沒有特別的事件。"
    if "關係摘要" in prompt:
        return "兩人關係維持原狀。"
    if "抽取" in prompt and "HAM" in prompt:
        for name in ["Amy", "Ben", "Claire", "David", "Emma"]:
            if name in prompt:
                return f"{name} | 工作 | 平凡 | 無 | 今天"
        return ""
    if "選出最值得" in prompt:
        return ""
    if "規劃" in prompt and "時間表" in prompt:
        return """[
  {"time": "07:00", "action": "起床", "location": "公寓"},
  {"time": "09:00", "action": "工作", "location": "辦公室"},
  {"time": "12:00", "action": "吃飯", "location": "公司附近"},
  {"time": "13:00", "action": "工作", "location": "辦公室"},
  {"time": "18:00", "action": "回家", "location": "公寓"},
  {"time": "23:00", "action": "睡覺", "location": "公寓"}
]"""

    # 深思 / 對話 fallback
    return """[ACTION] 休息
[TARGET]
[CONTENT]

[THOUGHT] 今天有點累，想稍微休息一下。

[HAM]
- 角色 | 感到 | 疲憊 | 無 | 無
[/HAM]"""


# ================================================================
# 主流程
# ================================================================

def main():
    parser = argparse.ArgumentParser(description="AI-Town 離線模擬")
    parser.add_argument("--days", type=int, default=SIMULATION_DEFAULT_DAYS)
    parser.add_argument("--no-model", action="store_true",
                          help="使用假模型，不需 GPU")
    parser.add_argument("--report-only", action="store_true",
                          help="只產生報告，不執行模擬")
    args = parser.parse_args()

    logger.info("=== AI-Town 離線模擬啟動 ===")
    logger.info(f"參數：days={args.days}, no_model={args.no_model}")

    # 載入 loader
    if args.no_model:
        loader = FakeLoader()
        logger.info("使用 FakeLoader（無模型模式）")
    else:
        from model.model_loader import ModelLoader
        loader = ModelLoader()
        loader.load()

    clock   = WorldClock()
    manager = AgentManager(loader, clock)

    if args.report_only:
        logger.info("Report-only 模式")
        sim_data = {"days": [], "total_ticks": 0}
        report_path = generate_report(manager, sim_data)
        print(f"\n報告：{report_path}")
        return

    start = time.time()
    try:
        sim_data = manager.run_autonomous_days(args.days)
    except KeyboardInterrupt:
        logger.warning("使用者中斷")
        sim_data = {"days": [], "total_ticks": 0}
    except Exception as e:
        logger.error(f"模擬發生錯誤：{e}")
        traceback.print_exc()
        sim_data = {"days": [], "total_ticks": 0}

    elapsed = time.time() - start
    logger.info(f"模擬完成，耗時 {elapsed:.1f} 秒")

    report_path = generate_report(manager, sim_data)
    print(f"\n=== 完成 ===")
    print(f"報告：{report_path}")
    print(f"耗時：{elapsed:.1f} 秒")
    print(f"總 tick：{sim_data.get('total_ticks', 0)}")


if __name__ == "__main__":
    main()
