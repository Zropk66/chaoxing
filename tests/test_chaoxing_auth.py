import unittest
from unittest.mock import MagicMock, patch
import requests
from api.chaoxing_auth import ChaoXingQRManager


class TestChaoXingAuth(unittest.TestCase):
    def setUp(self):
        self.auth_mgr = ChaoXingQRManager()

    def test_qr_session_lifecycle(self):
        status = self.auth_mgr.check_status("non_existent_uuid")
        self.assertEqual(status["status"], "EXPIRED")

    @patch("requests.Session.get")
    def test_create_session(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": True,
            "uuid": "test-uuid-1234",
            "enc": "test-enc-5678",
        }
        mock_get.return_value = mock_resp

        res = self.auth_mgr.create_session()
        self.assertTrue(res["status"])
        self.assertEqual(res["session_id"], "test-uuid-1234")
        self.assertIn("qr_url", res)

    def test_check_status_success(self):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": True, "type": 4}
        mock_resp.cookies = {"UID": "12345", "_uid": "12345"}
        mock_session.cookies = {"UID": "12345"}
        mock_session.post.return_value = mock_resp

        self.auth_mgr._sessions["test-uuid-1234"] = {
            "uuid": "test-uuid-1234",
            "enc": "test-enc-5678",
            "created_at": 9999999999,
            "session": mock_session,
        }

        status = self.auth_mgr.check_status("test-uuid-1234")
        self.assertEqual(status["status"], "SUCCESS")
        self.assertIn("cookies", status)
