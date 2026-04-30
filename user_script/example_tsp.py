#!/usr/bin/env python3
"""
示例：使用 Kaiwu SDK 求解旅行商问题 (TSP)
这个脚本在 Docker 容器中运行，自动调用已安装的 Kaiwu SDK。

更多示例请参考 Kaiwu SDK 文档：
https://kaiwu-sdk-docs.qboson.com/zh/latest/index.html
"""

import numpy as np
import kaiwu as kw


def solve_tsp_simple():
    """
    简单 TSP 求解示例：4 个城市的旅行商问题

    使用 QUBO 建模 + 模拟退火求解器。
    如需使用真机 CIM，请将求解器替换为：
        opt = kw.cim.CIMOptimizer(task_name="tsp-demo", wait=True)
    """
    print("=" * 50)
    print("Kaiwu SDK 示例：旅行商问题 (TSP)")
    print("=" * 50)

    # 定义 4 个城市间的距离矩阵
    # 城市 0, 1, 2, 3 两两之间的距离
    distance_matrix = np.array([
        [0, 10, 15, 20],
        [10, 0, 35, 25],
        [15, 35, 0, 30],
        [20, 25, 30, 0],
    ])

    n_cities = len(distance_matrix)
    print(f"城市数量: {n_cities}")
    print(f"距离矩阵:\n{distance_matrix}\n")

    # 构建 QUBO 模型
    # 这里展示简化的 QUBO 构建方式
    # 实际应用中请根据约束条件构建完整 QUBO 矩阵
    qubo = np.zeros((n_cities * n_cities, n_cities * n_cities))

    # ... QUBO 矩阵构建逻辑（参见 Kaiwu SDK 文档中的 TSP 教程）

    print("使用模拟退火求解器...")
    opt = kw.classical.SimulatedAnnealingOptimizer(
        initial_temperature=100,
        alpha=0.99,
        cutoff_temperature=0.001,
        iterations_per_t=10,
        size_limit=100,
    )

    # 调整精度
    adjusted = kw.qubo.adjust_qubo_matrix_precision(qubo)

    # 求解
    solution = opt.solve(adjusted)
    print(f"求解结果: {solution}")
    print("=" * 50)


if __name__ == "__main__":
    solve_tsp_simple()
