from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import subprocess

router = APIRouter(prefix="/api/v1/demos", tags=["core_demos"])

@router.get("/lead-forager/stream")
async def lead_forager():
    from demo_lead_forager import generate_leads_stream
    return StreamingResponse(generate_leads_stream(), media_type="text/event-stream")

class BookingPayload(BaseModel):
    message: str = ""
    history: str = ""

@router.post("/booking/chat")
async def booking(payload: BookingPayload):
    from demo_autonomous_booking import process_chat_turn
    return process_chat_turn(payload.message, payload.history)

@router.post("/ghost/launch")
async def ghost():
    try:
        subprocess.Popen(["C:\\AI-BS\\Launch_Ghost_Demo.bat"], cwd="C:\\AI-BS")
        return {"status": "Ghost launched successfully"}
    except Exception as e:
        return {"error": str(e)}
