"""Cross-model panel: Claude Opus vs GPT-4o categorise the same pool. Agree = confident, disagree = flag."""
import os, re, json, pandas as pd
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    for k in ["ANTHROPIC_API_KEY","OPENAI_API_KEY","SUPABASE_URL","SUPABASE_SERVICE_KEY","SUPABASE_ANON_KEY"]:
        if line.startswith(k): os.environ[k]=line.split("=",1)[1].strip().strip('"').strip("'")
from supabase import create_client
import anthropic
from openai import OpenAI
WIN_A,WIN_B="2026-06-02","2026-06-09"
def norm(t): return re.sub(r"[^a-z0-9 ]",""," ".join(str(t).lower().split()))
sb=create_client(os.environ["SUPABASE_URL"],os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
dash=pd.DataFrame(sb.table("v_dashboard").select("title,url,article_date,summary").execute().data)
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
    seen.add(k); pool.append({"id":f"{len(pool)}","title":str(r["Title"]),"description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:250]})
for _,r in dash.iterrows():
    k=norm(r["title"])[:80]
    if k in seen: continue
    seen.add(k); pool.append({"id":f"{len(pool)}","title":r["title"],"description":(r["summary"] or "")[:250]})
print(f"POOL: {len(pool)} items")
SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech","Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]
TASK=f"""Assign each item to exactly ONE of these education-newsletter sections: {SECTIONS}.
Return ONLY a JSON array of objects with keys "id" and "section".
Items: {json.dumps(pool,ensure_ascii=False)}"""

def parse(txt): return {o["id"]:o["section"] for o in json.loads(re.search(r"\[.*\]",txt,re.S).group(0))}
print("Claude Opus..."); 
ar=anthropic.Anthropic().messages.create(model="claude-opus-4-8",max_tokens=3000,messages=[{"role":"user","content":TASK}])
CLA=parse("".join(b.text for b in ar.content if b.type=="text"))
print("GPT-4o...")
gr=OpenAI().chat.completions.create(model="gpt-4o",messages=[{"role":"user","content":TASK}])
GPT=parse(gr.choices[0].message.content)

byid={it["id"]:it for it in pool}
both=[i for i in CLA if i in GPT]
agree=[i for i in both if CLA[i]==GPT[i]]; dis=[i for i in both if CLA[i]!=GPT[i]]
print(f"\nAGREE (confident): {len(agree)}/{len(both)} = {len(agree)/len(both):.0%}")
print(f"DISAGREE (flag for curator): {len(dis)}\n")
print(f'{"ITEM":48} | Claude              | GPT-4o')
print('-'*100)
for i in dis:
    print(f'{byid[i]["title"][:48]:48} | {CLA[i][:18]:18} | {GPT.get(i,"?")[:24]}')
from collections import Counter
pairs=Counter(tuple(sorted([CLA[i],GPT[i]])) for i in dis)
print("\nDisagreement boundaries:")
for p,n in pairs.most_common(): print(f"  {n}x  {p[0]}  <->  {p[1]}")
