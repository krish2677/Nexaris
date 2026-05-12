"""Event schemas."""

from pydantic import BaseModel


class EventCreate(BaseModel):
    event_name: str
    metadata_json: str = "{}"
