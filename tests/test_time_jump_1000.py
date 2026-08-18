from doug_core.iteration import DougIterator


def test_time_jump_1000_profile_is_bounded():
    iterator = DougIterator.time_jump_1000()
    assert iterator.max_iterations == 1000
    assert iterator.target_score == 0.995


def test_iterator_rejects_unbounded_depth():
    try:
        DougIterator(max_iterations=1001)
    except ValueError as exc:
        assert "may not exceed 1000" in str(exc)
    else:
        raise AssertionError("expected max iteration guard")


def test_iterator_rejects_zero_iterations():
    try:
        DougIterator(max_iterations=0)
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("expected minimum iteration guard")
