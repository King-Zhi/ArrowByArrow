"""
游戏主循环与交互控制系统
全面接入方案D赛博霓虹与合成波街机风 UI、全息状态栏、矢量激光箭头与粒子管线
"""

import math
import time
from enum import Enum
from typing import Optional, List, Tuple
import pygame

from .core.arrow import Arrow, ArrowState
from .core.board import Board
from .core.level_manager import LevelManager, Level
from .core.solver import Solver
from .audio.sound import SoundManager
from .ui.theme import ColorPalette, FontManager, draw_card, draw_tactile_arrow, draw_soft_shadow
from .ui.renderer import Renderer, ModernButton


class GameState(Enum):
    MENU = "MENU"
    PLAYING = "PLAYING"
    LEVEL_SELECT = "LEVEL_SELECT"
    LEVEL_CLEAR = "LEVEL_CLEAR"
    GAME_OVER = "GAME_OVER"
    ALL_CLEAR = "ALL_CLEAR"


class GameApp:
    """游戏主程序"""

    def __init__(self, width: int = 960, height: int = 720):
        pygame.init()
        pygame.display.set_caption("一箭又一箭 - 赛博合成波街机版 (Arrow by Arrow)")

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.running = True

        # 子系统
        self.sound_mgr = SoundManager()
        self.level_mgr = LevelManager()
        self.renderer = Renderer(width, height)

        # 状态机
        self.state = GameState.MENU
        self.current_board: Optional[Board] = None
        self.level_start_time = 0.0
        self.level_elapsed = 0.0
        self.hover_cell: Optional[Tuple[int, int]] = None

        # AI 自动求解
        self.ai_solving = False
        self.ai_last_step_time = 0.0
        self.ai_step_delay = 0.45

        # 初始化按钮
        self._init_buttons()
        self._load_level(0)

    def _init_buttons(self):
        """初始化赛博霓虹触感交互按钮（纯几何矢量图标，绝无方块乱码 □）"""
        cx = self.width // 2

        # 1. 主菜单核心选项
        btn_w, btn_h = 280, 52
        self.menu_buttons = [
            ModernButton(
                pygame.Rect(cx - btn_w // 2, 295, btn_w, btn_h),
                "开始挑战",
                icon_type="play",
                bg_color=(18, 42, 70),
                hover_color=(25, 65, 110),
                font_size=18,
                radius=10,
                accent_border=ColorPalette.CYAN
            ),
            ModernButton(
                pygame.Rect(cx - btn_w // 2, 365, btn_w, btn_h),
                "关卡选择",
                icon_type="levels",
                bg_color=(45, 18, 54),
                hover_color=(75, 25, 88),
                font_size=16,
                radius=10,
                accent_border=ColorPalette.MAGENTA
            ),
            ModernButton(
                pygame.Rect(cx - btn_w // 2, 435, btn_w, btn_h),
                "音效: 开启",
                icon_type="sound_on",
                bg_color=(18, 45, 30),
                hover_color=(28, 70, 48),
                font_size=16,
                radius=10,
                accent_border=ColorPalette.LIME
            ),
            ModernButton(
                pygame.Rect(cx - btn_w // 2, 505, btn_w, btn_h),
                "退出游戏",
                icon_type="quit",
                bg_color=(42, 18, 32),
                hover_color=(70, 25, 48),
                font_size=16,
                radius=10,
                accent_border=ColorPalette.ROSE
            ),
        ]

        # 2. 游戏中底部悬浮工具栏
        bar_y = self.height - 70
        w_item, h_item = 135, 44
        gap = 16
        total_w = 5 * w_item + 4 * gap
        start_x = (self.width - total_w) // 2

        self.game_buttons = {
            "restart": ModernButton(
                pygame.Rect(start_x, bar_y, w_item, h_item),
                "重置关卡",
                icon_type="restart",
                bg_color=(22, 28, 55),
                hover_color=(32, 44, 85),
                font_size=14,
                radius=8,
                accent_border=ColorPalette.CYAN
            ),
            "hint": ModernButton(
                pygame.Rect(start_x + (w_item + gap), bar_y, w_item, h_item),
                "提示 (H)",
                icon_type="hint",
                bg_color=(45, 36, 18),
                hover_color=(75, 60, 24),
                font_size=14,
                radius=8,
                accent_border=ColorPalette.AMBER
            ),
            "undo": ModernButton(
                pygame.Rect(start_x + 2 * (w_item + gap), bar_y, w_item, h_item),
                "撤销 (U)",
                icon_type="undo",
                bg_color=(20, 32, 56),
                hover_color=(32, 50, 85),
                font_size=14,
                radius=8,
                accent_border=(0, 190, 245)
            ),
            "solve": ModernButton(
                pygame.Rect(start_x + 3 * (w_item + gap), bar_y, w_item, h_item),
                "AI演示 (A)",
                icon_type="solve",
                bg_color=(48, 16, 52),
                hover_color=(75, 24, 82),
                font_size=14,
                radius=8,
                accent_border=ColorPalette.MAGENTA
            ),
            "menu": ModernButton(
                pygame.Rect(start_x + 4 * (w_item + gap), bar_y, w_item, h_item),
                "主菜单",
                icon_type="menu",
                bg_color=(24, 20, 44),
                hover_color=(38, 30, 68),
                font_size=14,
                radius=8,
                accent_border=ColorPalette.PANEL_BORDER
            ),
        }

        # 3. 模态弹窗操作按钮
        modal_cx = self.width // 2
        modal_y = self.height // 2 + 88
        self.win_buttons = [
            ModernButton(
                pygame.Rect(modal_cx - 150, modal_y, 135, 46),
                "进入下一关",
                icon_type="next",
                bg_color=(15, 60, 42),
                hover_color=(24, 95, 65),
                accent_border=ColorPalette.EMERALD,
                radius=8
            ),
            ModernButton(
                pygame.Rect(modal_cx + 15, modal_y, 135, 46),
                "返回主菜单",
                icon_type="menu",
                bg_color=ColorPalette.CELL_BG,
                accent_border=ColorPalette.PANEL_BORDER,
                radius=8
            ),
        ]

        self.fail_buttons = [
            ModernButton(
                pygame.Rect(modal_cx - 150, modal_y, 135, 46),
                "重新挑战",
                icon_type="restart",
                bg_color=(60, 20, 35),
                hover_color=(95, 28, 50),
                accent_border=ColorPalette.ROSE,
                radius=8
            ),
            ModernButton(
                pygame.Rect(modal_cx + 15, modal_y, 135, 46),
                "返回主菜单",
                icon_type="menu",
                bg_color=ColorPalette.CELL_BG,
                accent_border=ColorPalette.PANEL_BORDER,
                radius=8
            ),
        ]

        self.all_clear_buttons = [
            ModernButton(
                pygame.Rect(modal_cx - 150, modal_y, 135, 46),
                "重玩全关",
                icon_type="play",
                bg_color=(55, 45, 15),
                hover_color=(85, 70, 24),
                accent_border=ColorPalette.AMBER,
                radius=8
            ),
            ModernButton(
                pygame.Rect(modal_cx + 15, modal_y, 135, 46),
                "返回主菜单",
                icon_type="menu",
                bg_color=ColorPalette.CELL_BG,
                accent_border=ColorPalette.PANEL_BORDER,
                radius=8
            ),
        ]

    def _load_level(self, index: int):
        """载入关卡数据"""
        level = self.level_mgr.set_level(index)
        self.current_board = Board(level.rows, level.cols, level.arrows, level.max_mistakes)
        self.level_start_time = time.time()
        self.level_elapsed = 0.0
        self.ai_solving = False

    def run(self):
        """主游戏循环"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()

        pygame.quit()

    def _handle_events(self):
        """事件派发"""
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(mouse_pos)

        # 悬浮态
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
        """快捷键支持"""
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
        elif self.state in (GameState.LEVEL_CLEAR, GameState.GAME_OVER, GameState.ALL_CLEAR, GameState.LEVEL_SELECT):
            if key == pygame.K_ESCAPE:
                self.state = GameState.MENU

    def _handle_click(self, mouse_pos: Tuple[int, int]):
        """鼠标左键点击派发"""
        if self.state == GameState.MENU:
            if self.menu_buttons[0].rect.collidepoint(mouse_pos):
                self._load_level(self.level_mgr.current_level_index)
                self.state = GameState.PLAYING
            elif self.menu_buttons[1].rect.collidepoint(mouse_pos):
                self.state = GameState.LEVEL_SELECT
            elif self.menu_buttons[2].rect.collidepoint(mouse_pos):
                enabled = self.sound_mgr.toggle_sound()
                self.menu_buttons[2].text = f"音效: {'开启' if enabled else '关闭'}"
                self.menu_buttons[2].icon_type = "sound_on" if enabled else "sound_off"
            elif self.menu_buttons[3].rect.collidepoint(mouse_pos):
                self.running = False

        elif self.state == GameState.LEVEL_SELECT:
            self._handle_level_select_click(mouse_pos)

        elif self.state == GameState.PLAYING:
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
                if self.current_board and not self.ai_solving:
                    grid_pos = self.renderer.screen_to_grid(mouse_pos, self.current_board.rows, self.current_board.cols)
                    if grid_pos:
                        self._trigger_arrow_click(grid_pos[0], grid_pos[1])

        elif self.state == GameState.LEVEL_CLEAR:
            if self.win_buttons[0].rect.collidepoint(mouse_pos):
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
        """执行箭头点击物理反馈与粒子喷发"""
        if not self.current_board:
            return

        arrow = self.current_board.get_arrow(r, c)
        if not arrow:
            return

        cx = self.renderer.grid_origin_x + (c + 0.5) * self.renderer.cell_size
        cy = self.renderer.grid_origin_y + (r + 0.5) * self.renderer.cell_size

        res = self.current_board.click_arrow(r, c)
        status = res.get("status")

        if status == "success":
            self.sound_mgr.play("fly")
            self.renderer.add_particles(cx, cy, count=18)
        elif status == "blocked":
            # 箭头启动飞出，在飞抵阻挡物接触点时再触发碰撞重击音效与粒子喷发
            self.sound_mgr.play("click")

    def _action_restart(self):
        """重启当前关卡"""
        if self.current_board:
            self.current_board.reset()
            self.level_start_time = time.time()
            self.level_elapsed = 0.0
            self.ai_solving = False

    def _action_hint(self):
        """提示功能"""
        if not self.current_board:
            return
        hint_arrow = Solver.get_hint(self.current_board)
        if hint_arrow:
            self.current_board.clear_highlights()
            hint_arrow.is_highlighted = True
            self.sound_mgr.play("hint")

    def _action_undo(self):
        """撤销步数"""
        if self.current_board and self.current_board.undo():
            self.sound_mgr.play("click")

    def _action_toggle_ai_solve(self):
        """切换 AI 自动求解"""
        self.ai_solving = not self.ai_solving
        self.ai_last_step_time = time.time()

    def _update(self, dt: float):
        """帧逻辑更新"""
        self.renderer.update(dt)

        if self.state == GameState.PLAYING and self.current_board:
            self.level_elapsed = time.time() - self.level_start_time
            self.current_board.update(dt, self.renderer.cell_size)

            # 监测受阻箭头是否刚好在当前帧飞抵并撞击阻挡箭头
            for arrow in self.current_board.grid.values():
                if getattr(arrow, "just_impacted", False):
                    arrow.just_impacted = False
                    self.sound_mgr.play("blocked")
                    # 在箭头尖端与阻挡箭头的物理接触交界处爆发展现霓虹火花
                    dr, dc = arrow.direction.delta
                    hit_x = self.renderer.grid_origin_x + (arrow.col + 0.5) * self.renderer.cell_size + arrow.offset_x + dc * (self.renderer.cell_size * 0.38)
                    hit_y = self.renderer.grid_origin_y + (arrow.row + 0.5) * self.renderer.cell_size + arrow.offset_y + dr * (self.renderer.cell_size * 0.38)
                    self.renderer.add_particles(
                        hit_x, hit_y, count=16,
                        palette=[ColorPalette.ROSE, (255, 140, 160), (255, 230, 240), ColorPalette.CYAN]
                    )

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

            # 过关胜利检测
            if self.current_board.is_cleared():
                self.ai_solving = False
                self.sound_mgr.play("win")
                cx, cy = self.width // 2, self.height // 2
                self.renderer.add_particles(cx, cy, count=80, palette=[ColorPalette.AMBER, ColorPalette.EMERALD, (255, 255, 255), ColorPalette.CYAN, ColorPalette.MAGENTA])
                if self.level_mgr.has_next_level():
                    self.state = GameState.LEVEL_CLEAR
                else:
                    self.state = GameState.ALL_CLEAR

            # 失败检测
            elif self.current_board.is_failed():
                self.ai_solving = False
                self.sound_mgr.play("fail")
                self.state = GameState.GAME_OVER

    def _render(self):
        """渲染绘制管线"""
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
        """渲染视觉冲击力更强的赛博合成波主菜单"""
        cx = self.width // 2

        # 1. 标题发光卡片与大气排版
        font_arcade = FontManager.get(14, bold=True)
        arc_surf = font_arcade.render("//  CYBER SYNTHWAVE ARCADE · 2026 EDITION  //", True, ColorPalette.CYAN)
        self.screen.blit(arc_surf, arc_surf.get_rect(center=(cx, 95)))

        font_logo = FontManager.get(50, bold=True)
        # 赛博双色霓虹发光阴影（左下偏洋红，右上偏天青）
        logo_pink_glow = font_logo.render("一 箭 又 一 箭", True, (160, 0, 85))
        self.screen.blit(logo_pink_glow, logo_pink_glow.get_rect(center=(cx - 2, 147)))
        logo_cyan_glow = font_logo.render("一 箭 又 一 箭", True, (0, 140, 170))
        self.screen.blit(logo_cyan_glow, logo_cyan_glow.get_rect(center=(cx + 2, 143)))

        # 主文字层
        logo_surf = font_logo.render("一 箭 又 一 箭", True, (255, 255, 255))
        self.screen.blit(logo_surf, logo_surf.get_rect(center=(cx, 145)))

        # 左右两侧浮雕动感修饰飞箭
        arrow_pulse = math.sin(pygame.time.get_ticks() * 0.005) * 6
        draw_tactile_arrow(self.screen, (cx - 215 + arrow_pulse, 145), size=40, angle_deg=90)
        draw_tactile_arrow(self.screen, (cx + 215 - arrow_pulse, 145), size=40, angle_deg=270)

        # 副标（采用未加粗的高清字体与微透科技胶囊底板，字体边缘平滑清晰，彻底告别锯齿与杂点）
        sub_card_rect = pygame.Rect(cx - 185, 195, 370, 32)
        draw_card(self.screen, sub_card_rect, bg_color=(20, 16, 42), border_color=(65, 52, 105), radius=8, shadow=False, tech_corners=False)

        font_sub = FontManager.get(15, bold=False)
        sub_surf = font_sub.render("观察方向  ·  巧妙规避  ·  箭无虚发", True, (225, 235, 255))
        sub_rect = sub_surf.get_rect(center=sub_card_rect.center)
        self.screen.blit(sub_surf, sub_rect)

        # 左右两侧精致微光菱形点缀
        for sign in (-1, 1):
            dx = sign * (sub_card_rect.width // 2 - 14)
            dia_pts = [(cx + dx, sub_card_rect.centery - 4), (cx + dx + 4, sub_card_rect.centery), (cx + dx, sub_card_rect.centery + 4), (cx + dx - 4, sub_card_rect.centery)]
            pygame.draw.polygon(self.screen, ColorPalette.CYAN, dia_pts)

        # 2. 菜单卡片选项
        for btn in self.menu_buttons:
            btn.draw(self.screen)

    def _render_playing(self):
        """渲染主游戏界面与状态"""
        if not self.current_board:
            return

        curr_level = self.level_mgr.get_current_level()

        # 1. 浮动岛顶部状态栏
        self.renderer.draw_top_bar(
            self.screen,
            curr_level,
            remaining_arrows=self.current_board.remaining_count(),
            remaining_mistakes=self.current_board.remaining_mistakes,
            max_mistakes=curr_level.max_mistakes,
            elapsed_time=self.level_elapsed
        )

        # 2. 棋盘与网格实体
        self.renderer.draw_board(self.screen, self.current_board, self.hover_cell)

        # 3. 底部悬浮控制栏
        for btn in self.game_buttons.values():
            btn.draw(self.screen)

        # 4. 模态弹窗
        if self.state == GameState.LEVEL_CLEAR:
            mistakes_made = curr_level.max_mistakes - self.current_board.remaining_mistakes
            stars = 3 if mistakes_made == 0 else (2 if mistakes_made == 1 else 1)
            self.renderer.draw_modal(
                self.screen,
                title="关 卡 通 关 达 成！",
                subtitle=f"本关通关用时: {int(self.level_elapsed)}s   |   失误次数: {mistakes_made}次",
                title_color=ColorPalette.EMERALD,
                buttons=self.win_buttons,
                stars=stars
            )
        elif self.state == GameState.GAME_OVER:
            self.renderer.draw_modal(
                self.screen,
                title="关 卡 挑 战 失败",
                subtitle="失误机会已全部耗尽，点击下方按钮重新挑战！",
                title_color=ColorPalette.ROSE,
                buttons=self.fail_buttons
            )
        elif self.state == GameState.ALL_CLEAR:
            self.renderer.draw_modal(
                self.screen,
                title="全 部 关 卡 彻 底 通 关！",
                subtitle="登峰造极！你已彻底攻破全部箭阵迷局，成为特级神箭手！",
                title_color=ColorPalette.AMBER,
                buttons=self.all_clear_buttons,
                stars=3
            )

    def _render_level_select(self):
        """渲染关卡选择面板"""
        cx = self.width // 2
        font_title = FontManager.get(30, bold=True)
        title_surf = font_title.render("选 择 挑 战 关 卡", True, ColorPalette.TEXT_TITLE)
        self.screen.blit(title_surf, title_surf.get_rect(center=(cx, 95)))

        card_w, card_h = 440, 88
        start_y = 155
        gap = 20
        mouse_pos = pygame.mouse.get_pos()

        for idx, lvl in enumerate(self.level_mgr.levels):
            card_x = cx - card_w // 2
            card_y = start_y + idx * (card_h + gap)
            rect = pygame.Rect(card_x, card_y, card_w, card_h)

            is_hover = rect.collidepoint(mouse_pos)
            bg = ColorPalette.PANEL_HOVER if is_hover else ColorPalette.PANEL_BG
            border = ColorPalette.CYAN if is_hover else ColorPalette.PANEL_BORDER

            draw_card(self.screen, rect, bg_color=bg, border_color=border, radius=12, shadow=True, tech_corners=True)

            # 关卡徽标
            b_rect = pygame.Rect(card_x + 20, card_y + 18, 68, 24)
            pygame.draw.rect(self.screen, (32, 24, 60), b_rect, border_radius=4)
            pygame.draw.rect(self.screen, ColorPalette.CYAN if is_hover else (120, 90, 170), b_rect, width=1, border_radius=4)
            b_txt = FontManager.get(12, bold=True).render(f"LV 0{lvl.level_id}", True, ColorPalette.CYAN if is_hover else ColorPalette.TEXT_MAIN)
            self.screen.blit(b_txt, b_txt.get_rect(center=b_rect.center))

            # 关卡名称
            f_name = FontManager.get(18, bold=True)
            n_surf = f_name.render(lvl.name.split("：")[-1], True, ColorPalette.TEXT_TITLE)
            self.screen.blit(n_surf, (card_x + 100, card_y + 18))

            # 关卡信息描述
            f_info = FontManager.get(13)
            info_str = f"棋盘规格: {lvl.rows}x{lvl.cols}   ·   箭头总数: {lvl.total_arrows} 支   ·   容错: {lvl.max_mistakes} 次"
            i_surf = f_info.render(info_str, True, ColorPalette.TEXT_MUTED)
            self.screen.blit(i_surf, (card_x + 20, card_y + 54))

        # 返回主菜单按钮
        back_btn = ModernButton(
            pygame.Rect(cx - 75, self.height - 75, 150, 44),
            "返回主菜单",
            icon_type="menu",
            bg_color=ColorPalette.CELL_BG,
            radius=10,
            accent_border=ColorPalette.PANEL_BORDER
        )
        back_btn.check_hover(mouse_pos)
        back_btn.draw(self.screen)

    def _handle_level_select_click(self, mouse_pos: Tuple[int, int]):
        """关卡选择点击事件"""
        cx = self.width // 2
        card_w, card_h = 440, 88
        start_y = 155
        gap = 20

        for idx in range(self.level_mgr.total_levels):
            card_x = cx - card_w // 2
            card_y = start_y + idx * (card_h + gap)
            rect = pygame.Rect(card_x, card_y, card_w, card_h)
            if rect.collidepoint(mouse_pos):
                self._load_level(idx)
                self.state = GameState.PLAYING
                return

        back_rect = pygame.Rect(cx - 75, self.height - 75, 150, 44)
        if back_rect.collidepoint(mouse_pos):
            self.state = GameState.MENU
