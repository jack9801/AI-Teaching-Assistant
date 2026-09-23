from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncIterator, Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.graph import ChatMessage, run_graph


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=8000)


class EvaluateRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    messages: list[Message] = Field(min_length=1, max_length=100)


class SseEvent(BaseModel):
    type: Literal["text", "done", "error"]
    delta: str | None = None
    requestId: str | None = None
    message: str | None = None


app = FastAPI(title="AI Teaching Assistant Worker", version="0.1.0")


async def event_stream(response: str, request_id: str) -> AsyncIterator[bytes]:
    try:
        words = response.split(" ")
        for index, word in enumerate(words):
            delta = word + (" " if index < len(words) - 1 else "")
            yield f"data: {SseEvent(type='text', delta=delta).model_dump_json()}\n\n".encode()
            await asyncio.sleep(0.01)
        yield f"data: {SseEvent(type='done', requestId=request_id).model_dump_json()}\n\n".encode()
    except Exception as exc:
        yield f"data: {SseEvent(type='error', message=str(exc)).model_dump_json()}\n\n".encode()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/internal/evaluate")
async def evaluate(
    request: EvaluateRequest,
    x_worker_token: str | None = Header(default=None),
) -> StreamingResponse:
    expected = os.getenv("WORKER_SHARED_SECRET", "").strip()
    if expected and x_worker_token != expected:
        raise HTTPException(status_code=401, detail="Invalid worker token")

    result = await asyncio.to_thread(
        run_graph,
        [ChatMessage(role=m.role, content=m.content) for m in request.messages],
    )
    response = result.get("response", "").strip()
    if not response:
        raise HTTPException(status_code=500, detail="Worker produced an empty response")

    request_id = result.get("request_id") or str(uuid.uuid4())
    return StreamingResponse(
        event_stream(response, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
