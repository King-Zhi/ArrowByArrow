"""
箭头实体类与方向枚举定义
包含四向移动向量、动画状态及插值更新
"""

from enum import Enum
import math
from typing import Tuple, Optional


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def delta(self) -> Tuple[int, int]:
        """返回 (dr, dc) 矩阵行与列的变化量"""
        if self == Direction.UP:
            return (-1, 0)
        elif self == Direction.DOWN:
            return (1, 0)
        elif self == Direction.LEFT:
            return (0, -1)
        elif self == Direction.RIGHT:
            return (0, 1)
        raise ValueError(f"Unknown direction: {self}")

    @property
    def angle(self) -> float:
        """返回旋转角度（以向上为 0 度，顺时针）"""
        if self == Direction.UP:
            return 0.0
        elif self == Direction.RIGHT:
            return 90.0
        elif self == Direction.DOWN:
            return 180.0
        elif self == Direction.LEFT:
            return 270.0
        return 0.0

    @property
    def symbol(self) -> str:
        """字符表示符号"""
        mapping = {
            Direction.UP: "↑",
            Direction.DOWN: "↓",
            Direction.LEFT: "←",
            Direction.RIGHT: "→",
        }
        return mapping[self]

    @classmethod
    def from_str(cls, val: str) -> "Direction":
        """从字符串或符号解析方向"""
        val_upper = val.strip().upper()
        if val_upper in ("UP", "^", "U", "↑"):
            return cls.UP
        if val_upper in ("DOWN", "V", "D", "↓"):
            return cls.DOWN
        if val_upper in ("LEFT", "<", "L", "←"):
            return cls.LEFT
        if val_upper in ("RIGHT", ">", "R", "→"):
            return cls.RIGHT
        raise ValueError(f"Cannot parse Direction from '{val}'")


class ArrowState(Enum):
    IDLE = "IDLE"           # 静止等待点击
    FLYING = "FLYING"       # 正在飞出棋盘
    COLLIDING = "COLLIDING" # 阻挡碰撞中（晃动并微弹回）
    ELIMINATED = "ELIMINATED" # 已飞出并消除


class Arrow:
    """网格中的箭头实体"""

    _id_counter = 0

    def __init__(self, row: int, col: int, direction: Direction):
        Arrow._id_counter += 1
        self.id = Arrow._id_counter
        self.row = row
        self.col = col
        self.direction = direction
        self.state = ArrowState.IDLE

        # 动画参数
        self.anim_progress = 0.0      # 0.0 -> 1.0
        self.offset_x = 0.0           # 屏幕像素偏移 X
        self.offset_y = 0.0           # 屏幕像素偏移 Y
        self.anim_duration = 0.25     # 秒

        # 高亮提示（用于提示功能）
        self.is_highlighted = False

    def copy(self) -> "Arrow":
        """浅克隆一个带有相同位置与方向的箭头"""
        new_arrow = Arrow(self.row, self.col, self.direction)
        new_arrow.id = self.id
        new_arrow.state = self.state
        return new_arrow

    def start_flying(self, duration: float = 0.3):
        """开始飞出动画"""
        self.state = ArrowState.FLYING
        self.anim_progress = 0.0
        self.anim_duration = duration

    def start_collision(self, duration: float = 0.35):
        """开始碰撞受阻动画（前冲微移然后左右晃动回位）"""
        self.state = ArrowState.COLLIDING
        self.anim_progress = 0.0
        self.anim_duration = duration

    def update(self, dt: float, cell_size: float = 70.0) -> bool:
        """
        更新动画插值
        返回 True 表示状态发生了改变（例如飞出完成或晃动结束）
        """
        if self.state == ArrowState.IDLE or self.state == ArrowState.ELIMINATED:
            self.offset_x = 0.0
            self.offset_y = 0.0
            return False

        self.anim_progress += dt / self.anim_duration

        if self.state == ArrowState.FLYING:
            # 沿箭头方向高速飞向视口外部（飞出 8~10 个格子长度）
            dr, dc = self.direction.delta
            dist = (self.anim_progress ** 1.6) * cell_size * 10
            self.offset_x = dc * dist
            self.offset_y = dr * dist

            if self.anim_progress >= 1.0:
                self.state = ArrowState.ELIMINATED
                self.anim_progress = 1.0
                return True

        elif self.state == ArrowState.COLLIDING:
            # 撞墙反馈效果：先向前试探性微冲 15 像素，遇到阻挡发生高频衰减晃动，最后恢复原位
            t = min(1.0, self.anim_progress)
            dr, dc = self.direction.delta

            # 衰减晃动正弦波
            decay = math.exp(-3.0 * t)
            shake_amp = 14.0 * decay * math.sin(t * math.pi * 5)

            # 向前阻挡回弹
            forward_amp = math.sin(t * math.pi) * 12.0

            # 侧向晃动方向（垂直于运动方向）
            perp_r, perp_c = -dc, dr

            self.offset_x = dc * forward_amp + perp_c * shake_amp
            self.offset_y = dr * forward_amp + perp_r * shake_amp

            if self.anim_progress >= 1.0:
                self.state = ArrowState.IDLE
                self.anim_progress = 0.0
                self.offset_x = 0.0
                self.offset_y = 0.0
                return True

        return False

    def reset_state(self):
        """重置状态为静止"""
        self.state = ArrowState.IDLE
        self.anim_progress = 0.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.is_highlighted = False

    def __repr__(self) -> str:
        return f"Arrow({self.row}, {self.col}, {self.direction.name}, state={self.state.name})"
