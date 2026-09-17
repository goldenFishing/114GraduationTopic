"""
tests/test_server_interface.py

測試 server/ws_server.py 的 UE5 資料輸入/輸出介面。
"""

import sys
import os
import unittest

# 確保專案根目錄在 import 路徑中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.ws_server import UEDataReceiver, UEActionSender


class TestUEDataReceiver(unittest.TestCase):

    def test_register_and_receive(self):
        """情境 1：UEDataReceiver 可以正確 register 和 receive"""
        receiver = UEDataReceiver()
        received = []
        receiver.register_handler("A", lambda p: received.append(p))
        result = receiver.receive_perception("A", {"location": "咖啡店"})

        self.assertTrue(result)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["location"], "咖啡店")

    def test_receive_without_handler_returns_false(self):
        """情境 2：無 handler 時 receive 回傳 False"""
        receiver = UEDataReceiver()
        result = receiver.receive_perception("B", {"location": "超市"})

        self.assertFalse(result)


class TestUEActionSender(unittest.TestCase):

    def test_send_and_get_pending(self):
        """情境 3：UEActionSender 可以 send 和 get_pending"""
        sender = UEActionSender()
        sender.send_action("A", 9)
        sender.send_action("B", 12)
        pending = sender.get_pending()

        self.assertEqual(pending, {"A": 9, "B": 12})

    def test_clear_pending(self):
        """情境 4：clear_pending 清空 queue"""
        sender = UEActionSender()
        sender.send_action("A", 9)
        sender.clear_pending()

        self.assertEqual(sender.get_pending(), {})


if __name__ == "__main__":
    unittest.main()
