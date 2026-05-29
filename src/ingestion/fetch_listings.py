import os
import time
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ConfigDict

import src.db.connection as db
import src.utils as utils

UPSERT_SQL = """
    INSERT INTO raw_listings (
        id, title, company, location, description,
        salary_min, salary_max, created, redirect_url,
        category, contract_type
    ) VALUES %s
    ON CONFLICT (id) DO UPDATE SET
        title       = EXCLUDED.title,
        company     = EXCLUDED.company,
        description = EXCLUDED.description,
        fetched_at  = NOW()
"""

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
RESULTS_PER_PAGE = 50
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0

SEARCH_KEYWORDS = [
    "data engineer",
    "analytics engineer",
    "data analyst",
    "dbt",
]


class AdzunaCompany(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    display_name: str | None = None


class AdzunaLocation(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    display_name: str | None = None


class AdzunaCategory(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    label: str | None = None


class AdzunaListing(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: str
    title: str
    company: AdzunaCompany | None = None
    location: AdzunaLocation | None = None
    description: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    created: str | None = None
    redirect_url: str | None = None
    category: AdzunaCategory | None = None
    contract_type: str | None = None


@dataclass(frozen=True)
class AdzunaClient:
    app_id: str
    app_key: str
    country: str = "us"


def _get_page(
    client: AdzunaClient, keywords: str, location: str, page: int
) -> utils.Result[list[AdzunaListing]]:
    url = f"{ADZUNA_BASE_URL}/{client.country}/search/{page}"
    params = {
        "app_id": client.app_id,
        "app_key": client.app_key,
        "what": keywords,
        "where": location,
        "results_per_page": str(RESULTS_PER_PAGE),
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.get(url, params=params, timeout=30.0)
        except httpx.RequestError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                continue
            return utils.err(e, f"Network error on page {page} for '{keywords}'")

        if response.status_code == 429:
            wait = RETRY_DELAY_SECONDS * (attempt + 1) * 2
            print(f"Rate limited — waiting {wait}s before retry")
            time.sleep(wait)
            continue

        if response.status_code != 200:
            return utils.err(
                RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}"),
                f"Failed fetching page {page} for '{keywords}'",
            )

        results = response.json().get("results", [])
        listings = [AdzunaListing.model_validate(r) for r in results]
        return utils.ok(listings)

    return utils.err(
        RuntimeError(f"Exhausted {MAX_RETRIES} retries"),
        f"Page {page} for '{keywords}'",
    )


def search(
    client: AdzunaClient, keywords: str, location: str, pages: int = 5
) -> utils.Result[list[AdzunaListing]]:
    all_listings: list[AdzunaListing] = []

    for page in range(1, pages + 1):
        listings, err = _get_page(client, keywords, location, page)
        if err is not None:
            return utils.err(err, f"Search failed on page {page}")
        if not listings:
            break
        all_listings.extend(listings)

    return utils.ok(all_listings)


def deduplicate(listings: list[AdzunaListing]) -> list[AdzunaListing]:
    seen: set[str] = set()
    unique: list[AdzunaListing] = []
    for listing in listings:
        if listing.id in seen:
            continue
        seen.add(listing.id)
        unique.append(listing)
    return unique


def _to_row(listing: AdzunaListing) -> tuple:
    return (
        listing.id,
        listing.title,
        listing.company.display_name if listing.company else None,
        listing.location.display_name if listing.location else None,
        listing.description,
        listing.salary_min,
        listing.salary_max,
        listing.created,
        listing.redirect_url,
        listing.category.label if listing.category else None,
        listing.contract_type,
    )


def load_raw(listings: list[AdzunaListing]) -> utils.Result[int]:
    values = [_to_row(l) for l in listings]
    count, err = db.upsert_many(UPSERT_SQL, values)
    if err is not None:
        return utils.err(err, "Failed to upsert raw listings")
    return utils.ok(count)


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    app_id = os.environ["ADZUNA_APP_ID"]
    app_key = os.environ["ADZUNA_APP_KEY"]
    location = os.getenv("SEARCH_LOCATION", "United States")

    client = AdzunaClient(app_id=app_id, app_key=app_key)
    all_listings: list[AdzunaListing] = []

    for keywords in SEARCH_KEYWORDS:
        listings, err = search(client, keywords, location)
        if err is not None:
            print(f"Warning: failed '{keywords}': {err}")
            continue
        all_listings.extend(listings)
        print(f"Fetched {len(listings)} listings for '{keywords}'")

    unique = deduplicate(all_listings)
    print(f"\nTotal unique listings: {len(unique)}")

    count, err = load_raw(unique)
    if err is not None:
        print(f"Error loading to database: {err}")
        return

    print(f"Upserted {count} listings into raw_listings")


if __name__ == "__main__":
    main()
