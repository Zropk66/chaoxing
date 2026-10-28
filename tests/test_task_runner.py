import threading
import time
import unittest
from api.task_runner import TaskStateHub


class TestTaskStateHub(unittest.TestCase):
    def setUp(self):
        self.hub = TaskStateHub()
        self.hub._pending_questions.clear()
        self.hub._workers.clear()
        self.hub._logs.clear()

    def test_speed_dispatch(self):
        self.hub.set_global_speed(1.5)
        self.assertEqual(self.hub.get_global_speed(), 1.5)
        self.assertEqual(self.hub.get_effective_speed("worker_1"), 1.5)

        self.hub.set_worker_speed("worker_1", 1.8)
        self.assertEqual(self.hub.get_effective_speed("worker_1"), 1.8)
        self.assertEqual(self.hub.get_effective_speed("worker_2"), 1.5)

    def test_manual_question_submit(self):
        prompt_data = {
            "title": "测试一阶微分方程",
            "type": "single",
            "options": ["A. 选项1", "B. 选项2"]
        }
        res_container = []

        def worker():
            ans = self.hub.request_manual_answer(prompt_data, timeout=3.0)
            res_container.append(ans)

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.1)

        pending = self.hub.get_pending_questions()
        self.assertEqual(len(pending), 1)
        prompt_id = pending[0]["prompt_id"]

        success = self.hub.submit_manual_answer(prompt_id, "A")
        self.assertTrue(success)
        t.join(timeout=2.0)
        self.assertEqual(res_container, ["A"])

    def test_manual_question_skip(self):
        prompt_data = {"title": "跳过题目", "type": "judgement"}
        res_container = []

        def worker():
            ans = self.hub.request_manual_answer(prompt_data, timeout=3.0)
            res_container.append(ans)

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.1)

        pending = self.hub.get_pending_questions()
        prompt_id = pending[0]["prompt_id"]
        self.hub.skip_manual_answer(prompt_id)
        t.join(timeout=2.0)
        self.assertEqual(res_container, [None])
