import pytest

from zyra import MemoryRecord, ZyraMemory


def test_remember_and_recall():
    memory = ZyraMemory()
    record = memory.remember(
        MemoryRecord(
            content="Ontology-first retrieval is required",
            tags=["ontology", "retrieval"],
        )
    )

    assert memory.recall(record.id) == record


def test_search():
    memory = ZyraMemory()
    memory.remember(MemoryRecord(content="Use Hugging Face models", tags=["models"]))

    results = memory.search("hugging")

    assert len(results) == 1


def test_forget():
    memory = ZyraMemory()
    record = memory.remember(MemoryRecord(content="temporary memory"))

    assert memory.forget(record.id) is True
    assert memory.recall(record.id) is None


def test_reject_invalid_confidence():
    memory = ZyraMemory()

    with pytest.raises(ValueError):
        memory.remember(MemoryRecord(content="bad", confidence=1.5))
