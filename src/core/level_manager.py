"""
关卡管理模块
定义预设关卡数据、通关顺序验证与关卡切换
"""

from typing import List, Dict, Any, Tuple, Optional
from .arrow import Direction
from .solver import Solver


class Level:
    """单个关卡数据"""

    def __init__(self, level_id: int, name: str, rows: int, cols: int, arrows: List[Tuple[int, int, str]], max_mistakes: int = 3, description: str = ""):
        self.level_id = level_id
        self.name = name
        self.rows = rows
        self.cols = cols
        # 将方向字符串转换为 Direction 枚举
        self.arrows: List[Tuple[int, int, Direction]] = [
            (r, c, Direction.from_str(d)) for r, c, d in arrows
        ]
        self.max_mistakes = max_mistakes
        self.description = description

        # 校验该关卡是否可解
        self.solution = Solver.solve(self.rows, self.cols, self.arrows)
        if self.solution is None:
            raise ValueError(f"关卡 {level_id} ({name}) 不存在可行通关解，设计存在死锁！")

    @property
    def total_arrows(self) -> int:
        return len(self.arrows)


class LevelManager:
    """关卡管理器"""

    def __init__(self):
        self.levels: List[Level] = []
        self._init_default_levels()
        self.current_level_index = 0

    def _init_default_levels(self):
        """初始化官方预设的 4 个精美关卡（均通过严格可解性检验）"""

        # 第 1 关：新手起步（4x4 基础教学，学习边缘向外飞出与阻挡消除）
        # 布局说明：
        # (0, 1) 向左 (0, 1 -> 0, 0 为空，可直接消除)
        # (0, 3) 向上 (0, 3 直接飞出)
        # (1, 1) 向上 (等待 (0, 1) 消除后可飞出)
        # (2, 2) 向右 (2, 3 为空，可直接飞出)
        # (2, 1) 向下 (2, 1 -> 3, 1 为空，可直接飞出)
        # (3, 2) 向上 (等待 (2, 2) 消除后可飞出)
        l1_arrows = [
            (0, 1, "LEFT"),
            (0, 3, "UP"),
            (1, 1, "UP"),
            (2, 2, "RIGHT"),
            (2, 1, "DOWN"),
            (3, 2, "UP")
        ]

        # 第 2 关：纵横交错（5x5 进阶迷局，多重路径重叠）
        l2_arrows = [
            (0, 2, "UP"),
            (1, 0, "LEFT"),
            (1, 2, "UP"),
            (1, 4, "RIGHT"),
            (2, 2, "RIGHT"),
            (2, 4, "DOWN"),
            (3, 1, "DOWN"),
            (3, 3, "UP"),
            (4, 1, "LEFT"),
            (4, 3, "DOWN")
        ]

        # 第 3 关：步步为营（5x5 高难度，深层拓扑依赖）
        l3_arrows = [
            (0, 0, "RIGHT"),
            (0, 4, "DOWN"),
            (1, 1, "UP"),
            (1, 3, "LEFT"),
            (2, 0, "UP"),
            (2, 2, "RIGHT"),
            (2, 4, "RIGHT"),
            (3, 1, "DOWN"),
            (3, 3, "DOWN"),
            (4, 0, "LEFT"),
            (4, 2, "UP"),
            (4, 4, "DOWN")
        ]

        # 第 4 关：箭阵迷宫（6x6 终极挑战关卡，16枚复杂多维箭头）
        l4_arrows = [
            (0, 3, "UP"),
            (5, 0, "DOWN"),
            (5, 1, "LEFT"),
            (4, 5, "DOWN"),
            (5, 3, "LEFT"),
            (3, 2, "DOWN"),
            (1, 0, "LEFT"),
            (1, 1, "DOWN"),
            (5, 4, "DOWN"),
            (4, 4, "DOWN"),
            (0, 4, "LEFT"),
            (4, 0, "RIGHT"),
            (3, 0, "DOWN"),
            (3, 5, "RIGHT"),
            (1, 3, "UP"),
            (2, 3, "RIGHT")
        ]

        self.levels.append(Level(1, "第一关：小试牛刀", 4, 4, l1_arrows, max_mistakes=3, description="观察直接指向棋盘外侧的箭头，先扫清外围！"))
        self.levels.append(Level(2, "第二关：纵横交织", 5, 5, l2_arrows, max_mistakes=3, description="注意十字交叉处的相互阻挡，寻找突破口。"))
        self.levels.append(Level(3, "第三关：步步为营", 5, 5, l3_arrows, max_mistakes=4, description="多层依赖考验观察力，按合理顺序层层剥离。"))
        self.levels.append(Level(4, "第四关：箭阵迷宫", 6, 6, l4_arrows, max_mistakes=4, description="宏大箭阵，综合考量全盘拓扑关系！"))

    @property
    def total_levels(self) -> int:
        return len(self.levels)

    def get_current_level(self) -> Level:
        return self.levels[self.current_level_index]

    def set_level(self, index: int) -> Level:
        if 0 <= index < len(self.levels):
            self.current_level_index = index
        return self.get_current_level()

    def has_next_level(self) -> bool:
        return self.current_level_index + 1 < len(self.levels)

    def next_level(self) -> Optional[Level]:
        if self.has_next_level():
            self.current_level_index += 1
            return self.get_current_level()
        return None
