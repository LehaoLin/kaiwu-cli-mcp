#!/usr/bin/env python3
"""
kaiwu-cli — Command-line interface for Kaiwu SDK Docker toolchain.
Usage:
  kaiwu-cli build                        Build the Docker image
  kaiwu-cli license init                 Generate license from user_config.yaml
  kaiwu-cli license init --user-id U --sdk-code C   Generate license with given credentials
  kaiwu-cli license check                Check license status
  kaiwu-cli run <script.py>              Run a script in user_script/ inside Docker
  kaiwu-cli solve --qubo '<json>'        Solve a QUBO problem
  kaiwu-cli solve --ising '<json>'       Solve an Ising problem
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
    parser_run = subparsers.add_parser("run", help="Run a Python script in Docker")
    parser_run.add_argument("script", help="Path to script (relative to user_script/)")

    # solve
    parser_solve = subparsers.add_parser("solve", help="Solve a QUBO or Ising problem")
    parser_solve.add_argument("--qubo", help="QUBO matrix as JSON string")
    parser_solve.add_argument("--ising", help="Ising matrix as JSON string")
    parser_solve.add_argument("--cim", action="store_true", help="Use CIM quantum optimizer (default: simulated annealing)")
    parser_solve.add_argument("--task-name", default="kaiwu-task", help="Task name for CIM submission")

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
            if args.qubo:
                result = solve_qubo(args.qubo, use_cim=args.cim, task_name=args.task_name)
            elif args.ising:
                result = solve_ising(args.ising, use_cim=args.cim, task_name=args.task_name)
            else:
                print("Error: --qubo or --ising required", file=sys.stderr)
                parser_solve.print_help()
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
