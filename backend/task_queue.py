"""
In-process serial task queue.
Only one inference job runs at a time; others wait in queue.
Tasks expire after TASK_TIMEOUT seconds.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from config import TASK_TIMEOUT


@dataclass
class Task:
    task_id: str
    model: str
    explain_mode: str
    image_bytes: bytes
    created_at: float = field(default_factory=time.time)
    status: str = "queued"        # queued | running | done | timeout | error
    result: dict | None = None
    error: str | None = None


class SerialTaskQueue:
    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._worker_started = False

    def _make_id(self) -> str:
        return str(uuid.uuid4())

    async def submit(self, model: str, image_bytes: bytes, explain_mode: str = "template") -> str:
        task_id = self._make_id()
        task = Task(task_id=task_id, model=model, explain_mode=explain_mode, image_bytes=image_bytes)
        self._tasks[task_id] = task
        await self._queue.put(task_id)
        if not self._worker_started:
            self._worker_started = True
            asyncio.create_task(self._worker())
        return task_id

    def get_status(self, task_id: str) -> dict | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        # Check timeout
        if task.status in ("queued", "running"):
            if time.time() - task.created_at > TASK_TIMEOUT:
                task.status = "timeout"
        resp: dict[str, Any] = {
            "task_id": task_id,
            "status":  task.status,
            "model":   task.model,
            "explain_mode": task.explain_mode,
        }
        if task.status == "done" and task.result:
            resp["result"] = task.result
        if task.status == "error":
            resp["error"] = task.error
        return resp

    async def _worker(self):
        """Processes tasks serially from the queue."""
        import httpx
        from config import INFERENCE_URL

        while True:
            task_id = await self._queue.get()
            task = self._tasks.get(task_id)
            if task is None:
                continue

            # Skip timed-out tasks
            if time.time() - task.created_at > TASK_TIMEOUT:
                task.status = "timeout"
                continue

            task.status = "running"
            url = f"{INFERENCE_URL}/infer/{task.model}"

            try:
                async with httpx.AsyncClient(timeout=TASK_TIMEOUT + 10) as client:
                    resp = await client.post(
                        url,
                        files={"file": ("image.png", task.image_bytes, "image/png")},
                        data={"explain_mode": task.explain_mode},
                    )
                if resp.status_code == 200:
                    task.result = resp.json()
                    task.status = "done"
                else:
                    task.error  = f"Inference service error {resp.status_code}: {resp.text[:200]}"
                    task.status = "error"
            except Exception as exc:
                task.error  = str(exc)
                task.status = "error"


# Module-level singleton
queue = SerialTaskQueue()
