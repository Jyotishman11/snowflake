"""Create a deterministic, realistic-looking CSV for this project."""
from pathlib import Path
import csv
import random
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "youtube_trending.csv"
random.seed(20260915)

CATEGORIES = [("Music", "Pop"), ("Music", "Hip Hop"), ("Gaming", "Esports"),
              ("Gaming", "Walkthrough"), ("Education", "Technology"),
              ("Education", "Science"), ("Entertainment", "Comedy"),
              ("Entertainment", "Film & Animation")]
REGIONS = ["India", "United States", "United Kingdom", "Canada", "Australia"]
CHANNELS = ["Individual", "Media Company", "Brand", "Educational"]

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["video_id", "title", "category", "subcategory", "region", "channel_type",
              "published_at", "trending_date", "views", "likes", "comments", "shares",
              "watch_time_minutes", "subscriber_count", "days_since_published", "tag_count", "ad_spend"]
    start = date(2025, 1, 1)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i in range(1500):
            category, subcategory = random.choice(CATEGORIES)
            region, channel = random.choice(REGIONS), random.choice(CHANNELS)
            published = start + timedelta(days=random.randrange(300))
            age = random.randrange(1, 15)
            trending = published + timedelta(days=age)
            subscribers = random.randint(2_000, 4_000_000)
            tags, ad_spend = random.randint(2, 18), random.randint(0, 18_000)
            category_factor = {"Music": 1.5, "Gaming": 1.25, "Entertainment": 1.35, "Education": .85}[category]
            potential = (subscribers * random.uniform(.018, .19) + ad_spend * 27 + tags * 13000) * category_factor / (age ** .18)
            views = max(1000, int(potential + random.gauss(0, potential * .18)))
            likes = int(views * random.uniform(.025, .12))
            comments, shares = int(likes * random.uniform(.03, .18)), int(likes * random.uniform(.015, .09))
            writer.writerow({"video_id": f"YT{i:05d}", "title": f"{subcategory} creator video {i}: trending ideas",
                "category": category, "subcategory": subcategory, "region": region, "channel_type": channel,
                "published_at": published.isoformat(), "trending_date": trending.isoformat(), "views": views,
                "likes": likes, "comments": comments, "shares": shares,
                "watch_time_minutes": round(views * random.uniform(.04, .28), 2),
                "subscriber_count": subscribers, "days_since_published": age, "tag_count": tags, "ad_spend": ad_spend})
    print(f"Created {OUT}")

if __name__ == "__main__":
    main()
