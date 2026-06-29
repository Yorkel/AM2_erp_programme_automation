"""Three-voice panel: Claude Opus + GPT-4o + your classifier. Majority (>=2) wins; 3-way split = flag."""
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
WIN_A,WIN_B="2026-06-09","2026-06-15"
def norm(t): return re.sub(r"[^a-z0-9 ]",""," ".join(str(t).lower().split()))
CLF_MAP={'edtech':'EdTech','four_nations':'Four Nations','policy_practice_research':'Research – Practice – Policy',
 'political_environment_key_organisations':'Political environment and key organisations',
 'teacher_rrd':'Teacher recruitment, retention & development','what_matters_ed':'What matters in education?'}

sb=create_client(os.environ["SUPABASE_URL"],os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
dash=pd.DataFrame(sb.table("v_dashboard").select("title,url,article_date,summary").execute().data)
dash["article_date"]=pd.to_datetime(dash["article_date"],errors="coerce")
dash=dash[(dash["article_date"]>=WIN_A)&(dash["article_date"]<=WIN_B+" 23:59:59")]
rej={r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action","reject").execute().data}
dash=dash[~dash["url"].isin(rej)]
man=pd.read_excel("agent_draft/ERPNewsletterSubmissions.xlsx",sheet_name="Sheet1").dropna(how="all")
man=man[man["Title"].notna() & (man["Title"].astype(str).str.strip().str.lower()!="end")]
man["Completion time"]=pd.to_datetime(man["Completion time"],errors="coerce")
man=man[(man["Completion time"]>=WIN_A)&(man["Completion time"]<=WIN_B+" 23:59:59")]
pool=[]; seen=set()
for _,r in man.iterrows():
    k=norm(r["Title"])[:80]
    if k in seen: continue
    seen.add(k); pool.append({"id":str(len(pool)),"title":str(r["Title"]),"description":"" if pd.isna(r["Short description"]) else str(r["Short description"])[:250]})
for _,r in dash.iterrows():
    k=norm(r["title"])[:80]
    if k in seen: continue
    seen.add(k); pool.append({"id":str(len(pool)),"title":r["title"],"description":(r["summary"] or "")[:250]})
print(f"POOL: {len(pool)} items")
SECTIONS=["Update from PI / Programme","Teacher recruitment, retention & development","EdTech","Political environment and key organisations","Four Nations","Research – Practice – Policy","What matters in education?"]
TASK=f"""Assign each item to exactly ONE of these education-newsletter sections: {SECTIONS}.
Return ONLY a JSON array of objects with keys "id" and "section".
Items: {json.dumps(pool,ensure_ascii=False)}"""
def parse(t): return {o["id"]:o["section"] for o in json.loads(re.search(r"\[.*\]",t,re.S).group(0))}
print("Claude..."); CLA=parse("".join(b.text for b in anthropic.Anthropic().messages.create(model="claude-opus-4-8",max_tokens=3000,messages=[{"role":"user","content":TASK}]).content if b.type=="text"))
print("GPT-4o..."); GPT=parse(OpenAI().chat.completions.create(model="gpt-4o",messages=[{"role":"user","content":TASK}]).choices[0].message.content)
print("Your classifier...")
st=SentenceTransformer("all-MiniLM-L6-v2"); clf=joblib.load("models/sbert_classifier_no_meta.joblib")
texts=[(it["title"]+". "+it["description"]).strip() for it in pool]
emb=st.encode(texts,show_progress_bar=False); preds=clf.predict(emb)
CLF={pool[i]["id"]:CLF_MAP.get(preds[i],preds[i]) for i in range(len(pool))}

byid={it["id"]:it for it in pool}
unan=maj=flag=0; flagged=[]
print(f'\n{"ITEM":42} | Claude          | GPT-4o          | Classifier      | VERDICT')
print('-'*120)
for i in [x["id"] for x in pool]:
    votes=[CLA.get(i,"?"),GPT.get(i,"?"),CLF.get(i,"?")]
    c=Counter(votes); top,n=c.most_common(1)[0]
    if n==3: unan+=1; v="3/3 "+top[:24]
    elif n==2: maj+=1; v="2/3 "+top[:24]
    else: flag+=1; v="FLAG (all differ)"; flagged.append(i)
    if n<3:  # show non-unanimous
        print(f'{byid[i]["title"][:42]:42} | {votes[0][:15]:15} | {votes[1][:15]:15} | {votes[2][:15]:15} | {v}')
print('-'*120)
print(f"\nUnanimous 3/3: {unan}   Majority 2/3: {maj}   3-way split (flag for you): {flag}   (of {len(pool)})")
print(f"=> the panel auto-assigns {unan+maj}/{len(pool)} and only asks you about {flag}.")
