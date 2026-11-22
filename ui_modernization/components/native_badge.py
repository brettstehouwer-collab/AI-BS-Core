"""Scoped presentation for the existing native StatusBadge contract."""
from ui_modernization.generated.native_palette import COLORS, RADIUS, TYPOGRAPHY, MOM_TYPOGRAPHY


def badge_style(online: bool, mom: bool = False) -> str:
    """Use verified tokens without changing the badge's meaning or ownership."""
    color = COLORS["ready"] if online else COLORS["unavailable"]
    font = MOM_TYPOGRAPHY if mom else TYPOGRAPHY
    return (
        'QLabel[aibsVisualVariant="fluent"] { '
        f'color: {color}; background-color: {COLORS["raised"]}; '
        f'border: 1px solid {color}; border-radius: {RADIUS["pill"]}px; '
        f'padding: 3px 8px; font-size: {font["caption"]}px; font-weight: 600; '
        '}'
    )
