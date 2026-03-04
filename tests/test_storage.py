"""Tests for bot.storage."""

import os
import tempfile
import unittest

from bot.storage import Storage


class TestStorage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self._tmp.close()
        self.storage = Storage(db_path=self._tmp.name)

    def tearDown(self):
        self.storage.close()
        os.unlink(self._tmp.name)

    def test_subscribe_new_group(self):
        self.assertTrue(self.storage.subscribe(12345))
        self.assertTrue(self.storage.is_subscribed(12345))

    def test_subscribe_duplicate(self):
        self.storage.subscribe(12345)
        self.assertFalse(self.storage.subscribe(12345))

    def test_unsubscribe(self):
        self.storage.subscribe(99999)
        self.assertTrue(self.storage.unsubscribe(99999))
        self.assertFalse(self.storage.is_subscribed(99999))

    def test_unsubscribe_nonexistent(self):
        self.assertFalse(self.storage.unsubscribe(77777))

    def test_list_subscribed(self):
        self.storage.subscribe(100)
        self.storage.subscribe(200)
        self.storage.subscribe(300)
        result = self.storage.list_subscribed()
        self.assertEqual(sorted(result), [100, 200, 300])

    def test_list_empty(self):
        self.assertEqual(self.storage.list_subscribed(), [])


if __name__ == "__main__":
    unittest.main()
