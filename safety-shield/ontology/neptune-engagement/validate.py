"""Validate this portable ontology using only the Python standard library."""

import copy
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def load(name):
    return json.loads((BASE / name).read_text())


def validate(model, objects, links):
    ids = [obj["id"] for obj in objects]
    assert len(ids) == len(set(ids)), "Duplicate object IDs"

    index = {obj["id"]: obj for obj in objects}
    evidence = {obj["id"] for obj in objects if obj["type"] == "Evidence"}
    for obj in objects:
        assert obj["type"] in model["object_types"], "Unknown object type"
        assert set(model["object_types"][obj["type"]]["required_properties"]) <= set(
            obj["properties"]
        ), "Missing property"
        assert set(obj["source_ids"]) <= evidence, "Missing provenance"
        assert obj["type"] == "Evidence" or obj["source_ids"], "Unattributed object"

        props = obj["properties"]
        for key in ["verification_status", "maturity", "readiness", "registration_status"]:
            if key in props:
                assert props[key] in model["enums"][key], "Invalid enum"

        status_enum = {
            "Membership": "membership_status",
            "Submission": "submission_status",
            "Agreement": "agreement_status",
            "Task": "task_status",
        }.get(obj["type"])
        if status_enum:
            assert props["status"] in model["enums"][status_enum], "Invalid status"

        if obj["type"] == "Membership" and props["status"] == "confirmed":
            assert props["verification_status"] in [
                "document_supported",
                "independently_verified",
            ], "Unverified membership promotion"
            ref = props.get("official_confirmation_reference")
            assert ref in evidence, "Missing membership confirmation"
            assert index[ref]["properties"]["source_kind"] in [
                "membership_confirmation",
                "executed_agreement",
            ], "Wrong membership evidence kind"

        if obj["type"] == "Event" and props["registration_status"] in [
            "registered",
            "attended",
        ]:
            assert props.get("registration_evidence_id") in evidence, (
                "Missing registration evidence"
            )

        if obj["type"] == "Submission" and props["status"] == "submitted":
            assert (
                props["submitted_at"] and props.get("receipt_evidence_id") in evidence
            ), "Missing submission receipt"

        if obj["type"] == "Agreement" and props["status"] in ["signed", "awarded"]:
            assert props.get("executed_document_evidence_id") in evidence, (
                "Missing executed agreement"
            )
            if props["status"] == "awarded":
                assert props["award_number"], "Missing award identifier"

        if obj["type"] == "Capability" and props["readiness"] in [
            "tested",
            "operational",
        ]:
            assert props.get("test_evidence") in evidence, "Missing test evidence"

    link_ids = [link["id"] for link in links]
    assert len(link_ids) == len(set(link_ids)), "Duplicate link IDs"
    for link in links:
        assert link["type"] in model["link_types"], "Unknown link type"
        assert link["source_id"] in index and link["target_id"] in index, "Dangling link"

        spec = model["link_types"][link["type"]]
        assert index[link["source_id"]]["type"] == spec["source_type"], "Wrong source type"
        assert index[link["target_id"]]["type"] == spec["target_type"], "Wrong target type"
        assert link["evidence_ids"] and set(link["evidence_ids"]) <= evidence, (
            "Missing link evidence"
        )
        assert link["relationship_status"] in model["enums"]["relationship_status"], (
            "Invalid relationship status"
        )

    return True


if __name__ == "__main__":
    model, objects, links = load("ontology.json"), load("objects.json"), load("links.json")
    validate(model, objects, links)

    evidence_portal = next(obj for obj in objects if obj["id"] == "evidence.portal")
    assert (
        hashlib.sha256((BASE / "source_portal_export.md").read_bytes()).hexdigest()
        == evidence_portal["properties"]["sha256"]
    ), "Source changed"

    tests = []

    def rejected(name, candidate_objects, candidate_links):
        try:
            validate(model, candidate_objects, candidate_links)
        except AssertionError:
            tests.append({"test": name, "result": "pass"})
            return
        raise AssertionError("Invalid fixture accepted: " + name)

    candidate_objects = copy.deepcopy(objects)
    next(obj for obj in candidate_objects if obj["type"] == "Membership")["properties"][
        "status"
    ] = "confirmed"
    rejected("Block unsupported membership confirmation", candidate_objects, links)

    candidate_links = copy.deepcopy(links)
    candidate_links[0]["target_id"] = "missing"
    rejected("Reject dangling relationship", objects, candidate_links)

    candidate_links = copy.deepcopy(links)
    candidate_links[0]["target_id"] = "person.douglas"
    rejected("Reject incorrect endpoint type", objects, candidate_links)

    candidate_objects = copy.deepcopy(objects)
    next(obj for obj in candidate_objects if obj["type"] == "Event")["properties"][
        "registration_status"
    ] = "registered"
    rejected("Require registration evidence", candidate_objects, links)

    candidate_objects = copy.deepcopy(objects)
    next(obj for obj in candidate_objects if obj["type"] == "Submission")["properties"][
        "status"
    ] = "submitted"
    rejected("Require submission receipt", candidate_objects, links)

    candidate_objects = copy.deepcopy(objects)
    next(obj for obj in candidate_objects if obj["type"] == "Capability")["properties"][
        "readiness"
    ] = "tested"
    rejected("Require capability test evidence", candidate_objects, links)

    report = {
        "status": "passed",
        "objects": len(objects),
        "links": len(links),
        "object_types": len(model["object_types"]),
        "link_types": len(model["link_types"]),
        "source_hash": "verified",
        "negative_tests": tests,
        "limits": "Structural checks do not authenticate documents, establish membership or replace live authorization.",
    }
    (BASE / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
