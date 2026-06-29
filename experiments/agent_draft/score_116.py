"""Score the #116 panel against the REAL published #116 (from Gemma's email): recall + categorisation + flag-alignment."""
import os, re, json, joblib, pandas as pd
from collections import Counter
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    for k in ["ANTHROPIC_API_KEY","OPENAI_API_KEY","SUPABASE_URL","SUPABASE_SERVICE_KEY","SUPABASE_ANON_KEY"]:
        if line.startswith(k): os.environ[k]=line.split("=",1)[1].strip().strip('"').strip("'")
from supabase import create_client
import anthropic
from openai import OpenAI
from sentence_transformers import SentenceTransformer
def norm(t): return re.sub(r"[^a-z0-9 ]","",str(t).lower())
WIN_A,WIN_B="2026-06-09","2026-06-15"
CLF_MAP={'edtech':'EdTech','four_nations':'Four Nations','policy_practice_research':'Research – Practice – Policy','political_environment_key_organisations':'Political environment and key organisations','teacher_rrd':'Teacher recruitment, retention & development','what_matters_ed':'What matters in education?'}
SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech","Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]
# --- REAL published #116 (keyword -> section Gemma filed it under) ---
PUB=[("research sharing event","Update from PI / Programme"),("digital empowerment in language","Update from PI / Programme"),
("70 of 6500","Teacher recruitment, retention & development"),("4500 bonus","Teacher recruitment, retention & development"),("innovative and creative pedagogy","Teacher recruitment, retention & development"),
("under 16 social media ban","EdTech"),("statement from the childrens commissioner","EdTech"),("use of artificial intelligence and edtech","EdTech"),("secondary teachers uses and perceptions","EdTech"),("generative ai on learning and cognition","EdTech"),
("early education partnerships guide","Political environment and key organisations"),("initial teacher education ite inspection","Political environment and key organisations"),("every child to get access to enriching","Political environment and key organisations"),("growing apart","Political environment and key organisations"),("children and young peoples reading in 2026","Political environment and key organisations"),
("education hasnt been doing as well","Four Nations"),("ascl cymru comment on initial teacher","Four Nations"),("scottish schools cutting subjects","Four Nations"),
("hidden ref","Research – Practice – Policy"),("six camps of metascience","Research – Practice – Policy"),
("should we stream","What matters in education?"),("growing up in the unequal kingdom","What matters in education?"),("breaking the mould","What matters in education?")]

sb=create_client(os.environ["SUPABASE_URL"],os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
d=pd.DataFrame(sb.table("v_dashboard").select("title,url,article_date,summary").execute().data); d["article_date"]=pd.to_datetime(d["article_date"],errors="coerce")
d=d[(d["article_date"]>=WIN_A)&(d["article_date"]<=WIN_B+" 23:59:59")]
rej={r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action","reject").execute().data}; d=d[~d["url"].isin(rej)]
m=pd.read_excel("agent_draft/ERPNewsletterSubmissions.xlsx",sheet_name="Sheet1").dropna(how="all"); m["Completion time"]=pd.to_datetime(m["Completion time"],errors="coerce")
m=m[m["Title"].notna() & (m["Title"].astype(str).str.strip().str.lower()!="end")]; m=m[(m["Completion time"]>=WIN_A)&(m["Completion time"]<=WIN_B+" 23:59:59")]
pool=[]; seen=set()
for _,r in m.iterrows():
    k=norm(r["Title"])[:80]
    if k not in seen: seen.add(k); pool.append({"id":str(len(pool)),"title":str(r["Title"]),"description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:250]})
for _,r in d.iterrows():
    k=norm(r["title"])[:80]
    if k not in seen: seen.add(k); pool.append({"id":str(len(pool)),"title":r["title"],"description":(r["summary"] or "")[:250]})
print(f"POOL: {len(pool)} items")
# --- 3-voice panel ---
TASK=f"Assign each item to exactly ONE of these education-newsletter sections: {SECTIONS}.\nReturn ONLY a JSON array of objects with keys \"id\" and \"section\".\nItems: {json.dumps(pool,ensure_ascii=False)}"
def parse(t): return {o["id"]:o["section"] for o in json.loads(re.search(r"\[.*\]",t,re.S).group(0))}
CLA=parse("".join(b.text for b in anthropic.Anthropic().messages.create(model="claude-opus-4-8",max_tokens=3000,messages=[{"role":"user","content":TASK}]).content if b.type=="text"))
GPT=parse(OpenAI().chat.completions.create(model="gpt-4o",messages=[{"role":"user","content":TASK}]).choices[0].message.content)
ST=SentenceTransformer("all-MiniLM-L6-v2"); clf=joblib.load("models/sbert_classifier_no_meta.joblib")
CLF={pool[i]["id"]:CLF_MAP.get(p,p) for i,p in enumerate(clf.predict(ST.encode([(it["title"]+". "+it["description"]).strip() for it in pool],show_progress_bar=False)))}
def majority(i):
    c=Counter([CLA.get(i,"?"),GPT.get(i,"?"),CLF.get(i,"?")]); top,n=c.most_common(1)[0]
    return (top if n>=2 else "FLAG"), n
pool_norm={it["id"]:norm(it["title"]) for it in pool}
# --- recall + categorisation vs published ---
in_pool=cat_ok=cat_tot=0; missing=[]
print(f"\n{'PUBLISHED #116 ITEM':40} | in pool | panel section vs Gemma")
print('-'*100)
for kw,realsec in PUB:
    k=norm(kw); hit=[i for i,t in pool_norm.items() if k in t]
    if not hit: missing.append(kw); print(f"{kw[:40]:40} | NO (not in pool)"); continue
    in_pool+=1; sec,n=majority(hit[0]); cat_tot+=1
    ok = sec!='FLAG' and norm(sec)==norm(realsec); cat_ok+=ok
    print(f"{kw[:40]:40} | yes     | {('OK ' if ok else 'XX ')}{sec[:26]:26} (Gemma: {realsec[:22]})")
print('-'*100)
print(f"\nRECALL: {in_pool}/{len(PUB)} of published #116 items were in our candidate pool")
print(f"CATEGORISATION: panel section matched Gemma on {cat_ok}/{cat_tot} of the items in the pool")
