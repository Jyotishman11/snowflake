"""ETL, local dimensional warehouse, OLAP summaries, linear-regression prediction, and SVG charts."""
from pathlib import Path
import csv, math, statistics
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
RAW, PROCESSED, REPORTS = ROOT / "data/raw/youtube_trending.csv", ROOT / "data/processed", ROOT / "reports"
NUMERIC = ["views", "likes", "comments", "shares", "watch_time_minutes", "subscriber_count", "days_since_published", "tag_count", "ad_spend"]

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def load_clean():
    clean, rejected = [], []
    with RAW.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                if not row["video_id"] or not row["category"] or not row["region"]: raise ValueError("missing business key")
                for col in NUMERIC: row[col] = float(row[col])
                if any(row[c] < 0 for c in NUMERIC): raise ValueError("negative metric")
                row["title_length"] = len(row["title"].strip())
                clean.append(row)
            except (ValueError, KeyError) as e:
                row["reject_reason"] = str(e); rejected.append(row)
    write_csv(PROCESSED / "cleaned_youtube_trending.csv", clean, list(clean[0]))
    if rejected: write_csv(PROCESSED / "rejected_rows.csv", rejected, list(rejected[0]))
    return clean

def warehouse(rows):
    dates = sorted({r["trending_date"] for r in rows}); geos = sorted({r["region"] for r in rows})
    channels = sorted({r["channel_type"] for r in rows}); cats = sorted({r["category"] for r in rows})
    ddate = [{"date_key": i+1, "full_date": x, "year": x[:4], "month": x[5:7], "day": x[8:]} for i,x in enumerate(dates)]
    dgeo = [{"geography_key": i+1, "region": x} for i,x in enumerate(geos)]
    dchannel = [{"channel_key": i+1, "channel_type": x} for i,x in enumerate(channels)]
    dcat = [{"category_key": i+1, "category_name": x} for i,x in enumerate(cats)]
    datekey, geokey, channelkey, catkey = ({x[k]:x["%s_key" % n] for x in arr} for arr,k,n in [(ddate,"full_date","date"),(dgeo,"region","geography"),(dchannel,"channel_type","channel"),(dcat,"category_name","category")])
    subs = sorted({(r["subcategory"], r["category"]) for r in rows})
    dsub = [{"subcategory_key": i+1,"subcategory_name": s,"category_key":catkey[c]} for i,(s,c) in enumerate(subs)]
    subkey = {x["subcategory_name"]: x["subcategory_key"] for x in dsub}
    minv, maxv = min(r["views"] for r in rows), max(r["views"] for r in rows)
    fact=[]
    for i,r in enumerate(rows, 1):
        score = 100 * (.70*(r["views"]-minv)/(maxv-minv) + .20*min(1,r["likes"]/max(r["views"],1)*10) + .10*min(1,r["shares"]/max(r["views"],1)*25))
        fact.append({"trend_fact_key":i,"video_id":r["video_id"],"date_key":datekey[r["trending_date"]],"geography_key":geokey[r["region"]],"channel_key":channelkey[r["channel_type"]],"subcategory_key":subkey[r["subcategory"]],"views":round(r["views"]),"likes":round(r["likes"]),"comments":round(r["comments"]),"shares":round(r["shares"]),"watch_time_minutes":round(r["watch_time_minutes"],2),"subscriber_count":round(r["subscriber_count"]),"days_since_published":round(r["days_since_published"]),"tag_count":round(r["tag_count"]),"ad_spend":round(r["ad_spend"],2),"title_length":r["title_length"],"popularity_score":round(score,4)})
    for name, data in [("dim_date",ddate),("dim_geography",dgeo),("dim_channel",dchannel),("dim_category",dcat),("dim_subcategory",dsub),("fact_video_trending",fact)]: write_csv(PROCESSED/(name+".csv"),data,list(data[0]))
    return fact, dgeo, dchannel, dsub, dcat

def olap(fact, geos, channels, subs, cats):
    geo = {x["geography_key"]:x["region"] for x in geos}; channel={x["channel_key"]:x["channel_type"] for x in channels}; sub={x["subcategory_key"]:x["subcategory_name"] for x in subs}; cat={x["category_key"]:x["category_name"] for x in cats}; subcat={x["subcategory_key"]:cat[x["category_key"]] for x in subs}
    aggregates=defaultdict(lambda:[0,0,0])
    for r in fact:
        for level,key in [("category",subcat[r["subcategory_key"]]),("region",geo[r["geography_key"]]),("channel",channel[r["channel_key"]])]:
            a=aggregates[(level,key)]; a[0]+=r["views"];a[1]+=r["likes"];a[2]+=r["popularity_score"]
    rows=[{"dimension":d,"member":m,"total_views":v[0],"total_likes":v[1],"avg_popularity_score":round(v[2]/sum(1 for r in fact if (d=="category" and subcat[r["subcategory_key"]]==m) or (d=="region" and geo[r["geography_key"]]==m) or (d=="channel" and channel[r["channel_key"]]==m)),2)} for (d,m),v in aggregates.items()]
    write_csv(REPORTS/"olap_summary.csv", rows, list(rows[0])); return rows

def solve(a,b):
    # Gauss-Jordan solver used by normal-equation linear regression.
    n=len(b); aug=[a[i][:]+[b[i]] for i in range(n)]
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:abs(aug[r][col])); aug[col],aug[pivot]=aug[pivot],aug[col]
        div=aug[col][col]
        if abs(div)<1e-10: return [0]*n
        aug[col]=[x/div for x in aug[col]]
        for r in range(n):
            if r!=col:
                f=aug[r][col]; aug[r]=[aug[r][j]-f*aug[col][j] for j in range(n+1)]
    return [r[-1] for r in aug]

def predict(fact):
    channels=sorted({r["channel_key"] for r in fact}); subs=sorted({r["subcategory_key"] for r in fact}); geos=sorted({r["geography_key"] for r in fact})
    def features(r): return [1, math.log1p(r["subscriber_count"]),r["days_since_published"],r["tag_count"],math.log1p(r["ad_spend"]),r["title_length"]]+[int(r["channel_key"]==x) for x in channels[1:]]+[int(r["subcategory_key"]==x) for x in subs[1:]]+[int(r["geography_key"]==x) for x in geos[1:]]
    train,test=fact[:int(.8*len(fact))],fact[int(.8*len(fact)):]; x=[features(r) for r in train]; y=[r["popularity_score"] for r in train]; p=len(x[0]); lam=.05
    a=[[sum(row[i]*row[j] for row in x)+(lam if i==j and i else 0) for j in range(p)] for i in range(p)]; b=[sum(row[i]*target for row,target in zip(x,y)) for i in range(p)]; beta=solve(a,b)
    actual=[r["popularity_score"] for r in test]; predicted=[max(0,min(100,sum(v*w for v,w in zip(features(r),beta)))) for r in test]; mae=sum(abs(a-b) for a,b in zip(actual,predicted))/len(test); mean=statistics.mean(actual); r2=1-sum((a-b)**2 for a,b in zip(actual,predicted))/sum((a-mean)**2 for a in actual)
    write_csv(REPORTS/"predictions.csv", [{"video_id":r["video_id"],"actual_popularity_score":round(a,2),"predicted_popularity_score":round(b,2)} for r,a,b in zip(test,actual,predicted)], ["video_id","actual_popularity_score","predicted_popularity_score"])
    (REPORTS/"model_metrics.txt").write_text(f"Model: ridge linear regression (lambda={lam})\nTrain/test split: 80/20 chronological CSV order\nTest MAE: {mae:.3f}\nTest R²: {r2:.3f}\nFeatures exclude views, likes, comments, shares and watch time to limit target leakage.\n",encoding="utf-8")
    return actual,predicted

def svg_bar(path,title,labels,values,color="#ff4e45"):
    width,height,pad=900,460,70; mx=max(values); step=(width-2*pad)/len(values)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"><rect width="100%" height="100%" fill="#fffaf7"/><text x="{pad}" y="35" font-size="20" font-family="Arial" font-weight="bold">{title}</text><line x1="{pad}" y1="390" x2="850" y2="390" stroke="#555"/>']
    for i,(lab,val) in enumerate(zip(labels,values)):
        h=280*val/mx; x=pad+i*step+20;parts.append(f'<rect x="{x:.1f}" y="{390-h:.1f}" width="{step-40:.1f}" height="{h:.1f}" fill="{color}"/><text x="{x:.1f}" y="410" font-size="11" font-family="Arial">{lab[:15]}</text><text x="{x:.1f}" y="{380-h:.1f}" font-size="10" font-family="Arial">{val/1e6:.1f}M</text>')
    path.write_text("".join(parts)+"</svg>",encoding="utf-8")

def main():
    if not RAW.exists(): raise SystemExit("Input missing. Run generate_sample_data.py or provide data/raw/youtube_trending.csv")
    PROCESSED.mkdir(parents=True,exist_ok=True); REPORTS.mkdir(parents=True,exist_ok=True)
    clean=load_clean(); fact,geos,channels,subs,cats=warehouse(clean); summary=olap(fact,geos,channels,subs,cats); actual,predicted=predict(fact)
    cat=[r for r in summary if r["dimension"]=="category"]; region=[r for r in summary if r["dimension"]=="region"]
    svg_bar(REPORTS/"views_by_category.svg","Total Trending Views by Category",[r["member"] for r in cat],[r["total_views"] for r in cat])
    svg_bar(REPORTS/"views_by_region.svg","Total Trending Views by Region",[r["member"] for r in region],[r["total_views"] for r in region],"#4169e1")
    print(f"Processed {len(clean)} records. Outputs: {REPORTS}")

if __name__=="__main__": main()
