from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from core.lexicon_service import LexiconService

router = APIRouter(prefix="/lexicon", tags=["Lexicon Vault"])

class EnrichRequest(BaseModel):
    text: str

@router.get("/synonyms")
async def get_synonyms(word: str = Query(..., description="The word to find synonyms for"), limit: int = Query(10, description="Max synonyms to return")):
    try:
        synonyms = LexiconService.get_synonyms(word, limit)
        return {"word": word, "synonyms": synonyms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enrich")
async def enrich_text(req: EnrichRequest):
    try:
        expansion_map = LexiconService.bulk_expand(req.text)
        return {"original_text": req.text, "expansion_map": expansion_map}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
