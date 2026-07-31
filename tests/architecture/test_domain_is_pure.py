"""Source scan: the inner layers (domain + ports) carry no cost and no nondeterminism.

import-linter stops framework *imports*; this stops the subtler leaks an import graph
can't see — wall-clock reads, randomness, env, filesystem, sockets. Those must arrive
through an L1 port. Parsing via `ast` means comments and string literals are naturally
excluded: *naming* `datetime.now` in a docstring is not a violation.
"""

from __future__ import annotations

import ast

import pytest
from tests.architecture._paths import DOMAIN, PORTS

# Module imports that have no place in a pure core at all.
BANNED_IMPORT_ROOTS = frozenset(
    {
        "random",
        "secrets",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "asyncio",
        "sqlite3",
        "sqlalchemy",
        "fastapi",
        "pydantic",
    }
)

# Attribute-call idioms that smuggle in the clock, rng, env, or the filesystem.
BANNED_ATTR_SUFFIXES = (
    "datetime.now",
    "datetime.utcnow",
    "date.today",
    "time.time",
    "time.monotonic",
    "time.localtime",
    "time.sleep",
    "os.environ",
    "os.getenv",
    "os.urandom",
    "random.random",
    "random.randint",
    "random.choice",
    "secrets.token_hex",
    "secrets.choice",
)

# Bare builtins that touch the outside world.
BANNED_CALL_NAMES = frozenset({"open"})


def _dotted(node: ast.AST) -> str | None:
    """Reconstruct a dotted name from a Name/Attribute chain, else None."""
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _violations(path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in BANNED_IMPORT_ROOTS:
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in BANNED_IMPORT_ROOTS:
                found.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Attribute):
            dotted = _dotted(node)
            if dotted and any(dotted.endswith(s) for s in BANNED_ATTR_SUFFIXES):
                found.append(dotted)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in BANNED_CALL_NAMES
        ):
            found.append(f"{node.func.id}(...)")
    return found


def _pure_layer_files():
    files = []
    for layer in (DOMAIN, PORTS):
        files.extend(p for p in layer.rglob("*.py") if p.name != "__init__.py")
    return files


@pytest.mark.arch
def test_domain_and_ports_have_no_cost_or_nondeterminism():
    offenders: dict[str, list[str]] = {}
    for path in _pure_layer_files():
        v = _violations(path)
        if v:
            offenders[str(path)] = v
    assert not offenders, (
        "Inner layers must be pure — cost/nondeterminism found (route it through an "
        f"L1 port instead):\n{offenders}"
    )
