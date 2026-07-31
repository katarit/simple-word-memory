"""デザイントークンと QSS。

配色と寸法の値はすべてここに集約する。個々のウィジェット側で色や余白を
直書きしない（テーマ切り替えで追従しなくなるため）。
"""

from __future__ import annotations

LIGHT = {
    "bg": "#E4EAF0",
    "surface": "#F4F7FA",
    "surface_rgb": "244, 247, 250",
    "surface_alt": "#E6ECF3",
    "field": "#FFFFFF",
    "ink": "#1B2430",
    "ink_muted": "#5A6675",
    "border": "#D2DBE4",
    "accent": "#C97A2B",
    "accent_ink": "#FFFFFF",
    "danger": "#B3432B",
    "widget_edge": "rgba(255, 255, 255, 0.55)",
}

DARK = {
    "bg": "#1A1F26",
    "surface": "#232A33",
    "surface_rgb": "35, 42, 51",
    "surface_alt": "#2B333D",
    "field": "#1E242B",
    "ink": "#E8EBEF",
    "ink_muted": "#9BA6B3",
    "border": "#38414C",
    "accent": "#E3A34E",
    "accent_ink": "#1C1206",
    "danger": "#E08165",
    "widget_edge": "rgba(255, 255, 255, 0.10)",
}

FONT_FAMILY = '"Segoe UI Variable", "Segoe UI", "Yu Gothic UI", sans-serif'

# 寸法（8pt グリッド）
WIDGET_WIDTH = 240
WIDGET_HEIGHT = 72
WIDGET_RADIUS = 16
WIDGET_PADDING_X = 16
WIDGET_WORD_SIZE = 22

PANEL_WIDTH = 384
PANEL_HEIGHT = 520
PANEL_HEADER_HEIGHT = 56
PANEL_TAB_HEIGHT = 40
PANEL_CONTENT_PADDING = 24
ROW_HEIGHT = 56
THEME_BUTTON_HEIGHT = 22


def is_dark(app) -> bool:
    """OS のテーマ設定を読む。取得できない環境では明度から推定する。"""
    try:
        from PySide6.QtCore import Qt

        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except (AttributeError, ImportError):
        pass
    return app.palette().window().color().lightness() < 128


def tokens(dark: bool) -> dict[str, str]:
    return DARK if dark else LIGHT


def widget_qss(t: dict[str, str]) -> str:
    """ウィジェット（枠なし半透明カード）。"""
    return f"""
    #widgetCard {{
        background-color: rgba({t["surface_rgb"]}, 0.90);
        border: 1px solid {t["widget_edge"]};
        border-radius: {WIDGET_RADIUS}px;
    }}
    #widgetWord {{
        font-family: {FONT_FAMILY};
        font-size: {WIDGET_WORD_SIZE}px;
        font-weight: 600;
        color: {t["ink"]};
        background: transparent;
    }}
    #widgetEmpty {{
        font-family: {FONT_FAMILY};
        font-size: 14px;
        color: {t["ink_muted"]};
        background: transparent;
    }}
    """


def panel_qss(t: dict[str, str]) -> str:
    """管理パネル。"""
    return f"""
    QWidget {{
        font-family: {FONT_FAMILY};
        color: {t["ink"]};
    }}
    #panelRoot, #page, QStackedWidget {{
        background-color: {t["surface"]};
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: {t["surface"]};
    }}
    #panelHeader {{
        background-color: {t["surface"]};
        border-bottom: 1px solid {t["border"]};
    }}
    #panelTitle {{
        font-size: 15px;
        font-weight: 600;
    }}
    #tabBar {{
        background-color: {t["surface"]};
        border-bottom: 1px solid {t["border"]};
    }}
    QPushButton#tab {{
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 0;
    }}
    QPushButton#tab:checked {{
        border-bottom: 2px solid {t["accent"]};
    }}
    #tabLabel {{
        font-size: 13px;
        font-weight: 600;
        color: {t["ink_muted"]};
        background: transparent;
    }}
    #tabLabelActive {{
        font-size: 13px;
        font-weight: 600;
        color: {t["ink"]};
        background: transparent;
    }}
    #badge, #badgeActive {{
        font-size: 11px;
        font-weight: 600;
        color: {t["ink_muted"]};
        background: transparent;
        padding: 0;
    }}
    #fieldLabel {{
        font-size: 12px;
        font-weight: 600;
        color: {t["ink_muted"]};
    }}
    #metaLine {{
        font-size: 12px;
        color: {t["ink_muted"]};
    }}
    QLineEdit, QPlainTextEdit {{
        border: 1px solid {t["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        color: {t["ink"]};
        background-color: {t["field"]};
        selection-background-color: {t["accent"]};
        selection-color: {t["accent_ink"]};
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {t["accent"]};
    }}
    QPushButton#primary {{
        background-color: {t["accent"]};
        color: {t["accent_ink"]};
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        padding: 0 18px;
    }}
    QPushButton#ghost {{
        background: transparent;
        color: {t["ink_muted"]};
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        padding: 0 18px;
    }}
    QPushButton#back {{
        background: transparent;
        color: {t["ink_muted"]};
        border: none;
        font-size: 12px;
        font-weight: 600;
        text-align: left;
        padding: 0;
    }}
    #hint {{
        font-size: 12px;
        color: {t["ink_muted"]};
    }}
    #hintError {{
        font-size: 12px;
        color: {t["danger"]};
    }}
    #rowWord {{
        font-size: 14px;
        font-weight: 600;
        color: {t["ink"]};
    }}
    #rowWordLearned {{
        font-size: 14px;
        font-weight: 400;
        color: {t["ink_muted"]};
    }}
    #rowDate, #rowNote {{
        color: {t["ink_muted"]};
    }}
    #rowDate {{ font-size: 11px; }}
    #rowNote {{ font-size: 12px; }}
    #row {{
        background-color: {t["surface"]};
        border: none;
        border-bottom: 1px solid {t["border"]};
    }}
    #emptyState {{
        font-size: 13px;
        color: {t["ink_muted"]};
    }}
    QPushButton#themeToggle {{
        font-size: 12px;
        font-weight: 600;
        color: {t["ink_muted"]};
        background-color: {t["surface_alt"]};
        border: 1px solid {t["border"]};
        border-radius: 11px;
        padding: 0 12px;
    }}
    QPushButton#themeToggle:hover {{
        color: {t["ink"]};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {t["border"]};
        border-radius: 4px;
        background-color: {t["field"]};
    }}
    QCheckBox::indicator:checked {{
        background-color: {t["accent"]};
        border: 1px solid {t["accent"]};
        image: none;
    }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t["border"]};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
