CREATE TABLE IF NOT EXISTS cleaned_listings (
    id                VARCHAR PRIMARY KEY,
    title             TEXT,
    company           TEXT,
    location_raw      TEXT,
    location_city     TEXT,
    location_state    TEXT,
    description_clean TEXT,
    salary_min        NUMERIC,
    salary_max        NUMERIC,
    salary_midpoint   NUMERIC,
    is_remote         BOOLEAN,
    created           TIMESTAMP,
    redirect_url      TEXT,
    category          TEXT,
    keywords_matched  TEXT[],
    cleaned_at        TIMESTAMP DEFAULT NOW()
);
