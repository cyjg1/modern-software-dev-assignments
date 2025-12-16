"""
Week 2 TODO 3 refactor:
- Use Pydantic schemas for clearer API contracts.

Week 2 TODO 4:
- Expose an endpoint to retrieve all notes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import NoteCreateRequest, NoteResponse

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("")
def create_note(payload: NoteCreateRequest) -> NoteResponse:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    note_id = db.insert_note(content)
    note = db.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=500, detail="failed to create note")
    return NoteResponse(id=note["id"], content=note["content"], created_at=note["created_at"])


@router.get("")
def list_all_notes() -> list[NoteResponse]:
    rows = db.list_notes()
    return [NoteResponse(id=r["id"], content=r["content"], created_at=r["created_at"]) for r in rows]


@router.get("/{note_id}")
def get_single_note(note_id: int) -> NoteResponse:
    row = db.get_note(note_id)
    if row is None:
        raise HTTPException(status_code=404, detail="note not found")
    return NoteResponse(id=row["id"], content=row["content"], created_at=row["created_at"])
