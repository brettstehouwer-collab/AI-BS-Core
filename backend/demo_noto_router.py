from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
import demo_noto

router = APIRouter(prefix="/api/v1/demos/noto", tags=["noto"])

class EtiquettePayload(BaseModel):
    message: str = ""
    history: list = []

@router.post("/etiquette")
async def etiquette(payload: EtiquettePayload):
    return await demo_noto.handle_etiquette_chat(payload.message, payload.history)

@router.post("/bocce-upsell")
async def bocce():
    return await demo_noto.handle_bocce_upsell()

class BanquetPayload(BaseModel):
    prompt: str = ""

@router.post("/banquet-architect")
async def banquet(payload: BanquetPayload):
    return await demo_noto.handle_banquet_architect(payload.prompt)

@router.post("/cellar-master")
async def cellar(payload: Dict[Any, Any]):
    return await demo_noto.handle_cellar_master(payload)

class UnrealControlPayload(BaseModel):
    command: str = ""
    payload: Dict[Any, Any] = {}

@router.post("/unreal-remote-control")
async def unreal_control(req: UnrealControlPayload):
    return await demo_noto.handle_unreal_remote_control(req.command, req.payload)

class MediaAssistantPayload(BaseModel):
    prompt: str = ""

@router.post("/media-assistant")
async def media_assistant(req: MediaAssistantPayload):
    return await demo_noto.handle_media_assistant_nlp(req.prompt)

@router.get("/plate-scraping")
async def plate():
    return await demo_noto.get_plate_scraping_data()

@router.get("/scheduling")
async def scheduling():
    return await demo_noto.get_scheduling_data()

@router.get("/employee-chat")
async def emp_chat():
    return await demo_noto.get_employee_chat()

@router.get("/master-calendar")
async def calendar():
    return await demo_noto.get_master_calendar()

class SuggestionPayload(BaseModel):
    suggestion: str = ""
    name: str = ""

@router.post("/anonymous-suggestion")
async def suggestion(payload: SuggestionPayload):
    return await demo_noto.handle_anonymous_suggestion(payload.suggestion, payload.name)

class NfcPayload(BaseModel):
    lat: float = 0.0
    lng: float = 0.0

@router.post("/nfc-timeclock")
async def nfc(payload: NfcPayload):
    return await demo_noto.handle_nfc_timeclock(payload.lat, payload.lng)
