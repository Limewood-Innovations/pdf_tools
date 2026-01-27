#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAML Workflow Executor.

This script executes workflows defined in YAML format, providing variable
substitution, dependency management, and error handling.

Usage:
    python run_workflow.py workflow.yaml --var input_pdf=document.pdf
    python run_workflow.py workflow.yaml --dry-run
"""

import argparse
import os
import re
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_workflow(yaml_file: Path) -> Dict[str, Any]:
    """Load workflow definition from YAML file.

    Args:
        yaml_file: Path to the YAML workflow file.

    Returns:
        Dict: Parsed workflow definition.
    """
    with open(yaml_file) as f:
        return yaml.safe_load(f)


def expand_env_vars(text: str) -> str:
    """Expand environment variables in bash-style format.

    Supports:
    - ${VAR} - direct substitution
    - ${VAR:-default} - use default if VAR is unset
    - ${VAR:+value} - use value if VAR is set

    Args:
        text: String containing environment variable references.

    Returns:
        str: String with variables expanded.
    """
    def replacer(match):
        var_expr = match.group(1)

        # ${VAR:-default}
        if ":-" in var_expr:
            var_name, default = var_expr.split(":-", 1)
            return os.getenv(var_name, default)

        # ${VAR:+value}
        if ":+" in var_expr:
            var_name, value = var_expr.split(":+", 1)
            return value if os.getenv(var_name) else ""

        # ${VAR}
        return os.getenv(var_expr, f"${{{var_expr}}}")

    pattern = r"\$\{([^}]+)\}"
    return re.sub(pattern, replacer, text)


def substitute_variables(text: str, variables: Dict[str, str]) -> str:
    """Substitute variables in text using both env vars and provided variables.

    Args:
        text: String containing variable references.
        variables: Dictionary of variable values.

    Returns:
        str: String with variables substituted.
    """
    # First expand environment variables
    text = expand_env_vars(text)

    # Then substitute workflow variables
    for key, value in variables.items():
        text = text.replace(f"${{{key}}}", str(value))

    return text


def evaluate_condition(condition: str, variables: Dict[str, str]) -> bool:
    """Evaluate a condition string.

    Args:
        condition: Condition expression to evaluate.
        variables: Dictionary of variable values.

    Returns:
        bool: Result of condition evaluation.
    """
    condition = substitute_variables(condition, variables)

    # Simple boolean evaluation
    if condition.lower() in ("true", "1", "yes"):
        return True
    if condition.lower() in ("false", "0", "no", ""):
        return False

    # If variable reference remains, it's unset
    if "${" in condition:
        return False

    return bool(condition)


def execute_workflow(
    workflow: Dict[str, Any],
    variables: Dict[str, str],
    dry_run: bool = False,
) -> bool:
    """Execute workflow steps sequentially.

    Args:
        workflow: Parsed workflow definition.
        variables: Additional variables to merge with workflow variables.
        dry_run: If ``True``, print what would be executed without running.

    Returns:
        bool: ``True`` if workflow completed successfully.
    """
    workflow_vars = workflow.get("variables", {})
    # Expand environment variables in workflow variables
    for key, value in workflow_vars.items():
        workflow_vars[key] = expand_env_vars(str(value))

    # Merge with provided variables (provided vars take precedence)
    all_vars = {**workflow_vars, **variables}

    print(f"{'='*60}")
    print(f"Workflow: {workflow['name']}")
    print(f"Description: {workflow.get('description', 'N/A')}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN MODE - No actual execution]\\n")

    # Track completed steps for dependency checking
    completed_steps = set()
    step_outputs: Dict[str, Any] = {}

    for step_idx, step in enumerate(workflow.get("steps", []), 1):
        step_name = step["name"]
        description = step.get("description", "")
        depends_on = step.get("depends_on", [])
        on_error = step.get("on_error", "stop")
        condition = step.get("condition")

        # Check dependencies
        if depends_on:
            missing_deps = set(depends_on) - completed_steps
            if missing_deps:
                print(f"[SKIP] {step_name}: Missing dependencies {missing_deps}")
                continue

        # Evaluate condition if present
        if condition and not evaluate_condition(condition, all_vars):
            print(f"[SKIP] {step_name}: Condition not met ({condition})")
            continue

        print(f"[{step_idx}] {step_name}")
        if description:
            print(f"    {description}")

        # Get script or command
        script = step.get("script", step.get("command", ""))
        script = substitute_variables(script, all_vars)

        if dry_run:
            print(f"    Script:\n{script}\n")
            completed_steps.add(step_name)
            continue

        # Execute the script
        try:
            # Create execution context with step outputs
            exec_globals = {**step_outputs}

            exec(script, exec_globals)

            # Capture outputs
            for output_var in step.get("outputs", []):
                if output_var in exec_globals:
                    step_outputs[output_var] = exec_globals[output_var]

            print(f"    ✓ Completed\n")
            completed_steps.add(step_name)

        except Exception as e:
            print(f"    ✗ Failed: {e}\n", file=sys.stderr)
            if on_error == "stop":
                print("Workflow stopped due to error.", file=sys.stderr)
                return False
            # on_error == "continue": keep going

    # Run post-workflow steps
    if not dry_run:
        for post_step in workflow.get("post_workflow", []):
            post_name = post_step.get("name", "Post-workflow")
            post_script = substitute_variables(post_step.get("script", ""), all_vars)

            print(f"[POST] {post_name}")
            try:
                exec(post_script, step_outputs)
            except Exception as e:
                print(f"       Warning: {e}", file=sys.stderr)

    print(f"\n{'='*60}")
    print(f"Workflow completed: {len(completed_steps)}/{len(workflow.get('steps', []))} steps")
    print(f"{'='*60}")

    return True


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Execute YAML-based workflows for PDF processing"
    )
    parser.add_argument(
        "workflow_file",
        type=Path,
        help="Path to YAML workflow file"
    )
    parser.add_argument(
        "--var",
        action="append",
        dest="variables",
        metavar="KEY=VALUE",
        help="Set workflow variable (can be used multiple times)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running"
    )

    args = parser.parse_args()

    if not args.workflow_file.exists():
        print(f"Error: Workflow file not found: {args.workflow_file}", file=sys.stderr)
        return 1

    # Parse variables
    variables = {}
    if args.variables:
        for var_assignment in args.variables:
            if "=" not in var_assignment:
                print(f"Error: Invalid variable format: {var_assignment}", file=sys.stderr)
                print("Expected format: KEY=VALUE", file=sys.stderr)
                return 1
            key, value = var_assignment.split("=", 1)
            variables[key.strip()] = value.strip()

    try:
        workflow = load_workflow(args.workflow_file)
        success = execute_workflow(workflow, variables, dry_run=args.dry_run)
        return 0 if success else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
