"""
COO correction handler for people records.

When the COO corrects an AI-assigned role, this module updates the
person record with ``role_source: coo_corrected`` and stores the
correction as a hard fact in the memory system.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundException, ValidationException
from app.models.base import generate_uuid, utc_now

logger = logging.getLogger(__name__)


async def apply_correction(
    person_id: str,
    correction_data: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Apply a COO correction to a person record.

    Updates the person's role, department, or other fields and marks
    the change source as ``coo_corrected``. Also stores the correction
    as a hard fact in the memory system for future context.

    Args:
        person_id: UUID of the person to correct.
        correction_data: Dict with fields to update. Supported keys:
            - ``role``: New role label.
            - ``department``: New department name.
            - ``name``: Corrected display name.
            - ``email``: Corrected email address.
        db: Motor database handle.

    Returns:
        The updated person document.

    Raises:
        NotFoundException: If the person_id does not exist.
        ValidationException: If correction_data is empty.
    """
    if not correction_data:
        raise ValidationException(
            message="Correction data cannot be empty",
            errors=[{"field": "correction_data", "message": "At least one field must be provided"}],
        )

    person = await db.people.find_one({"person_id": person_id})
    if not person:
        raise NotFoundException(resource="Person", identifier=person_id)

    update_fields: dict[str, Any] = {
        "updated_at": utc_now(),
    }

    # Track what changed for the hard fact
    changes: list[str] = []
    old_values: dict[str, Any] = {}

    if "role" in correction_data:
        new_role = correction_data["role"].strip()
        if new_role:
            old_values["role"] = person.get("role", "")
            update_fields["role"] = new_role
            update_fields["role_source"] = "coo_corrected"
            changes.append(f"role changed from '{old_values['role']}' to '{new_role}'")

    if "department" in correction_data:
        new_dept = correction_data["department"].strip()
        if new_dept:
            old_values["department"] = person.get("department", "")
            update_fields["department"] = new_dept
            changes.append(f"department changed from '{old_values['department']}' to '{new_dept}'")

    if "name" in correction_data:
        new_name = correction_data["name"].strip()
        if new_name:
            old_values["name"] = person.get("name", "")
            update_fields["name"] = new_name
            changes.append(f"name changed from '{old_values['name']}' to '{new_name}'")

    if "email" in correction_data:
        new_email = correction_data["email"].strip()
        if new_email:
            old_values["email"] = person.get("email", "")
            update_fields["email"] = new_email
            changes.append(f"email changed from '{old_values['email']}' to '{new_email}'")

    if not changes:
        raise ValidationException(
            message="No valid changes provided",
            errors=[{"field": "correction_data", "message": "All provided fields were empty"}],
        )

    # Apply the update
    await db.people.update_one(
        {"person_id": person_id},
        {"$set": update_fields},
    )

    # Store correction as a hard fact
    await _store_correction_fact(
        person_id=person_id,
        person_name=person.get("name", ""),
        changes=changes,
        correction_data=correction_data,
        db=db,
    )

    # Log the correction
    await _log_correction(
        person_id=person_id,
        person_name=person.get("name", ""),
        changes=changes,
        old_values=old_values,
        db=db,
    )

    # Return the updated document
    updated = await db.people.find_one({"person_id": person_id})
    if updated and "_id" in updated:
        updated["_id"] = str(updated["_id"])

    logger.info(
        "COO correction applied to person %s (%s): %s",
        person_id,
        person.get("name", ""),
        "; ".join(changes),
    )

    return updated or {}


async def _store_correction_fact(
    person_id: str,
    person_name: str,
    changes: list[str],
    correction_data: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Store the correction as a hard fact in the memory system."""
    fact_content = f"COO corrected {person_name}: {'; '.join(changes)}"

    fact_doc = {
        "fact_id": generate_uuid(),
        "category": "people_correction",
        "content": fact_content,
        "source": "coo_correction",
        "entity_type": "person",
        "entity_id": person_id,
        "correction_data": correction_data,
        "active": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }

    # Supersede any previous correction facts for this person
    await db.conversation_facts.update_many(
        {
            "entity_type": "person",
            "entity_id": person_id,
            "category": "people_correction",
            "active": True,
        },
        {"$set": {"active": False, "superseded_at": utc_now()}},
    )

    await db.conversation_facts.insert_one(fact_doc)


async def _log_correction(
    person_id: str,
    person_name: str,
    changes: list[str],
    old_values: dict[str, Any],
    db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
) -> None:
    """Log the correction in the audit log."""
    await db.audit_log.insert_one({
        "request_id": generate_uuid(),
        "action": "people_correction",
        "entity_type": "person",
        "entity_id": person_id,
        "entity_name": person_name,
        "changes": changes,
        "old_values": old_values,
        "created_at": utc_now(),
    })
