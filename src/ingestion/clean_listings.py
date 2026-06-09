from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict

import src.db.connection as db

REMOTE_PATTERNS = frozenset({"remote", "work from home", "wfh", "fully remote", "hybrid remote"})


class CleanedRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    title: str
    company: str | None
    location_raw: str | None
    location_city: str | None
    location_state: str | None
    description_clean: str | None
    salary_min: float | None
    salary_max: float | None
    salary_midpoint: float | None
    is_remote: bool
    created: datetime | None
    redirect_url: str | None
    category: str | None
    keywords_matched: list[str]


def strip_html(text: str) -> str:
    return BeautifulSoup(text, "html.parser").get_text(separator=" ").strip()


def extract_city_state(location_raw: str | None) -> tuple[str | None, str | None]:
    if not location_raw:
        return None, None
    parts = [p.strip() for p in location_raw.split(",")]
    city = parts[0] if parts else None
    state = parts[1] if len(parts) > 1 else None
    return city, state


def detect_remote(description: str | None, location: str | None) -> bool:
    text = f"{description or ''} {location or ''}".lower()
    return any(pattern in text for pattern in REMOTE_PATTERNS)


def compute_midpoint(salary_min: float | None, salary_max: float | None) -> float | None:
    if salary_min is None or salary_max is None:
        return None
    return (salary_min + salary_max) / 2


def clean_row(raw: dict) -> CleanedRow:
    city, state = extract_city_state(raw.get("location"))
    description_clean = strip_html(raw.get("description") or "") or None

    return CleanedRow(
        id=raw["id"],
        title=raw["title"],
        company=raw.get("company"),
        location_raw=raw.get("location"),
        location_city=city,
        location_state=state,
        description_clean=description_clean,
        salary_min=raw.get("salary_min"),
        salary_max=raw.get("salary_max"),
        salary_midpoint=compute_midpoint(raw.get("salary_min"), raw.get("salary_max")),
        is_remote=detect_remote(raw.get("description"), raw.get("location")),
        created=raw.get("created"),
        redirect_url=raw.get("redirect_url"),
        category=raw.get("category"),
        keywords_matched=[],
    )


def main() -> None:
    load_dotenv()

    rows, err = db.fetch_all("SELECT * FROM raw_listings")
    if err:
        print(f"Failed to fetch raw listings: {err}")
        return

    cleaned = [clean_row(r) for r in rows]

    sql = """
        INSERT INTO cleaned_listings (
            id, title, company, location_raw, location_city, location_state,
            description_clean, salary_min, salary_max, salary_midpoint,
            is_remote, created, redirect_url, category, keywords_matched
        ) VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description_clean = EXCLUDED.description_clean,
            is_remote = EXCLUDED.is_remote,
            salary_midpoint = EXCLUDED.salary_midpoint,
            cleaned_at = NOW()
    """
    values = [
        (
            r.id, r.title, r.company, r.location_raw, r.location_city,
            r.location_state, r.description_clean, r.salary_min, r.salary_max,
            r.salary_midpoint, r.is_remote, r.created, r.redirect_url,
            r.category, r.keywords_matched,
        )
        for r in cleaned
    ]

    _, err = db.upsert_many(sql, values)
    if err:
        print(f"Failed to upsert cleaned listings: {err}")
        return

    print(f"Upserted {len(cleaned)} listings into cleaned_listings")


if __name__ == "__main__":
    main()
