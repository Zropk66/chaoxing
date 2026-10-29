import unittest
from unittest.mock import MagicMock, patch
from api.base import Chaoxing, StudyResult
from api.task_runner import TaskStateHub
from main import stop_study_task, _task_run_lock


class TestTaskCancellation(unittest.TestCase):
    def setUp(self):
        self.hub = TaskStateHub()
        self.hub.set_web_mode(True)
        self.hub.set_task_running(True)

    def tearDown(self):
        self.hub.set_task_running(False)
        self.hub.clear_workers()

    def test_study_video_aborts_immediately_when_stopped(self):
        cx = Chaoxing()
        mock_session = MagicMock()
        cx._session = mock_session

        info_resp = MagicMock()
        info_resp.json.return_value = {
            "status": "success",
            "dtoken": "tok1",
            "duration": 100,
            "crc": "",
            "key": "",
        }
        mock_session.get.return_value = info_resp

        cx.video_progress_log = MagicMock(return_value=(False, 200))
        self.hub.set_task_running(False)

        res = cx.study_video(
            {"clazzId": "1", "courseId": "2", "cpi": "3", "title": "测试课程"},
            {"jobid": "1", "objectid": "obj1", "name": "测试视频", "playTime": 0},
            {},
        )
        self.assertEqual(res, StudyResult.ERROR)

    def test_stop_study_task_handles_none_processor(self):
        import main
        with main._task_run_lock:
            main._is_task_running = True
            main._current_study_processor = None

        self.assertTrue(stop_study_task())
        self.assertFalse(self.hub.is_task_running())


if __name__ == "__main__":
    unittest.main()
