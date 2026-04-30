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
)


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

    # compile
    parser_compile = subparsers.add_parser("compile", help="Compile problem description to QUBO matrix (via qubify)")
    parser_compile.add_argument("--preset", choices=["tsp", "maxcut", "knapsack"], help="qubify preset to use")
    parser_compile.add_argument("--data", help="JSON data for the preset")
    parser_compile.add_argument("--dsl", help="qubify DSL problem description as JSON")

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
            if args.tsp:
                result = compile_and_solve(
                    preset="tsp", data=args.tsp,
                    use_cim=args.cim, task_name=args.task_name,
                )
            elif args.maxcut:
                result = compile_and_solve(
                    preset="maxcut", data=args.maxcut,
                    use_cim=args.cim, task_name=args.task_name,
                )
            elif args.knapsack:
                result = compile_and_solve(
                    preset="knapsack", data=args.knapsack,
                    use_cim=args.cim, task_name=args.task_name,
                )
            elif args.dsl:
                result = compile_and_solve(
                    dsl=args.dsl,
                    use_cim=args.cim, task_name=args.task_name,
                )
            elif args.qubo:
                result = solve_qubo(args.qubo, use_cim=args.cim, task_name=args.task_name)
            elif args.ising:
                result = solve_ising(args.ising, use_cim=args.cim, task_name=args.task_name)
            else:
                print("Error: provide --tsp, --maxcut, --knapsack, --dsl, --qubo, or --ising", file=sys.stderr)
                parser_solve.print_help()
                sys.exit(1)
        elif args.command == "compile":
            result = compile_problem(preset=args.preset, data=args.data, dsl=args.dsl)
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
