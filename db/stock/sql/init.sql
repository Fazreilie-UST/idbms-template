-- Dimension tables
CREATE TABLE dim_statement (
    statement_id   INTEGER PRIMARY KEY,
    statement_name TEXT NOT NULL
);

CREATE TABLE dim_date (
    date_id   INTEGER PRIMARY KEY,
    full_date DATE NOT NULL,
    year      INTEGER,
    month     INTEGER,
    quarter   INTEGER
);

CREATE TABLE dim_stock (
    stock_id    INTEGER PRIMARY KEY,
    stock_code  TEXT NOT NULL,
    stock_number INTEGER,
    stock_name  TEXT,
    weblink     TEXT,
    price       NUMERIC(18,4)
);

CREATE TABLE dim_metric (
    metric_id       INTEGER PRIMARY KEY,
    metric_name     TEXT NOT NULL,
    statement_id    INTEGER NOT NULL REFERENCES dim_statement(statement_id),
    parent_metric_id INTEGER REFERENCES dim_metric(metric_id)
);

-- Fact table
CREATE TABLE fact_financial_values (
    stock_id     INTEGER NOT NULL REFERENCES dim_stock(stock_id),
    metric_id    INTEGER NOT NULL REFERENCES dim_metric(metric_id),
    statement_id INTEGER NOT NULL REFERENCES dim_statement(statement_id),
    date_id      INTEGER NOT NULL REFERENCES dim_date(date_id),
    value        NUMERIC(18,4),
    PRIMARY KEY (stock_id, metric_id, statement_id, date_id)
);