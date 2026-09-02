from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from models import Laboratory


def find_labs(db: Session, product_description: str, standard_number: str | None = None, limit: int = 10):
    """
    Deterministic SQL lookup against the Laboratory table.
    No Gemini/LLM call — this is structured data, not free-text
    document chunks, so a direct filter is safer and simpler
    than semantic search.

    Matches product_description against name, location, and capabilities
    (case-insensitive substring match). If standard_number is provided,
    results are additionally required to match it against standard_numbers,
    since a standard number is a precise, validated filter rather than a
    fuzzy keyword.
    """
    if not product_description or not product_description.strip():
        return []

    pattern = f"%{product_description.strip()}%"

    description_filter = or_(
        Laboratory.capabilities.ilike(pattern),
        Laboratory.name.ilike(pattern),
        Laboratory.location.ilike(pattern),
    )

    filters = [description_filter]

    if standard_number and standard_number.strip():
        std_pattern = f"%{standard_number.strip()}%"
        filters.append(Laboratory.standard_numbers.ilike(std_pattern))

    results = (
        db.query(Laboratory)
        .filter(and_(*filters))
        .limit(limit)
        .all()
    )

    return results