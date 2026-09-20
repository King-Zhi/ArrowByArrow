"""
棋盘模型与核心路径检测算法
包含二维网格管理、射线投射碰撞检测、失误判定与撤销机制
"""

from typing import Dict, Tuple, Optional, List, Any
from .arrow import Arrow, ArrowState, Direction


class Board:
    """网格棋盘与核心判定逻辑"""

    def __init__(self, rows: int, cols: int, arrows_config: List[Tuple[int, int, Direction]], max_mistakes: int = 3):
        self.rows = rows
        self.cols = cols
        self.max_mistakes = max_mistakes
        self.remaining_mistakes = max_mistakes

        # 初始配置暂存，用于重启关卡
        self.initial_arrows_config = [(r, c, d) for r, c, d in arrows_config]

        # 当前网格坐标映射: (row, col) -> Arrow
        self.grid: Dict[Tuple[int, int], Arrow] = {}

        # 飞出中的箭头列表（用于动画渲染直至完全飞出）
        self.flying_arrows: List[Arrow] = []

        # 撤销历史栈（支持附加分功能：撤销上一步）
        self.history_stack: List[Dict[str, Any]] = []

        # 初始化棋盘
        self._load_config(self.initial_arrows_config)

    def _load_config(self, config: List[Tuple[int, int, Direction]]):
        """根据配置生成箭头实体"""
        self.grid.clear()
        self.flying_arrows.clear()
        for r, c, direction in config:
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                raise ValueError(f"Arrow coordinates ({r}, {c}) out of board bounds ({self.rows}x{self.cols})")
            arrow = Arrow(r, c, direction)
            self.grid[(r, c)] = arrow

    def reset(self):
        """重置棋盘为初始状态（满足作业 T06 需求）"""
        self.remaining_mistakes = self.max_mistakes
        self.history_stack.clear()
        self._load_config(self.initial_arrows_config)

    def is_path_clear(self, arrow: Arrow) -> Tuple[bool, Optional[Arrow]]:
        """
        核心路径检测算法：
        判断箭头在其朝向的行/列方向上，直至棋盘边界，是否存在其他未消除箭头的阻挡。
        
        返回值:
            (True, None) - 前方无阻挡，可成功飞出
            (False, blocking_arrow) - 前方有阻挡，返回碰到的第一个箭头对象
        """
        r, c = arrow.row, arrow.col
        dr, dc = arrow.direction.delta

        curr_r = r + dr
        curr_c = c + dc

        # 沿着方向射线一直延伸至棋盘边界
        while 0 <= curr_r < self.rows and 0 <= curr_c < self.cols:
            target_cell = (curr_r, curr_c)
            # 检查该坐标处是否有活跃箭头
            if target_cell in self.grid:
                blocker = self.grid[target_cell]
                # 处于 IDLE 或 COLLIDING 状态的箭头均构成实体阻挡
                if blocker.state != ArrowState.ELIMINATED:
                    return False, blocker
            curr_r += dr
            curr_c += dc

        # 射线延伸出边界未碰到阻挡，判定为路径畅通
        return True, None

    def has_colliding_arrow(self) -> bool:
        """检查棋盘上是否有任何箭头正处于受阻碰撞/回退原位的动画过程中"""
        return any(arrow.state == ArrowState.COLLIDING for arrow in self.grid.values())

    def click_arrow(self, row: int, col: int) -> Dict[str, Any]:
        """
        处理对指定坐标箭头的点击交互
        
        返回结果字典包含：
            - status: 'success' | 'blocked' | 'invalid' | 'animating'
            - arrow: 操作的箭头对象
            - blocker: 阻挡物（若受阻）
            - mistakes_left: 剩余失误次数
        """
        # 若棋盘上有任何箭头正处于受阻碰撞回退原位的动画过程中，禁止触发新的点击交互
        if self.has_colliding_arrow():
            return {"status": "animating", "arrow": None}

        if (row, col) not in self.grid:
            return {"status": "invalid", "arrow": None}

        arrow = self.grid[(row, col)]

        # 如果箭头正在飞出或受阻晃动中，忽略重复点击
        if arrow.state != ArrowState.IDLE:
            return {"status": "animating", "arrow": arrow}

        # 清除所有高亮提示
        self.clear_highlights()

        can_fly, blocker = self.is_path_clear(arrow)

        if can_fly:
            # 记录历史状态供撤销使用
            self.history_stack.append({
                "type": "fly",
                "arrow": arrow.copy(),
                "mistakes_left": self.remaining_mistakes
            })

            # 从棋盘主网格移出，进入飞出动画列表
            del self.grid[(row, col)]
            arrow.start_flying()
            self.flying_arrows.append(arrow)

            return {
                "status": "success",
                "arrow": arrow,
                "mistakes_left": self.remaining_mistakes
            }
        else:
            # 碰撞受阻：计算距离阻挡物的网格距离
            self.remaining_mistakes = max(0, self.remaining_mistakes - 1)
            dist_cells = abs(blocker.row - arrow.row) + abs(blocker.col - arrow.col) if blocker else 1.0
            arrow.start_collision(dist_cells=dist_cells)

            self.history_stack.append({
                "type": "mistake",
                "arrow": arrow.copy(),
                "mistakes_left": self.remaining_mistakes + 1
            })

            return {
                "status": "blocked",
                "arrow": arrow,
                "blocker": blocker,
                "dist_cells": dist_cells,
                "mistakes_left": self.remaining_mistakes
            }

    def undo(self) -> bool:
        """撤销上一步操作（附加功能）"""
        if not self.history_stack:
            return False

        last_action = self.history_stack.pop()
        action_type = last_action["type"]

        if action_type == "fly":
            # 恢复消除的箭头
            saved_arrow: Arrow = last_action["arrow"]
            restored = Arrow(saved_arrow.row, saved_arrow.col, saved_arrow.direction)
            self.grid[(restored.row, restored.col)] = restored
            # 从正在飞出的列表中移除（如果仍在）
            self.flying_arrows = [a for a in self.flying_arrows if a.id != saved_arrow.id]
            self.remaining_mistakes = last_action["mistakes_left"]
            return True

        elif action_type == "mistake":
            # 恢复失误次数
            self.remaining_mistakes = last_action["mistakes_left"]
            return True

        return False

    def update(self, dt: float, cell_size: float = 70.0):
        """更新所有进行中动画的状态"""
        # 更新棋盘内正在晃动的箭头
        for arrow in list(self.grid.values()):
            arrow.update(dt, cell_size)

        # 更新正在飞出屏幕的箭头
        for arrow in list(self.flying_arrows):
            arrow.update(dt, cell_size)
            if arrow.state == ArrowState.ELIMINATED:
                self.flying_arrows.remove(arrow)

    def is_cleared(self) -> bool:
        """检查当前关卡是否全部消除完成"""
        return len(self.grid) == 0 and len(self.flying_arrows) == 0

    def is_failed(self) -> bool:
        """检查是否失败（失误次数耗尽且未通关）"""
        return self.remaining_mistakes <= 0 and not self.is_cleared()

    def is_animating(self) -> bool:
        """检查棋盘当前是否有任何箭头正在飞出或受阻碰撞动画中"""
        if len(self.flying_arrows) > 0:
            return True
        return any(arrow.state != ArrowState.IDLE for arrow in self.grid.values())

    @property
    def display_remaining_mistakes(self) -> int:
        """
        用于 UI 呈现的失误次数：
        当箭头被点击后在飞向阻挡物途中（尚未触碰撞击），视觉上保留该心形；
        直到箭头真正撞上阻挡箭头（impact_triggered 触发）的瞬间才扣除！
        """
        pending = sum(
            1 for arrow in self.grid.values()
            if arrow.state == ArrowState.COLLIDING and not getattr(arrow, "impact_triggered", True)
        )
        return min(self.max_mistakes, self.remaining_mistakes + pending)

    def remaining_count(self) -> int:
        """当前棋盘剩余箭头数量"""
        return len(self.grid)

    def clear_highlights(self):
        """清除全部高亮"""
        for arrow in self.grid.values():
            arrow.is_highlighted = False

    def get_arrow(self, row: int, col: int) -> Optional[Arrow]:
        """获取指定位置的箭头"""
        return self.grid.get((row, col))
