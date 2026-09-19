"""
游戏主循环与状态控制器
负责场景流转（主菜单、关卡选择、主游戏、胜利/失败结算）、事件交互与音效调度
"""

import time
from enum import Enum
from typing import Optional, List, Tuple
import pygame

from .core.arrow import Arrow, ArrowState
from .core.board import Board
from .core.level_manager import LevelManager, Level
from .core.solver import Solver
from .audio.sound import SoundManager
from .ui.theme import Theme, FontManager, draw_rounded_rect, draw_arrow_polygon
from .ui.renderer import Renderer, Button


class GameState(Enum):
    MENU = "MENU"
    PLAYING = "PLAYING"
    LEVEL_SELECT = "LEVEL_SELECT"
    LEVEL_CLEAR = "LEVEL_CLEAR"
    GAME_OVER = "GAME_OVER"
    ALL_CLEAR = "ALL_CLEAR"


class GameApp:
    """游戏主程序类"""

    def __init__(self, width: int = 960, height: int = 720):
        pygame.init()
        pygame.display.set_caption("一箭又一箭 - 休闲解谜小游戏 (AIGC 软件工程个人作业)")

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.running = True

        # 系统子模块
        self.sound_mgr = SoundManager()
        self.level_mgr = LevelManager()
        self.renderer = Renderer(width, height)

        # 游戏状态
        self.state = GameState.MENU
        self.current_board: Optional[Board] = None
        self.level_start_time = 0.0
        self.level_elapsed = 0.0
        self.hover_cell: Optional[Tuple[int, int]] = None

        # AI 自动求解状态
        self.ai_solving = False
        self.ai_last_step_time = 0.0
        self.ai_step_delay = 0.45  # 秒

        # 初始化各界面按钮
        self._init_buttons()

        # 加载初始关卡
        self._load_level(0)

    def _init_buttons(self):
        """初始化各个界面的交互按钮"""
        cx = self.width // 2

        # 1. 开始菜单按钮
        self.menu_buttons = [
            Button(pygame.Rect(cx - 120, 310, 240, 50), "开始挑战", bg_color=Theme.COLOR_INFO, font_size=20),
            Button(pygame.Rect(cx - 120, 380, 240, 50), "关卡选择", font_size=18),
            Button(pygame.Rect(cx - 120, 450, 240, 50), "音效: 开启", font_size=18),
            Button(pygame.Rect(cx - 120, 520, 240, 50), "退出游戏", bg_color=(50, 56, 68), font_size=18),
        ]

        # 2. 游戏中底部操作栏按钮
        btn_y = self.height - 75
        btn_w, btn_h = 130, 42
        gap = 20
        total_w = 5 * btn_w + 4 * gap
        start_x = (self.width - total_w) // 2

        self.game_buttons = {
            "restart": Button(pygame.Rect(start_x, btn_y, btn_w, btn_h), "重新开始 (R)", font_size=15),
            "hint": Button(pygame.Rect(start_x + (btn_w + gap), btn_y, btn_w, btn_h), "提示 (H)", font_size=15, bg_color=(50, 100, 150)),
            "undo": Button(pygame.Rect(start_x + 2 * (btn_w + gap), btn_y, btn_w, btn_h), "撤销 (U)", font_size=15),
            "solve": Button(pygame.Rect(start_x + 3 * (btn_w + gap), btn_y, btn_w, btn_h), "AI演示 (A)", font_size=15, bg_color=(70, 60, 110)),
            "menu": Button(pygame.Rect(start_x + 4 * (btn_w + gap), btn_y, btn_w, btn_h), "主菜单 (ESC)", font_size=15, bg_color=(50, 56, 68)),
        }

        # 3. 弹窗按钮
        modal_cx = self.width // 2
        modal_y = self.height // 2 + 65
        self.win_buttons = [
            Button(pygame.Rect(modal_cx - 160, modal_y, 140, 44), "下一关", bg_color=Theme.COLOR_SUCCESS),
            Button(pygame.Rect(modal_cx + 20, modal_y, 140, 44), "返回主菜单", bg_color=Theme.BG_CELL),
        ]

        self.fail_buttons = [
            Button(pygame.Rect(modal_cx - 160, modal_y, 140, 44), "重新挑战", bg_color=Theme.COLOR_DANGER),
            Button(pygame.Rect(modal_cx + 20, modal_y, 140, 44), "返回主菜单", bg_color=Theme.BG_CELL),
        ]

        self.all_clear_buttons = [
            Button(pygame.Rect(modal_cx - 160, modal_y, 140, 44), "重玩全关", bg_color=Theme.COLOR_SUCCESS),
            Button(pygame.Rect(modal_cx + 20, modal_y, 140, 44), "返回主菜单", bg_color=Theme.BG_CELL),
        ]

    def _load_level(self, index: int):
        """载入指定关卡"""
        level = self.level_mgr.set_level(index)
        self.current_board = Board(level.rows, level.cols, level.arrows, level.max_mistakes)
        self.level_start_time = time.time()
        self.level_elapsed = 0.0
        self.ai_solving = False

    def run(self):
        """游戏主运行循环"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # 60 FPS 物理与动画时间步
            self._handle_events()
            self._update(dt)
            self._render()

        pygame.quit()

    def _handle_events(self):
        """事件派发处理"""
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(mouse_pos)

        # 更新悬浮状态
        if self.state == GameState.PLAYING and self.current_board:
            self.hover_cell = self.renderer.screen_to_grid(mouse_pos, self.current_board.rows, self.current_board.cols)
            for btn in self.game_buttons.values():
                btn.check_hover(mouse_pos)
        elif self.state == GameState.MENU:
            for btn in self.menu_buttons:
                btn.check_hover(mouse_pos)
        elif self.state == GameState.LEVEL_CLEAR:
            for btn in self.win_buttons:
                btn.check_hover(mouse_pos)
        elif self.state == GameState.GAME_OVER:
            for btn in self.fail_buttons:
                btn.check_hover(mouse_pos)
        elif self.state == GameState.ALL_CLEAR:
            for btn in self.all_clear_buttons:
                btn.check_hover(mouse_pos)

    def _handle_keydown(self, key):
        """键盘快捷键支持"""
        if self.state == GameState.PLAYING:
            if key == pygame.K_r:
                self._action_restart()
            elif key == pygame.K_h:
                self._action_hint()
            elif key == pygame.K_u:
                self._action_undo()
            elif key == pygame.K_a:
                self._action_toggle_ai_solve()
            elif key == pygame.K_ESCAPE:
                self.state = GameState.MENU
        elif self.state in (GameState.LEVEL_CLEAR, GameState.GAME_OVER, GameState.ALL_CLEAR):
            if key == pygame.K_ESCAPE or key == pygame.K_SPACE:
                self.state = GameState.MENU

    def _handle_click(self, mouse_pos: Tuple[int, int]):
        """处理鼠标左键点击"""
        self.sound_mgr.play("click")

        if self.state == GameState.MENU:
            if self.menu_buttons[0].rect.collidepoint(mouse_pos):
                # 开始游戏
                self._load_level(self.level_mgr.current_level_index)
                self.state = GameState.PLAYING
            elif self.menu_buttons[1].rect.collidepoint(mouse_pos):
                # 关卡选择
                self.state = GameState.LEVEL_SELECT
            elif self.menu_buttons[2].rect.collidepoint(mouse_pos):
                # 切换音效
                is_on = self.sound_mgr.toggle_sound()
                self.menu_buttons[2].text = f"音效: {'开启' if is_on else '静音'}"
            elif self.menu_buttons[3].rect.collidepoint(mouse_pos):
                # 退出游戏
                self.running = False

        elif self.state == GameState.LEVEL_SELECT:
            self._handle_level_select_click(mouse_pos)

        elif self.state == GameState.PLAYING:
            # 检查底部按钮点击
            if self.game_buttons["restart"].rect.collidepoint(mouse_pos):
                self._action_restart()
            elif self.game_buttons["hint"].rect.collidepoint(mouse_pos):
                self._action_hint()
            elif self.game_buttons["undo"].rect.collidepoint(mouse_pos):
                self._action_undo()
            elif self.game_buttons["solve"].rect.collidepoint(mouse_pos):
                self._action_toggle_ai_solve()
            elif self.game_buttons["menu"].rect.collidepoint(mouse_pos):
                self.state = GameState.MENU
            else:
                # 点击棋盘箭头
                if self.current_board and not self.ai_solving:
                    grid_pos = self.renderer.screen_to_grid(mouse_pos, self.current_board.rows, self.current_board.cols)
                    if grid_pos:
                        self._trigger_arrow_click(grid_pos[0], grid_pos[1])

        elif self.state == GameState.LEVEL_CLEAR:
            if self.win_buttons[0].rect.collidepoint(mouse_pos):
                # 进入下一关
                if self.level_mgr.has_next_level():
                    self.level_mgr.next_level()
                    self._load_level(self.level_mgr.current_level_index)
                    self.state = GameState.PLAYING
                else:
                    self.state = GameState.ALL_CLEAR
            elif self.win_buttons[1].rect.collidepoint(mouse_pos):
                self.state = GameState.MENU

        elif self.state == GameState.GAME_OVER:
            if self.fail_buttons[0].rect.collidepoint(mouse_pos):
                # 重新挑战
                self._action_restart()
                self.state = GameState.PLAYING
            elif self.fail_buttons[1].rect.collidepoint(mouse_pos):
                self.state = GameState.MENU

        elif self.state == GameState.ALL_CLEAR:
            if self.all_clear_buttons[0].rect.collidepoint(mouse_pos):
                self._load_level(0)
                self.state = GameState.PLAYING
            elif self.all_clear_buttons[1].rect.collidepoint(mouse_pos):
                self.state = GameState.MENU

    def _trigger_arrow_click(self, r: int, c: int):
        """触发箭头点击逻辑"""
        if not self.current_board:
            return

        arrow = self.current_board.get_arrow(r, c)
        if not arrow:
            return

        # 记录触发前世界坐标用于粒子发生
        cx = self.renderer.grid_origin_x + (c + 0.5) * self.renderer.cell_size
        cy = self.renderer.grid_origin_y + (r + 0.5) * self.renderer.cell_size

        res = self.current_board.click_arrow(r, c)
        status = res.get("status")

        if status == "success":
            self.sound_mgr.play("fly")
            self.renderer.add_particles(cx, cy, count=12)
        elif status == "blocked":
            self.sound_mgr.play("blocked")
            # 冒出红色警示粒子
            self.renderer.add_particles(cx, cy, count=8, color_palette=[(240, 70, 70), (200, 50, 50)])

    def _action_restart(self):
        """重新开始当前关卡（T06 需求）"""
        if self.current_board:
            self.current_board.reset()
            self.level_start_time = time.time()
            self.level_elapsed = 0.0
            self.ai_solving = False

    def _action_hint(self):
        """提示功能：高亮一枚可通行的箭头"""
        if not self.current_board:
            return
        hint_arrow = Solver.get_hint(self.current_board)
        if hint_arrow:
            self.current_board.clear_highlights()
            hint_arrow.is_highlighted = True
            self.sound_mgr.play("hint")

    def _action_undo(self):
        """撤销上一步操作"""
        if self.current_board and self.current_board.undo():
            self.sound_mgr.play("click")

    def _action_toggle_ai_solve(self):
        """开启或暂停 AI 自动求解演示"""
        self.ai_solving = not self.ai_solving
        self.ai_last_step_time = time.time()

    def _update(self, dt: float):
        """状态逻辑步进更新"""
        self.renderer.update_particles(dt)

        if self.state == GameState.PLAYING and self.current_board:
            self.level_elapsed = time.time() - self.level_start_time
            self.current_board.update(dt, self.renderer.cell_size)

            # AI 自动步进推演
            if self.ai_solving:
                now = time.time()
                if now - self.ai_last_step_time >= self.ai_step_delay:
                    clearable = Solver.get_clearable_arrows(self.current_board)
                    if clearable:
                        target = clearable[0]
                        self._trigger_arrow_click(target.row, target.col)
                        self.ai_last_step_time = now
                    else:
                        self.ai_solving = False

            # 关卡通关检测
            if self.current_board.is_cleared():
                self.ai_solving = False
                self.sound_mgr.play("win")
                # 爆发出胜利彩带烟花
                cx, cy = self.width // 2, self.height // 2
                self.renderer.add_particles(cx, cy, count=60)
                if self.level_mgr.has_next_level():
                    self.state = GameState.LEVEL_CLEAR
                else:
                    self.state = GameState.ALL_CLEAR

            # 关卡失败检测
            elif self.current_board.is_failed():
                self.ai_solving = False
                self.sound_mgr.play("fail")
                self.state = GameState.GAME_OVER

    def _render(self):
        """画面重绘"""
        self.renderer.draw_background(self.screen)

        if self.state == GameState.MENU:
            self._render_menu()
        elif self.state == GameState.LEVEL_SELECT:
            self._render_level_select()
        elif self.state in (GameState.PLAYING, GameState.LEVEL_CLEAR, GameState.GAME_OVER, GameState.ALL_CLEAR):
            self._render_playing()

        self.renderer.draw_particles(self.screen)
        pygame.display.flip()

    def _render_menu(self):
        """渲染主菜单界面"""
        cx = self.width // 2

        # 游戏大标题与副标题
        font_logo = FontManager.get_font(46, bold=True)
        logo_surf = font_logo.render("一 箭 又 一 箭", True, Theme.ARROW_HIGHLIGHT)
        logo_rect = logo_surf.get_rect(center=(cx, 150))
        self.screen.blit(logo_surf, logo_rect)

        # 绘制标题装饰小箭头
        draw_arrow_polygon(self.screen, (cx - 180, 150), size=40, angle_deg=90, fill_color=Theme.COLOR_INFO)
        draw_arrow_polygon(self.screen, (cx + 180, 150), size=40, angle_deg=270, fill_color=Theme.COLOR_INFO)

        font_sub = FontManager.get_font(18)
        sub_surf = font_sub.render("观察方向 · 巧妙规避 · 箭无虚发", True, Theme.TEXT_MUTED)
        sub_rect = sub_surf.get_rect(center=(cx, 210))
        self.screen.blit(sub_surf, sub_rect)

        # 绘制主菜单按钮
        for btn in self.menu_buttons:
            btn.draw(self.screen)

        # 底部署名与作业说明
        font_foot = FontManager.get_font(13)
        foot_surf = font_foot.render("2026秋软件工程课程个人作业 · Python + Pygame", True, (90, 100, 115))
        foot_rect = foot_surf.get_rect(center=(cx, self.height - 30))
        self.screen.blit(foot_surf, foot_rect)

    def _render_playing(self):
        """渲染游戏进行中画面"""
        if not self.current_board:
            return

        curr_level = self.level_mgr.get_current_level()

        # 1. 顶部状态栏
        self.renderer.draw_top_bar(
            self.screen,
            curr_level,
            remaining_arrows=self.current_board.remaining_count(),
            remaining_mistakes=self.current_board.remaining_mistakes,
            max_mistakes=curr_level.max_mistakes,
            elapsed_time=self.level_elapsed
        )

        # 2. 棋盘与网格
        self.renderer.draw_board(self.screen, self.current_board, self.hover_cell)

        # 3. 底部操作按钮
        for btn in self.game_buttons.values():
            btn.draw(self.screen)

        # 4. 弹窗渲染
        if self.state == GameState.LEVEL_CLEAR:
            mistakes_made = curr_level.max_mistakes - self.current_board.remaining_mistakes
            stars = 3 if mistakes_made == 0 else (2 if mistakes_made == 1 else 1)
            self.renderer.draw_modal(
                self.screen,
                title="关 卡 通 关！",
                subtitle=f"耗时 {int(self.level_elapsed)} 秒 | 失误 {mistakes_made} 次",
                title_color=Theme.COLOR_SUCCESS,
                buttons=self.win_buttons,
                stars=stars
            )
        elif self.state == GameState.GAME_OVER:
            self.renderer.draw_modal(
                self.screen,
                title="挑 战 失 败",
                subtitle="失误机会已耗尽，请调整思路重新开始！",
                title_color=Theme.COLOR_DANGER,
                buttons=self.fail_buttons
            )
        elif self.state == GameState.ALL_CLEAR:
            self.renderer.draw_modal(
                self.screen,
                title="🎉 恭喜通关全部关卡！ 🎉",
                subtitle="你已经完全破解了所有箭阵迷局，堪称神箭手！",
                title_color=Theme.ARROW_HIGHLIGHT,
                buttons=self.all_clear_buttons,
                stars=3
            )

    def _render_level_select(self):
        """渲染关卡选择列表"""
        cx = self.width // 2
        font_title = FontManager.get_font(32, bold=True)
        title_surf = font_title.render("选 择 关 卡", True, Theme.TEXT_MAIN)
        self.screen.blit(title_surf, title_surf.get_rect(center=(cx, 90)))

        # 渲染 4 个关卡卡片
        card_w, card_h = 360, 90
        start_y = 160
        gap = 25
        mouse_pos = pygame.mouse.get_pos()

        for idx, lvl in enumerate(self.level_mgr.levels):
            card_x = (self.width - card_w) // 2
            card_y = start_y + idx * (card_h + gap)
            rect = pygame.Rect(card_x, card_y, card_w, card_h)

            is_hover = rect.collidepoint(mouse_pos)
            bg = Theme.BG_CELL_HOVER if is_hover else Theme.BG_PANEL
            draw_rounded_rect(self.screen, rect, bg, radius=12, border_color=Theme.COLOR_INFO if is_hover else Theme.BORDER, border_width=1)

            # 关卡名称
            f_name = FontManager.get_font(20, bold=True)
            n_surf = f_name.render(lvl.name, True, Theme.TEXT_MAIN)
            self.screen.blit(n_surf, (card_x + 25, card_y + 20))

            # 关卡规格
            f_info = FontManager.get_font(14)
            i_surf = f_info.render(f"棋盘: {lvl.rows}x{lvl.cols}   箭头: {lvl.total_arrows} 支   失误上限: {lvl.max_mistakes} 次", True, Theme.TEXT_MUTED)
            self.screen.blit(i_surf, (card_x + 25, card_y + 52))

        # 返回按钮
        back_rect = pygame.Rect(cx - 70, self.height - 80, 140, 44)
        btn = Button(back_rect, "返回主菜单", bg_color=Theme.BG_CELL)
        btn.check_hover(mouse_pos)
        btn.draw(self.screen)

    def _handle_level_select_click(self, mouse_pos: Tuple[int, int]):
        """处理关卡选择界面的点击"""
        cx = self.width // 2
        card_w, card_h = 360, 90
        start_y = 160
        gap = 25

        for idx in range(self.level_mgr.total_levels):
            card_x = (self.width - card_w) // 2
            card_y = start_y + idx * (card_h + gap)
            rect = pygame.Rect(card_x, card_y, card_w, card_h)
            if rect.collidepoint(mouse_pos):
                self._load_level(idx)
                self.state = GameState.PLAYING
                return

        back_rect = pygame.Rect(cx - 70, self.height - 80, 140, 44)
        if back_rect.collidepoint(mouse_pos):
            self.state = GameState.MENU
