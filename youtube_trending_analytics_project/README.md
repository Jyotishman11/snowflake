# YouTube Trending Content Analytics & Popularity Prediction

An end-to-end, dependency-free academic project that ingests a YouTube Trending CSV, cleans and warehouses it in a **Snowflake schema**, produces OLAP summaries, trains a popularity-prediction model, and creates SVG visualizations.

## Project structure

```
data/raw/                 Input CSV (generated demo data lives here)
data/processed/           Cleaned records, dimensions, and fact table
sql/                      Snowflake DDL/load script and OLAP queries
src/generate_sample_data.py  Reproducible CSV generator
src/run_pipeline.py       ETL + warehouse export + OLAP + ML + charts
reports/                  Model metrics and visualization files
```

## Run

Requires Python 3.10+ only (no `pip install` necessary):

```powershell
cd C:\Users\lenovo\Documents\Codex\2026-09-15\new-chat\outputs\youtube_trending_analytics
python src/generate_sample_data.py
python src/run_pipeline.py
```

To use a real dataset, replace `data/raw/youtube_trending.csv` with a CSV having the same columns. The pipeline writes invalid rows to `data/processed/rejected_rows.csv`.

## Design

`FACT_VIDEO_TRENDING` stores one video/region/trending-date observation. It links to `DIM_DATE`, `DIM_GEOGRAPHY`, `DIM_CHANNEL`, and `DIM_SUBCATEGORY`. The subcategory dimension links to `DIM_CATEGORY`, forming a snowflake (normalized) dimensional model.

The model uses metadata available near publication (category, region, channel type, subscriber count, age, tags, ad spend, title length) to predict `popularity_score` on a 0–100 scale. Engagement metrics are deliberately excluded from features to reduce target leakage.

## Snowflake execution

1. Create a database and warehouse in Snowsight.
2. Run `sql/01_warehouse_setup.sql`.
3. Upload the raw CSV to the named internal stage (or change the script to your external stage) and run the `COPY INTO` command.
4. Execute `sql/02_olap_queries.sql` for the OLAP results.

The local Python pipeline provides reproducible results without a Snowflake account; the SQL files are the deployable warehouse equivalent.
