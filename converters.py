"""
Converters: thin wrappers around qubify presets.
Takes business data, returns QUBO matrices ready for Kaiwu SDK.

qubify = make it QUBO
"""

import json
import numpy as np


def tsp_to_qubo(distances):
    """Convert TSP distance matrix to QUBO matrix.

    Args:
        distances: n×n list of lists or JSON string of distance matrix.

    Returns:
        (qubo_matrix, var_map) — qubo_matrix is a numpy array.
    """
    from qubify.presets import tsp

    if isinstance(distances, str):
        distances = json.loads(distances)
    D = np.array(distances, dtype=float)
    return tsp(D)


def maxcut_to_qubo(adjacency):
    """Convert graph adjacency matrix to QUBO matrix.

    Args:
        adjacency: n×n list of lists or JSON string of adjacency matrix.

    Returns:
        (qubo_matrix, var_map)
    """
    from qubify.presets import maxcut

    if isinstance(adjacency, str):
        adjacency = json.loads(adjacency)
    A = np.array(adjacency, dtype=float)
    return maxcut(A)


def knapsack_to_qubo(values, weights, capacity, slack_bits=4):
    """Convert knapsack instance to QUBO matrix.

    Args:
        values: list of item values
        weights: list of item weights
        capacity: int, max total weight
        slack_bits: number of slack binary variables (default 4)

    Returns:
        (qubo_matrix, var_map)
    """
    from qubify.presets import knapsack

    if isinstance(values, str):
        data = json.loads(values)
        return knapsack(
            data["values"], data["weights"], data["capacity"],
            slack_bits=data.get("slack_bits", 4),
        )
    return knapsack(values, weights, capacity, slack_bits)


def dsl_to_qubo(problem_desc):
    """Compile a qubify DSL problem description to QUBO matrix.

    Args:
        problem_desc: dict or JSON string matching qubify DSL schema.

    Returns:
        (qubo_matrix, var_map)
    """
    from qubify import qubify as qf

    if isinstance(problem_desc, str):
        problem_desc = json.loads(problem_desc)
    return qf(problem_desc)
