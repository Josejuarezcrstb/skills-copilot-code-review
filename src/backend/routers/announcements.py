"""
Announcement management endpoints for Mergington High School API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import date
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    message: str
    expiration_date: str
    start_date: Optional[str] = None


def _user_is_teacher(teacher_username: str):
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    return teacher


def _format_announcement(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "message": doc.get("message", ""),
        "start_date": doc.get("start_date"),
        "expiration_date": doc.get("expiration_date"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at")
    }


@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements():
    announcements = []
    for doc in announcements_collection.find().sort("expiration_date", 1):
        announcements.append(_format_announcement(doc))
    return announcements


@router.get("/active", response_model=List[Dict[str, Any]])
def get_active_announcements():
    today = date.today().isoformat()

    query = {
        "expiration_date": {"$gte": today},
        "$or": [
            {"start_date": {"$lte": today}},
            {"start_date": {"$exists": False}},
            {"start_date": ""}
        ]
    }

    announcements = []
    for doc in announcements_collection.find(query).sort("expiration_date", 1):
        announcements.append(_format_announcement(doc))
    return announcements


@router.post("/")
def create_announcement(
    announcement: AnnouncementCreate,
    teacher_username: str
):
    _user_is_teacher(teacher_username)

    message = announcement.message.strip()
    expiration_date = announcement.expiration_date
    start_date = announcement.start_date

    if not message:
        raise HTTPException(status_code=400, detail="Announcement message is required")

    if not expiration_date:
        raise HTTPException(status_code=400, detail="Expiration date is required")

    if start_date and start_date > expiration_date:
        raise HTTPException(status_code=400, detail="Start date cannot be after expiration date")

    now = date.today().isoformat()
    announcement_doc = {
        "message": message,
        "start_date": start_date if start_date else None,
        "expiration_date": expiration_date,
        "created_at": now,
        "updated_at": now
    }
    created = announcements_collection.insert_one(announcement_doc)

    return {"id": str(created.inserted_id), **announcement_doc}


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    announcement: AnnouncementCreate,
    teacher_username: str
):
    _user_is_teacher(teacher_username)

    try:
        object_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    existing = announcements_collection.find_one({"_id": object_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    message = announcement.message.strip()
    expiration_date = announcement.expiration_date
    start_date = announcement.start_date

    if not message:
        raise HTTPException(status_code=400, detail="Announcement message is required")

    if not expiration_date:
        raise HTTPException(status_code=400, detail="Expiration date is required")

    if start_date and start_date > expiration_date:
        raise HTTPException(status_code=400, detail="Start date cannot be after expiration date")

    now = date.today().isoformat()
    updated_doc = {
        "message": message,
        "start_date": start_date if start_date else None,
        "expiration_date": expiration_date,
        "updated_at": now
    }

    announcements_collection.update_one(
        {"_id": object_id},
        {"$set": updated_doc}
    )

    final_doc = announcements_collection.find_one({"_id": object_id})
    return _format_announcement(final_doc)


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, teacher_username: str):
    _user_is_teacher(teacher_username)

    try:
        object_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    deleted = announcements_collection.delete_one({"_id": object_id})
    if deleted.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
