from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from core.chat_film_store import FilmStore
from core.personal_memory_scope import current_memory_principal

router=APIRouter(prefix='/api/chat/films',tags=['Chat films'])

@router.get('/{film_id}/download')
def download(film_id: str):
    try:
        owner=current_memory_principal();store=FilmStore();film=store.get(owner,film_id)
        if film['state']!='complete' or not film.get('output'):raise ValueError('Film is not assembled')
        path=Path(film['output']).resolve()
        if not path.is_relative_to(store.directory(owner,film_id).resolve()) or not path.is_file():
            raise ValueError('Saved output unavailable')
        return FileResponse(path,media_type='video/mp4',filename=f'AI-BS-film-{film_id}.mp4',headers={'Cache-Control':'private, no-store'})
    except (PermissionError,ValueError):
        raise HTTPException(status_code=404,detail='Film unavailable for this account') from None
