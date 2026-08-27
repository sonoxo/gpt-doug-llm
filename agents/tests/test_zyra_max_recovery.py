from zyra_max import _robust_extract_json


def test_extracts_strict_json_action():
    value = _robust_extract_json('{"action":"read_file","path":"intel/qtfy/JCSA-20260826-01.json"}')
    assert value["action"] == "read_file"


def test_extracts_fenced_json_action():
    raw = 'Here is the action:\n```json\n{"action":"list_files","path":"intel/qtfy"}\n```'
    value = _robust_extract_json(raw)
    assert value == {"action": "list_files", "path": "intel/qtfy"}


def test_extracts_python_dict_action():
    raw = "{'action': 'run_check', 'check': 'syntax'}"
    value = _robust_extract_json(raw)
    assert value == {"action": "run_check", "check": "syntax"}


def test_extracts_json_with_trailing_prose():
    raw = '{"action":"finish","summary":"done"}\nMission complete.'
    value = _robust_extract_json(raw)
    assert value["action"] == "finish"
