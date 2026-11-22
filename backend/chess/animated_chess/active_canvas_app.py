import os, sys
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame as _pg
_orig_flip = _pg.display.flip
_frame_path = r'C:\\AI-BS\\backend\\chess\\animated_chess\\_frame.bmp'
def _stream_flip():
    _orig_flip()
    try:
        surf = _pg.display.get_surface()
        if surf:
            _pg.image.save(surf, _frame_path)
    except Exception:
        pass
_pg.display.flip = _stream_flip

import pygame
pygame.init()
