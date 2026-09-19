"""
赛博霓虹与合成波街机风渲染引擎（Cyberpunk Synthwave & Neon Arcade Renderer）
负责高能全息顶部状态栏、纳米网格悬浮棋盘、霓虹按键与辉光结算弹窗
"""

import math
import random
import time
from typing import Tuple, List, Dict, Optional, Any
import pygame

from .theme import (
    ColorPalette, FontManager, AssetLoader, draw_card, draw_soft_shadow,
    draw_styled_heart, draw_star, draw_tactile_arrow, draw_vector_icon
)
from ..core.arrow import Arrow, ArrowState, Direction
from ..core.board import Board
from ..core.level_manager import Level


class Particle:
    """消除与飞溅动态霓虹微粒"""

    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int], size: float = 4.0, lifetime: float = 0.5):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.age = 0.0

    def update(self, dt: float) -> bool:
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 180.0 * dt
        self.vx *= 0.98
        return self.age < self.lifetime

    def draw(self, surface: pygame.Surface):
        progress = self.age / self.lifetime
        current_size = max(1.0, self.size * (1.0 - progress))
        # 辉光微粒
        p_surf = pygame.Surface((int(current_size * 2 + 4), int(current_size * 2 + 4)), pygame.SRCALPHA)
        alpha = int(255 * (1.0 - progress))
        pygame.draw.circle(p_surf, (*self.color, alpha), (int(current_size + 2), int(current_size + 2)), int(current_size))
        surface.blit(p_surf, (self.x - current_size - 2, self.y - current_size - 2))


class AmbientMote:
    """合成波背景漂浮星尘光点"""

    def __init__(self, screen_w: int, screen_h: int):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.x = random.uniform(0, screen_w)
        self.y = random.uniform(0, screen_h)
        self.speed = random.uniform(10, 26)
        self.radius = random.uniform(1.6, 3.2)
        self.alpha = random.uniform(40, 110)
        self.drift_phase = random.uniform(0, math.pi * 2)
        self.color = random.choice([ColorPalette.CYAN, ColorPalette.MAGENTA, (220, 240, 255)])

    def update(self, dt: float):
        self.y -= self.speed * dt
        self.x += math.sin(self.drift_phase + pygame.time.get_ticks() * 0.0015) * 0.6
        if self.y < -10:
            self.y = self.screen_h + 10
            self.x = random.uniform(0, self.screen_w)

    def draw(self, surface: pygame.Surface):
        s = pygame.Surface((int(self.radius * 2 + 4), int(self.radius * 2 + 4)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, int(self.alpha)), (int(self.radius + 2), int(self.radius + 2)), int(self.radius))
        surface.blit(s, (self.x - self.radius - 2, self.y - self.radius - 2))


class ModernButton:
    """
    赛博霓虹街机风触感按钮
    配备纯几何矢量图标、多层悬浮霓虹光晕与按压立体唇缘
    """

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        icon_type: str = "",
        bg_color: Tuple[int, int, int] = ColorPalette.PANEL_BG,
        hover_color: Optional[Tuple[int, int, int]] = None,
        text_color: Tuple[int, int, int] = ColorPalette.TEXT_MAIN,
        radius: int = 10,
        font_size: int = 16,
        accent_border: Optional[Tuple[int, int, int]] = None
    ):
        self.rect = rect
        self.text = text
        self.icon_type = icon_type
        self.bg_color = bg_color
        self.hover_color = hover_color or (min(255, bg_color[0] + 20), min(255, bg_color[1] + 16), min(255, bg_color[2] + 35))
        self.text_color = text_color
        self.radius = radius
        self.font_size = font_size
        self.accent_border = accent_border or ColorPalette.PANEL_BORDER
        self.is_hovered = False

    def check_hover(self, mouse_pos: Tuple[int, int]) -> bool:
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        return self.is_hovered

    def draw(self, surface: pygame.Surface):
        draw_rect = self.rect.copy()

        # 悬浮态位移与强力霓虹辉光
        if self.is_hovered:
            draw_rect.y -= 2
            border_col = self.accent_border if self.accent_border != ColorPalette.PANEL_BORDER else ColorPalette.CYAN
            draw_soft_shadow(surface, draw_rect, radius=self.radius, blur=14, alpha=110, color=border_col)
            main_col = self.hover_color
        else:
            draw_soft_shadow(surface, draw_rect, radius=self.radius, blur=6, alpha=50, color=(10, 8, 22))
            main_col = self.bg_color
            border_col = self.accent_border

        # 1. 绘制 3D 按钮下沉立体下沿（底厚感）
        bevel_rect = pygame.Rect(draw_rect.x, draw_rect.y + 3, draw_rect.width, draw_rect.height)
        dark_lip = (max(0, main_col[0] - 15), max(0, main_col[1] - 12), max(0, main_col[2] - 25))
        pygame.draw.rect(surface, dark_lip, bevel_rect, border_radius=self.radius)

        # 2. 绘制按钮主体正面
        pygame.draw.rect(surface, main_col, draw_rect, border_radius=self.radius)

        # 3. 绘制霓虹外边框
        if border_col:
            pygame.draw.rect(surface, border_col, draw_rect, width=2 if self.is_hovered else 1, border_radius=self.radius)

        # 4. 内容排版：矢量图标 + 文字
        font = FontManager.get(self.font_size, bold=True)
        txt_col = (255, 255, 255) if self.is_hovered else self.text_color
        txt_surf = font.render(self.text, True, txt_col)
        t_w, t_h = txt_surf.get_size()

        if self.icon_type:
            icon_size = 18
            spacing = 8
            total_content_w = icon_size + spacing + t_w
            start_x = draw_rect.centerx - total_content_w // 2

            # 绘制纯几何矢量图标
            icon_center = (start_x + icon_size // 2, draw_rect.centery)
            icon_col = border_col if self.is_hovered else (210, 225, 255)
            draw_vector_icon(surface, icon_center, icon_size, self.icon_type, icon_col)

            # 绘制文字
            txt_pos = (start_x + icon_size + spacing, draw_rect.centery - t_h // 2)
            surface.blit(txt_surf, txt_pos)
        else:
            txt_rect = txt_surf.get_rect(center=draw_rect.center)
            surface.blit(txt_surf, txt_rect)


class Renderer:
    """赛博霓虹主渲染管线"""

    def __init__(self, screen_width: int = 960, screen_height: int = 720):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.particles: List[Particle] = []
        self.ambient_motes = [AmbientMote(screen_width, screen_height) for _ in range(36)]

        # 棋盘布局几何参数
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.cell_size = 72.0
        self.grid_origin_x = 0.0
        self.grid_origin_y = 0.0

    def add_particles(self, x: float, y: float, count: int = 18, palette: Optional[List[Tuple[int, int, int]]] = None):
        """生成霓虹粒子喷溅特效"""
        colors = palette or [ColorPalette.CYAN, ColorPalette.MAGENTA, ColorPalette.LIME, ColorPalette.AMBER, (255, 255, 255)]
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(90, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(
                Particle(x, y, vx, vy, random.choice(colors), size=random.uniform(3.5, 6.5), lifetime=random.uniform(0.35, 0.65))
            )

    def update(self, dt: float):
        """更新所有粒子与背景微粒"""
        self.particles = [p for p in self.particles if p.update(dt)]
        for mote in self.ambient_motes:
            mote.update(dt)

    def calculate_board_layout(self, rows: int, cols: int, top_margin: int = 118, bottom_margin: int = 108):
        """自适应棋盘居中几何计算"""
        avail_w = self.screen_width - 120
        avail_h = self.screen_height - top_margin - bottom_margin

        cell_w = avail_w / cols
        cell_h = avail_h / rows
        self.cell_size = max(50.0, min(84.0, min(cell_w, cell_h)))

        board_w = self.cell_size * cols
        board_h = self.cell_size * rows

        self.grid_origin_x = (self.screen_width - board_w) / 2.0
        self.grid_origin_y = top_margin + (avail_h - board_h) / 2.0
        self.board_rect = pygame.Rect(int(self.grid_origin_x), int(self.grid_origin_y), int(board_w), int(board_h))

    def screen_to_grid(self, mouse_pos: Tuple[int, int], rows: int, cols: int) -> Optional[Tuple[int, int]]:
        """屏幕坐标转换为网格单元坐标"""
        mx, my = mouse_pos
        if not self.board_rect.collidepoint(mx, my):
            return None
        c = int((mx - self.grid_origin_x) // self.cell_size)
        r = int((my - self.grid_origin_y) // self.cell_size)
        if 0 <= r < rows and 0 <= c < cols:
            return (r, c)
        return None

    def draw_background(self, surface: pygame.Surface):
        """绘制合成波 80s 透视霓虹背景贴图与浮游尘埃"""
        bg_tex = AssetLoader.get_background(self.screen_width, self.screen_height)
        surface.blit(bg_tex, (0, 0))

        # 漂浮发光氛围尘埃
        for mote in self.ambient_motes:
            mote.draw(surface)

    def draw_top_bar(self, surface: pygame.Surface, level: Level, remaining_arrows: int, remaining_mistakes: int, max_mistakes: int, elapsed_time: float):
        """绘制赛博朋克全息顶部信息栏"""
        bar_h = 76
        bar_rect = pygame.Rect(30, 16, self.screen_width - 60, bar_h)

        # 悬浮深色高透科技卡片
        draw_card(surface, bar_rect, bg_color=ColorPalette.PANEL_BG, border_color=ColorPalette.PANEL_BORDER, radius=12, shadow=True, tech_corners=True)

        # 1. 左侧：关卡勋章徽标与名称
        badge_rect = pygame.Rect(48, 28, 88, 24)
        pygame.draw.rect(surface, (28, 22, 56), badge_rect, border_radius=4)
        pygame.draw.rect(surface, ColorPalette.CYAN, badge_rect, width=1, border_radius=4)
        f_badge = FontManager.get(12, bold=True)
        b_surf = f_badge.render(f"STAGE 0{level.level_id}", True, ColorPalette.CYAN)
        surface.blit(b_surf, b_surf.get_rect(center=badge_rect.center))

        f_title = FontManager.get(20, bold=True)
        t_surf = f_title.render(level.name.split("：")[-1], True, ColorPalette.TEXT_TITLE)
        surface.blit(t_surf, (148, 28))

        f_desc = FontManager.get(12)
        d_surf = f_desc.render(level.description, True, ColorPalette.TEXT_MUTED)
        surface.blit(d_surf, (50, 60))

        # 2. 中间：失误生命槽（精致立体心形排布）
        mid_x = self.screen_width // 2
        f_label = FontManager.get(13, bold=True)
        l_surf = f_label.render("失误防护", True, ColorPalette.TEXT_MUTED)
        surface.blit(l_surf, (mid_x - 105, 42))

        heart_gap = 28
        heart_start_x = mid_x - 22
        for i in range(max_mistakes):
            is_filled = (i < remaining_mistakes)
            draw_styled_heart(surface, (heart_start_x + i * heart_gap, 50), size=20, filled=is_filled)

        # 3. 右侧：胶囊指标（剩余箭头与用时）
        right_x = self.screen_width - 240
        arrow_pill = pygame.Rect(right_x, 30, 92, 46)
        pygame.draw.rect(surface, ColorPalette.CELL_BG, arrow_pill, border_radius=6)
        pygame.draw.rect(surface, (0, 180, 220), arrow_pill, width=1, border_radius=6)
        a_lbl = f_badge.render("REMAIN", True, ColorPalette.TEXT_MUTED)
        surface.blit(a_lbl, (right_x + 8, 34))
        a_val = FontManager.get(18, bold=True).render(f"{remaining_arrows}", True, ColorPalette.CYAN)
        surface.blit(a_val, (right_x + 8, 50))

        time_pill = pygame.Rect(right_x + 104, 30, 92, 46)
        pygame.draw.rect(surface, ColorPalette.CELL_BG, time_pill, border_radius=6)
        pygame.draw.rect(surface, (200, 160, 20), time_pill, width=1, border_radius=6)
        m = int(elapsed_time) // 60
        s = int(elapsed_time) % 60
        t_lbl = f_badge.render("TIME", True, ColorPalette.TEXT_MUTED)
        surface.blit(t_lbl, (right_x + 112, 34))
        t_val = FontManager.get(18, bold=True).render(f"{m:02d}:{s:02d}", True, ColorPalette.AMBER)
        surface.blit(t_val, (right_x + 112, 50))

    def draw_board(self, surface: pygame.Surface, board: Board, hover_pos: Optional[Tuple[int, int]]):
        """绘制赛博纳米网格悬浮棋盘与凹陷单元格"""
        self.calculate_board_layout(board.rows, board.cols)

        # 1. 棋盘大底板
        padding = 16
        outer_rect = pygame.Rect(
            int(self.grid_origin_x - padding),
            int(self.grid_origin_y - padding),
            int(self.board_rect.width + padding * 2),
            int(self.board_rect.height + padding * 2)
        )
        draw_card(surface, outer_rect, bg_color=ColorPalette.PANEL_BG, border_color=(68, 52, 115), radius=14, shadow=True, tech_corners=True)

        # 2. 网格凹陷质感单元格
        gap = 4.0
        for r in range(board.rows):
            for c in range(board.cols):
                cx = self.grid_origin_x + c * self.cell_size
                cy = self.grid_origin_y + r * self.cell_size
                cell_rect = pygame.Rect(int(cx + gap), int(cy + gap), int(self.cell_size - gap * 2), int(self.cell_size - gap * 2))

                is_hover = (hover_pos == (r, c))
                bg = ColorPalette.CELL_HOVER if is_hover else ColorPalette.CELL_BG
                border = ColorPalette.CYAN if is_hover else ColorPalette.CELL_BORDER

                pygame.draw.rect(surface, bg, cell_rect, border_radius=6)
                pygame.draw.rect(surface, border, cell_rect, width=1 if not is_hover else 2, border_radius=6)

        # 3. 绘制棋盘上的活跃箭头
        for (r, c), arrow in board.grid.items():
            self._draw_arrow_entity(surface, arrow, is_hover=(hover_pos == (r, c)))

        # 4. 绘制正在飞出屏幕的箭头
        for arrow in board.flying_arrows:
            self._draw_arrow_entity(surface, arrow, is_hover=False)

    def _draw_arrow_entity(self, surface: pygame.Surface, arrow: Arrow, is_hover: bool = False):
        """调用激光拟态引擎绘制单个箭头"""
        base_cx = self.grid_origin_x + (arrow.col + 0.5) * self.cell_size
        base_cy = self.grid_origin_y + (arrow.row + 0.5) * self.cell_size

        draw_cx = base_cx + arrow.offset_x
        draw_cy = base_cy + arrow.offset_y

        state_col = "normal"
        if arrow.state == ArrowState.COLLIDING:
            state_col = "collision"

        draw_tactile_arrow(
            surface,
            (draw_cx, draw_cy),
            size=self.cell_size * 0.84,
            angle_deg=arrow.direction.angle,
            state_col=state_col,
            is_hover=is_hover,
            is_highlighted=arrow.is_highlighted
        )

    def draw_modal(self, surface: pygame.Surface, title: str, subtitle: str, title_color: Tuple[int, int, int], buttons: List[ModernButton], stars: int = 0):
        """赛博霓虹终端全屏弹窗"""
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((10, 8, 20, 225))
        surface.blit(overlay, (0, 0))

        modal_w, modal_h = 500, 350
        modal_x = (self.screen_width - modal_w) // 2
        modal_y = (self.screen_height - modal_h) // 2
        card_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        draw_card(surface, card_rect, bg_color=ColorPalette.PANEL_BG, border_color=title_color, radius=16, shadow=True, tech_corners=True)

        font_title = FontManager.get(28, bold=True)
        t_surf = font_title.render(title, True, title_color)
        surface.blit(t_surf, t_surf.get_rect(center=(modal_x + modal_w // 2, modal_y + 54)))

        if stars > 0:
            star_gap = 48
            star_start_x = modal_x + modal_w // 2 - (star_gap * 2) // 2
            for i in range(3):
                star_pos = (star_start_x + i * star_gap, modal_y + 112)
                draw_star(surface, star_pos, outer_r=18, inner_r=8, filled=(i < stars))

        stat_rect = pygame.Rect(modal_x + 36, modal_y + (160 if stars > 0 else 125), modal_w - 72, 50)
        pygame.draw.rect(surface, ColorPalette.CELL_BG, stat_rect, border_radius=6)
        pygame.draw.rect(surface, ColorPalette.PANEL_BORDER, stat_rect, width=1, border_radius=6)

        font_sub = FontManager.get(14, bold=True)
        sub_surf = font_sub.render(subtitle, True, ColorPalette.TEXT_MAIN)
        surface.blit(sub_surf, sub_surf.get_rect(center=stat_rect.center))

        for btn in buttons:
            btn.draw(surface)

    def draw_particles(self, surface: pygame.Surface):
        """绘制所有活动粒子"""
        for p in self.particles:
            p.draw(surface)
