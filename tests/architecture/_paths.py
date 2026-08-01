"""Shared paths for the architecture-enforcement tests.

These tests are the machine gate for what import-linter cannot express (source-level
cost/nondeterminism) and for the structural test-doctrine. They pass trivially on the
empty tree and tighten automatically as each ring of code lands.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
SLR = BACKEND / "slr"

DOMAIN = SLR / "domain"
PORTS = SLR / "ports"
ADAPTERS = SLR / "adapters"
USECASES = SLR / "usecases"

TESTS = REPO_ROOT / "tests"
UNIT_TESTS = TESTS / "unit"
PORT_CONFORMANCE = TESTS / "integration" / "ports"
USECASE_TESTS = TESTS / "integration" / "usecases"


def module_files(package_dir: Path) -> list[Path]:
    """Public `.py` modules in a layer, skipping dunders and private `_`-prefixed files."""
    if not package_dir.is_dir():
        return []
    return sorted(
        p
        for p in package_dir.glob("*.py")
        if not p.name.startswith("_")
    )
