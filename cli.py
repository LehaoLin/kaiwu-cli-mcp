#!/usr/bin/env python3
"""
kaiwu-cli — Command-line interface for Kaiwu SDK Docker toolchain.
Usage:
  kaiwu-cli build                        Build the Docker image
  kaiwu-cli license init                 Generate license from user_config.yaml
  kaiwu-cli license init --user-id U --sdk-code C   Generate license with given credentials
  kaiwu-cli license check                Check license status
  kaiwu-cli run <script.py>              Run a Python script anywhere on the host inside Docker
  kaiwu-cli solve --qubo '<json>'        Solve a raw QUBO problem
  kaiwu-cli solve --ising '<json>'       Solve a raw Ising problem
  kaiwu-cli solve --tsp '<distances>'    Solve TSP (auto-compiled via qubify)
  kaiwu-cli solve --maxcut '<adjacency>' Solve Max-Cut (auto-compiled via qubify)
  kaiwu-cli solve --knapsack '<json>'    Solve Knapsack (auto-compiled via qubify)
  kaiwu-cli solve --dsl '<json>'         Solve from qubify DSL description
  kaiwu-cli compile --preset tsp --data '<json>'   Compile problem → QUBO matrix
  kaiwu-cli convert qubo-to-ising '<json>'         Convert QUBO matrix → Ising matrix
  kaiwu-cli convert ising-to-qubo '<json>'         Convert Ising matrix → QUBO matrix
  kaiwu-cli status                       Show container status
"""

import argparse
import json
import sys

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
    convert_qubo_to_ising,
    convert_ising_to_qubo,
)


def _add_sa_args(parser):
    """Add SA optimizer parameters to a parser."""
    parser.add_argument("--sa-temp", type=float, help="SA initial temperature (default: 100)")
    parser.add_argument("--sa-alpha", type=float, help="SA cooling rate (default: 0.99)")
    parser.add_argument("--sa-cutoff", type=float, help="SA cutoff temperature (default: 0.001)")
    parser.add_argument("--sa-iters", type=int, help="SA iterations per temperature (default: 10)")
    parser.add_argument("--sa-size", type=int, help="SA solution count limit (default: 100)")
    parser.add_argument("--sa-procs", type=int, help="SA parallel processes, -1 for all cores (default: 1)")


def _extract_sa_params(args) -> dict:
    """Extract non-None SA params from parsed args."""
    mapping = {
        "sa_temp": "initial_temperature",
        "sa_alpha": "alpha",
        "sa_cutoff": "cutoff_temperature",
        "sa_iters": "iterations_per_t",
        "sa_size": "size_limit",
        "sa_procs": "process_num",
    }
    return {dst: getattr(args, src) for src, dst in mapping.items() if getattr(args, src) is not None}


def _add_cim_args(parser):
    """Add CIM optimizer parameters to a parser."""
    parser.add_argument("--cim-interval", type=int, help="CIM polling interval in minutes (default: 1)")
    parser.add_argument("--cim-project", type=str, help="CIM project number")
    parser.add_argument("--cim-task-mode", choices=["quota", "sample"], help="CIM task mode (default: quota)")
    parser.add_argument("--cim-samples", type=int, help="CIM sample count for sample mode (default: 10, max: 2000)")


def _extract_cim_params(args) -> dict:
    """Extract non-None CIM params from parsed args."""
    mapping = {
        "cim_interval": "interval",
        "cim_project": "project_no",
        "cim_task_mode": "task_mode",
        "cim_samples": "sample_number",
    }
    return {dst: getattr(args, src) for src, dst in mapping.items() if getattr(args, src) is not None}


def main():
    parser = argparse.ArgumentParser(
        prog="kaiwu-cli",
        description="Kaiwu SDK CLI tool — 玻色量子CIM相干光量子计算机 Python SDK wrapper",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # build
    parser_build = subparsers.add_parser("build", help="Build the Kaiwu SDK Docker image")

    # license
    parser_license = subparsers.add_parser("license", help="License management")
    license_sub = parser_license.add_subparsers(dest="license_action")

    license_init = license_sub.add_parser("init", help="Generate Kaiwu SDK license")
    license_init.add_argument("--user-id", help="User ID (default from user_config.yaml)")
    license_init.add_argument("--sdk-code", help="SDK authorization code (default from user_config.yaml)")

    license_check = license_sub.add_parser("check", help="Check license status")

    # run
    parser_run = subparsers.add_parser("run", help="Run a Python script in Docker (from anywhere on host)")
    parser_run.add_argument("script", help="Path to Python script (absolute or relative to user_script/)")

    # solve
    parser_solve = subparsers.add_parser("solve", help="Solve optimization problems (raw matrix or auto-compiled via qubify)")
    parser_solve.add_argument("--qubo", help="Raw QUBO matrix as JSON string")
    parser_solve.add_argument("--ising", help="Raw Ising matrix as JSON string")
    parser_solve.add_argument("--tsp", help="TSP distance matrix as JSON (auto-compiled via qubify)")
    parser_solve.add_argument("--maxcut", help="Max-Cut adjacency matrix as JSON (auto-compiled via qubify)")
    parser_solve.add_argument("--knapsack", help="Knapsack data as JSON {values, weights, capacity} (auto-compiled via qubify)")
    parser_solve.add_argument("--dsl", help="qubify DSL problem description as JSON (auto-compiled via qubify)")
    parser_solve.add_argument("--cim", action="store_true", help="Use CIM quantum optimizer (default: simulated annealing)")
    parser_solve.add_argument("--task-name", default="kaiwu-task", help="Task name for CIM submission")
    _add_sa_args(parser_solve)
    _add_cim_args(parser_solve)

    # compile
    parser_compile = subparsers.add_parser("compile", help="Compile problem description to QUBO matrix (via qubify)")
    parser_compile.add_argument("--preset", choices=["tsp", "maxcut", "knapsack"], help="qubify preset to use")
    parser_compile.add_argument("--data", help="JSON data for the preset")
    parser_compile.add_argument("--dsl", help="qubify DSL problem description as JSON")

    # convert
    parser_convert = subparsers.add_parser("convert", help="Convert between QUBO and Ising matrix formats")
    convert_sub = parser_convert.add_subparsers(dest="convert_action")

    convert_q2i = convert_sub.add_parser("qubo-to-ising", help="Convert QUBO matrix to Ising matrix")
    convert_q2i.add_argument("matrix", help="QUBO matrix as JSON string")

    convert_i2q = convert_sub.add_parser("ising-to-qubo", help="Convert Ising matrix to QUBO matrix")
    convert_i2q.add_argument("matrix", help="Ising matrix as JSON string")

    # status
    parser_status = subparsers.add_parser("status", help="Show container status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "build":
            result = build_image()
        elif args.command == "license":
            if args.license_action == "init":
                result = init_license(user_id=args.user_id, sdk_code=args.sdk_code)
            elif args.license_action == "check":
                result = check_license()
            else:
                parser_license.print_help()
                sys.exit(1)
        elif args.command == "run":
            result = run_script(args.script)
        elif args.command == "solve":
            sa_params = _extract_sa_params(args)
            cim_params = _extract_cim_params(args)
            if args.tsp:
                result = compile_and_solve(
                    preset="tsp", data=args.tsp,
                    use_cim=args.cim, task_name=args.task_name,
                    sa_params=sa_params, cim_params=cim_params,
                )
            elif args.maxcut:
                result = compile_and_solve(
                    preset="maxcut", data=args.maxcut,
                    use_cim=args.cim, task_name=args.task_name,
                    sa_params=sa_params, cim_params=cim_params,
                )
            elif args.knapsack:
                result = compile_and_solve(
                    preset="knapsack", data=args.knapsack,
                    use_cim=args.cim, task_name=args.task_name,
                    sa_params=sa_params, cim_params=cim_params,
                )
            elif args.dsl:
                result = compile_and_solve(
                    dsl=args.dsl,
                    use_cim=args.cim, task_name=args.task_name,
                    sa_params=sa_params, cim_params=cim_params,
                )
            elif args.qubo:
                result = solve_qubo(args.qubo, use_cim=args.cim, task_name=args.task_name,
                                    sa_params=sa_params, cim_params=cim_params)
            elif args.ising:
                result = solve_ising(args.ising, use_cim=args.cim, task_name=args.task_name,
                                     sa_params=sa_params, cim_params=cim_params)
            else:
                print("Error: provide --tsp, --maxcut, --knapsack, --dsl, --qubo, or --ising", file=sys.stderr)
                parser_solve.print_help()
                sys.exit(1)
        elif args.command == "compile":
            result = compile_problem(preset=args.preset, data=args.data, dsl=args.dsl)
        elif args.command == "convert":
            if args.convert_action == "qubo-to-ising":
                result = convert_qubo_to_ising(args.matrix)
            elif args.convert_action == "ising-to-qubo":
                result = convert_ising_to_qubo(args.matrix)
            else:
                parser_convert.print_help()
                sys.exit(1)
        elif args.command == "status":
            result = container_status()
        else:
            parser.print_help()
            sys.exit(1)

        # Output
        if result.get("success"):
            if result.get("output"):
                print(result["output"])
            if result.get("message"):
                print(result["message"])
        else:
            print(f"Error: {result.get('message', 'Unknown error')}", file=sys.stderr)
            if result.get("output"):
                print(result["output"], file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
