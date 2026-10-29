import os
import shutil
import unittest
from api.account_manager import AccountManager


class TestAccountManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join("tests", "test_accounts")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.manager = AccountManager(accounts_dir=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_list_accounts(self):
        saved_file = self.manager.save_account("13800000000", {
            "cookies": "_uid=12345;UID=12345;vc3=abc",
            "use_cookies": "true",
            "course_list": "111,222",
        })
        self.assertTrue(os.path.exists(saved_file))
        accounts = self.manager.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["username"], "13800000000")
        active = self.manager.switch_account(accounts[0]["id"])
        self.assertEqual(active["cookies"], "_uid=12345;UID=12345;vc3=abc")

    def test_auto_create_accounts_dir(self):
        custom_dir = os.path.join("tests", "test_nested_accounts")
        if os.path.exists(custom_dir):
            shutil.rmtree(custom_dir)
        mgr = AccountManager(accounts_dir=custom_dir)
        self.assertTrue(os.path.exists(custom_dir))
        shutil.rmtree(custom_dir)

    def test_daily_watch_tracking(self):
        self.assertEqual(self.manager.get_daily_watched_seconds("user1"), 0.0)
        total = self.manager.add_daily_watched_seconds("user1", 120.5)
        self.assertEqual(total, 120.5)
        self.assertEqual(self.manager.get_daily_watched_seconds("user1"), 120.5)
        total2 = self.manager.add_daily_watched_seconds("user1", 30.0)
        self.assertEqual(total2, 150.5)
        self.assertEqual(self.manager.get_daily_watched_seconds("user1"), 150.5)
        self.assertEqual(self.manager.get_daily_watched_seconds("user2"), 0.0)
