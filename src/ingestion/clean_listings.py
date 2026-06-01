from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict

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
    created: str | None
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
