"""Structural test-doctrine: missing test scaffolding fails the build like missing code.

Every domain module has a unit test; every port has a conformance suite; every use-case
has a fake-based test (ARCHITECTURE.md §Enforcement). Enforced by naming convention so
the map stays mechanical:

    backend/slr/domain/fares.py       -> tests/unit/test_fares.py
    backend/slr/ports/repository.py   -> tests/integration/ports/test_repository.py
    backend/slr/usecases/hold_seat.py -> tests/integration/usecases/test_hold_seat.py

Trivially green on the empty tree; each rule bites the moment its layer gets a module.
"""

from __future__ import annotations

import pytest
from tests.architecture._paths import (
    DOMAIN,
    PORT_CONFORMANCE,
    PORTS,
    UNIT_TESTS,
    USECASE_TESTS,
    USECASES,
    module_files,
)


def _missing(source_dir, test_dir) -> list[str]:
    return [
        f"{m.relative_to(source_dir.parent)} -> {(test_dir / f'test_{m.name}')}"
        for m in module_files(source_dir)
        if not (test_dir / f"test_{m.name}").exists()
    ]


@pytest.mark.arch
def test_every_domain_module_has_a_unit_test():
    missing = _missing(DOMAIN, UNIT_TESTS)
    assert not missing, f"Domain modules without a unit test:\n{missing}"


@pytest.mark.arch
def test_every_port_has_a_conformance_suite():
    missing = _missing(PORTS, PORT_CONFORMANCE)
    assert not missing, f"Ports without a conformance suite:\n{missing}"


@pytest.mark.arch
def test_every_usecase_has_a_fake_based_test():
    missing = _missing(USECASES, USECASE_TESTS)
    assert not missing, f"Use-cases without a fake-based test:\n{missing}"
