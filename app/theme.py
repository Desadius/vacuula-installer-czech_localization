"""Class containing colours to use, and the stylesheet"""

# Colours chosen based on Vacuula logo and what Philip likes
# They will need refinement

# Don't question the stylesheet, I know what im doing™

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg_colour: str = "#25262d"

    border_soft: str = "#4B4B65"

    text_primary: str = "#f3f0fa"
    text_muted: str = "#8f84ac"
    flair_text: str = "#cabdec"

    accent_blue: str = "#5c73f6"
    accent_blue_hover: str = "#707cff"
    accent_blue_pressed: str = "#4758c9"

    accent_green: str = "#0f9616"
    accent_green_hover: str = "#0f9616"
    accent_green_pressed: str = "#0f9616"

    gold_top: str = "#f5db8c"
    gold_bottom: str = "#c99b34"
    gold_hover_top: str = "#ffe8a8"
    gold_pressed_bottom: str = "#a87e26"
    gold_text: str = "#2a1d08"


PALETTE = Palette()

STYLE_SHEET = f"""
QWidget#central {{
    background: {PALETTE.bg_colour};
}}


QWidget#leftPanel {{
    background: {PALETTE.bg_colour};
}}

QWidget#rightPanel {{
    background: {PALETTE.bg_colour};
}}

QLabel {{
    color: {PALETTE.text_primary};
}}

QLabel#taglineLabel {{
    color: {PALETTE.text_muted};
    font-size: 14px;
}}

QLabel#connectInstructionLabel {{
    color: {PALETTE.text_primary};
    font-size: 18px;
    font-weight: 600;
}}

QLabel#serversearchTitleLabel {{
    color: {PALETTE.text_primary};
    font-size: 40px;
    font-weight: 700;
}}

QLabel#serversearchBodyLabel {{
    color: {PALETTE.text_primary};
    font-weight: 500;
    font-size: 18px;

}}

QLabel#serversearchDetailLabel {{
    color: {PALETTE.text_primary};
    font-size: 14px;
}}

QLabel#serverSearchDOTS {{
    color: {PALETTE.text_muted};
    font-size: 24px;

}}
QLabel#serverSearchCROSS {{
    color: {PALETTE.text_muted};
    font-size: 40px;
    
}}

QLabel#statusLabel {{
    color: {PALETTE.text_muted};
    font-size: 12px;
}}

QToolButton#flagButton {{
    background-color: rgba(255, 255, 255, 20); 
    border: 1px solid {PALETTE.border_soft};
    border-radius: 32px;
    font-size: 28px;
    padding-top: 3px;
}}

QToolButton#flagButton:hover {{
    background-color: {PALETTE.accent_blue_hover};
}}

QToolButton#flagButton::menu-indicator {{
    image: none;
    width: 0px;
}}

QMenu#languageMenu {{
    background-color: {PALETTE.bg_colour};
    border: 1px solid {PALETTE.border_soft};
    border-radius: 16px;
}}

QMenu#languageMenu::item {{
    padding: 0px;
    background: transparent;
}}

QMenu#languageMenu::item:selected {{
    background: transparent;
}}

QToolButton#backButton {{
    color: {PALETTE.text_muted};
    font-size: 24px;
    font-weight: 700;
    background: transparent;
    border: none;
}}

QToolButton#backButton:hover {{
    color: {PALETTE.text_primary};
}}

QPushButton#continueButton {{
    background-color: {PALETTE.accent_blue};
    color: white;
    border: none;
    border-radius: 22px;
    padding: 12px 42px;
    font-size: 14px;
    font-weight: 600;
}}

QPushButton#continueButton:hover {{
    background-color: {PALETTE.accent_blue_hover};
}}

QPushButton#continueButton:pressed {{
    background-color: {PALETTE.accent_blue_pressed};
}}

QPushButton#goldButton {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {PALETTE.gold_top},
        stop:1 {PALETTE.gold_bottom}
    );
    color: {PALETTE.gold_text};
    border: none;
    border-radius: 24px;
    padding: 15px 48px;
    font-size: 15px;
    font-weight: 700;
}}

QPushButton#goldButton:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {PALETTE.gold_hover_top},
        stop:1 {PALETTE.gold_bottom}
    );
}}

QPushButton#goldButton:pressed {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {PALETTE.gold_bottom},
        stop:1 {PALETTE.gold_pressed_bottom}
    );
}}

QPushButton#goldButton:disabled {{
    background: {PALETTE.border_soft};
    color: {PALETTE.text_muted};
}}
"""
