import importlib.util
import sys
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "skills" / "global_skill_lattice.py"
    spec = importlib.util.spec_from_file_location("global_skill_lattice", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_lattice_cardinality_and_axes():
    m = load_module()
    assert len(m.SECTORS) == 100
    assert len(m.CAPABILITIES) == 100
    assert len(m.WORKFLOWS) == 100
    assert len(m.DELIVERY_MODES) == 100
    assert m.TOTAL_SKILLS == 100_000_000


def test_lattice_is_deterministic():
    m = load_module()
    a = m.resolve(54_217_804)
    b = m.resolve(54_217_804)
    assert a == b
    assert a.skill_id == 54_217_804


def test_lattice_bounds():
    m = load_module()
    try:
        m.resolve(100_000_000)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range skill id must fail")
