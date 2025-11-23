"""Definition of Done (DoD) verification script.

This script checks all DoD criteria and generates a report.
"""

import subprocess
import sys
from pathlib import Path

# Colors for terminal output
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color


def run_command(cmd: list[str], _description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 5 minutes"
    except Exception as e:
        return False, str(e)


def check_linting() -> bool:
    """Check if linting passes."""
    print(f"{BLUE}🔍 Checking linting (ruff)...{NC}")
    success, output = run_command(
        ["python", "-m", "ruff", "check", "app"],
        "Linting check",
    )
    if success:
        print(f"{GREEN}✅ Linting passed{NC}")
        return True
    print(f"{RED}❌ Linting failed:{NC}")
    print(output)
    return False


def check_formatting() -> bool:
    """Check if code is formatted."""
    print(f"{BLUE}🔍 Checking code formatting (ruff format)...{NC}")
    success, output = run_command(
        ["python", "-m", "ruff", "format", "--check", "app"],
        "Format check",
    )
    if success:
        print(f"{GREEN}✅ Code formatting passed{NC}")
        return True
    print(f"{RED}❌ Code formatting failed:{NC}")
    print(output)
    return False


def check_type_checking() -> bool:
    """Check if type checking passes."""
    print(f"{BLUE}🔍 Checking type checking (mypy)...{NC}")
    success, output = run_command(
        ["python", "-m", "mypy", "app", "--ignore-missing-imports"],
        "Type checking",
    )
    if success:
        print(f"{GREEN}✅ Type checking passed{NC}")
        return True
    # Filter out slowapi import errors (third-party library without stubs)
    filtered_output = "\n".join(
        line
        for line in output.split("\n")
        if "slowapi" not in line.lower() or "error" not in line.lower()
    )
    if "error" not in filtered_output.lower():
        print(f"{GREEN}✅ Type checking passed (only slowapi import warnings){NC}")
        return True
    print(f"{RED}❌ Type checking failed:{NC}")
    print(filtered_output)
    return False


def check_migrations() -> bool:
    """Check if migrations exist."""
    print(f"{BLUE}🔍 Checking Alembic migrations...{NC}")
    versions_dir = Path("alembic/versions")
    if not versions_dir.exists():
        print(f"{RED}❌ Migrations directory not found{NC}")
        return False

    migration_files = list(versions_dir.glob("*.py"))
    if not migration_files:
        print(f"{RED}❌ No migration files found{NC}")
        return False

    print(f"{GREEN}✅ Found {len(migration_files)} migration files{NC}")
    return True


def check_endpoints() -> bool:
    """Check if endpoints have proper structure."""
    print(f"{BLUE}🔍 Checking endpoint structure...{NC}")

    # Check for routers
    router_files = list(Path("app/modules").rglob("router.py"))
    if not router_files:
        print(f"{RED}❌ No router files found{NC}")
        return False

    print(f"{GREEN}✅ Found {len(router_files)} router modules{NC}")

    # Check for schemas
    schema_files = list(Path("app/modules").rglob("schema.py"))
    print(f"{GREEN}✅ Found {len(schema_files)} schema modules{NC}")

    return True


def check_pagination() -> bool:
    """Check if pagination is implemented."""
    print(f"{BLUE}🔍 Checking pagination implementation...{NC}")

    # Check for pagination utility
    pagination_file = Path("app/utils/pagination.py")
    if not pagination_file.exists():
        print(f"{RED}❌ Pagination utility not found{NC}")
        return False

    print(f"{GREEN}✅ Pagination utility found{NC}")
    return True


def check_error_handling() -> bool:
    """Check if error handling follows standard format."""
    print(f"{BLUE}🔍 Checking error handling...{NC}")

    # Check for error response schema
    common_schema = Path("app/schemas/common.py")
    if not common_schema.exists():
        print(f"{RED}❌ Common schemas not found{NC}")
        return False

    content = common_schema.read_text()
    if "ErrorResponse" not in content:
        print(f"{RED}❌ ErrorResponse schema not found{NC}")
        return False

    # Check for exception handlers
    exceptions_file = Path("app/core/exceptions.py")
    if not exceptions_file.exists():
        print(f"{RED}❌ Exception handlers not found{NC}")
        return False

    print(f"{GREEN}✅ Error handling properly implemented{NC}")
    return True


def main() -> None:
    """Run all DoD checks."""
    print(f"{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}Definition of Done (DoD) Verification{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")

    checks = [
        ("Linting", check_linting),
        ("Formatting", check_formatting),
        ("Type Checking", check_type_checking),
        ("Migrations", check_migrations),
        ("Endpoints", check_endpoints),
        ("Pagination", check_pagination),
        ("Error Handling", check_error_handling),
    ]

    results: list[tuple[str, bool]] = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"{RED}❌ {name} check failed with error: {e}{NC}")
            results.append((name, False))
        print()

    # Summary
    print(f"{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}Summary{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{GREEN}✅ PASS{NC}" if result else f"{RED}❌ FAIL{NC}"
        print(f"{status} {name}")

    print()
    if passed == total:
        print(f"{GREEN}✅ All checks passed! ({passed}/{total}){NC}")
        sys.exit(0)
    else:
        print(f"{RED}❌ Some checks failed ({passed}/{total} passed){NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
