-- YouTube Trending Analytics: Snowflake schema and CSV load.
CREATE OR REPLACE DATABASE YOUTUBE_ANALYTICS;
CREATE OR REPLACE SCHEMA YOUTUBE_ANALYTICS.DW;
CREATE OR REPLACE WAREHOUSE YOUTUBE_ETL_WH WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60;
USE WAREHOUSE YOUTUBE_ETL_WH;
USE DATABASE YOUTUBE_ANALYTICS;
USE SCHEMA DW;

CREATE OR REPLACE FILE FORMAT YOUTUBE_CSV_FORMAT TYPE=CSV SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"' NULL_IF=('','NULL');
CREATE OR REPLACE STAGE YOUTUBE_RAW_STAGE FILE_FORMAT=YOUTUBE_CSV_FORMAT;
CREATE OR REPLACE TABLE STG_YOUTUBE_TRENDING (
 video_id STRING,title STRING,category STRING,subcategory STRING,region STRING,channel_type STRING,
 published_at DATE,trending_date DATE,views NUMBER,likes NUMBER,comments NUMBER,shares NUMBER,
 watch_time_minutes FLOAT,subscriber_count NUMBER,days_since_published NUMBER,tag_count NUMBER,ad_spend FLOAT);
-- Upload data/raw/youtube_trending.csv to @YOUTUBE_RAW_STAGE, then run:
COPY INTO STG_YOUTUBE_TRENDING FROM @YOUTUBE_RAW_STAGE/youtube_trending.csv;

CREATE OR REPLACE TABLE DIM_DATE (date_key INTEGER AUTOINCREMENT, full_date DATE UNIQUE, year NUMBER, month NUMBER, day NUMBER);
CREATE OR REPLACE TABLE DIM_GEOGRAPHY (geography_key INTEGER AUTOINCREMENT, region STRING UNIQUE);
CREATE OR REPLACE TABLE DIM_CHANNEL (channel_key INTEGER AUTOINCREMENT, channel_type STRING UNIQUE);
CREATE OR REPLACE TABLE DIM_CATEGORY (category_key INTEGER AUTOINCREMENT, category_name STRING UNIQUE);
CREATE OR REPLACE TABLE DIM_SUBCATEGORY (subcategory_key INTEGER AUTOINCREMENT, subcategory_name STRING UNIQUE, category_key INTEGER REFERENCES DIM_CATEGORY(category_key));
CREATE OR REPLACE TABLE FACT_VIDEO_TRENDING (
 trend_fact_key INTEGER AUTOINCREMENT,video_id STRING,date_key INTEGER REFERENCES DIM_DATE(date_key),
 geography_key INTEGER REFERENCES DIM_GEOGRAPHY(geography_key),channel_key INTEGER REFERENCES DIM_CHANNEL(channel_key),subcategory_key INTEGER REFERENCES DIM_SUBCATEGORY(subcategory_key),
 views NUMBER,likes NUMBER,comments NUMBER,shares NUMBER,watch_time_minutes FLOAT,subscriber_count NUMBER,days_since_published NUMBER,tag_count NUMBER,ad_spend FLOAT,title_length NUMBER,popularity_score FLOAT);

INSERT INTO DIM_DATE(full_date,year,month,day) SELECT DISTINCT trending_date,YEAR(trending_date),MONTH(trending_date),DAY(trending_date) FROM STG_YOUTUBE_TRENDING;
INSERT INTO DIM_GEOGRAPHY(region) SELECT DISTINCT region FROM STG_YOUTUBE_TRENDING;
INSERT INTO DIM_CHANNEL(channel_type) SELECT DISTINCT channel_type FROM STG_YOUTUBE_TRENDING;
INSERT INTO DIM_CATEGORY(category_name) SELECT DISTINCT category FROM STG_YOUTUBE_TRENDING;
INSERT INTO DIM_SUBCATEGORY(subcategory_name,category_key) SELECT DISTINCT s.subcategory,c.category_key FROM STG_YOUTUBE_TRENDING s JOIN DIM_CATEGORY c ON c.category_name=s.category;
INSERT INTO FACT_VIDEO_TRENDING(video_id,date_key,geography_key,channel_key,subcategory_key,views,likes,comments,shares,watch_time_minutes,subscriber_count,days_since_published,tag_count,ad_spend,title_length,popularity_score)
SELECT s.video_id,d.date_key,g.geography_key,ch.channel_key,sc.subcategory_key,s.views,s.likes,s.comments,s.shares,s.watch_time_minutes,s.subscriber_count,s.days_since_published,s.tag_count,s.ad_spend,LENGTH(TRIM(s.title)),
  100*(.70*(s.views-MIN(s.views) OVER())/NULLIF(MAX(s.views) OVER()-MIN(s.views) OVER(),0)+.20*LEAST(1,s.likes/NULLIF(s.views,0)*10)+.10*LEAST(1,s.shares/NULLIF(s.views,0)*25))
FROM STG_YOUTUBE_TRENDING s JOIN DIM_DATE d ON d.full_date=s.trending_date JOIN DIM_GEOGRAPHY g ON g.region=s.region JOIN DIM_CHANNEL ch ON ch.channel_type=s.channel_type JOIN DIM_SUBCATEGORY sc ON sc.subcategory_name=s.subcategory;
