"""Cell atlas is a bounded educational model, not a biological protocol."""
import pytest

from pineal.cells import list_cells, simulate


def test_curated_cells_have_origin_and_no_wetlab_protocol():
    cells = list_cells()
    names = {c['id'] for c in cells}
    assert {'neuron', 'cardiomyocyte', 'hepatocyte', 't_lymphocyte', 'hematopoietic_stem_cell'} <= names
    assert all(c['species'] == 'Homo sapiens' and c['status'] == 'educational_metadata' for c in cells)
    assert all(c['function'] and c['lineage'] and c['caution'] for c in cells)
    assert not any('protocol' in c for c in cells)


def test_simulation_is_deterministic_symbolic_and_disclaims_parthenogenesis():
    left = simulate('neuron', steps=5)
    assert left == simulate('neuron', steps=5)
    assert left['created_living_cells'] is False
    assert left['mode'] == 'symbolic_educational_simulation'
    assert len(left['timeline']) == 5
    assert all(row['step'] == i + 1 for i, row in enumerate(left['timeline']))
    assert 'imprinting' in left['scientific_limitations'].lower()
    assert 'not' in left['scientific_limitations'].lower()


@pytest.mark.parametrize('cell,steps', [('unknown', 1), ('neuron', 0), ('neuron', 51), ('neuron', True)])
def test_simulation_rejects_invalid_requests(cell, steps):
    with pytest.raises(ValueError):
        simulate(cell, steps=steps)


def test_cell_ontology_can_be_queried_by_concept():
    from pineal.cells import search_cells
    matches = search_cells('neural')
    assert any(row['id'] == 'neuron' for row in matches)
    assert search_cells('quantum-reanimation') == []
