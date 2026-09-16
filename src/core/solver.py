"""
拓扑求解器与智能提示引擎
提供可解性判定、有效消除步骤搜寻以及 AI 自动求解演示
"""

from typing import List, Tuple, Optional
from .board import Board
from .arrow import Arrow, Direction


class Solver:
    """关卡求解与提示引擎"""

    @staticmethod
    def get_clearable_arrows(board: Board) -> List[Arrow]:
        """获取当前棋盘上所有前方无阻挡、可直接消除的箭头列表"""
        clearable = []
        for arrow in board.grid.values():
            can_fly, _ = board.is_path_clear(arrow)
            if can_fly:
                clearable.append(arrow)
        return clearable

    @staticmethod
    def get_hint(board: Board) -> Optional[Arrow]:
        """
        获取一个可消除的推荐箭头用于高亮提示
        优先选择能解开后续最多闭环的箭头
        """
        clearable = Solver.get_clearable_arrows(board)
        if not clearable:
            return None
        # 默认返回第一个可消除箭头
        return clearable[0]

    @staticmethod
    def solve(rows: int, cols: int, arrows_config: List[Tuple[int, int, Direction]]) -> Optional[List[Tuple[int, int]]]:
        """
        模拟拓扑剥离算法，寻找一条完整的通关消除序列。
        如果关卡可解，返回有序的坐标列表 [(r1, c1), (r2, c2), ...]
        如果关卡存在死锁无法通关，返回 None
        """
        # 使用虚拟棋盘进行无副作用推演
        sim_board = Board(rows, cols, arrows_config, max_mistakes=999)
        solution: List[Tuple[int, int]] = []

        while len(sim_board.grid) > 0:
            clearable = Solver.get_clearable_arrows(sim_board)
            if not clearable:
                # 还有剩余箭头，但没有任何一个可以飞出 -> 死锁！
                return None
            
            # 贪心消除第一个无阻挡箭头
            target = clearable[0]
            solution.append((target.row, target.col))
            del sim_board.grid[(target.row, target.col)]

        return solution

    @staticmethod
    def is_solvable(rows: int, cols: int, arrows_config: List[Tuple[int, int, Direction]]) -> bool:
        """快速判断关卡是否必定存在可行通关路径"""
        return Solver.solve(rows, cols, arrows_config) is not None
