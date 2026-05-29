CREATE TABLE IF NOT EXISTS raw_listings (
    id            VARCHAR PRIMARY KEY,
    title         TEXT,
    company       TEXT,
    location      TEXT,
    description   TEXT,
    salary_min    NUMERIC,
    salary_max    NUMERIC,
    created       TIMESTAMP,
    redirect_url  TEXT,
    category      TEXT,
    contract_type TEXT,
    fetched_at    TIMESTAMP DEFAULT NOW()
);
