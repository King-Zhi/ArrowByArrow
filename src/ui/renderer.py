"""
界面渲染器模块
负责游戏主画面、开始菜单、关卡选择、胜利/失败结算弹窗与粒子特效绘制
"""

import math
import random
import time
from typing import Tuple, List, Dict, Optional, Any
import pygame

from .theme import Theme, FontManager, draw_rounded_rect, draw_arrow_polygon
from ..core.arrow import Arrow, ArrowState, Direction
from ..core.board import Board
from ..core.level_manager import Level


class Particle:
    """消除与过关彩带粒子"""

    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int], size: float = 4.0, lifetime: float = 0.6):
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
        self.vy += 250.0 * dt  # 重力加速度
        return self.age < self.lifetime

    def draw(self, surface: pygame.Surface):
        progress = self.age / self.lifetime
        current_size = max(1.0, self.size * (1.0 - progress))
        alpha = max(0, int(255 * (1.0 - progress)))
        # 简单绘制圆形粒子
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(current_size))


class Button:
    """现代圆角交互按钮"""

    def __init__(self, rect: pygame.Rect, text: str, bg_color: Tuple[int, int, int] = Theme.BG_PANEL, text_color: Tuple[int, int, int] = Theme.TEXT_MAIN, hover_color: Optional[Tuple[int, int, int]] = None, radius: int = 8, font_size: int = 18):
        self.rect = rect
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.hover_color = hover_color or (min(255, bg_color[0] + 25), min(255, bg_color[1] + 25), min(255, bg_color[2] + 25))
        self.radius = radius
        self.font_size = font_size
        self.is_hovered = False

    def check_hover(self, mouse_pos: Tuple[int, int]) -> bool:
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        return self.is_hovered

    def draw(self, surface: pygame.Surface):
        color = self.hover_color if self.is_hovered else self.bg_color
        draw_rounded_rect(surface, self.rect, color, radius=self.radius, border_color=Theme.BORDER, border_width=1)
        font = FontManager.get_font(self.font_size, bold=True)
        txt_surf = font.render(self.text, True, self.text_color)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)


class Renderer:
    """主渲染引擎"""

    def __init__(self, screen_width: int = 900, screen_height: int = 700):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.particles: List[Particle] = []

        # 棋盘绘制缓存参数
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.cell_size = 70.0
        self.grid_origin_x = 0.0
        self.grid_origin_y = 0.0

    def add_particles(self, x: float, y: float, count: int = 15, color_palette: Optional[List[Tuple[int, int, int]]] = None):
        """在指定位置炸出粒子效果"""
        palette = color_palette or [Theme.COLOR_INFO, Theme.ARROW_HIGHLIGHT, (255, 255, 255), Theme.COLOR_SUCCESS]
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 260)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            col = random.choice(palette)
            self.particles.append(Particle(x, y, vx, vy, col, size=random.uniform(3, 6), lifetime=random.uniform(0.4, 0.7)))

    def update_particles(self, dt: float):
        """更新所有活跃粒子"""
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw_particles(self, surface: pygame.Surface):
        """绘制粒子"""
        for p in self.particles:
            p.draw(surface)

    def calculate_board_layout(self, rows: int, cols: int, top_margin: int = 110, bottom_margin: int = 110):
        """动态计算棋盘居中布局参数"""
        avail_w = self.screen_width - 80
        avail_h = self.screen_height - top_margin - bottom_margin

        # 计算每个格子的合适边长（最大 80 像素，最小 50 像素）
        cell_w = avail_w / cols
        cell_h = avail_h / rows
        self.cell_size = max(45.0, min(80.0, min(cell_w, cell_h)))

        board_w = self.cell_size * cols
        board_h = self.cell_size * rows

        self.grid_origin_x = (self.screen_width - board_w) / 2.0
        self.grid_origin_y = top_margin + (avail_h - board_h) / 2.0
        self.board_rect = pygame.Rect(int(self.grid_origin_x), int(self.grid_origin_y), int(board_w), int(board_h))

    def screen_to_grid(self, mouse_pos: Tuple[int, int], rows: int, cols: int) -> Optional[Tuple[int, int]]:
        """将屏幕鼠标点击坐标转换为棋盘网格 (row, col)"""
        mx, my = mouse_pos
        if not self.board_rect.collidepoint(mx, my):
            return None
        c = int((mx - self.grid_origin_x) // self.cell_size)
        r = int((my - self.grid_origin_y) // self.cell_size)
        if 0 <= r < rows and 0 <= c < cols:
            return (r, c)
        return None

    def draw_background(self, surface: pygame.Surface):
        """绘制深色优雅渐变/微网格背景"""
        surface.fill(Theme.BG_MAIN)
        # 绘制背景装饰点线
        for x in range(0, self.screen_width, 40):
            for y in range(0, self.screen_height, 40):
                surface.set_at((x, y), (28, 34, 44))

    def draw_top_bar(self, surface: pygame.Surface, level: Level, remaining_arrows: int, remaining_mistakes: int, max_mistakes: int, elapsed_time: float):
        """绘制顶部信息状态栏（关卡、失误心形、剩余箭头、用时）"""
        bar_rect = pygame.Rect(20, 15, self.screen_width - 40, 75)
        draw_rounded_rect(surface, bar_rect, Theme.BG_PANEL, radius=12, border_color=Theme.BORDER, border_width=1)

        # 关卡名称与描述
        font_title = FontManager.get_font(22, bold=True)
        title_surf = font_title.render(level.name, True, Theme.TEXT_MAIN)
        surface.blit(title_surf, (40, 25))

        font_desc = FontManager.get_font(13)
        desc_surf = font_desc.render(level.description, True, Theme.TEXT_MUTED)
        surface.blit(desc_surf, (40, 56))

        # 中间：失误次数显示（爱心/红圈）
        center_x = self.screen_width // 2
        font_info = FontManager.get_font(15, bold=True)
        mistake_label = font_info.render("失误机会:", True, Theme.TEXT_MUTED)
        surface.blit(mistake_label, (center_x - 110, 30))

        # 绘制爱心生命图标
        heart_start_x = center_x - 20
        for i in range(max_mistakes):
            color = Theme.COLOR_DANGER if i < remaining_mistakes else (80, 50, 50)
            pygame.draw.circle(surface, color, (heart_start_x + i * 22, 40), 7)

        # 剩余箭头与计时
        right_x = self.screen_width - 240
        arrow_text = font_info.render(f"剩余: {remaining_arrows} 支", True, Theme.TEXT_ACCENT)
        surface.blit(arrow_text, (right_x, 30))

        minutes = int(elapsed_time) // 60
        seconds = int(elapsed_time) % 60
        time_text = font_info.render(f"用时: {minutes:02d}:{seconds:02d}", True, Theme.TEXT_MAIN)
        surface.blit(time_text, (right_x + 110, 30))

    def draw_board(self, surface: pygame.Surface, board: Board, hover_pos: Optional[Tuple[int, int]]):
        """绘制网格棋盘与所有箭头"""
        self.calculate_board_layout(board.rows, board.cols)

        # 棋盘大底板
        outer_margin = 12
        outer_rect = pygame.Rect(
            int(self.grid_origin_x - outer_margin),
            int(self.grid_origin_y - outer_margin),
            int(self.board_rect.width + outer_margin * 2),
            int(self.board_rect.height + outer_margin * 2)
        )
        draw_rounded_rect(surface, outer_rect, Theme.BG_PANEL, radius=14, border_color=Theme.BORDER, border_width=1)

        # 绘制网格底色单元格
        for r in range(board.rows):
            for c in range(board.cols):
                cx = self.grid_origin_x + c * self.cell_size
                cy = self.grid_origin_y + r * self.cell_size
                cell_rect = pygame.Rect(int(cx + 3), int(cy + 3), int(self.cell_size - 6), int(self.cell_size - 6))

                is_hover = (hover_pos == (r, c))
                cell_color = Theme.BG_CELL_HOVER if is_hover else Theme.BG_CELL
                draw_rounded_rect(surface, cell_rect, cell_color, radius=8)

        # 绘制棋盘内的活跃箭头
        for (r, c), arrow in board.grid.items():
            self._draw_single_arrow(surface, arrow, is_hover=(hover_pos == (r, c)))

        # 绘制正在飞出屏幕的箭头
        for arrow in board.flying_arrows:
            self._draw_single_arrow(surface, arrow, is_hover=False)

    def _draw_single_arrow(self, surface: pygame.Surface, arrow: Arrow, is_hover: bool = False):
        """绘制单个箭头"""
        base_cx = self.grid_origin_x + (arrow.col + 0.5) * self.cell_size
        base_cy = self.grid_origin_y + (arrow.row + 0.5) * self.cell_size

        draw_cx = base_cx + arrow.offset_x
        draw_cy = base_cy + arrow.offset_y

        # 根据箭头状态决定配色
        if arrow.state == ArrowState.COLLIDING:
            fill_col = Theme.ARROW_COLLISION
            border_col = (255, 120, 120)
        elif arrow.is_highlighted:
            fill_col = Theme.ARROW_HIGHLIGHT
            border_col = (255, 240, 150)
        elif is_hover:
            fill_col = (100, 180, 255)
            border_col = (180, 220, 255)
        else:
            fill_col = Theme.ARROW_BODY
            border_col = Theme.ARROW_BORDER

        # 高亮提示时绘制发光外环
        if arrow.is_highlighted:
            pulse = (math.sin(time.time() * 8) + 1) * 0.5
            ring_r = int((self.cell_size * 0.45) + pulse * 4)
            pygame.draw.circle(surface, (255, 215, 0), (int(draw_cx), int(draw_cy)), ring_r, width=2)

        draw_arrow_polygon(
            surface,
            (draw_cx, draw_cy),
            size=self.cell_size * 0.82,
            angle_deg=arrow.direction.angle,
            fill_color=fill_col,
            border_color=border_col
        )

    def draw_modal(self, surface: pygame.Surface, title: str, subtitle: str, title_color: Tuple[int, int, int], buttons: List[Button], stars: int = 0):
        """绘制全屏居中模态结算弹窗（用于通关或失败）"""
        # 黑色半透明遮罩
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((10, 12, 16, 190))
        surface.blit(overlay, (0, 0))

        # 弹窗卡片
        modal_w, modal_h = 460, 320
        modal_x = (self.screen_width - modal_w) // 2
        modal_y = (self.screen_height - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        draw_rounded_rect(surface, modal_rect, Theme.BG_PANEL, radius=16, border_color=Theme.BORDER, border_width=2)

        # 标题
        font_title = FontManager.get_font(28, bold=True)
        t_surf = font_title.render(title, True, title_color)
        t_rect = t_surf.get_rect(center=(modal_x + modal_w // 2, modal_y + 55))
        surface.blit(t_surf, t_rect)

        # 星级评定（通关时显示）
        if stars > 0:
            star_str = "★ " * stars + "☆ " * (3 - stars)
            font_stars = FontManager.get_font(26, bold=True)
            s_surf = font_stars.render(star_str.strip(), True, Theme.ARROW_HIGHLIGHT)
            s_rect = s_surf.get_rect(center=(modal_x + modal_w // 2, modal_y + 100))
            surface.blit(s_surf, s_rect)

        # 副标题说明
        font_sub = FontManager.get_font(16)
        sub_surf = font_sub.render(subtitle, True, Theme.TEXT_MUTED)
        sub_y = modal_y + 140 if stars > 0 else modal_y + 115
        sub_rect = sub_surf.get_rect(center=(modal_x + modal_w // 2, sub_y))
        surface.blit(sub_surf, sub_rect)

        # 按钮绘制
        for btn in buttons:
            btn.draw(surface)
