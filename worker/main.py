from __future__ import annotations
import asyncio
import uuid
from typing import AsyncIterator, Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from agent.graph import ChatMessage, run_graph

class Message(BaseModel):
    role: Literal["user","assistant","system"]
    content: str = Field(min_length=1,max_length=8000)
class EvaluateRequest(BaseModel):
    session_id: str = Field(min_length=1,max_length=128)
    messages: list[Message] = Field(min_length=1,max_length=100)
class SseEvent(BaseModel):
    type: Literal["text","done","error"]
    delta: str|None=None
    requestId: str|None=None
    message: str|None=None
app=FastAPI(title="AI Teaching Assistant Worker",version="0.1.0")
async def event_stream(response:str,request_id:str)->AsyncIterator[bytes]:
    try:
        for token in response.split(" "):
            yield f"data: {SseEvent(type='text',delta=token+' ').model_dump_json()}\n\n".encode(); await asyncio.sleep(.01)
        yield f"data: {SseEvent(type='done',requestId=request_id).model_dump_json()}\n\n".encode()
    except Exception as exc:
        yield f"data: {SseEvent(type='error',message=str(exc)).model_dump_json()}\n\n".encode()
@app.get("/health")
async def health()->dict[str,str]: return {"status":"ok"}
@app.post("/internal/evaluate")
async def evaluate(request:EvaluateRequest)->StreamingResponse:
    if not request.messages: raise HTTPException(400,"At least one message is required")
    result=run_graph([ChatMessage(role=m.role,content=m.content) for m in request.messages]); response=result.get("response","").strip()
    if not response: raise HTTPException(500,"Worker produced an empty response")
    return StreamingResponse(event_stream(response,result.get("request_id",str(uuid.uuid4()))),media_type="text/event-stream",headers={"Cache-Control":"no-cache","Connection":"keep-alive","X-Accel-Buffering":"no"})
