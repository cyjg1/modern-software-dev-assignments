import json

from ..app.services import extract as extract_module
from ..app.services.extract import extract_action_items, extract_action_items_llm


def test_extract_bullets_and_checkboxes():
    text = """
    Notes from meeting:
    - [ ] Set up database
    * implement API extract endpoint
    1. Write tests
    Some narrative sentence.
    """.strip()

    items = extract_action_items(text)
    assert "Set up database" in items
    assert "implement API extract endpoint" in items
    assert "Write tests" in items


def test_extract_action_items_llm_parses_json_and_dedupes(monkeypatch):
    def fake_chat(*, model, messages, format):
        assert model
        assert messages[-1]["role"] == "user"
        assert "Write tests" in messages[-1]["content"]
        return {
            "message": {
                "content": json.dumps(
                    {
                        "items": [
                            " Write tests ",
                            "write tests",
                            "",
                            "Email Bob",
                        ]
                    }
                )
            }
        }

    monkeypatch.setattr(extract_module, "chat", fake_chat)

    items = extract_action_items_llm("- Write tests\nTODO: email Bob")
    assert items == ["Write tests", "Email Bob"]


def test_extract_action_items_llm_empty_input_returns_empty_list(monkeypatch):
    def fail_chat(*args, **kwargs):
        raise AssertionError("chat should not be called for empty input")

    monkeypatch.setattr(extract_module, "chat", fail_chat)

    assert extract_action_items_llm("") == []
    assert extract_action_items_llm("   \n\t") == []


def test_extract_action_items_llm_falls_back_on_invalid_json(monkeypatch):
    def fake_chat(*, model, messages, format):
        return {"message": {"content": "not valid json"}}

    monkeypatch.setattr(extract_module, "chat", fake_chat)

    text = "- [ ] Set up database\nSome narrative."
    items = extract_action_items_llm(text)
    assert "Set up database" in items
