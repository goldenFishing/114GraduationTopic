# ================================================================
# utils/logger.py
# 日誌系統
#
# 對應 ARCHITECTURE.md §6.7.2
#
# 修改重點：
#   1. 用 config 設定的 LOG_LEVEL_CONSOLE / LOG_LEVEL_FILE
#   2. 新增 log_interrupt, log_dialogue_invite 等
# ================================================================

import logging
import os
from datetime import datetime

from config.world_config import (
    LOG_DIR,
    LOG_LEVEL_CONSOLE,
    LOG_LEVEL_FILE,
)


_LEVEL_MAP = {
    "DEBUG":    logging.DEBUG,
    "INFO":     logging.INFO,
    "WARNING":  logging.WARNING,
    "ERROR":    logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def get_logger(name: str = "world") -> logging.Logger:
    """取得 logger，同時輸出到 console 和當天的 log 檔。"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(_LEVEL_MAP.get(LOG_LEVEL_CONSOLE, logging.INFO))
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler（每天一個檔）
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    log_path = os.path.join(LOG_DIR, f"{today}.log")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(_LEVEL_MAP.get(LOG_LEVEL_FILE, logging.DEBUG))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# ================================================================
# 結構化日誌函式
# ================================================================

def log_turn(logger: logging.Logger, code: str, turn_id: str,
             action: str, c_value: float, mode: str):
    """每輪決策的摘要 log。"""
    logger.info(
        f"[{code}] {turn_id} | mode={mode} | C={c_value:.3f} | action={action}"
    )


def log_consolidation(logger: logging.Logger, code: str, day: int,
                       stm_count: int, ltm_count: int):
    """睡眠濃縮完成 log。"""
    logger.info(
        f"[{code}] Day {day} 睡眠濃縮完成 | "
        f"抽 HAM {stm_count} 筆 → LTM 共 {ltm_count} 筆"
    )


def log_interrupt(logger: logging.Logger, code: str,
                   event_type: str, strength: str,
                   interrupted: bool, new_action: str = ""):
    """中斷事件 log。"""
    state = f"中斷→{new_action}" if interrupted else "繼續原行動"
    logger.info(
        f"[{code}] 中斷事件 type={event_type} strength={strength} → {state}"
    )


def log_dialogue_invite(logger: logging.Logger,
                         initiator: str, responder: str,
                         accepted: bool):
    """對話邀請結果 log。"""
    state = "接受" if accepted else "拒絕"
    logger.info(f"[{initiator}→{responder}] 對話邀請被{state}")
