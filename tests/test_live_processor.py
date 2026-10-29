import unittest
from unittest.mock import MagicMock, patch
from api.live import Live
from api.live_process import LiveProcessor
from api.task_runner import TaskStateHub


class TestLiveProcessor(unittest.TestCase):
    def test_live_custom_session(self):
        mock_session = MagicMock()
        live = Live(
            attachment={"property": {"title": "测试直播", "streamName": "s1", "vdoid": "v1"}},
            defaults={"userid": "100", "clazzId": "200", "knowledgeid": "300"},
            course_id="c1",
            session=mock_session,
        )
        self.assertIs(live.session, mock_session)

        mock_resp = MagicMock()
        mock_resp.text = "@success"
        mock_session.get.return_value = mock_resp

        self.assertTrue(live.do_finish())
        mock_session.get.assert_called_once()

    def test_run_live_updates_hub_state(self):
        hub = TaskStateHub()
        hub.set_web_mode(True)

        mock_live = MagicMock()
        mock_live.name = "形势与政策第二次直播"
        mock_live.get_status.return_value = {
            "temp": {"data": {"duration": 120}}
        }
        mock_live.do_finish.return_value = True

        with patch("time.sleep", return_value=None):
            success = LiveProcessor.run_live(mock_live, speed=2.0, course_title="形势与政策")
            self.assertTrue(success)

        snapshot = hub.get_snapshot()
        self.assertEqual(len(snapshot["workers"]), 0)


if __name__ == "__main__":
    unittest.main()
