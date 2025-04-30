# backend/app/sse.py
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from typing import AsyncGenerator, Dict
import asyncio

router = APIRouter()

_clients: Dict[str, "asyncio.Queue[str]"] = {}


async def _event_generator(task_id: str) -> AsyncGenerator[str, None]:
    q = _clients[task_id]
    try:
        while True:
            data = await q.get()
            yield data
            if data.startswith("event: finish") or data.startswith("event: error"):
                break
    finally:
        _clients.pop(task_id, None)


@router.get("/agent/sse")
async def sse_endpoint(request: Request, task_id: str):
    if task_id not in _clients:
        _clients[task_id] = asyncio.Queue()
    return EventSourceResponse(_event_generator(task_id))
