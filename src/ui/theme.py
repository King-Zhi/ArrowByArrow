"""
UI 主题配色、字体渲染与矢量图形绘制工具
提供现代暗色系卡片视觉风格与多平台中文字体自适应回退
"""

import math
from typing import Tuple, List, Optional
import pygame


class Theme:
    """现代极简雅致暗色主题"""

    # 背景与面板
    BG_MAIN = (18, 22, 28)
    BG_PANEL = (28, 34, 44)
    BG_CELL = (38, 45, 58)
    BG_CELL_HOVER = (48, 56, 72)
    BORDER = (58, 68, 86)

    # 文本颜色
    TEXT_MAIN = (245, 247, 250)
    TEXT_MUTED = (145, 155, 170)
    TEXT_ACCENT = (100, 180, 255)

    # 状态与指示色
    COLOR_SUCCESS = (46, 204, 113)
    COLOR_DANGER = (231, 76, 60)
    COLOR_WARNING = (241, 196, 15)
    COLOR_INFO = (52, 152, 219)

    # 箭头视觉
    ARROW_BODY = (70, 150, 240)
    ARROW_BORDER = (120, 190, 255)
    ARROW_HIGHLIGHT = (255, 215, 0)
    ARROW_COLLISION = (240, 70, 70)


class FontManager:
    """中英文字体加载管理器（支持 Windows 字体回退）"""

    _fonts = {}

    @classmethod
    def get_font(cls, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key in cls._fonts:
            return cls._fonts[key]

        font_names = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "Arial", "sans-serif"]
        chosen_font = None

        for name in font_names:
            try:
                matched = pygame.font.match_font(name, bold=bold)
                if matched:
                    chosen_font = pygame.font.Font(matched, size)
                    break
            except Exception:
                continue

        if chosen_font is None:
            chosen_font = pygame.font.SysFont("sans-serif", size, bold=bold)

        cls._fonts[key] = chosen_font
        return chosen_font


def draw_rounded_rect(surface: pygame.Surface, rect: pygame.Rect, color: Tuple[int, int, int], radius: int = 10, border_color: Optional[Tuple[int, int, int]] = None, border_width: int = 0):
    """绘制现代平滑圆角矩形"""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color and border_width > 0:
        pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=radius)


def draw_arrow_polygon(surface: pygame.Surface, center: Tuple[float, float], size: float, angle_deg: float, fill_color: Tuple[int, int, int], border_color: Optional[Tuple[int, int, int]] = None):
    """
    在指定中心绘制带尖头和箭身的精致矢量箭头多边形
    angle_deg: 0度向上，90度向右，180度向下，270度向左
    """
    # 局部坐标系下的箭头顶点（以 (0, 0) 为中心，朝上）
    # 箭头长度约为 size * 0.8
    half = size * 0.42
    w_head = size * 0.36
    w_shaft = size * 0.16
    h_head = size * 0.38

    # 顶点：从顶部尖角开始顺时针
    local_pts = [
        (0, -half),                   # 箭头顶点
        (w_head, -half + h_head),     # 箭头右翼尖
        (w_shaft, -half + h_head),    # 箭头右颈
        (w_shaft, half),              # 箭尾右角
        (-w_shaft, half),             # 箭尾左角
        (-w_shaft, -half + h_head),   # 箭头左颈
        (-w_head, -half + h_head),    # 箭头左翼尖
    ]

    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    cx, cy = center
    transformed_pts = []
    for lx, ly in local_pts:
        # 顺时针旋转公式: rx = lx*cos - ly*sin, ry = lx*sin + ly*cos
        rx = lx * cos_a - ly * sin_a + cx
        ry = lx * sin_a + ly * cos_a + cy
        transformed_pts.append((rx, ry))

    pygame.draw.polygon(surface, fill_color, transformed_pts)
    if border_color:
        pygame.draw.polygon(surface, border_color, transformed_pts, width=2)
