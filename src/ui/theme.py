"""
赛博霓虹与合成波街机风 UI 主题引擎（Cyberpunk Synthwave & Neon Arcade）
包含高阶激光箭头绘制、霓虹发光晕染、科技感直角角标面板与全几何矢量物理图标库
"""

import math
import os
import sys
from typing import Tuple, List, Optional, Dict
import pygame


class ColorPalette:
    """赛博霓虹与合成波街机风色彩矩阵"""

    # 宇宙与暗夜深邃底色
    BG_DEEP = (12, 10, 24)           # 深邃黑紫
    BG_GRID_DOT = (38, 30, 68)

    # 悬浮面板与科技卡片
    PANEL_BG = (22, 17, 44)          # 暗黑曜石微透紫
    PANEL_BORDER = (65, 52, 110)     # 基础暗紫金属边框
    PANEL_BORDER_NEON = (0, 240, 255)# 霓虹天青外框
    PANEL_BORDER_MAG = (255, 0, 128) # 霓虹洋红外框
    PANEL_HOVER = (36, 28, 70)

    # 棋盘网格单元
    CELL_BG = (16, 13, 34)           # 凹陷感深色暗核瓷砖
    CELL_BORDER = (46, 36, 76)       # 电子网格线
    CELL_HOVER = (38, 30, 80)        # 悬停激活底

    # 文字层级
    TEXT_TITLE = (255, 255, 255)
    TEXT_MAIN = (228, 238, 255)
    TEXT_MUTED = (142, 150, 188)
    TEXT_GOLD = (255, 220, 60)
    TEXT_CYAN = (0, 240, 255)
    TEXT_PINK = (255, 60, 160)

    # 核心高能霓虹强调色
    CYAN = (0, 240, 255)             # 电光天青 (Electric Cyan)
    MAGENTA = (255, 0, 128)          # 霓虹洋红 (Hot Magenta / Synthwave Pink)
    LIME = (57, 255, 20)             # 激光翠绿 (Neon Lime Green)
    PURPLE = (175, 60, 255)          # 幻能电紫 (Cyber Violet)
    AMBER = (255, 205, 0)            # 极光琥珀金 (Electric Gold)
    ROSE = (255, 45, 85)             # 警报霓红 (Cyber Coral Red)
    EMERALD = (0, 255, 160)          # 能量通关绿 (Matrix Mint)
    BLUE = (0, 150, 255)             # 脉冲深蓝

    # 方向特征激光霓虹色 (上/右/下/左 独立色彩)
    DIR_UP = (0, 240, 255)           # 天青
    DIR_RIGHT = (255, 20, 140)       # 桃红
    DIR_DOWN = (60, 255, 80)         # 亮绿
    DIR_LEFT = (255, 195, 20)        # 亮金

    # 3D 箭头配色（基础兼容）
    ARROW_BODY = (0, 220, 255)
    ARROW_LIGHT = (210, 250, 255)
    ARROW_DARK = (0, 110, 190)
    ARROW_BORDER = (0, 240, 255)

    ARROW_HIGHLIGHT = (255, 225, 0)
    ARROW_HL_LIGHT = (255, 255, 210)
    ARROW_HL_DARK = (190, 145, 0)

    ARROW_COLLISION = (255, 45, 85)
    ARROW_COL_LIGHT = (255, 180, 195)
    ARROW_COL_DARK = (180, 20, 50)


class AssetLoader:
    """美术素材加载器（带优雅回退）"""

    _cached_bg: Optional[pygame.Surface] = None

    @classmethod
    def get_path(cls, rel_path: str) -> str:
        """获取资源文件的绝对路径（兼容开发环境与 PyInstaller 解压运行环境）"""
        base_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        return os.path.join(base_dir, rel_path)

    @classmethod
    def get_background(cls, width: int = 960, height: int = 720) -> pygame.Surface:
        if cls._cached_bg and cls._cached_bg.get_size() == (width, height):
            return cls._cached_bg

        base_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        bg_path = os.path.join(base_dir, "assets", "images", "bg.png")
        if os.path.exists(bg_path):
            try:
                loaded = pygame.image.load(bg_path).convert()
                if loaded.get_size() != (width, height):
                    loaded = pygame.transform.smoothscale(loaded, (width, height))
                cls._cached_bg = loaded
                return cls._cached_bg
            except Exception as e:
                print(f"[AssetLoader] 加载背景图异常，采用动态合成: {e}")

        # 回退：动态渲染 80s 合成波透视网格背景
        fallback = pygame.Surface((width, height))
        for y in range(height):
            t = y / height
            r = int(12 + 20 * math.sin(t * math.pi * 0.9))
            g = int(10 + 12 * math.sin(t * math.pi * 0.9))
            b = int(24 + 36 * math.sin(t * math.pi * 0.9))
            pygame.draw.line(fallback, (r, g, b), (0, y), (width, y))

        # 透视网格地平面
        horizon = int(height * 0.6)
        vanish_x = width // 2
        for deg in range(-70, 71, 14):
            slope = math.tan(math.radians(deg))
            bx = vanish_x + (height - horizon) * slope * 2.2
            pygame.draw.line(fallback, (70, 20, 80), (vanish_x, horizon), (int(bx), height), 1)

        cls._cached_bg = fallback
        return cls._cached_bg


class FontManager:
    """字体引擎（支持全平台系统回退）"""

    _cache: Dict[Tuple[int, bool], pygame.font.Font] = {}

    @classmethod
    def get(cls, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key in cls._cache:
            return cls._cache[key]

        font_candidates = [
            "Microsoft YaHei UI", "Microsoft YaHei", "SimHei",
            "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei",
            "Segoe UI", "Arial", "sans-serif"
        ]

        font_obj = None
        for name in font_candidates:
            try:
                matched = pygame.font.match_font(name, bold=bold)
                if matched:
                    font_obj = pygame.font.Font(matched, size)
                    break
            except Exception:
                continue

        if not font_obj:
            font_obj = pygame.font.SysFont("sans-serif", size, bold=bold)

        cls._cache[key] = font_obj
        return font_obj


# ==========================================
# 矢量图标绘制器（100% 杜绝字体缺字方块 □ 问题）
# ==========================================

def draw_vector_icon(surface: pygame.Surface, center: Tuple[int, int], size: int, icon_type: str, color: Tuple[int, int, int]):
    """
    用纯几何矢量算法绘制高质感游戏图标，完全摆脱字体字形限制
    """
    cx, cy = center
    hs = size // 2

    if icon_type == "play":
        # 播放三角形
        pts = [(cx - hs * 0.6, cy - hs * 0.8), (cx + hs * 0.9, cy), (cx - hs * 0.6, cy + hs * 0.8)]
        pygame.draw.polygon(surface, color, pts)

    elif icon_type == "levels":
        # 2x2 关卡方块矩阵
        box_s = max(3, size // 3)
        gap = max(2, size // 6)
        for dx in (-gap - box_s // 2, gap - box_s // 2):
            for dy in (-gap - box_s // 2, gap - box_s // 2):
                pygame.draw.rect(surface, color, (cx + dx, cy + dy, box_s, box_s), border_radius=2)

    elif icon_type == "music_on":
        # 赛博连梁双音符 (♫)
        # 左音符头与符干
        pygame.draw.ellipse(surface, color, (cx - hs * 0.65, cy + hs * 0.15, hs * 0.45, hs * 0.38))
        pygame.draw.line(surface, color, (cx - hs * 0.22, cy + hs * 0.35), (cx - hs * 0.22, cy - hs * 0.55), width=2)
        # 右音符头与符干
        pygame.draw.ellipse(surface, color, (cx + hs * 0.15, cy - hs * 0.05, hs * 0.45, hs * 0.38))
        pygame.draw.line(surface, color, (cx + hs * 0.58, cy + hs * 0.15), (cx + hs * 0.58, cy - hs * 0.75), width=2)
        # 顶部斜向连梁
        beam_pts = [
            (cx - hs * 0.25, cy - hs * 0.55),
            (cx + hs * 0.60, cy - hs * 0.75),
            (cx + hs * 0.60, cy - hs * 0.45),
            (cx - hs * 0.25, cy - hs * 0.25),
        ]
        pygame.draw.polygon(surface, color, beam_pts)

    elif icon_type == "music_off":
        # 赛博连梁双音符 + 玫瑰红斜向静音杠
        pygame.draw.ellipse(surface, color, (cx - hs * 0.65, cy + hs * 0.15, hs * 0.45, hs * 0.38))
        pygame.draw.line(surface, color, (cx - hs * 0.22, cy + hs * 0.35), (cx - hs * 0.22, cy - hs * 0.55), width=2)
        pygame.draw.ellipse(surface, color, (cx + hs * 0.15, cy - hs * 0.05, hs * 0.45, hs * 0.38))
        pygame.draw.line(surface, color, (cx + hs * 0.58, cy + hs * 0.15), (cx + hs * 0.58, cy - hs * 0.75), width=2)
        beam_pts = [
            (cx - hs * 0.25, cy - hs * 0.55),
            (cx + hs * 0.60, cy - hs * 0.75),
            (cx + hs * 0.60, cy - hs * 0.45),
            (cx - hs * 0.25, cy - hs * 0.25),
        ]
        pygame.draw.polygon(surface, color, beam_pts)
        pygame.draw.line(surface, ColorPalette.ROSE, (cx - hs * 0.75, cy - hs * 0.75), (cx + hs * 0.75, cy + hs * 0.75), width=2)

    elif icon_type == "sound_on":
        # 喇叭主体 + 声音波纹
        pygame.draw.rect(surface, color, (cx - hs * 0.8, cy - hs * 0.35, hs * 0.45, hs * 0.7), border_radius=1)
        horn_pts = [
            (cx - hs * 0.4, cy - hs * 0.35),
            (cx - hs * 0.05, cy - hs * 0.75),
            (cx - hs * 0.05, cy + hs * 0.75),
            (cx - hs * 0.4, cy + hs * 0.35)
        ]
        pygame.draw.polygon(surface, color, horn_pts)
        wave_box1 = pygame.Rect(cx - hs * 0.3, cy - hs * 0.5, hs * 0.9, hs * 1.0)
        pygame.draw.arc(surface, color, wave_box1, -math.pi * 0.35, math.pi * 0.35, width=2)
        wave_box2 = pygame.Rect(cx - hs * 0.2, cy - hs * 0.8, hs * 1.4, hs * 1.6)
        pygame.draw.arc(surface, color, wave_box2, -math.pi * 0.35, math.pi * 0.35, width=2)

    elif icon_type == "sound_off":
        # 喇叭主体 + 斜红叉
        pygame.draw.rect(surface, color, (cx - hs * 0.8, cy - hs * 0.35, hs * 0.45, hs * 0.7), border_radius=1)
        horn_pts = [
            (cx - hs * 0.4, cy - hs * 0.35),
            (cx - hs * 0.05, cy - hs * 0.75),
            (cx - hs * 0.05, cy + hs * 0.75),
            (cx - hs * 0.4, cy + hs * 0.35)
        ]
        pygame.draw.polygon(surface, color, horn_pts)
        pygame.draw.line(surface, ColorPalette.ROSE, (cx + hs * 0.2, cy - hs * 0.5), (cx + hs * 0.8, cy + hs * 0.5), width=2)
        pygame.draw.line(surface, ColorPalette.ROSE, (cx + hs * 0.8, cy - hs * 0.5), (cx + hs * 0.2, cy + hs * 0.5), width=2)

    elif icon_type == "quit":
        # 退出 X 符号
        w = max(2, size // 8)
        pygame.draw.line(surface, color, (cx - hs * 0.7, cy - hs * 0.7), (cx + hs * 0.7, cy + hs * 0.7), width=w)
        pygame.draw.line(surface, color, (cx + hs * 0.7, cy - hs * 0.7), (cx - hs * 0.7, cy + hs * 0.7), width=w)

    elif icon_type == "restart":
        # 环形刷新箭头
        arc_rect = pygame.Rect(cx - hs * 0.75, cy - hs * 0.75, hs * 1.5, hs * 1.5)
        pygame.draw.arc(surface, color, arc_rect, -math.pi * 0.3, math.pi * 1.3, width=2)
        arrow_tip = [
            (cx + hs * 0.75, cy - hs * 0.3),
            (cx + hs * 0.95, cy + hs * 0.1),
            (cx + hs * 0.45, cy + hs * 0.1)
        ]
        pygame.draw.polygon(surface, color, arrow_tip)

    elif icon_type == "hint":
        # 科技灯泡图标
        pygame.draw.circle(surface, color, (cx, cy - hs * 0.2), int(hs * 0.55))
        pygame.draw.rect(surface, color, (cx - hs * 0.25, cy + hs * 0.3, hs * 0.5, hs * 0.3), border_radius=1)
        # 灯丝发光核心
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy - hs * 0.2), max(1, int(hs * 0.25)))

    elif icon_type == "undo":
        # 弯曲撤销箭头
        arc_rect = pygame.Rect(cx - hs * 0.8, cy - hs * 0.8, hs * 1.6, hs * 1.6)
        pygame.draw.arc(surface, color, arc_rect, math.pi * 0.1, math.pi * 1.0, width=2)
        arrow_pts = [
            (cx - hs * 0.8, cy),
            (cx - hs * 0.4, cy - hs * 0.4),
            (cx - hs * 0.4, cy + hs * 0.4)
        ]
        pygame.draw.polygon(surface, color, arrow_pts)

    elif icon_type == "solve":
        # 闪电 AI 图标
        bolt_pts = [
            (cx + hs * 0.1, cy - hs * 0.85),
            (cx - hs * 0.55, cy + hs * 0.05),
            (cx - hs * 0.05, cy + hs * 0.05),
            (cx - hs * 0.2, cy + hs * 0.85),
            (cx + hs * 0.6, cy - hs * 0.15),
            (cx + hs * 0.05, cy - hs * 0.15),
        ]
        pygame.draw.polygon(surface, color, bolt_pts)

    elif icon_type == "menu":
        # 现代科技终端主页图标
        roof_pts = [(cx, cy - hs * 0.8), (cx + hs * 0.8, cy - hs * 0.1), (cx - hs * 0.8, cy - hs * 0.1)]
        pygame.draw.polygon(surface, color, roof_pts)
        pygame.draw.rect(surface, color, (cx - hs * 0.55, cy - hs * 0.1, hs * 1.1, hs * 0.8), border_radius=1)
        pygame.draw.rect(surface, ColorPalette.BG_DEEP, (cx - hs * 0.2, cy + hs * 0.2, hs * 0.4, hs * 0.5), border_radius=1)

    elif icon_type == "next":
        # 向右箭头
        pts = [(cx - hs * 0.4, cy - hs * 0.6), (cx + hs * 0.5, cy), (cx - hs * 0.4, cy + hs * 0.6)]
        pygame.draw.polygon(surface, color, pts)


# ==========================================
# 拟态物理光影、霓虹晕染与图形绘制工具集
# ==========================================

def draw_soft_shadow(surface: pygame.Surface, rect: pygame.Rect, radius: int = 12, blur: int = 14, alpha: int = 90, color: Tuple[int, int, int] = (0, 0, 0)):
    """绘制细腻柔和的扩散环境阴影或霓虹辉光晕"""
    shadow_surf = pygame.Surface((rect.width + blur * 2, rect.height + blur * 2), pygame.SRCALPHA)
    for i in range(blur, 0, -2):
        layer_alpha = int(alpha * ((blur - i + 1) / blur) ** 1.8)
        inner_rect = pygame.Rect(blur - i, blur - i, rect.width + i * 2, rect.height + i * 2)
        pygame.draw.rect(shadow_surf, (*color, min(255, layer_alpha)), inner_rect, border_radius=radius + i)
    surface.blit(shadow_surf, (rect.x - blur, rect.y - blur + 2))


def draw_card(
    surface: pygame.Surface,
    rect: pygame.Rect,
    bg_color: Tuple[int, int, int] = ColorPalette.PANEL_BG,
    border_color: Tuple[int, int, int] = ColorPalette.PANEL_BORDER,
    radius: int = 12,
    shadow: bool = True,
    tech_corners: bool = True
):
    """
    绘制赛博朋克科技感发光面板（含可选高能拐角装饰）
    """
    if shadow:
        draw_soft_shadow(surface, rect, radius=radius, blur=14, alpha=80, color=(10, 8, 22))

    # 底板
    pygame.draw.rect(surface, bg_color, rect, border_radius=radius)

    # 边框
    if border_color:
        pygame.draw.rect(surface, border_color, rect, width=1, border_radius=radius)

    # 科技感四角微型发光直角标点缀（赛博 HUD 质感）
    if tech_corners and rect.width > 40 and rect.height > 40:
        c_len = min(12, int(rect.height * 0.2))
        c_col = ColorPalette.CYAN if border_color != ColorPalette.PANEL_BORDER else (120, 100, 180)
        # 左上
        pygame.draw.line(surface, c_col, (rect.left + 4, rect.top + 4), (rect.left + 4 + c_len, rect.top + 4), 2)
        pygame.draw.line(surface, c_col, (rect.left + 4, rect.top + 4), (rect.left + 4, rect.top + 4 + c_len), 2)
        # 右上
        pygame.draw.line(surface, c_col, (rect.right - 5, rect.top + 4), (rect.right - 5 - c_len, rect.top + 4), 2)
        pygame.draw.line(surface, c_col, (rect.right - 5, rect.top + 4), (rect.right - 5, rect.top + 4 + c_len), 2)
        # 左下
        pygame.draw.line(surface, c_col, (rect.left + 4, rect.bottom - 5), (rect.left + 4 + c_len, rect.bottom - 5), 2)
        pygame.draw.line(surface, c_col, (rect.left + 4, rect.bottom - 5), (rect.left + 4, rect.bottom - 5 - c_len), 2)
        # 右下
        pygame.draw.line(surface, c_col, (rect.right - 5, rect.bottom - 5), (rect.right - 5 - c_len, rect.bottom - 5), 2)
        pygame.draw.line(surface, c_col, (rect.right - 5, rect.bottom - 5), (rect.right - 5, rect.bottom - 5 - c_len), 2)


def draw_styled_heart(surface: pygame.Surface, center: Tuple[float, float], size: float, filled: bool = True):
    """矢量绘制赛博充能爱心护盾（采用高精度数学心形曲线）"""
    cx, cy = center
    col_main = ColorPalette.MAGENTA if filled else (45, 30, 60)
    col_border = (255, 120, 200) if filled else (75, 48, 95)

    scale = size / 34.0
    pts = []
    for deg in range(0, 360, 15):
        t = math.radians(deg)
        x = cx + scale * (16.0 * (math.sin(t) ** 3))
        y = cy - scale * (13.0 * math.cos(t) - 5.0 * math.cos(2*t) - 2.0 * math.cos(3*t) - math.cos(4*t))
        pts.append((x, y))

    if filled:
        # 霓虹光晕底层
        glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(glow_surf, (*ColorPalette.MAGENTA, 85), pts)
        surface.blit(glow_surf, (0, 0))

    pygame.draw.polygon(surface, col_main, pts)
    pygame.draw.polygon(surface, col_border, pts, width=1)

    # 核心高能白亮光斑
    if filled:
        pygame.draw.circle(surface, (255, 230, 245), (int(cx - size * 0.16), int(cy - size * 0.16)), max(1, int(size * 0.08)))


def draw_star(surface: pygame.Surface, center: Tuple[float, float], outer_r: float, inner_r: float, filled: bool = True, color: Tuple[int, int, int] = ColorPalette.AMBER):
    """绘制赛博五角星（通关结算评星）"""
    cx, cy = center
    fill_col = color if filled else (45, 35, 68)
    border_col = (255, 240, 150) if filled else (75, 58, 105)

    pts = []
    for i in range(10):
        r = outer_r if i % 2 == 0 else inner_r
        angle = math.radians(i * 36 - 90)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    if filled:
        # 发光晕染
        glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(glow_surf, (*color, 90), pts)
        surface.blit(glow_surf, (0, 0))

    pygame.draw.polygon(surface, fill_col, pts)
    pygame.draw.polygon(surface, border_col, pts, width=1)

    if filled:
        # 星核光亮
        pygame.draw.circle(surface, (255, 255, 255), (int(cx), int(cy)), max(2, int(inner_r * 0.45)))


def draw_tactile_arrow(
    surface: pygame.Surface,
    center: Tuple[float, float],
    size: float,
    angle_deg: float,
    state_col: str = "normal",
    is_hover: bool = False,
    is_highlighted: bool = False
):
    """
    绘制方案 D 赛博霓虹激光箭头（Neon Laser Chevron Arrow）
    采用多层渲染：环境微暗投影 + 外围霓虹辉光 + 饱和激光主体 + 晶棱倒角切面 + 中心超导白光能束 + 极速外框描边
    """
    cx, cy = center

    # 1. 颜色与能量色彩解析（支持方向专属霓虹色）
    norm_angle = (round(angle_deg) % 360 + 360) % 360

    if state_col == "collision":
        # 警报受阻态：炽红警报
        c_body = ColorPalette.ARROW_COLLISION
        c_light = ColorPalette.ARROW_COL_LIGHT
        c_dark = ColorPalette.ARROW_COL_DARK
        c_border = (255, 140, 160)
        c_glow = (255, 30, 70)
    elif is_highlighted:
        # 提示引导态：耀眼脉冲金
        c_body = ColorPalette.ARROW_HIGHLIGHT
        c_light = ColorPalette.ARROW_HL_LIGHT
        c_dark = ColorPalette.ARROW_HL_DARK
        c_border = (255, 255, 180)
        c_glow = (255, 210, 0)
    else:
        # 方向色彩矩阵
        if norm_angle in (0, 360):        # 上：电光天青
            base_color = ColorPalette.DIR_UP
        elif norm_angle == 90:            # 右：合成波洋红
            base_color = ColorPalette.DIR_RIGHT
        elif norm_angle == 180:           # 下：激光翠绿
            base_color = ColorPalette.DIR_DOWN
        else:                             # 左：极光琥珀金
            base_color = ColorPalette.DIR_LEFT

        if is_hover:
            # 悬停激活态：高亮过载充能
            c_body = (min(255, base_color[0] + 40), min(255, base_color[1] + 40), min(255, base_color[2] + 40))
            c_light = (255, 255, 255)
            c_dark = base_color
            c_border = (255, 255, 255)
            c_glow = base_color
        else:
            c_body = base_color
            c_light = (min(255, base_color[0] + 90), min(255, base_color[1] + 90), min(255, base_color[2] + 90))
            c_dark = (int(base_color[0] * 0.55), int(base_color[1] * 0.55), int(base_color[2] * 0.55))
            c_border = (min(255, base_color[0] + 70), min(255, base_color[1] + 70), min(255, base_color[2] + 70))
            c_glow = base_color

    # 2. 旋转坐标变换数学计算
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    def rotate_pt(x: float, y: float, ox: float, oy: float) -> Tuple[float, float]:
        return (x * cos_a - y * sin_a + ox, x * sin_a + y * cos_a + oy)

    # 犀利未来感的激光折角箭头几何学
    h = size * 0.44
    w_head = size * 0.38
    w_neck = size * 0.16
    h_neck = -size * 0.04
    w_tail = size * 0.16
    h_tail = size * 0.44
    tail_notch = size * 0.30

    local_coords = [
        (0, -h),                   # 0: 顶端尖角
        (w_head, h_neck),          # 1: 右侧翼尖
        (w_neck, h_neck),          # 2: 右侧内颈
        (w_tail, h_tail),          # 3: 右侧尾尖
        (0, tail_notch),           # 4: 尾部中心切角
        (-w_tail, h_tail),         # 5: 左侧尾尖
        (-w_neck, h_neck),         # 6: 左侧内颈
        (-w_head, h_neck),         # 7: 左侧翼尖
    ]

    body_pts = [rotate_pt(lx, ly, cx, cy) for lx, ly in local_coords]

    # 3. 绘制外层霓虹辉光晕（Glow Bloom）
    glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    glow_alpha = 135 if is_hover else (150 if is_highlighted else 75)

    # 微膨胀辉光边界
    exp = 3.5 if not is_hover else 5.5
    local_glow = [
        (0, -h - exp),
        (w_head + exp, h_neck),
        (w_neck + exp * 0.5, h_neck),
        (w_tail + exp, h_tail + exp),
        (0, tail_notch + exp * 0.5),
        (-w_tail - exp, h_tail + exp),
        (-w_neck - exp * 0.5, h_neck),
        (-w_head - exp, h_neck),
    ]
    glow_pts = [rotate_pt(lx, ly, cx, cy) for lx, ly in local_glow]
    pygame.draw.polygon(glow_surf, (*c_glow, glow_alpha), glow_pts)
    surface.blit(glow_surf, (0, 0))

    # 4. 绘制饱和主体
    pygame.draw.polygon(surface, c_body, body_pts)

    # 5. 绘制晶棱高光半面（立体切角质感）
    highlight_left = [
        rotate_pt(0, -h, cx, cy),
        rotate_pt(0, tail_notch, cx, cy),
        rotate_pt(-w_tail, h_tail, cx, cy),
        rotate_pt(-w_neck, h_neck, cx, cy),
        rotate_pt(-w_head, h_neck, cx, cy),
    ]
    hl_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(hl_surf, (*c_light, 90), highlight_left)
    surface.blit(hl_surf, (0, 0))

    # 6. 绘制高能白亮激光能量核心脊线（Laser Spine）
    tip_pt = rotate_pt(0, -h * 0.78, cx, cy)
    notch_pt = rotate_pt(0, tail_notch * 0.85, cx, cy)
    pygame.draw.line(surface, (255, 255, 255), tip_pt, notch_pt, width=2)

    # 7. 外轮廓描边
    pygame.draw.polygon(surface, c_border, body_pts, width=2 if is_hover else 1)

    # 8. 提示高亮动态雷达脉冲环 (Hint Pulse Ring)
    if is_highlighted:
        pulse = math.sin(pygame.time.get_ticks() * 0.009)
        pulse_r = size * 0.52 + pulse * 5
        p_surf = pygame.Surface((int(pulse_r * 2 + 16), int(pulse_r * 2 + 16)), pygame.SRCALPHA)
        center_p = (int(pulse_r + 8), int(pulse_r + 8))
        pygame.draw.circle(p_surf, (*ColorPalette.AMBER, 130), center_p, int(pulse_r), width=2)
        # 四向科技十字标
        for angle in (0, 90, 180, 270):
            arad = math.radians(angle)
            p1 = (center_p[0] + (pulse_r - 4) * math.cos(arad), center_p[1] + (pulse_r - 4) * math.sin(arad))
            p2 = (center_p[0] + (pulse_r + 5) * math.cos(arad), center_p[1] + (pulse_r + 5) * math.sin(arad))
            pygame.draw.line(p_surf, ColorPalette.AMBER, p1, p2, width=2)
        surface.blit(p_surf, (cx - pulse_r - 8, cy - pulse_r - 8))
