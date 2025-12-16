"""
Week 2 TODO 3 refactor:
- Use Pydantic schemas for clearer API contracts.

Week 2 TODO 4:
- Add a new endpoint for LLM-powered extraction.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import (
    ActionItemResponse,
    ExtractActionItemsRequest,
    ExtractActionItemsResponse,
    ExtractedActionItem,
    MarkDoneRequest,
    MarkDoneResponse,
)
from ..services.extract import extract_action_items, extract_action_items_llm

router = APIRouter(prefix="/action-items", tags=["action-items"])


@router.post("/extract")
def extract(payload: ExtractActionItemsRequest) -> ExtractActionItemsResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    note_id: int | None = None
    if payload.save_note:
        note_id = db.insert_note(text)

    items = extract_action_items(text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractActionItemsResponse(
        note_id=note_id,
        items=[ExtractedActionItem(id=i, text=t) for i, t in zip(ids, items)],
    )


@router.post("/extract-llm")
def extract_llm(payload: ExtractActionItemsRequest) -> ExtractActionItemsResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    note_id: int | None = None
    if payload.save_note:
        note_id = db.insert_note(text)

    items = extract_action_items_llm(text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractActionItemsResponse(
        note_id=note_id,
        items=[ExtractedActionItem(id=i, text=t) for i, t in zip(ids, items)],
    )


@router.get("")
def list_all(note_id: int | None = None) -> list[ActionItemResponse]:
    rows = db.list_action_items(note_id=note_id)
    return [
        ActionItemResponse(
            id=r["id"],
            note_id=r["note_id"],
            text=r["text"],
            done=bool(r["done"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/{action_item_id}/done")
def mark_done(action_item_id: int, payload: MarkDoneRequest) -> MarkDoneResponse:
    done = bool(payload.done)
    db.mark_action_item_done(action_item_id, done)
    return MarkDoneResponse(id=action_item_id, done=done)
