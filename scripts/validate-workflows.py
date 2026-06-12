#!/usr/bin/env python3
"""
GitHub Actions Workflow Validator
Validates all GitHub Actions workflows in the repository
"""

import yaml
import glob
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")

def validate_workflow(filepath: Path) -> tuple:
    """Validate a single workflow file."""
    errors = []
    warnings = []
    
    # Read raw content to check for 'on' key properly
    raw_content = filepath.read_text()
    
    # Check for 'on' key in raw YAML (YAML parses 'on' as boolean True)
    if "on:" not in raw_content and "on :" not in raw_content and "on =" not in raw_content:
        errors.append("Missing required trigger 'on' (YAML parses 'on' as boolean)")
    
    try:
        with open(filepath) as f:
            workflow = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [f"YAML syntax error: {e}"], []
    
    if not workflow:
        return False, ["Empty workflow file"], []
    
    # Check required top-level keys
    for key in ["name", "jobs"]:
        if key not in workflow:
            errors.append(f"Missing required key: {key}")
    
    # Check name
    if "name" in workflow and not workflow["name"]:
        errors.append("Workflow name is empty")
    
    # Check triggers - already checked above
    
    # Check jobs
    if "jobs" in workflow:
        for job_name, job in workflow["jobs"].items():
            # Check runs-on
            if "runs-on" not in job:
                errors.append(f"Job '{job_name}' missing 'runs-on'")
            
            # Check steps
            if "steps" not in job:
                errors.append(f"Job '{job_name}' missing 'steps'")
            else:
                has_checkout = False
                for step in job.get("steps", []):
                    if isinstance(step, dict) and "uses" in step:
                        if "actions/checkout" in step["uses"]:
                            has_checkout = True
                
                if not has_checkout:
                    warnings.append(f"Job '{job_name}' may be missing checkout step")
            
            # Check permissions
            if "permissions" not in job:
                warnings.append(f"Job '{job_name}' missing explicit permissions")
    
    return len(errors) == 0, errors, warnings

def main():
    workflow_files = list(WORKFLOW_DIR.glob("*.yml")) + list(WORKFLOW_DIR.glob("*.yaml"))
    
    if not workflow_files:
        print("No workflow files found")
        sys.exit(1)
    
    all_valid = True
    total_errors = 0
    total_warnings = 0
    
    print("=" * 60)
    print("GitHub Actions Workflow Validation")
    print("=" * 60)
    
    for filepath in sorted(workflow_files):
        valid, errors, warnings = validate_workflow(filepath)
        
        status = "✓ PASS" if valid else "✗ FAIL"
        print(f"\n{status} {filepath.name}")
        
        for error in errors:
            print(f"  ✗ ERROR: {error}")
            total_errors += 1
        
        for warning in warnings:
            print(f"  ⚠ WARN:  {warning}")
            total_warnings += 1
        
        if not valid:
            all_valid = False
    
    print("\n" + "=" * 60)
    print(f"Summary: {total_errors} errors, {total_warnings} warnings")
    
    if not all_valid or total_warnings > 0:
        print("✗ Validation FAILED (errors or warnings)")
        sys.exit(1)
    else:
        print("✓ All workflows valid")
        sys.exit(0)

if __name__ == "__main__":
    main()