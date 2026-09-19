"""
自动化单元测试套件
严格对应软件工程作业规格要求测试用例 T01 ~ T06 以及关键边界条件
"""

import unittest
import sys
import os

# 确保能正确导入 src 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.arrow import Arrow, ArrowState, Direction
from src.core.board import Board
from src.core.solver import Solver
from src.core.level_manager import LevelManager, Level


class TestArrowGame(unittest.TestCase):
    """一箭又一箭核心逻辑与功能测试"""

    def setUp(self):
        """测试环境准备：构造标准 4x4 测试网格"""
        # 测试布局设计：
        # (0, 0) 朝上: 位于边界且朝外 (T03)
        # (1, 1) 朝右: 前方 (1, 3) 有阻挡 (T02)
        # (1, 3) 朝右: 位于边缘前方无阻挡 (T01)
        # (3, 2) 朝下: 位于边缘前方无阻挡
        self.arrows_config = [
            (0, 0, Direction.UP),
            (1, 1, Direction.RIGHT),
            (1, 3, Direction.RIGHT),
            (3, 2, Direction.DOWN),
        ]
        self.board = Board(rows=4, cols=4, arrows_config=self.arrows_config, max_mistakes=3)

    def test_t01_unblocked_arrow_flies_out(self):
        """
        [T01] 点击前方无阻挡的箭头
        预期结果：箭头成功触发飞出并从主网格中移出，进入飞出消除状态
        """
        # (1, 3) 朝右，其右侧即为棋盘边缘无阻挡
        res = self.board.click_arrow(1, 3)

        self.assertEqual(res["status"], "success")
        self.assertIsNotNone(res["arrow"])
        self.assertEqual(res["arrow"].state, ArrowState.FLYING)
        # 验证已从棋盘活跃坐标映射中移除
        self.assertNotIn((1, 3), self.board.grid)
        # 验证失误次数未扣减
        self.assertEqual(self.board.remaining_mistakes, 3)

    def test_t02_blocked_arrow_deducts_mistake(self):
        """
        [T02] 点击前方有阻挡的箭头
        预期结果：箭头不消失，状态变为受阻晃动，失误次数减 1
        """
        # (1, 1) 朝右，前进方向上有 (1, 3) 阻挡
        initial_mistakes = self.board.remaining_mistakes
        res = self.board.click_arrow(1, 1)

        self.assertEqual(res["status"], "blocked")
        self.assertIsNotNone(res["blocker"])
        self.assertEqual(res["blocker"].row, 1)
        self.assertEqual(res["blocker"].col, 3)
        # 箭头依然保留在网格中
        self.assertIn((1, 1), self.board.grid)
        self.assertEqual(self.board.grid[(1, 1)].state, ArrowState.COLLIDING)
        # 失误次数减少 1
        self.assertEqual(self.board.remaining_mistakes, initial_mistakes - 1)

    def test_t03_edge_arrow_facing_outside(self):
        """
        [T03] 点击位于边缘且朝向棋盘外的箭头
        预期结果：正常飞出消除，不发生索引越界错误
        """
        # (0, 0) 位于最顶行且朝上 (UP)
        can_fly, blocker = self.board.is_path_clear(self.board.get_arrow(0, 0))
        self.assertTrue(can_fly)
        self.assertIsNone(blocker)

        res = self.board.click_arrow(0, 0)
        self.assertEqual(res["status"], "success")
        self.assertNotIn((0, 0), self.board.grid)

        # 同样测试 (3, 2) 最底行朝下 (DOWN)
        can_fly_bottom, blocker_bottom = self.board.is_path_clear(self.board.get_arrow(3, 2))
        self.assertTrue(can_fly_bottom)
        self.assertIsNone(blocker_bottom)
        res_bottom = self.board.click_arrow(3, 2)
        self.assertEqual(res_bottom["status"], "success")

    def test_t04_clear_all_arrows(self):
        """
        [T04] 消除本关全部箭头
        预期结果：显示通关判定生效，棋盘处于已清空状态，可进入下一关
        """
        # 构造简单可通关顺序：(0, 0) -> (1, 3) -> (1, 1) -> (3, 2)
        steps = [(0, 0), (1, 3), (1, 1), (3, 2)]
        for r, c in steps:
            res = self.board.click_arrow(r, c)
            self.assertEqual(res["status"], "success", f"点击 ({r}, {c}) 应当成功")

        # 模拟动画更新完成飞出
        self.board.update(dt=1.0)

        self.assertTrue(self.board.is_cleared())
        self.assertFalse(self.board.is_failed())

        # 验证关卡管理器的切关能力
        lm = LevelManager()
        self.assertTrue(lm.has_next_level())
        next_lvl = lm.next_level()
        self.assertIsNotNone(next_lvl)
        self.assertEqual(next_lvl.level_id, 2)

    def test_t05_mistakes_depleted(self):
        """
        [T05] 失误次数耗尽
        预期结果：显示失败并允许重新开始
        """
        # 连续点击 3 次受阻的 (1, 1)
        for expected_left in [2, 1, 0]:
            # 为测试方便将晃动状态手动恢复或调用 update
            self.board.grid[(1, 1)].reset_state()
            res = self.board.click_arrow(1, 1)
            self.assertEqual(res["status"], "blocked")
            self.assertEqual(self.board.remaining_mistakes, expected_left)

        # 验证失败触发
        self.assertTrue(self.board.is_failed())
        self.assertFalse(self.board.is_cleared())

        # 验证重置后生命恢复
        self.board.reset()
        self.assertEqual(self.board.remaining_mistakes, 3)
        self.assertFalse(self.board.is_failed())

    def test_t06_restart_during_game(self):
        """
        [T06] 游戏进行中重新开始
        预期结果：箭头布局和失误次数完整恢复至初始状态
        """
        # 1. 先进行若干操作：消除一个、点错一个
        self.board.click_arrow(0, 0)  # 成功消除
        self.board.click_arrow(1, 1)  # 碰撞失误

        self.assertEqual(self.board.remaining_count(), 3)
        self.assertEqual(self.board.remaining_mistakes, 2)
        self.assertNotIn((0, 0), self.board.grid)

        # 2. 执行重启
        self.board.reset()

        # 3. 验证状态已恢复
        self.assertEqual(self.board.remaining_count(), 4)
        self.assertEqual(self.board.remaining_mistakes, 3)
        self.assertIn((0, 0), self.board.grid)
        self.assertEqual(self.board.get_arrow(0, 0).state, ArrowState.IDLE)
        self.assertEqual(self.board.get_arrow(1, 1).state, ArrowState.IDLE)

    def test_all_preset_levels_solvable(self):
        """验证关卡管理器中的所有关卡均能由求解器解出（保证不存在死锁）"""
        lm = LevelManager()
        for lvl in lm.levels:
            sol = Solver.solve(lvl.rows, lvl.cols, lvl.arrows)
            self.assertIsNotNone(sol, f"关卡 {lvl.level_id} 必须存在通关解")
            self.assertEqual(len(sol), lvl.total_arrows)

    def test_hint_and_undo_features(self):
        """验证扩展功能：提示（Hint）与撤销（Undo）"""
        # 提示应当返回一个前方无阻挡的箭头
        hint = Solver.get_hint(self.board)
        self.assertIsNotNone(hint)
        can_fly, _ = self.board.is_path_clear(hint)
        self.assertTrue(can_fly)

        # 撤销消除测试
        self.board.click_arrow(0, 0)
        self.assertNotIn((0, 0), self.board.grid)
        undo_res = self.board.undo()
        self.assertTrue(undo_res)
        self.assertIn((0, 0), self.board.grid)


if __name__ == "__main__":
    unittest.main()
