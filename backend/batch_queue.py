"""Serial batch queue for folder-based image inference."""
from __future__ import annotations

import asyncio
import mimetypes
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import TASK_TIMEOUT, get_inference_url


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


@dataclass
class BatchItem:
    file_name: str
    file_path: str
    status: str = "queued"
    result: dict | None = None
    error: str | None = None


@dataclass
class BatchTask:
    batch_id: str
    model: str
    explain_mode: str
    folder_path: str
    recursive: bool
    items: list[BatchItem]
    created_at: float = field(default_factory=time.time)
    status: str = "queued"
    completed: int = 0
    failed: int = 0
    error: str | None = None

    @property
    def total(self) -> int:
        return len(self.items)


class BatchTaskQueue:
    def __init__(self):
        self._tasks: dict[str, BatchTask] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_started = False

    def _make_id(self) -> str:
        return str(uuid.uuid4())

    def _scan_images(self, folder_path: str, recursive: bool) -> tuple[Path, list[Path]]:
        root = Path(folder_path).expanduser()
        if not root.exists():
            raise ValueError(f"Folder does not exist: {folder_path}")
        if not root.is_dir():
            raise ValueError(f"Path is not a folder: {folder_path}")

        iterator = root.rglob("*") if recursive else root.iterdir()
        images = sorted(
            path for path in iterator
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not images:
            raise ValueError("No supported image files found in this folder.")
        return root, images

    async def submit(
        self,
        model: str,
        folder_path: str,
        explain_mode: str = "template",
        recursive: bool = False,
    ) -> tuple[str, int]:
        root, images = self._scan_images(folder_path, recursive)
        batch_id = self._make_id()
        items = [
            BatchItem(
                file_name=path.name,
                file_path=str(path),
            )
            for path in images
        ]
        task = BatchTask(
            batch_id=batch_id,
            model=model,
            explain_mode=explain_mode,
            folder_path=str(root),
            recursive=recursive,
            items=items,
        )
        self._tasks[batch_id] = task
        await self._queue.put(batch_id)
        if not self._worker_started:
            self._worker_started = True
            asyncio.create_task(self._worker())
        return batch_id, task.total

    def get_status(self, batch_id: str) -> dict | None:
        task = self._tasks.get(batch_id)
        if task is None:
            return None
        return self._serialize(task)

    def get_image_path(self, batch_id: str, index: int) -> Path | None:
        task = self._tasks.get(batch_id)
        if task is None or index < 0 or index >= len(task.items):
            return None
        path = Path(task.items[index].file_path)
        if not path.exists() or not path.is_file():
            return None
        return path

    def _serialize(self, task: BatchTask) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "batch_id": task.batch_id,
            "status": task.status,
            "model": task.model,
            "explain_mode": task.explain_mode,
            "folder_path": task.folder_path,
            "recursive": task.recursive,
            "total": task.total,
            "completed": task.completed,
            "failed": task.failed,
            "items": [
                {
                    "file_name": item.file_name,
                    "file_path": item.file_path,
                    "status": item.status,
                    "result": item.result,
                    "error": item.error,
                }
                for item in task.items
            ],
        }
        if task.error:
            payload["error"] = task.error
        return payload

    async def _worker(self):
        import httpx

        while True:
            batch_id = await self._queue.get()
            task = self._tasks.get(batch_id)
            if task is None:
                continue

            task.status = "running"
            url = f"{get_inference_url(task.model)}/infer/{task.model}"

            try:
                async with httpx.AsyncClient(timeout=TASK_TIMEOUT + 10) as client:
                    for item in task.items:
                        item.status = "running"
                        try:
                            content_type = mimetypes.guess_type(item.file_path)[0] or "image/png"
                            with open(item.file_path, "rb") as image_file:
                                resp = await client.post(
                                    url,
                                    files={"file": (item.file_name, image_file, content_type)},
                                    data={"explain_mode": task.explain_mode},
                                )
                            if resp.status_code == 200:
                                item.result = resp.json()
                                item.status = "done"
                                task.completed += 1
                            else:
                                item.error = f"Inference service error {resp.status_code}: {resp.text[:4000]}"
                                item.status = "error"
                                task.failed += 1
                        except Exception as exc:
                            item.error = str(exc)
                            item.status = "error"
                            task.failed += 1

                task.status = "done" if task.failed == 0 else "error"
                if task.failed:
                    task.error = f"{task.failed} of {task.total} images failed."
            except Exception as exc:
                task.status = "error"
                task.error = str(exc)


batch_queue = BatchTaskQueue()
