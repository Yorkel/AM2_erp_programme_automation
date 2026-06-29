"""Two-agent categorisation panel. Agent A = topic lens, Agent B = editorial-purpose lens.
Agree -> confident. Disagree -> flag for the curator. Demonstrates disagreement = diagnostic."""
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
dash=pd.DataFrame(sb.table("v_dashboard").select("title,url,source,article_date,summary").execute().data)
dash["article_date"]=pd.to_datetime(dash["article_date"],errors="coerce")
dash=dash[(dash["article_date"]>=WIN_A)&(dash["article_date"]<=WIN_B+" 23:59:59")]
rej={r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action","reject").execute().data}
dash=dash[~dash["url"].isin(rej)]
man=pd.read_excel("agent_draft/ERPNewsletterSubmissions_June.xlsx",sheet_name="Sheet1").dropna(how="all")
man=man[man["Title"].notna() & (man["Title"].astype(str).str.strip().str.lower()!="end")]
pool=[]; seen=set()
for _,r in man.iterrows():
    k=norm(r["Title"])[:80]
    if k in seen: continue
    seen.add(k); pool.append({"id":f"M{len(pool)}","title":str(r["Title"]),"description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:250]})
for _,r in dash.iterrows():
    k=norm(r["title"])[:80]
    if k in seen: continue
    seen.add(k); pool.append({"id":f"P{len(pool)}","title":r["title"],"description":(r["summary"] or "")[:250]})
print(f"POOL: {len(pool)} items")
SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech","Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]

def categorise(lens):
    p=f"""Assign each item to ONE of these newsletter sections: {SECTIONS}.
{lens}
Return ONLY JSON: a list of {{"id","section"}}.
Items: {json.dumps(pool,ensure_ascii=False)}"""
    r=anthropic.Anthropic().messages.create(model="claude-opus-4-8",max_tokens=3000,messages=[{"role":"user","content":p}])
    arr=json.loads(re.search(r"\[.*\]",("".join(b.text for b in r.content if b.type=="text")),re.S).group(0))
    return {o["id"]:o["section"] for o in arr}

print("Agent A (topic lens)..."); A=categorise("Decide PURELY on the article's main SUBJECT MATTER - what it is about.")
print("Agent B (editorial-purpose lens)..."); B=categorise("Decide on the item's EDITORIAL PURPOSE for the newsletter's readers - what it is FOR and how a curator would file it, not just its surface topic.")

byid={it["id"]:it for it in pool}
agree=[i for i in A if A[i]==B.get(i)]
disagree=[i for i in A if A[i]!=B.get(i)]
print(f"\nAGREE (confident): {len(agree)}/{len(pool)} = {len(agree)/len(pool):.0%}")
print(f"DISAGREE (flag for curator): {len(disagree)}\n")
print(f'{"ITEM":50} | topic-agent        | purpose-agent')
print('-'*100)
for i in disagree:
    print(f'{byid[i]["title"][:50]:50} | {A[i][:18]:18} | {B.get(i,"?")[:22]}')
# which sections the disagreements involve
from collections import Counter
pairs=Counter(tuple(sorted([A[i],B.get(i,'?')])) for i in disagree)
print("\nMost common disagreement pairs:")
for pair,n in pairs.most_common(6): print(f"  {n}x  {pair[0]}  <->  {pair[1]}")
