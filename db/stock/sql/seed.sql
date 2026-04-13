-- This file is used to seed the database with initial data. It assumes that the CSV files are located in the /data directory  and that the tables have already been created.
-- Each COPY command loads data from the corresponding CSV file into the respective table. The CSV files should have a header row that matches the column names of the tables.  
-- Make sure to adjust the file paths if your CSV files are located in a different directory.
-- Docker Volume Mapping: If you're using Docker, ensure that the /data directory is correctly mapped to a directory on your host machine where the CSV files are stored. For example, you can use the following volume mapping in your Docker Compose file:
-- volumes:
--   - ./data:/data    
COPY dim_stock FROM '/data/dim_stock.csv' CSV HEADER;
COPY dim_statement FROM '/data/dim_statement.csv' CSV HEADER;
COPY dim_metric FROM '/data/dim_metric.csv' CSV HEADER;
COPY dim_date FROM '/data/dim_date.csv' CSV HEADER;
COPY fact_financial_values FROM '/data/fact_financial_values.csv' CSV HEADER;