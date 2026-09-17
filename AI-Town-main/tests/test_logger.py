"""
tests/test_logger.py

Tests for utils/logger.py — logging system.
"""

import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _fresh_logger(name: str) -> logging.Logger:
    """Remove any existing handlers on a logger so tests start clean."""
    log = logging.getLogger(name)
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    return log


class TestGetLogger(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmpdir_path = self._tmpdir.name
        # Ensure the named logger has no leftover handlers
        _fresh_logger("test_get_logger")

    def tearDown(self):
        _fresh_logger("test_get_logger")
        self._tmpdir.cleanup()

    def test_returns_logger_instance(self):
        """get_logger returns a logging.Logger."""
        from utils.logger import get_logger
        with patch("utils.logger.LOG_DIR", self._tmpdir_path):
            logger = get_logger("test_get_logger")
        self.assertIsInstance(logger, logging.Logger)

    def test_logger_has_handlers(self):
        """Logger is configured with at least one handler."""
        from utils.logger import get_logger
        with patch("utils.logger.LOG_DIR", self._tmpdir_path):
            logger = get_logger("test_get_logger")
        self.assertGreater(len(logger.handlers), 0)

    def test_same_name_returns_cached_logger(self):
        """Calling get_logger twice with the same name yields the same object."""
        from utils.logger import get_logger
        with patch("utils.logger.LOG_DIR", self._tmpdir_path):
            l1 = get_logger("test_get_logger")
            l2 = get_logger("test_get_logger")
        self.assertIs(l1, l2)

    def test_log_file_created(self):
        """A .log file is created inside LOG_DIR after calling get_logger."""
        _fresh_logger("test_log_file")
        from utils.logger import get_logger
        with patch("utils.logger.LOG_DIR", self._tmpdir_path):
            get_logger("test_log_file")
        log_files = [f for f in os.listdir(self._tmpdir_path)
                     if f.endswith(".log")]
        _fresh_logger("test_log_file")
        self.assertTrue(len(log_files) >= 1)

    def test_log_level_is_debug(self):
        """Logger base level is DEBUG (so handlers can apply their own filters)."""
        from utils.logger import get_logger
        with patch("utils.logger.LOG_DIR", self._tmpdir_path):
            logger = get_logger("test_get_logger")
        self.assertEqual(logger.level, logging.DEBUG)

    def test_propagate_is_false(self):
        """Logger does not propagate to the root logger."""
        from utils.logger import get_logger
        with patch("utils.logger.LOG_DIR", self._tmpdir_path):
            logger = get_logger("test_get_logger")
        self.assertFalse(logger.propagate)


class TestFormatterFormat(unittest.TestCase):
    """Verify the log message format includes expected tokens."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._handler_name = "test_format_check"
        _fresh_logger(self._handler_name)

    def tearDown(self):
        _fresh_logger(self._handler_name)
        self._tmpdir.cleanup()

    def test_formatter_pattern(self):
        """Log record text contains [LEVEL] and [name] tokens."""
        from utils.logger import get_logger
        import io
        buf = io.StringIO()

        with patch("utils.logger.LOG_DIR", self._tmpdir.name):
            logger = get_logger(self._handler_name)

        stream_handler = logging.StreamHandler(buf)
        stream_handler.setFormatter(logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(stream_handler)
        logger.info("hello world")

        output = buf.getvalue()
        self.assertIn("[INFO]", output)
        self.assertIn(self._handler_name, output)
        self.assertIn("hello world", output)


class TestStructuredLogFunctions(unittest.TestCase):
    """Test the structured log helper functions."""

    def _make_list_logger(self) -> tuple:
        """Return (logger, messages_list) where messages_list captures output."""
        messages = []

        class ListHandler(logging.Handler):
            def emit(self, record):
                messages.append(self.format(record))

        log = logging.getLogger("test_structured")
        for h in list(log.handlers):
            log.removeHandler(h)
        h = ListHandler()
        h.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(h)
        log.setLevel(logging.DEBUG)
        return log, messages

    def test_log_turn(self):
        """log_turn emits a message containing code, mode, C, and action."""
        from utils.logger import log_turn
        logger, msgs = self._make_list_logger()
        log_turn(logger, "A", "T001", "工作", 0.75, "deliberate")
        self.assertEqual(len(msgs), 1)
        text = msgs[0]
        self.assertIn("A", text)
        self.assertIn("T001", text)
        self.assertIn("deliberate", text)
        self.assertIn("0.750", text)
        self.assertIn("工作", text)

    def test_log_consolidation(self):
        """log_consolidation emits day, STM count, and LTM count."""
        from utils.logger import log_consolidation
        logger, msgs = self._make_list_logger()
        log_consolidation(logger, "B", 2, 10, 45)
        text = msgs[0]
        self.assertIn("B", text)
        self.assertIn("Day 2", text)
        self.assertIn("10", text)
        self.assertIn("45", text)

    def test_log_interrupt_interrupted(self):
        """log_interrupt when interrupted includes new_action."""
        from utils.logger import log_interrupt
        logger, msgs = self._make_list_logger()
        log_interrupt(logger, "C", "yolo_change", "strong", True, "逃跑")
        text = msgs[0]
        self.assertIn("C", text)
        self.assertIn("yolo_change", text)
        self.assertIn("strong", text)
        self.assertIn("逃跑", text)

    def test_log_interrupt_continued(self):
        """log_interrupt when not interrupted says 繼續原行動."""
        from utils.logger import log_interrupt
        logger, msgs = self._make_list_logger()
        log_interrupt(logger, "D", "yolo_change", "weak", False)
        self.assertIn("繼續原行動", msgs[0])

    def test_log_dialogue_invite_accepted(self):
        """log_dialogue_invite when accepted says 接受."""
        from utils.logger import log_dialogue_invite
        logger, msgs = self._make_list_logger()
        log_dialogue_invite(logger, "A", "B", True)
        self.assertIn("接受", msgs[0])
        self.assertIn("A", msgs[0])
        self.assertIn("B", msgs[0])

    def test_log_dialogue_invite_rejected(self):
        """log_dialogue_invite when rejected says 拒絕."""
        from utils.logger import log_dialogue_invite
        logger, msgs = self._make_list_logger()
        log_dialogue_invite(logger, "A", "C", False)
        self.assertIn("拒絕", msgs[0])


if __name__ == "__main__":
    unittest.main()
