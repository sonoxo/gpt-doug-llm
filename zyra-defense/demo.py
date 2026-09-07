from zyra_ontology import (
    AuthorizationDecision,
    HumanAuthorization,
    HumanAuthority,
    Mission,
    OntologyStore,
    PalantirOntologyAdapter,
    SimulatedTarget,
    Track,
    WeaponSystemModel,
    ZyraSimulationEngine,
)


def main() -> None:
    store = OntologyStore()
    engine = ZyraSimulationEngine(store)

    mission = store.add(Mission(name="Synthetic Range Alpha", purpose="training"))
    track = store.add(Track(label="SIM-TRACK-01", confidence=0.91, simulated=True))
    target = store.add(SimulatedTarget(track_id=track.id, label="synthetic-object-01"))
    model = store.add(
        WeaponSystemModel(
            name="Synthetic Effector Model",
            capabilities={"effect_model": "abstract"},
            simulation_only=True,
            has_actuation_interface=False,
        )
    )
    authority = store.add(HumanAuthority(display_name="range-controller"))

    rec = engine.recommend_simulated_action(
        mission=mission,
        target=target,
        track=track,
        recommendation="run synthetic effect model",
        rationale="training-only evaluation inside a closed simulation",
        confidence=0.84,
        weapon_model=model,
    )
    req = engine.request_human_authorization(rec)
    auth = store.add(
        HumanAuthorization(
            request_id=req.id,
            authority_id=authority.id,
            decision=AuthorizationDecision.APPROVE_SIMULATION,
            reason="approved for synthetic range run",
        )
    )
    effect = engine.simulate_effect(rec, auth, authority)

    print(effect.to_dict())
    adapter = PalantirOntologyAdapter()
    print(f"Palantir payloads: {len(adapter.batch(store.all()))}")
    print(f"Exported: {store.export_json('zyra_ontology_export.json')}")


if __name__ == "__main__":
    main()
