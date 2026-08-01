"""Id and reference conformance. Successive values are unique and non-empty."""

import pytest

from slr.adapters.seq_ids import SeqIdGen, SeqReferenceGen


@pytest.mark.integration
def test_ids_are_unique_and_non_empty():
    gen = SeqIdGen()
    ids = [gen.new_id() for _ in range(100)]
    assert all(ids)
    assert len(set(ids)) == len(ids)


@pytest.mark.integration
def test_references_are_unique_and_non_empty():
    gen = SeqReferenceGen()
    refs = [gen.new_reference() for _ in range(100)]
    assert all(refs)
    assert len(set(refs)) == len(refs)


@pytest.mark.integration
def test_reference_is_human_readable_and_zero_padded():
    gen = SeqReferenceGen(prefix="SLR", width=6)
    assert gen.new_reference() == "SLR-000001"
