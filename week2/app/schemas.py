"""
Week 2 TODO 3 refactor:
- Define explicit request/response schemas for clearer API contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NoteCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Full note content")


class NoteResponse(BaseModel):
    id: int
    content: str
    created_at: str


class ExtractActionItemsRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw notes text to extract action items from")
    save_note: bool = Field(default=True, description="Whether to persist the note in the database")


class ExtractedActionItem(BaseModel):
    id: int
    text: str


class ExtractActionItemsResponse(BaseModel):
    note_id: int | None
    items: list[ExtractedActionItem]


class ActionItemResponse(BaseModel):
    id: int
    note_id: int | None
    text: str
    done: bool
    created_at: str


class MarkDoneRequest(BaseModel):
    done: bool = True


class MarkDoneResponse(BaseModel):
    id: int
    done: bool
