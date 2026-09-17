# ================================================================
# main.py
# 程式進入點（UE 對接）
#
# 對應 ARCHITECTURE.md §6.8.2
#
# 兩種執行模式：
#   python main.py                  → 啟動 WebSocket 伺服器（與 UE 連接）
#   python main.py --demo           → 離線快速 demo（5 個假事件）
#
# 完整離線多日模擬請用 simulate.py
# ================================================================

import argparse
import sys

from model.model_loader import ModelLoader
from world.world_clock  import WorldClock
from agent.manager      import AgentManager
from utils.logger       import get_logger

logger = get_logger("main")


def build_system():
    """初始化所有系統元件。"""
    logger.info("=== AI 角色自主生活模擬系統 啟動 ===")

    loader = ModelLoader()
    loader.load()

    clock   = WorldClock()
    manager = AgentManager(loader=loader, clock=clock)

    return loader, clock, manager


# ── 模式 1：WebSocket 伺服器（與 UE 連接）────────────────────────

def run_server(host: str = "localhost", port: int = 8765):
    """啟動 WebSocket 伺服器，等待 UE 連線。"""
    from perception.yolo_handler import YoloHandler
    from server.ws_server import WSServer

    loader, clock, manager = build_system()
    yolo   = YoloHandler()
    server = WSServer(manager=manager, yolo=yolo, host=host, port=port)
    server.run()


# ── 模式 2：快速 demo（5 個假事件）──────────────────────────────

def run_demo(rounds: int = 3):
    """簡易離線測試，跑幾個 tick 後印結果。"""
    loader, clock, manager = build_system()

    logger.info(f"=== 開始 demo，跑 {rounds} 個 ticks ===")
    for i in range(rounds):
        result = manager.run_tick()
        print(f"\n--- Tick {i+1} ({result['time']}) ---")
        for code, dec in result.get("decide", {}).items():
            char = manager.get_character(code)
            print(f"[{char.name}] {dec.get('action', '')} "
                  f"{dec.get('target', '')}")

    logger.info("=== demo 結束 ===")


# ── CLI 進入點 ────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Town 主程式")
    parser.add_argument("--demo", action="store_true",
                          help="快速 demo 模式（不需 UE）")
    parser.add_argument("--rounds", type=int, default=3,
                          help="demo 模式 tick 數")
    parser.add_argument("--host", default="localhost",
                          help="WebSocket 伺服器 host")
    parser.add_argument("--port", type=int, default=8765,
                          help="WebSocket 伺服器 port")
    args = parser.parse_args()

    if args.demo:
        run_demo(rounds=args.rounds)
    else:
        run_server(host=args.host, port=args.port)
