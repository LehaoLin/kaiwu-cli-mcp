"""
Core business logic for kaiwu-cli-mcp.
No CLI args, no MCP decorators — pure Python functions.
All Docker orchestration happens here.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from config import load_config, PROJECT_ROOT, USER_SCRIPT_DIR, DOCKER_COMPOSE_FILE

# Temp script directory inside user_script/ (auto-mounted to container)
_TMP_DIR = USER_SCRIPT_DIR / ".tmp"


def _run_docker_compose(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a docker compose command from the project root."""
    cmd = ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE)]
    cmd.extend(args)
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=check)


def _run_in_container(python_code: str) -> subprocess.CompletedProcess:
    """Execute Python code inside the Kaiwu SDK container via a temp script file.

    Uses file-based execution instead of `python3 -c '...'` to avoid
    command injection via string interpolation.
    """
    _TMP_DIR.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(suffix=".py", dir=_TMP_DIR)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(python_code)
        container_path = f"/user_script/.tmp/{Path(tmp_path).name}"
        return _run_docker_compose([
            "run", "--rm", "kaiwu",
            "python3", container_path,
        ])
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def build_image() -> dict:
    """Build the Kaiwu SDK Docker image."""
    try:
        result = _run_docker_compose(["build", "--no-cache"])
        return {"success": True, "message": "Docker image built successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Build failed: {e.stderr}", "output": e.stderr}


def init_license(user_id: str = None, sdk_code: str = None) -> dict:
    """Generate Kaiwu SDK license inside the Docker container."""
    config = load_config()
    uid = user_id or config.get("user_id", "")
    code = sdk_code or config.get("sdk_code", "")

    if not uid or not code:
        return {
            "success": False,
            "message": "user_id and sdk_code are required. Set them in user_config.yaml or pass as arguments.",
        }

    script = f"""import json
import kaiwu as kw
kw.license.init({json.dumps(uid)}, {json.dumps(code)})
print('License generated successfully.')
"""
    try:
        result = _run_in_container(script)
        return {"success": True, "message": "License generated successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"License generation failed: {e.stderr}", "output": e.stderr}


def check_license() -> dict:
    """Check if Kaiwu SDK license is valid."""
    script = """import kaiwu as kw
try:
    from kaiwu.license import _LICENSE_FILE
    import os
    if os.path.exists(_LICENSE_FILE):
        print('License file exists.')
    else:
        print('License file not found.')
except Exception as e:
    print(f'Error checking license: {e}')
"""
    try:
        result = _run_in_container(script)
        return {"success": True, "message": "License check completed", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"License check failed: {e.stderr}", "output": e.stderr}


def run_script(script_path: str) -> dict:
    """Run a user Python script inside the Kaiwu SDK Docker container.

    Supports two modes:
    1. Scripts under user_script/ — directly accessible (already mounted)
    2. Scripts ANYWHERE on the host — auto-mounted via temporary volume
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


def solve_qubo(
    qubo_matrix_json: str,
    use_cim: bool = False,
    task_name: str = "kaiwu-task",
    sa_params: dict = None,
    cim_params: dict = None,
) -> dict:
    """Solve a QUBO problem using Kaiwu SDK inside Docker.

    The matrix is converted to Ising via kw.conversion, precision-adjusted,
    then passed to the optimizer.
    """
    sa_params = sa_params or {}
    cim_params = cim_params or {}

    optimizer_lines = _build_optimizer_code(use_cim, task_name, sa_params, cim_params)

    script = f"""import json
import numpy as np
import kaiwu as kw

matrix = np.array(json.loads({json.dumps(qubo_matrix_json)}))

# QUBO -> Ising conversion
ising_mat, bias = kw.conversion.qubo_matrix_to_ising_matrix(matrix)
# Precision adjustment
ising_mat = kw.ising.adjust_ising_matrix_precision(ising_mat)

{optimizer_lines}

sol = opt.solve(ising_mat)
print(json.dumps({{"solution": sol.tolist() if hasattr(sol, 'tolist') else sol, "bias": float(bias)}}))
"""
    try:
        result = _run_in_container(script)
        return {"success": True, "message": "QUBO solved", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"QUBO solving failed: {e.stderr}", "output": e.stderr}


def solve_ising(
    ising_matrix_json: str,
    use_cim: bool = False,
    task_name: str = "kaiwu-task",
    sa_params: dict = None,
    cim_params: dict = None,
) -> dict:
    """Solve an Ising problem using Kaiwu SDK inside Docker.

    The matrix is precision-adjusted, then passed to the optimizer.
    """
    sa_params = sa_params or {}
    cim_params = cim_params or {}

    optimizer_lines = _build_optimizer_code(use_cim, task_name, sa_params, cim_params)

    script = f"""import json
import numpy as np
import kaiwu as kw

matrix = np.array(json.loads({json.dumps(ising_matrix_json)}))
# Precision adjustment
matrix = kw.ising.adjust_ising_matrix_precision(matrix)

{optimizer_lines}

sol = opt.solve(matrix)
print(json.dumps({{"solution": sol.tolist() if hasattr(sol, 'tolist') else sol}}))
"""
    try:
        result = _run_in_container(script)
        return {"success": True, "message": "Ising solved", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Ising solving failed: {e.stderr}", "output": e.stderr}


def _build_optimizer_code(
    use_cim: bool,
    task_name: str,
    sa_params: dict,
    cim_params: dict,
) -> str:
    """Generate Python code to instantiate the optimizer."""
    if use_cim:
        kwargs = {"task_name": task_name, "wait": True}
        for key in ("interval", "project_no", "task_mode", "sample_number"):
            if key in cim_params:
                kwargs[key] = cim_params[key]
        return f"opt = kw.cim.CIMOptimizer(**{json.dumps(kwargs)})"
    else:
        kwargs = {}
        for key in ("initial_temperature", "alpha", "cutoff_temperature",
                     "iterations_per_t", "size_limit", "process_num"):
            if key in sa_params:
                kwargs[key] = sa_params[key]
        return f"opt = kw.classical.SimulatedAnnealingOptimizer(**{json.dumps(kwargs)})"


def container_status() -> dict:
    """Check Docker container status."""
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
    sa_params: dict = None,
    cim_params: dict = None,
) -> dict:
    """Compile a problem description to QUBO, then solve with Kaiwu SDK."""
    import numpy as np

    try:
        from converters import tsp_to_qubo, maxcut_to_qubo, knapsack_to_qubo, dsl_to_qubo
    except ImportError:
        return {
            "success": False,
            "message": "qubify is not installed. Run: pip install qubify",
        }

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

    matrix_json = json.dumps(qubo.tolist())
    result = solve_qubo(matrix_json, use_cim=use_cim, task_name=task_name,
                        sa_params=sa_params, cim_params=cim_params)

    if result.get("success") and var_map:
        result["var_map"] = var_map
        result["n_vars"] = qubo.shape[0]

    return result


def compile_problem(
    preset: str = None,
    data=None,
    dsl: dict = None,
) -> dict:
    """Compile a problem description to QUBO matrix ONLY (no solving)."""
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


def convert_qubo_to_ising(qubo_matrix_json: str) -> dict:
    """Convert QUBO matrix to Ising matrix via SDK."""
    script = f"""import json, numpy as np, kaiwu as kw
matrix = np.array(json.loads({json.dumps(qubo_matrix_json)}))
ising_mat, bias = kw.conversion.qubo_matrix_to_ising_matrix(matrix)
print(json.dumps({{"ising_matrix": ising_mat.tolist(), "bias": float(bias)}}))
"""
    try:
        result = _run_in_container(script)
        return {"success": True, "message": "QUBO converted to Ising", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Conversion failed: {e.stderr}", "output": e.stderr}


def convert_ising_to_qubo(ising_matrix_json: str) -> dict:
    """Convert Ising matrix to QUBO matrix via SDK."""
    script = f"""import json, numpy as np, kaiwu as kw
matrix = np.array(json.loads({json.dumps(ising_matrix_json)}))
qubo_mat, bias = kw.conversion.ising_matrix_to_qubo_matrix(matrix)
print(json.dumps({{"qubo_matrix": qubo_mat.tolist(), "bias": float(bias)}}))
"""
    try:
        result = _run_in_container(script)
        return {"success": True, "message": "Ising converted to QUBO", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Conversion failed: {e.stderr}", "output": e.stderr}
