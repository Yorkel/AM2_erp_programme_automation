"""#115 trial v2: caps (max 4/section, max 18 total) + prioritisation + composite_score tie-break."""
import os, re, json, difflib, pandas as pd
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    for k in ["ANTHROPIC_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","SUPABASE_SERVICE_KEY"]:
        if line.startswith(k): os.environ[k]=line.split("=",1)[1].strip().strip('"').strip("'")
from supabase import create_client
import anthropic
WIN_A,WIN_B="2026-06-02","2026-06-09"
def norm(t): return re.sub(r"[^a-z0-9 ]",""," ".join(str(t).lower().split()))[:80]

sb=create_client(os.environ["SUPABASE_URL"],os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
dash=pd.DataFrame(sb.table("v_dashboard").select("title,url,source,article_date,top1,summary,composite_score,country").execute().data)
dash["article_date"]=pd.to_datetime(dash["article_date"],errors="coerce")
dash=dash[(dash["article_date"]>=WIN_A)&(dash["article_date"]<=WIN_B+" 23:59:59")]
rej={r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action","reject").execute().data}
dash=dash[~dash["url"].isin(rej)]
dash_items=[{"id":f"D{i}","origin":"dashboard","title":r["title"],"source":r["source"],"country":r.get("country"),
  "description":(r["summary"] or "")[:300],"suggested_section":r["top1"],
  "composite_score":None if pd.isna(r["composite_score"]) else round(float(r["composite_score"]),3)}
  for i,(_,r) in enumerate(dash.iterrows())]

man=pd.read_excel("agent_draft/ERPNewsletterSubmissions_June.xlsx",sheet_name="Sheet1").dropna(how="all")
man=man[man["Title"].notna() & (man["Title"].astype(str).str.strip().str.lower()!="end")]
man_items=[{"id":f"M{i}","origin":"manual","title":str(r["Title"]),
  "source":"" if pd.isna(r["Organisation"]) else str(r["Organisation"]),
  "description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:300],
  "suggested_section":None if pd.isna(r["Which section of the newsletter is this for?"]) else str(r["Which section of the newsletter is this for?"]),
  "composite_score":None} for i,(_,r) in enumerate(man.iterrows())]

seen={}; pool=[]
for it in man_items+dash_items:
    k=norm(it["title"])
    if k in seen: continue
    seen[k]=1; pool.append(it)
print(f"POOL: {len(pool)} items ({len(man_items)} manual + {len(dash_items)} dashboard, deduped)")

SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech",
 "Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]
prompt=f"""You assist the curators of the ESRC Education Research Programme weekly newsletter (issue #115).
Scope: UK schools, pre-higher-education and further education, across the four nations and Ireland. Pure higher-education-sector content is out of scope.
Sections, in order: {SECTIONS}

HARD LIMITS: at most 4 items per section, at most 18 items in total. A normal issue is about 11 to 15 items, so be selective and cut.

PRIORITISATION when there are more good items than slots, prefer:
1. Timely items tied to a live policy moment or a just-released report.
2. Substance: research, evaluations and data over thin news.
3. Clear scope fit (schools / pre-HE / FE; the four nations).
4. Source spread: do not let one outlet dominate a section.
5. National balance: make sure the four nations are represented where possible.
6. Unique items that others are likely to miss.
7. Avoid near-duplicates: one story per theme.
Use composite_score (higher is better) only as a tie-break when items are otherwise equal.

For each item return decision include/exclude with a one-clause reason. For included items give the final section (keep suggested_section unless clearly wrong).
Return ONLY JSON: {{"decisions":[{{"id","section","decision","reason"}}],"draft_markdown":"the issue grouped by section in order, each item as **Source - Headline** then one or two factual sentences, no em dashes"}}.

Candidate pool:
{json.dumps(pool,ensure_ascii=False)}"""
print("calling Opus...")
resp=anthropic.Anthropic().messages.create(model="claude-opus-4-8",max_tokens=8000,messages=[{"role":"user","content":prompt}])
obj=json.loads(re.search(r"\{.*\}",("".join(b.text for b in resp.content if b.type=="text")),re.S).group(0))
dec=pd.DataFrame(obj["decisions"]); byid={it["id"]:it for it in pool}
dec["title"]=dec["id"].map(lambda i:byid.get(i,{}).get("title",""))
inc=dec[dec["decision"]=="include"]
print(f"\nKept {len(inc)} of {len(pool)}   (cap 18)")
print("Per section:"); print(inc["section"].value_counts().to_string())
PUB=[("Anthropology and Education Quarterly","Uncovering edtech embedded values"),("Schools Week","Secondary teacher job adverts historic low"),("BBC","Falling pupil numbers smaller class sizes"),("University of Cambridge","Limitations of technical fixes in AI policy"),("The Guardian","London school screen-free days"),("DfE","Free breakfast club early adopters"),("Committees","Children and young people mental health inquiry"),("Schools Week","Schools government route buy Management Information Systems"),("Scottish Government","Phone-free learning Scottish schools"),("Department of Education Northern Ireland","Givan award professional learning programme"),("N8","Equitable access to play"),("Coram","Fairness in school exclusions"),("BBC","Ministers guidance children screen use"),("Headteacher Update","Invitation to inspection"),("Fair Education Alliance","Five things government SEND reforms"),("Nuffield Foundation","I love it but I hate it growing up digital"),("UNESCO","When multilateralism fractures")]
def hit(t,c): return bool(difflib.get_close_matches(norm(t),[norm(x) for x in c],n=1,cutoff=0.5))
recalled=sum(hit(t,list(inc["title"])) for _,t in PUB)
print(f"\nRecall vs published #115: agent kept {recalled}/17 of the published items")
Path("agent_draft/draft_115_v2.md").write_text(obj["draft_markdown"])
print("saved -> agent_draft/draft_115_v2.md")
