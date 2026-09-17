"""
tests/test_file_io.py

Tests for utils/file_io.py — character JSON read/write operations.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Ensure project root is on the import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestGetPath(unittest.TestCase):
    """Test the internal _get_path helper."""

    def test_get_path_format(self):
        """_get_path returns a path that ends with <code>_init.json."""
        from utils.file_io import _get_path
        path = _get_path("A")
        self.assertTrue(path.endswith("A_init.json"))

    def test_get_path_uses_ai_data_dir(self):
        """_get_path is rooted at AI_DATA_DIR."""
        from utils.file_io import _get_path
        from config.world_config import AI_DATA_DIR
        path = _get_path("B")
        self.assertTrue(path.startswith(AI_DATA_DIR))


class TestSaveAndLoadCharacter(unittest.TestCase):
    """Test save_character / load_character round-trips with a temp directory."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmpdir_path = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def _patch_ai_data_dir(self):
        """Return a context-manager that patches AI_DATA_DIR to the temp dir."""
        import utils.file_io as fio
        return patch.object(
            fio, "_get_path",
            side_effect=lambda code: os.path.join(
                self._tmpdir_path, f"{code}_init.json"
            ),
        )

    def test_save_then_load_roundtrip(self):
        """save_character followed by load_character returns identical data."""
        from utils.file_io import save_character, load_character

        sample_data = {"name": "Amy", "emotion": "平靜", "day": 1}
        with self._patch_ai_data_dir():
            save_character("A", sample_data)
            loaded = load_character("A")

        self.assertEqual(loaded, sample_data)

    def test_save_writes_valid_json(self):
        """The file written by save_character is valid JSON."""
        from utils.file_io import save_character

        sample_data = {"name": "Ben", "location": "咖啡店"}
        with self._patch_ai_data_dir():
            save_character("B", sample_data)
            out_path = os.path.join(self._tmpdir_path, "B_init.json")
            with open(out_path, "r", encoding="utf-8") as f:
                loaded_raw = json.load(f)

        self.assertEqual(loaded_raw, sample_data)

    def test_save_uses_utf8_encoding(self):
        """Non-ASCII characters are preserved correctly (no ensure_ascii mangling)."""
        from utils.file_io import save_character, load_character

        sample_data = {"情緒": "開心", "位置": "公寓"}
        with self._patch_ai_data_dir():
            save_character("C", sample_data)
            loaded = load_character("C")

        self.assertEqual(loaded["情緒"], "開心")

    def test_load_missing_file_raises_file_not_found(self):
        """load_character raises FileNotFoundError when the file is absent."""
        from utils.file_io import load_character

        with self._patch_ai_data_dir():
            with self.assertRaises(FileNotFoundError):
                load_character("Z")

    def test_save_overwrites_existing_file(self):
        """A second save_character call replaces the previous content."""
        from utils.file_io import save_character, load_character

        first_data  = {"name": "David", "day": 1}
        second_data = {"name": "David", "day": 2}
        with self._patch_ai_data_dir():
            save_character("D", first_data)
            save_character("D", second_data)
            loaded = load_character("D")

        self.assertEqual(loaded["day"], 2)


class TestLoadAllAndSaveAll(unittest.TestCase):
    """Test load_all_characters / save_all_characters."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmpdir_path = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_fixture(self, code: str, data: dict):
        path = os.path.join(self._tmpdir_path, f"{code}_init.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def test_save_all_then_load_all(self):
        """save_all_characters + load_all_characters round-trips correctly."""
        import utils.file_io as fio
        from config.world_config import CHARACTER_NAMES

        characters = {
            code: {"name": name, "day": 1}
            for code, name in CHARACTER_NAMES.items()
        }

        def fake_get_path(code):
            return os.path.join(self._tmpdir_path, f"{code}_init.json")

        with patch.object(fio, "_get_path", side_effect=fake_get_path), \
             patch.object(fio, "AI_DATA_DIR", self._tmpdir_path), \
             patch.object(fio, "CHARACTER_NAMES", CHARACTER_NAMES):
            fio.save_all_characters(characters)
            loaded = fio.load_all_characters()

        self.assertEqual(set(loaded.keys()), set(CHARACTER_NAMES.keys()))
        for code in CHARACTER_NAMES:
            self.assertEqual(loaded[code]["name"], CHARACTER_NAMES[code])

    def test_load_all_ignores_unknown_files(self):
        """Files not matching <code>_init.json pattern are ignored."""
        import utils.file_io as fio
        from config.world_config import CHARACTER_NAMES

        # Write a valid file and a junk file
        self._write_fixture("A", {"name": "Amy"})
        junk_path = os.path.join(self._tmpdir_path, "UNKNOWN_init.json")
        with open(junk_path, "w") as f:
            json.dump({"name": "Ghost"}, f)

        def fake_get_path(code):
            return os.path.join(self._tmpdir_path, f"{code}_init.json")

        with patch.object(fio, "_get_path", side_effect=fake_get_path), \
             patch.object(fio, "AI_DATA_DIR", self._tmpdir_path), \
             patch.object(fio, "CHARACTER_NAMES", CHARACTER_NAMES):
            loaded = fio.load_all_characters()

        self.assertNotIn("UNKNOWN", loaded)
        self.assertIn("A", loaded)


if __name__ == "__main__":
    unittest.main()
