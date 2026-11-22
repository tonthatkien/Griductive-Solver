"""UI components tái sử dụng. (Scope F)

File này chỉ re-export để `from gui.components import ...` vẫn chạy như cũ.
Code thật nằm ở các module: draw_utils, anim, card_view (+ card_back, card_front, card_highlight),
grid_view, gadget_button, radial_menu, conan_widgets, effect_overlay, notebook_panel, clue_list,
night_backdrop, neon_widgets. Không chứa luật chơi hay suy luận.
"""
from gui.anim import ASSET_DIR, IDLE_FPS, Clock, Tween, Typer, character_pixmap, clock
from gui.clue_list import ClueListView
from gui.conan_widgets import ConanToast, ConanWidget
from gui.card_view import CardView
from gui.draw_utils import (A, ALIGN_CENTER, ALIGN_LEFT_MID, WRAP_CENTER, WRAP_TOP, draw_brackets,
                            draw_fitted, draw_neon_text, draw_typed, flags, make_font)
from gui.effect_overlay import EffectOverlay
from gui.gadget_button import GadgetButton
from gui.grid_view import GridView
from gui.neon_widgets import NeonTitle, TerminalMessage
from gui.night_backdrop import NightBackdrop
from gui.notebook_panel import NotebookPanel
from gui.radial_menu import RadialMenu

__all__ = [
    "A", "ALIGN_CENTER", "ALIGN_LEFT_MID", "ASSET_DIR", "CardView", "Clock", "ClueListView", "ConanToast",
    "ConanWidget", "EffectOverlay", "GadgetButton", "GridView", "IDLE_FPS", "NeonTitle", "NightBackdrop",
    "NotebookPanel", "RadialMenu", "TerminalMessage", "Tween", "Typer", "WRAP_CENTER", "WRAP_TOP",
    "character_pixmap", "clock", "draw_brackets", "draw_fitted", "draw_neon_text", "draw_typed", "flags",
    "make_font",
]
