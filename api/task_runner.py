import queue
import threading
import time
import uuid
from typing import Any, Optional


class TaskStateHub:
    """运行时单例状态总线，协调动态倍速、大屏监控与手动答题队列."""

    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls) -> "TaskStateHub":
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_hub()
            return cls._instance

    def _init_hub(self) -> None:
        self._lock = threading.Lock()
        self._web_mode = False
        self._global_speed = 1.0
        self._worker_speeds: dict[str, float] = {}
        self._workers: dict[str, dict[str, Any]] = {}
        self._logs: list[dict[str, str]] = []
        self._pending_questions: dict[str, dict[str, Any]] = {}
        self._listeners: list[queue.Queue] = []
        self._overall_stats = {
            "completed_jobs": 0,
            "total_jobs": 0,
            "passed_tests": 0,
            "start_time": time.time(),
        }

    def is_web_mode(self) -> bool:
        return self._web_mode

    def set_web_mode(self, enabled: bool) -> None:
        with self._lock:
            self._web_mode = enabled

    def set_global_speed(self, speed: float) -> None:
        speed = max(1.0, min(2.0, float(speed)))
        with self._lock:
            self._global_speed = speed
        self.broadcast_event("SPEED_CHANGE", {"type": "GLOBAL", "speed": speed})

    def get_global_speed(self) -> float:
        with self._lock:
            return self._global_speed

    def set_worker_speed(self, worker_id: str, speed: float) -> None:
        speed = max(1.0, min(2.0, float(speed)))
        with self._lock:
            self._worker_speeds[worker_id] = speed
        self.broadcast_event("SPEED_CHANGE", {"type": "WORKER", "worker_id": worker_id, "speed": speed})

    def get_effective_speed(self, worker_id: str) -> float:
        with self._lock:
            return self._worker_speeds.get(worker_id, self._global_speed)

    def update_worker_state(self, worker_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            if worker_id not in self._workers:
                self._workers[worker_id] = {"id": worker_id}
            self._workers[worker_id].update(data)
            self._workers[worker_id]["updated_at"] = time.time()
            worker_copy = dict(self._workers[worker_id])
        self.broadcast_event("WORKER_UPDATE", worker_copy)

    def set_total_jobs(self, total: int) -> None:
        with self._lock:
            self._overall_stats["total_jobs"] = total

    def increment_completed_jobs(self) -> None:
        with self._lock:
            self._overall_stats["completed_jobs"] += 1

    def increment_passed_tests(self) -> None:
        with self._lock:
            self._overall_stats["passed_tests"] += 1

    def append_log(self, level: str, message: str) -> None:
        now_str = time.strftime("%H:%M:%S")
        entry = {"timestamp": now_str, "level": level.upper(), "message": message}
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > 200:
                self._logs.pop(0)
        self.broadcast_event("LOG_APPEND", entry)

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            workers_list = list(self._workers.values())
            logs_copy = list(self._logs)
            elapsed = int(time.time() - self._overall_stats["start_time"])
            completed = self._overall_stats["completed_jobs"]
            total = self._overall_stats["total_jobs"]
            progress = round((completed / total * 100), 1) if total > 0 else 0.0
            return {
                "overall_progress": progress,
                "completed_jobs": completed,
                "total_jobs": total,
                "passed_tests": self._overall_stats["passed_tests"],
                "elapsed_seconds": elapsed,
                "global_speed": self._global_speed,
                "workers": workers_list,
                "logs": logs_copy,
            }

    def request_manual_answer(self, prompt_data: dict[str, Any], timeout: float = 120.0) -> Optional[str]:
        prompt_id = str(uuid.uuid4())
        event = threading.Event()
        entry = {
            "prompt_id": prompt_id,
            "data": prompt_data,
            "event": event,
            "answer": None,
            "resolved": False,
            "created_at": time.time(),
        }
        with self._lock:
            self._pending_questions[prompt_id] = entry

        broadcast_payload = {"prompt_id": prompt_id}
        broadcast_payload.update(prompt_data)
        self.broadcast_event("MANUAL_QUESTION_REQUEST", broadcast_payload)

        event.wait(timeout=timeout)

        with self._lock:
            res_entry = self._pending_questions.pop(prompt_id, None)

        self.broadcast_event("MANUAL_QUESTION_RESOLVED", {"prompt_id": prompt_id})

        if res_entry and res_entry["resolved"]:
            return res_entry["answer"]
        return None

    def submit_manual_answer(self, prompt_id: str, answer: str) -> bool:
        with self._lock:
            entry = self._pending_questions.get(prompt_id)
            if not entry:
                return False
            entry["answer"] = answer
            entry["resolved"] = True
            entry["event"].set()
            return True

    def skip_manual_answer(self, prompt_id: str) -> bool:
        with self._lock:
            entry = self._pending_questions.get(prompt_id)
            if not entry:
                return False
            entry["answer"] = None
            entry["resolved"] = True
            entry["event"].set()
            return True

    def get_pending_questions(self) -> list[dict[str, Any]]:
        with self._lock:
            results = []
            for prompt_id, entry in self._pending_questions.items():
                if not entry["resolved"]:
                    item = {"prompt_id": prompt_id}
                    item.update(entry["data"])
                    results.append(item)
            return results

    def subscribe_events(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._lock:
            self._listeners.append(q)
        return q

    def unsubscribe_events(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._listeners:
                self._listeners.remove(q)

    def broadcast_event(self, event_type: str, data: dict[str, Any]) -> None:
        msg = {"event": event_type, "data": data}
        with self._lock:
            dead_queues = []
            for q in self._listeners:
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    dead_queues.append(q)
            for dq in dead_queues:
                if dq in self._listeners:
                    self._listeners.remove(dq)
