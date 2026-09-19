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
        self.collision_dist_cells = 1.0 # 距离碰撞障碍物的格子数
        self.impact_triggered = False  # 是否已触发撞击接触点事件
        self.just_impacted = False     # 当前帧是否刚达到撞击点

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

    def start_collision(self, dist_cells: float = 1.0, duration: Optional[float] = None):
        """
        开始受阻碰撞物理动画：
        1. 箭头先沿着其方向飞过空格，直至接触前方阻挡它的箭头
        2. 在撞击接触点触发震颤、粒子与音效反馈
        3. 从撞击点平滑滑动回退至原初始单元格
        """
        self.state = ArrowState.COLLIDING
        self.anim_progress = 0.0
        self.collision_dist_cells = max(1.0, float(dist_cells))
        # 飞行距离越远，动画总时长相应微调，以保证视觉上清晰可见的飞行轨迹
        self.anim_duration = duration or (0.28 + 0.07 * min(4.0, self.collision_dist_cells))
        self.impact_triggered = False
        self.just_impacted = False

    def update(self, dt: float, cell_size: float = 70.0) -> bool:
        """
        更新动画插值
        返回 True 表示状态发生了改变（例如飞出完成或晃动结束）
        """
        self.just_impacted = False

        if self.state == ArrowState.IDLE or self.state == ArrowState.ELIMINATED:
            self.offset_x = 0.0
            self.offset_y = 0.0
            return False

        self.anim_progress += dt / self.anim_duration
        p = self.anim_progress

        if self.state == ArrowState.FLYING:
            # 沿箭头方向高速飞向视口外部（飞出 8~10 个格子长度）
            dr, dc = self.direction.delta
            dist = (p ** 1.6) * cell_size * 10
            self.offset_x = dc * dist
            self.offset_y = dr * dist

            if p >= 1.0:
                self.state = ArrowState.ELIMINATED
                self.anim_progress = 1.0
                return True

        elif self.state == ArrowState.COLLIDING:
            dr, dc = self.direction.delta
            # 物理撞击距离：飞至触碰阻挡物边沿
            max_travel_dist = max(18.0, (self.collision_dist_cells - 0.70) * cell_size)

            # 阶段时间划分：
            # 阶段 1 (0 -> t_hit): 向前飞抵阻挡物
            # 阶段 2 (t_hit -> t_shake): 在阻挡物处撞击震颤与受阻报警
            # 阶段 3 (t_shake -> 1.0): 平滑弹回并滑动复位
            t_hit = min(0.42, (0.10 + 0.045 * min(4.0, self.collision_dist_cells)) / self.anim_duration)
            t_shake = min(0.72, t_hit + 0.14 / self.anim_duration)

            if p < t_hit:
                # 阶段 1：平滑快速前飞奔向阻挡物
                k = (p / t_hit) ** 1.2
                curr_dist = k * max_travel_dist
                self.offset_x = dc * curr_dist
                self.offset_y = dr * curr_dist

            elif p < t_shake:
                # 刚到达撞击点瞬间触发事件
                if not self.impact_triggered:
                    self.impact_triggered = True
                    self.just_impacted = True

                # 阶段 2：在阻挡物面前高频衰减震颤反馈
                sp = (p - t_hit) / (t_shake - t_hit)
                decay = math.exp(-3.5 * sp)
                shake_amp = 8.0 * decay * math.sin(sp * math.pi * 5.0)
                recoil = -3.5 * math.sin(sp * math.pi)

                # 侧向晃动分量（垂直于运动方向）
                perp_r, perp_c = -dc, dr
                forward = max_travel_dist + recoil
                self.offset_x = dc * forward + perp_c * shake_amp
                self.offset_y = dr * forward + perp_r * shake_amp

            else:
                # 阶段 3：从阻挡物处平滑反弹滑回初始格位
                if not self.impact_triggered:
                    self.impact_triggered = True
                    self.just_impacted = True

                rp = (p - t_shake) / (1.0 - t_shake)
                # 平滑缓动回到 0
                ease = 0.5 - 0.5 * math.cos(rp * math.pi)
                curr_dist = max_travel_dist * (1.0 - ease)
                self.offset_x = dc * curr_dist
                self.offset_y = dr * curr_dist

            if p >= 1.0:
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
