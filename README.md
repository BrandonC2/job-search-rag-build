# job-search-rag-build

Personal job search tool — ingests listings from Adzuna into Postgres,
then uses embeddings + RAG to answer natural language questions about them.

## Week 1 status: ingestion + raw storage

Fetches listings across 4 keyword searches, deduplicates, and upserts
into a `raw_listings` table in Neon (serverless Postgres).

## Setup

**Prerequisites:** Python 3.12+, a [Neon](https://neon.tech) database (free tier works)

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in DATABASE_URL, ADZUNA_APP_ID, ADZUNA_APP_KEY
```

**Create the table:**
```bash
psql $DATABASE_URL -f sql/01_raw_schema.sql
```

**Run the ingestion:**
```bash
python -m src.ingestion.fetch_listings
```
