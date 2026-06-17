"""Run the 3-voice panel across several weeks, print one summary line each."""
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
def norm(t): return re.sub(r"[^a-z0-9 ]",""," ".join(str(t).lower().split()))
CLF_MAP={'edtech':'EdTech','four_nations':'Four Nations','policy_practice_research':'Research – Practice – Policy','political_environment_key_organisations':'Political environment and key organisations','teacher_rrd':'Teacher recruitment, retention & development','what_matters_ed':'What matters in education?'}
SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech","Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]
sb=create_client(os.environ["SUPABASE_URL"],os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
DASH=pd.DataFrame(sb.table("v_dashboard").select("title,url,article_date,summary").execute().data); DASH["article_date"]=pd.to_datetime(DASH["article_date"],errors="coerce")
REJ={r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action","reject").execute().data}
MAN=pd.read_excel("agent_draft/ERPNewsletterSubmissions.xlsx",sheet_name="Sheet1").dropna(how="all"); MAN["Completion time"]=pd.to_datetime(MAN["Completion time"],errors="coerce")
MAN=MAN[MAN["Title"].notna() & (MAN["Title"].astype(str).str.strip().str.lower()!="end")]
ST=SentenceTransformer("all-MiniLM-L6-v2"); CLF=joblib.load("models/sbert_classifier_no_meta.joblib")
ant=anthropic.Anthropic(); oai=OpenAI()
def parse(t): return {o["id"]:o["section"] for o in json.loads(re.search(r"\[.*\]",t,re.S).group(0))}
def run(a,b,label):
    d=DASH[(DASH["article_date"]>=a)&(DASH["article_date"]<=b+" 23:59:59")]; d=d[~d["url"].isin(REJ)]
    m=MAN[(MAN["Completion time"]>=a)&(MAN["Completion time"]<=b+" 23:59:59")]
    pool=[]; seen=set()
    for _,r in m.iterrows():
        k=norm(r["Title"])[:80]
        if k not in seen: seen.add(k); pool.append({"id":str(len(pool)),"title":str(r["Title"]),"description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:250]})
    for _,r in d.iterrows():
        k=norm(r["title"])[:80]
        if k not in seen: seen.add(k); pool.append({"id":str(len(pool)),"title":r["title"],"description":(r["summary"] or "")[:250]})
    if not pool: print(f"{label}: no items"); return
    TASK=f"Assign each item to exactly ONE of these education-newsletter sections: {SECTIONS}.\nReturn ONLY a JSON array of objects with keys \"id\" and \"section\".\nItems: {json.dumps(pool,ensure_ascii=False)}"
    cla=parse("".join(bk.text for bk in ant.messages.create(model="claude-opus-4-8",max_tokens=3000,messages=[{"role":"user","content":TASK}]).content if bk.type=="text"))
    gpt=parse(oai.chat.completions.create(model="gpt-4o",messages=[{"role":"user","content":TASK}]).choices[0].message.content)
    clf={pool[i]["id"]:CLF_MAP.get(p,p) for i,p in enumerate(CLF.predict(ST.encode([(it["title"]+". "+it["description"]).strip() for it in pool],show_progress_bar=False)))}
    u=mj=fl=0
    for it in pool:
        i=it["id"]; c=Counter([cla.get(i,"?"),gpt.get(i,"?"),clf.get(i,"?")]); n=c.most_common(1)[0][1]
        u+=n==3; mj+=n==2; fl+=n==1
    print(f"{label:6} ({a} to {b}): pool {len(pool):3d} | unanimous {u:2d} | majority {mj:2d} | FLAG {fl:2d}  -> review {fl} of {len(pool)}")
print("week    (window)                          pool | 3/3 | 2/3 | flag")
run("2026-05-19","2026-05-26","#113")
run("2026-05-26","2026-06-02","#114")
run("2026-06-02","2026-06-09","#115")
run("2026-06-09","2026-06-15","#116")
