import unittest
from main import parse_args


class TestCliWebFlag(unittest.TestCase):
    def test_webui_flag_default(self):
        args = parse_args([])
        self.assertFalse(args.webui)

    def test_webui_flag_enabled(self):
        args = parse_args(["--webui"])
        self.assertTrue(args.webui)
        self.assertEqual(args.port, 5000)

    def test_custom_port(self):
        args = parse_args(["--webui", "--port", "8080"])
        self.assertTrue(args.webui)
        self.assertEqual(args.port, 8080)

    def test_unicode_em_dash_tolerance(self):
        args1 = parse_args(["—-webui"])
        self.assertTrue(args1.webui)
        args2 = parse_args(["—webui"])
        self.assertTrue(args2.webui)
