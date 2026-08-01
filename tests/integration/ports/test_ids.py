"""Id and reference conformance. Successive values are unique and non-empty."""

import pytest

from slr.adapters.seq_ids import SeqIdGen, SeqReferenceGen
from slr.adapters.uuid_ids import UuidIdGen, UuidReferenceGen


@pytest.fixture(params=["fake", "real"])
def id_gen(request):
    return SeqIdGen() if request.param == "fake" else UuidIdGen()


@pytest.fixture(params=["fake", "real"])
def reference_gen(request):
    return SeqReferenceGen() if request.param == "fake" else UuidReferenceGen()


@pytest.mark.integration
def test_ids_are_unique_and_non_empty(id_gen):
    ids = [id_gen.new_id() for _ in range(100)]
    assert all(ids)
    assert len(set(ids)) == len(ids)


@pytest.mark.integration
def test_references_are_unique_and_non_empty(reference_gen):
    refs = [reference_gen.new_reference() for _ in range(100)]
    assert all(refs)
    assert len(set(refs)) == len(refs)


@pytest.mark.integration
def test_seq_reference_is_human_readable_and_zero_padded():
    assert SeqReferenceGen(prefix="SLR", width=6).new_reference() == "SLR-000001"
