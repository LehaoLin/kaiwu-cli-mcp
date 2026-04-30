#!/usr/bin/env python3
"""
MCP Server for kaiwu-cli-mcp — AI Agent access to Kaiwu SDK.
Provides tools for license management, script execution, and QUBO/Ising solving.
"""

import json
from fastmcp import FastMCP

from core import (
    build_image,
    init_license,
    check_license,
    run_script,
    solve_qubo,
    solve_ising,
    compile_and_solve,
    compile_problem,
    container_status,
)

mcp = FastMCP(
    name="kaiwu-sdk-tools",
    version="1.0.0",
    description="Kaiwu SDK tools for 玻色量子 CIM quantum computer — license management, script execution, QUBO/Ising problem solving",
)


@mcp.tool()
def kaiwu_build_image() -> str:
    """Build the Kaiwu SDK Docker image.

    Must be run once before using other tools. This builds a Docker image
    with Python 3.10 and the Kaiwu SDK installed.
    """
    result = build_image()
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_init_license(user_id: str = "", sdk_code: str = "") -> str:
    """Generate Kaiwu SDK license inside the Docker container.

    Args:
        user_id: 用户ID from https://platform.qboson.com/ (leave empty to use user_config.yaml)
        sdk_code: SDK授权码 from https://platform.qboson.com/ (leave empty to use user_config.yaml)
    """
    result = init_license(user_id=user_id or None, sdk_code=sdk_code or None)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_check_license() -> str:
    """Check if the Kaiwu SDK license is valid.

    Returns license file status and path.
    """
    result = check_license()
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_run_script(script_path: str) -> str:
    """Run a Python script inside the Kaiwu SDK Docker container.

    Supports two modes:
    1. Scripts under user_script/ — directly accessible (already mounted)
    2. Scripts ANYWHERE on the host — auto-mounted via temporary volume

    Args:
        script_path: Path to the Python script. Relative paths resolve
                     under user_script/ first. Absolute paths work from
                     anywhere on the host.
    """
    result = run_script(script_path)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_solve_qubo(
    qubo_matrix_json: str,
    use_cim: bool = False,
    task_name: str = "kaiwu-task",
) -> str:
    """Solve a QUBO (Quadratic Unconstrained Binary Optimization) problem.

    Uses SimulatedAnnealingOptimizer by default, or CIMOptimizer (real quantum hardware)
    if use_cim=True and cloud access is available.

    Args:
        qubo_matrix_json: JSON-encoded 2D array, e.g. '[[0.89, 0.22], [0.22, 0.23]]'
        use_cim: If True, submit to CIM quantum computer (requires cloud platform access)
        task_name: Task name for CIM submission (default: 'kaiwu-task')
    """
    result = solve_qubo(qubo_matrix_json, use_cim=use_cim, task_name=task_name)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_solve_ising(
    ising_matrix_json: str,
    use_cim: bool = False,
    task_name: str = "kaiwu-task",
) -> str:
    """Solve an Ising model problem.

    Uses SimulatedAnnealingOptimizer by default, or CIMOptimizer (real quantum hardware)
    if use_cim=True and cloud access is available.

    Args:
        ising_matrix_json: JSON-encoded 2D array for the Ising matrix
        use_cim: If True, submit to CIM quantum computer (requires cloud platform access)
        task_name: Task name for CIM submission (default: 'kaiwu-task')
    """
    result = solve_ising(ising_matrix_json, use_cim=use_cim, task_name=task_name)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_container_status() -> str:
    """Check the Kaiwu SDK Docker container status.

    Returns container running state, ports, and health info.
    """
    result = container_status()
    return json.dumps(result, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# qubify integration — compile problem descriptions to QUBO
# ═══════════════════════════════════════════════════════════════


@mcp.tool()
def kaiwu_solve_preset(
    preset: str,
    data_json: str,
    use_cim: bool = False,
    task_name: str = "kaiwu-task",
) -> str:
    """Compile a problem via qubify preset and solve with Kaiwu SDK.

    One-call pipeline: problem data → qubify compiler → QUBO matrix → solution.

    Args:
        preset: Problem type — 'tsp', 'maxcut', or 'knapsack'
        data_json: JSON data for the preset.
                   tsp: distance matrix [[0,10,15],[10,0,35]...]
                   maxcut: adjacency matrix [[0,1,0],[1,0,1]...]
                   knapsack: {"values":[60,100,120],"weights":[10,20,30],"capacity":50}
        use_cim: If True, submit to CIM quantum computer
        task_name: Task name for CIM submission
    """
    result = compile_and_solve(
        preset=preset, data=data_json,
        use_cim=use_cim, task_name=task_name,
    )
    # var_map isn't JSON-serializable, strip it from response
    result.pop("var_map", None)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_solve_dsl(
    dsl_json: str,
    use_cim: bool = False,
    task_name: str = "kaiwu-task",
) -> str:
    """Compile a qubify DSL problem description and solve with Kaiwu SDK.

    Args:
        dsl_json: JSON string of qubify DSL: {"variables":..., "objective":..., "constraints":...}
        use_cim: If True, submit to CIM quantum computer
        task_name: Task name for CIM submission
    """
    result = compile_and_solve(
        dsl=dsl_json,
        use_cim=use_cim, task_name=task_name,
    )
    result.pop("var_map", None)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def kaiwu_compile_problem(
    preset: str = "",
    data_json: str = "",
    dsl_json: str = "",
) -> str:
    """Compile a problem description to QUBO matrix (no solving).

    Use this to inspect the QUBO matrix before solving, or to feed it
    to a different solver.

    Args:
        preset: Problem type — 'tsp', 'maxcut', or 'knapsack' (use with data_json)
        data_json: JSON data for the preset
        dsl_json: qubify DSL problem description (alternative to preset+data)
    """
    result = compile_problem(
        preset=preset or None,
        data=data_json or None,
        dsl=dsl_json or None,
    )
    result.pop("var_map", None)
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
