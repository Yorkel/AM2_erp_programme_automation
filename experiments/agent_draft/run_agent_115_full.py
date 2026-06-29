"""Faithful #115 trial: merge manual Excel + non-rejected dashboard items, run the agent (Opus)
to select + draft, score against the published #115."""
import os, re, json, difflib, pandas as pd
from pathlib import Path

for line in Path(".env").read_text().splitlines():
    for k in ["ANTHROPIC_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","SUPABASE_SERVICE_KEY"]:
        if line.startswith(k): os.environ[k]=line.split("=",1)[1].strip().strip('"').strip("'")
from supabase import create_client
import anthropic

WIN_A, WIN_B = "2026-06-02", "2026-06-09"
def norm(t): return re.sub(r"[^a-z0-9 ]",""," ".join(str(t).lower().split()))[:80]

# ---- dashboard pool (minus rejects) ----
sb = create_client(os.environ["SUPABASE_URL"], os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
dash = pd.DataFrame(sb.table("v_dashboard").select("title,url,source,article_date,top1,top1_confidence,summary").execute().data)
dash["article_date"] = pd.to_datetime(dash["article_date"], errors="coerce")
dash = dash[(dash["article_date"]>=WIN_A)&(dash["article_date"]<=WIN_B+" 23:59:59")]
rejects = {r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action","reject").execute().data}
dash = dash[~dash["url"].isin(rejects)].copy()
dash_items = [{"id":f"D{i}","origin":"dashboard","title":r["title"],"source":r["source"],
               "description":(r["summary"] or "")[:300],"suggested_section":r["top1"]} for i,(_,r) in enumerate(dash.iterrows())]

# ---- manual Excel pool ----
man = pd.read_excel("agent_draft/ERPNewsletterSubmissions_June.xlsx",sheet_name="Sheet1").dropna(how="all")
man = man[man["Title"].notna() & (man["Title"].astype(str).str.strip().str.lower()!="end")]
man_items = [{"id":f"M{i}","origin":"manual","title":str(r["Title"]),
              "source":"" if pd.isna(r["Organisation"]) else str(r["Organisation"]),
              "description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:300],
              "suggested_section":None if pd.isna(r["Which section of the newsletter is this for?"]) else str(r["Which section of the newsletter is this for?"])}
             for i,(_,r) in enumerate(man.iterrows())]

# ---- merge + dedup by normalised title (keep manual over dashboard) ----
seen={}; pool=[]
for it in man_items+dash_items:
    k=norm(it["title"])
    if k in seen: continue
    seen[k]=1; pool.append(it)
print(f"POOL: {len(man_items)} manual + {len(dash_items)} non-rejected dashboard "
      f"-> {len(pool)} after dedup  (rejected {len(rejects)} dashboard URLs removed)")

# ---- agent (Opus) ----
SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech",
 "Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]
prompt=f"""You are assisting the curators of the ESRC Education Research Programme weekly newsletter (issue #115).
Scope: UK schools, pre-higher-education and further education, across the four nations and Ireland. Pure higher-education-sector content is out of scope.
The seven sections, in order: {SECTIONS}

You are given a merged candidate pool (manual submissions + dashboard items that survived curator filtering). Each may carry a suggested_section.
Tasks:
1. Drop duplicates and near-duplicates (same story).
2. For each item: decision "include" or "exclude" with a one-clause reason (e.g. duplicate, off-scope, out of date, thin, strong fit). Be selective - a typical issue has ~15-18 items, so reject generously.
3. For included items, give the final section (keep suggested_section unless clearly wrong).

Return ONLY JSON: {{"decisions":[{{"id","section","decision","reason"}}], "draft_markdown":"the assembled issue, grouped by section in order, each item as **Source - Headline** then one or two factual sentences, no em dashes"}}.

Candidate pool:
{json.dumps(pool, ensure_ascii=False)}"""
client=anthropic.Anthropic()
print("calling Opus...")
resp=client.messages.create(model="claude-opus-4-8",max_tokens=8000,messages=[{"role":"user","content":prompt}])
txt="".join(b.text for b in resp.content if b.type=="text")
obj=json.loads(re.search(r"\{.*\}",txt,re.S).group(0))
dec=pd.DataFrame(obj["decisions"]); 
byid={it["id"]:it for it in pool}
dec["title"]=dec["id"].map(lambda i: byid.get(i,{}).get("title",""))
inc=dec[dec["decision"]=="include"]
print(f"\nAgent kept {len(inc)} of {len(pool)}")

# ---- score vs published #115 (17 items) ----
PUB=[("Anthropology and Education Quarterly","Uncovering edtech's embedded values"),("Schools Week","Secondary teacher job adverts hit a historic low"),
("BBC","Falling pupil numbers should lead to smaller class sizes"),("University of Cambridge","Limitations of technical fixes in AI policy"),
("The Guardian","The London school that has screen-free days"),("DfE","Free breakfast club early adopters"),
("Education and Health and Social Care Committees","Children and young people's mental health inquiry"),("Schools Week","Schools expected to use government route to buy Management Information Systems"),
("Scottish Government","Phone-free learning in Scottish schools"),("Department of Education Northern Ireland","Givan announces award of professional learning programme"),
("The N8 Research Partnership","Equitable access to play"),("Coram","Fairness in school exclusions"),
("BBC","Ministers to issue guidance on children's screen use"),("Headteacher Update","Invitation to inspection"),
("Fair Education Alliance","Five things the government can do to ensure SEND reforms"),("Nuffield Foundation","I love it, but I hate it"),
("UNESCO","When multilateralism fractures")]
def best(t, cands): 
    m=difflib.get_close_matches(norm(t),[norm(c) for c in cands],n=1,cutoff=0.5); return m[0] if m else None
pool_titles=[it["title"] for it in pool]; inc_titles=list(inc["title"])
in_pool=sum(best(t,pool_titles) is not None for _,t in PUB)
recalled=sum(best(t,inc_titles) is not None for _,t in PUB)
print(f"\nPublished #115: {len(PUB)} items")
print(f"  present in our candidate pool (recall ceiling): {in_pool}/{len(PUB)}")
print(f"  the agent kept: {recalled}/{len(PUB)}  (of the {in_pool} that were reachable)")
print("\n--- agent decisions (sample) ---")
with pd.option_context("display.max_colwidth",50,"display.width",200):
    print(dec[["id","decision","section","reason"]].head(25).to_string(index=False))
Path("agent_draft/draft_115.md").write_text(obj["draft_markdown"])
dec.to_csv("agent_draft/decisions_115.csv",index=False)
print("\nsaved -> agent_draft/draft_115.md  and  decisions_115.csv")
