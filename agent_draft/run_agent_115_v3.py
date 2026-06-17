"""#115 trial v3: OVER-SAMPLE + RANK. Agent does not make the final cut; it returns a ranked
shortlist (up to 5/section) for the curator to trim. Measure recall vs published #115."""
import os, re, json, pandas as pd
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    for k in ["ANTHROPIC_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","SUPABASE_SERVICE_KEY"]:
        if line.startswith(k): os.environ[k]=line.split("=",1)[1].strip().strip('"').strip("'")
from supabase import create_client
import anthropic
WIN_A,WIN_B="2026-06-02","2026-06-09"
def norm(t): return re.sub(r"[^a-z0-9 ]",""," ".join(str(t).lower().split()))

sb=create_client(os.environ["SUPABASE_URL"],os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
dash=pd.DataFrame(sb.table("v_dashboard").select("title,url,source,article_date,top1,summary,composite_score,country").execute().data)
dash["article_date"]=pd.to_datetime(dash["article_date"],errors="coerce")
dash=dash[(dash["article_date"]>=WIN_A)&(dash["article_date"]<=WIN_B+" 23:59:59")]
rej={r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action","reject").execute().data}
dash=dash[~dash["url"].isin(rej)]
dash_items=[{"id":f"D{i}","origin":"dashboard","title":r["title"],"source":r["source"],"country":r.get("country"),
  "description":(r["summary"] or "")[:300],"suggested_section":r["top1"],
  "composite_score":None if pd.isna(r["composite_score"]) else round(float(r["composite_score"]),3)} for i,(_,r) in enumerate(dash.iterrows())]
man=pd.read_excel("agent_draft/ERPNewsletterSubmissions_June.xlsx",sheet_name="Sheet1").dropna(how="all")
man=man[man["Title"].notna() & (man["Title"].astype(str).str.strip().str.lower()!="end")]
man_items=[{"id":f"M{i}","origin":"manual","title":str(r["Title"]),"source":"" if pd.isna(r["Organisation"]) else str(r["Organisation"]),
  "description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:300],
  "suggested_section":None if pd.isna(r["Which section of the newsletter is this for?"]) else str(r["Which section of the newsletter is this for?"]),
  "composite_score":None} for i,(_,r) in enumerate(man.iterrows())]
seen={}; pool=[]
for it in man_items+dash_items:
    k=norm(it["title"])[:80]
    if k in seen: continue
    seen[k]=1; pool.append(it)
print(f"POOL: {len(pool)} items")

SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech","Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]
prompt=f"""You assist the curators of the ESRC Education Research Programme weekly newsletter (issue #115).
Scope: UK schools, pre-HE and FE, across the four nations and Ireland. Pure higher-education-sector content is out of scope.
Sections, in order: {SECTIONS}

DO NOT make the final selection. Your job is to give the curator a generous, RANKED shortlist to choose from.
- Place every candidate in its best section.
- Within each section, rank best-first and keep up to 5 as a shortlist.
- Exclude ONLY clear duplicates, clearly off-scope, or out-of-date items. When unsure, keep it in the shortlist.
- Rank by: timeliness, substance (research/evaluations/data), scope fit, source spread, national balance, uniqueness. Use composite_score (higher better) only as a tie-break.

Return ONLY JSON: {{"shortlist":[{{"id","section","rank","reason"}}], "draft_markdown":"shortlist grouped by section in order, best-first, each as **Source - Headline** then one or two factual sentences, no em dashes"}}.

Candidate pool:
{json.dumps(pool,ensure_ascii=False)}"""
print("calling Opus...")
resp=anthropic.Anthropic().messages.create(model="claude-opus-4-8",max_tokens=8000,messages=[{"role":"user","content":prompt}])
obj=json.loads(re.search(r"\{.*\}",("".join(b.text for b in resp.content if b.type=="text")),re.S).group(0))
sl=pd.DataFrame(obj["shortlist"]); byid={it["id"]:it for it in pool}
sl["title"]=sl["id"].map(lambda i:byid.get(i,{}).get("title",""))
print(f"\nShortlist: {len(sl)} items")
print(sl["section"].value_counts().to_string())

# recall vs published #115, verifiable per-item via keywords on shortlist titles
sl_text=" || ".join(norm(t) for t in sl["title"])
PUB=[('Uncovering edtech embedded values (PI)','embedded values'),('Schools Week - teacher job adverts','job adverts'),
('BBC - Falling pupil numbers','falling pupil'),('Cambridge - technical fixes in AI','technical fixes'),
('Guardian - screen-free days','screenfree'),('DfE - breakfast club','breakfast club'),
('Committees - mental health inquiry','mental health'),('Schools Week - buy MIS','management information'),
('Scottish Govt - phone-free','phonefree'),('NI - Givan programme','givan'),('N8 - access to play','access to play'),
('Coram - school exclusions','school exclusions'),('BBC - children screen use','screen use'),
('Headteacher Update - invitation to inspection','invitation to inspection'),('Fair Education - five things SEND','five things'),
('Nuffield - love it hate it','i love it'),('UNESCO - multilateralism','multilateralism')]
print(f'\n{"PUBLISHED #115 ITEM":46} | in shortlist?')
print('-'*64); n=0
for lab,kw in PUB:
    hit = kw.replace(" ","") in sl_text.replace(" ","")
    n+=hit; print(f'{lab:46} |   {"YES" if hit else " - "}')
print('-'*64); print(f'{"RECALL: of 17 published items, in shortlist":46} |   {n}/17')
Path("agent_draft/draft_115_shortlist.md").write_text(obj["draft_markdown"])
sl.to_csv("agent_draft/shortlist_115.csv",index=False)
print("\nsaved -> agent_draft/draft_115_shortlist.md  and  shortlist_115.csv")
