from ontology.models import Entity, Relation
from ontology.store import OntologyStore


def test_ontology_graph(tmp_path):
    store = OntologyStore(tmp_path)

    manufacturer = store.add_entity(
        Entity(
            type="Manufacturer",
            name="Example Manufacturer",
            jurisdiction="Germany",
        )
    )

    broker = store.add_entity(
        Entity(
            type="Broker",
            name="Example Broker",
            aliases=["BrokerCo"],
            jurisdiction="Turkey",
        )
    )

    importer = store.add_entity(
        Entity(
            type="Importer",
            name="Example Importer",
            jurisdiction="Russia",
        )
    )

    store.add_relation(
        Relation(
            source=manufacturer.id,
            target=broker.id,
            type="SUPPLIES",
        )
    )

    store.add_relation(
        Relation(
            source=broker.id,
            target=importer.id,
            type="SHIPS_TO",
            confidence="indicated",
        )
    )

    assert store.status()["entities"] == 3
    assert store.status()["relations"] == 2

    match = store.resolve_one("BrokerCo")
    assert match is not None
    assert match.id == broker.id

    path = store.path(
        "Example Manufacturer",
        "Example Importer",
    )

    assert [item["name"] for item in path] == [
        "Example Manufacturer",
        "Example Broker",
        "Example Importer",
    ]
