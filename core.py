"""
Core business logic for kaiwu-cli-mcp.
No CLI args, no MCP decorators — pure Python functions.
All Docker orchestration happens here.
"""

import subprocess
import sys
from pathlib import Path
from config import load_config, PROJECT_ROOT, USER_SCRIPT_DIR, DOCKER_COMPOSE_FILE


def _run_docker_compose(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a docker compose command from the project root."""
    cmd = ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE)]
    cmd.extend(args)
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=check)


def _run_in_container(python_code: str) -> subprocess.CompletedProcess:
    """Execute Python code inside the Kaiwu SDK container."""
    config = load_config()
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

    The script should be located under user_script/ (mapped to /user_script in container).

    Args:
        script_path: Relative path to the script under user_script/ (e.g., 'tsp_solver.py')
                     Or absolute path to any script on the host.

    Returns:
        dict with execution result.
    """
    script = Path(script_path)

    # If relative, assume it's under user_script/
    if not script.is_absolute():
        script = USER_SCRIPT_DIR / script_path

    if not script.exists():
        return {"success": False, "message": f"Script not found: {script}"}

    # Convert to path inside container (/user_script/...)
    try:
        rel_path = script.relative_to(USER_SCRIPT_DIR)
        container_path = f"/user_script/{rel_path}"
    except ValueError:
        # Script is outside user_script/, mount it directly
        return {
            "success": False,
            "message": f"Script must be under {USER_SCRIPT_DIR}. "
                       f"Please place your script in the user_script/ directory.",
        }

    try:
        result = _run_in_container(
            f"import subprocess, sys; "
            f"sys.exit(subprocess.run([sys.executable, '{container_path}']).returncode)"
        )
        return {"success": True, "message": "Script executed successfully", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Script execution failed", "output": e.stdout + "\n" + e.stderr}


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
