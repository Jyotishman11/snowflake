USE DATABASE YOUTUBE_ANALYTICS; USE SCHEMA DW;
-- Roll-up: category performance.
SELECT c.category_name, SUM(f.views) total_views, SUM(f.likes) total_likes, ROUND(AVG(f.popularity_score),2) avg_popularity
FROM FACT_VIDEO_TRENDING f JOIN DIM_SUBCATEGORY s ON f.subcategory_key=s.subcategory_key JOIN DIM_CATEGORY c ON s.category_key=c.category_key GROUP BY 1 ORDER BY total_views DESC;
-- Slice: India, by channel type.
SELECT ch.channel_type, COUNT(*) videos, SUM(f.views) total_views, ROUND(AVG(f.popularity_score),2) avg_popularity
FROM FACT_VIDEO_TRENDING f JOIN DIM_GEOGRAPHY g ON f.geography_key=g.geography_key JOIN DIM_CHANNEL ch ON f.channel_key=ch.channel_key WHERE g.region='India' GROUP BY 1 ORDER BY total_views DESC;
-- Drill-down: category to subcategory.
SELECT c.category_name,s.subcategory_name,SUM(f.views) total_views
FROM FACT_VIDEO_TRENDING f JOIN DIM_SUBCATEGORY s ON f.subcategory_key=s.subcategory_key JOIN DIM_CATEGORY c ON s.category_key=c.category_key GROUP BY ROLLUP(c.category_name,s.subcategory_name) ORDER BY 1,2;
-- Time trend.
SELECT d.year,d.month,SUM(f.views) total_views,ROUND(AVG(f.popularity_score),2) avg_popularity
FROM FACT_VIDEO_TRENDING f JOIN DIM_DATE d ON f.date_key=d.date_key GROUP BY 1,2 ORDER BY 1,2;
