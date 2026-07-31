import pytest

from slr.domain.errors import (
    DomainError,
    IllegalTransition,
    InvalidLeg,
    NoFeasibleSeat,
)


@pytest.mark.unit
@pytest.mark.parametrize("err", [InvalidLeg, IllegalTransition, NoFeasibleSeat])
def test_every_domain_error_is_a_domain_error(err):
    assert issubclass(err, DomainError)
    with pytest.raises(DomainError):
        raise err("boom")


@pytest.mark.unit
def test_domain_error_is_an_exception():
    assert issubclass(DomainError, Exception)
