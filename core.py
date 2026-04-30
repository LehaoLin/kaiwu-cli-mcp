"""
Core business logic for kaiwu-cli-mcp.
No CLI args, no MCP decorators — pure Python functions.
All Docker orchestration happens here.
"""

import subprocess
from pathlib import Path
from config import load_config, PROJECT_ROOT, USER_SCRIPT_DIR, DOCKER_COMPOSE_FILE


def _run_docker_compose(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a docker compose command from the project root."""
    cmd = ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE)]
    cmd.extend(args)
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=check)


def _run_in_container(python_code: str) -> subprocess.CompletedProcess:
    """Execute Python code inside the Kaiwu SDK container."""
    return _run_docker_compose([
        "run", "--rm", "kaiwu",
        "python3", "-c", python_code,
    ])


def build_image() -> dict:
    """Build the Kaiwu SDK Docker image.

    Returns:
        dict with success status and message.
    """
    try:
        result = _run_docker_compose(["build", "--no-cache"])
        return {"success": True, "message": "Docker image built successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Build failed: {e.stderr}", "output": e.stderr}


def init_license(user_id: str = None, sdk_code: str = None) -> dict:
    """Generate Kaiwu SDK license inside the Docker container.

    Args:
        user_id: 用户ID (from config if not provided)
        sdk_code: SDK授权码 (from config if not provided)

    Returns:
        dict with success status and message.
    """
    config = load_config()
    uid = user_id or config.get("user_id", "")
    code = sdk_code or config.get("sdk_code", "")

    if not uid or not code:
        return {
            "success": False,
            "message": "user_id and sdk_code are required. Set them in user_config.yaml or pass as arguments.",
        }

    license_code = (
        f"import kaiwu as kw; "
        f"kw.license.init('{uid}', '{code}'); "
        f"print('License generated successfully.')"
    )

    try:
        result = _run_in_container(license_code)
        return {"success": True, "message": "License generated successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"License generation failed: {e.stderr}", "output": e.stderr}


def check_license() -> dict:
    """Check if Kaiwu SDK license is valid.

    Returns:
        dict with license status.
    """
    try:
        result = _run_in_container(
            "import kaiwu as kw; "
            "try:\n"
            "    from kaiwu.license import _LICENSE_FILE\n"
            "    import os\n"
            "    if os.path.exists(_LICENSE_FILE):\n"
            "        print('License file exists.')\n"
            "    else:\n"
            "        print('License file not found.')\n"
            "except Exception as e:\n"
            "    print(f'Error checking license: {e}')"
        )
        return {"success": True, "message": "License check completed", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"License check failed: {e.stderr}", "output": e.stderr}


def run_script(script_path: str) -> dict:
    """Run a user Python script inside the Kaiwu SDK Docker container.

    Supports two modes:
    1. Scripts under user_script/ — directly accessible (already mounted)
    2. Scripts ANYWHERE on the host — auto-mounted via temporary volume

    Args:
        script_path: Path to the Python script.
                     Relative paths resolve under user_script/ first.
                     Absolute paths work from anywhere on the host.

    Returns:
        dict with execution result.
    """
    script = Path(script_path).resolve()

    # If relative, first check under user_script/
    if not Path(script_path).is_absolute():
        candidate = (USER_SCRIPT_DIR / script_path).resolve()
        if candidate.exists():
            script = candidate

    if not script.exists():
        return {"success": False, "message": f"Script not found: {script}"}

    # Case 1: Script is under user_script/ — already mounted at /user_script
    try:
        rel = script.relative_to(USER_SCRIPT_DIR)
        container_path = f"/user_script/{rel}"
        result = _run_docker_compose([
            "run", "--rm", "kaiwu",
            "python3", str(container_path),
        ])
        return {"success": True, "message": f"Script executed: {script}", "output": result.stdout}
    except ValueError:
        pass  # Not under user_script/, use volume mount
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": "Script execution failed", "output": e.stdout + "\n" + e.stderr}

    # Case 2: Script is ANYWHERE on host — mount its parent dir as /mnt/script
    host_dir = str(script.parent)
    container_path = f"/mnt/script/{script.name}"

    try:
        result = _run_docker_compose([
            "run", "--rm",
            "-v", f"{host_dir}:/mnt/script:ro",
            "kaiwu",
            "python3", container_path,
        ])
        return {"success": True, "message": f"Script executed: {script}", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": "Script execution failed", "output": e.stdout + "\n" + e.stderr}


def solve_qubo(qubo_matrix_json: str, use_cim: bool = False, task_name: str = "kaiwu-task") -> dict:
    """Solve a QUBO problem using Kaiwu SDK inside Docker.

    Args:
        qubo_matrix_json: JSON-encoded 2D array representing the QUBO matrix
        use_cim: If True, use CIM quantum optimizer (requires cloud access);
                 if False, use SimulatedAnnealingOptimizer
        task_name: Task name for CIM submission

    Returns:
        dict with solution result.
    """
    solver_code = (
        f"import json, numpy as np, kaiwu as kw; "
        f"matrix = np.array(json.loads('{qubo_matrix_json}')); "
    )
    if use_cim:
        solver_code += (
            f"opt = kw.cim.CIMOptimizer(task_name='{task_name}', wait=True); "
        )
    else:
        solver_code += (
            f"opt = kw.classical.SimulatedAnnealingOptimizer(); "
        )
    solver_code += (
        f"sol = opt.solve(matrix); "
        f"print(json.dumps({{'solution': sol.tolist() if hasattr(sol, 'tolist') else sol}}))"
    )

    try:
        result = _run_in_container(solver_code)
        return {"success": True, "message": "QUBO solved", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"QUBO solving failed: {e.stderr}", "output": e.stderr}


def solve_ising(ising_matrix_json: str, use_cim: bool = False, task_name: str = "kaiwu-task") -> dict:
    """Solve an Ising problem using Kaiwu SDK inside Docker.

    Args:
        ising_matrix_json: JSON-encoded 2D array representing the Ising matrix
        use_cim: If True, use CIM quantum optimizer (requires cloud access)
        task_name: Task name for CIM submission

    Returns:
        dict with solution result.
    """
    solver_code = (
        f"import json, numpy as np, kaiwu as kw; "
        f"matrix = np.array(json.loads('{ising_matrix_json}')); "
    )
    if use_cim:
        solver_code += (
            f"opt = kw.cim.CIMOptimizer(task_name='{task_name}', wait=True); "
        )
    else:
        solver_code += (
            f"opt = kw.classical.SimulatedAnnealingOptimizer(); "
        )
    solver_code += (
        f"sol = opt.solve(matrix); "
        f"print(json.dumps({{'solution': sol.tolist() if hasattr(sol, 'tolist') else sol}}))"
    )

    try:
        result = _run_in_container(solver_code)
        return {"success": True, "message": "Ising solved", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Ising solving failed: {e.stderr}", "output": e.stderr}


def container_status() -> dict:
    """Check Docker container status.

    Returns:
        dict with container state info.
    """
    try:
        result = _run_docker_compose(["ps"])
        return {"success": True, "message": "Container status retrieved", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Status check failed: {e.stderr}", "output": e.stderr}


# ═══════════════════════════════════════════════════════════════════
# qubify integration — problem → compile → solve in one shot
# ═══════════════════════════════════════════════════════════════════


def compile_and_solve(
    preset: str = None,
    data=None,
    dsl: dict = None,
    use_cim: bool = False,
    task_name: str = "kaiwu-task",
) -> dict:
    """Compile a problem description to QUBO, then solve with Kaiwu SDK.

    This is the one-call pipeline: problem → qubify → QUBO matrix → kw.solve()

    Args:
        preset: One of 'tsp', 'maxcut', 'knapsack'. Uses qubify presets.
        data: JSON-ready data for the preset (distances, adjacency, etc.)
        dsl: A qubify DSL problem dict (alternative to preset+data).
        use_cim: If True, use CIM quantum optimizer.
        task_name: Task name for CIM submission.

    Returns:
        dict with solution result.
    """
    import json
    import numpy as np

    try:
        from converters import tsp_to_qubo, maxcut_to_qubo, knapsack_to_qubo, dsl_to_qubo
    except ImportError:
        return {
            "success": False,
            "message": "qubify is not installed. Run: pip install qubify",
        }

    # ── Step 1: Compile problem → QUBO matrix ─────────────────
    var_map = None
    qubo = None

    if dsl:
        problem = json.loads(dsl) if isinstance(dsl, str) else dsl
        qubo, var_map = dsl_to_qubo(problem)
    elif preset == "tsp":
        qubo, var_map = tsp_to_qubo(data)
    elif preset == "maxcut":
        qubo, var_map = maxcut_to_qubo(data)
    elif preset == "knapsack":
        qubo, var_map = knapsack_to_qubo(data)
    else:
        return {
            "success": False,
            "message": "Provide either preset ('tsp'/'maxcut'/'knapsack') + data, or a dsl dict.",
        }

    # ── Step 2: Feed matrix to Kaiwu SDK solver ────────────────
    matrix_json = json.dumps(qubo.tolist())
    result = solve_qubo(matrix_json, use_cim=use_cim, task_name=task_name)

    # Attach variable map for decoding
    if result.get("success") and var_map:
        result["var_map"] = var_map
        result["n_vars"] = qubo.shape[0]

    return result


def compile_problem(
    preset: str = None,
    data=None,
    dsl: dict = None,
) -> dict:
    """Compile a problem description to QUBO matrix ONLY (no solving).

    Args:
        preset: One of 'tsp', 'maxcut', 'knapsack'.
        data: JSON-ready data for the preset.
        dsl: A qubify DSL problem dict.

    Returns:
        dict with 'qubo_matrix' (JSON string) and 'var_map'.
    """
    import json
    import numpy as np

    try:
        from converters import tsp_to_qubo, maxcut_to_qubo, knapsack_to_qubo, dsl_to_qubo
    except ImportError:
        return {
            "success": False,
            "message": "qubify is not installed. Run: pip install qubify",
        }

    qubo = None
    var_map = None

    if dsl:
        problem = json.loads(dsl) if isinstance(dsl, str) else dsl
        qubo, var_map = dsl_to_qubo(problem)
    elif preset == "tsp":
        qubo, var_map = tsp_to_qubo(data)
    elif preset == "maxcut":
        qubo, var_map = maxcut_to_qubo(data)
    elif preset == "knapsack":
        qubo, var_map = knapsack_to_qubo(data)
    else:
        return {
            "success": False,
            "message": "Provide either preset ('tsp'/'maxcut'/'knapsack') + data, or a dsl dict.",
        }

    return {
        "success": True,
        "message": f"Problem compiled ({qubo.shape[0]} variables)",
        "qubo_matrix": json.dumps(qubo.tolist()),
        "var_map": var_map,
    }
