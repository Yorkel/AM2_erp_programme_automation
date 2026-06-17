"""Trial: agent proposes section + include/exclude (with reasons) on the June #115 pool,
then compares to the curator's real decisions. The agent never sees Include or the section tag."""
import os, re, json, pandas as pd
from pathlib import Path

# --- load API key from .env ---
for line in Path(".env").read_text().splitlines():
    if line.startswith("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = line.split("=",1)[1].strip().strip('"').strip("'")
import anthropic
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5"   # matches the production summary stack

SECTIONS = ["Teacher recruitment, retention & development","EdTech",
    "Political environment and key organisations","Four Nations",
    "Research – Practice – Policy","What matters in education?",
    "Update from PI / Programme"]

df = pd.read_excel("agent_draft/ERPNewsletterSubmissions_June.xlsx", sheet_name="Sheet1").dropna(how="all")
df = df[df["Title"].notna() & (df["Title"].astype(str).str.strip().str.lower()!="end")].reset_index(drop=True)

# items the agent sees (answers hidden)
items = [{"id": i,
          "title": str(r["Title"]),
          "organisation": "" if pd.isna(r["Organisation"]) else str(r["Organisation"]),
          "description": "" if pd.isna(r["Short description"]) else str(r["Short description"])}
         for i,r in df.iterrows()]

prompt = f"""You are helping curate the ESRC Education Research Programme weekly newsletter.
Scope: UK schools, pre-higher-education and further education policy and research, across the four nations and Ireland. Pure higher-education-sector content is out of scope.

The seven sections are:
{chr(10).join('- '+s for s in SECTIONS)}

For EACH item below, return:
- "section": the single best section from the list,
- "decision": "include" or "exclude",
- "reason": one short clause (e.g. duplicate, off-scope, out of date, strong fit, thin content).

Be a triage aid, not a final editor. Return ONLY a JSON array of objects with keys id, section, decision, reason.

Items:
{json.dumps(items, ensure_ascii=False, indent=1)}"""

resp = client.messages.create(model=MODEL, max_tokens=4000,
    messages=[{"role":"user","content":prompt}])
text = "".join(b.text for b in resp.content if b.type=="text")
arr = json.loads(re.search(r"\[.*\]", text, re.S).group(0))
ag = {o["id"]: o for o in arr}

# --- gold from the curator ---
def gold_decision(v):
    s = str(v).lower()
    if "includ" in s: return "include"
    if "exclude" in s or "delete" in s: return "exclude"
    return "undecided"
SEC_MAP = {'edtech':'EdTech','political environment and key organisations':'Political environment and key organisations',
 'what matters in education?':'What matters in education?','research – practice – policy':'Research – Practice – Policy',
 'four nations':'Four Nations','teacher recruitment, retention and development':'Teacher recruitment, retention & development',
 'updates from projects & pis':'Update from PI / Programme','updates from the programme':'Update from PI / Programme'}
def gold_section(v): return SEC_MAP.get(str(v).strip().lower(),'(untagged)')

rows=[]
for i,r in df.iterrows():
    o=ag.get(i,{})
    rows.append({"title":str(r["Title"])[:55],
        "agent_section":o.get("section",""),"your_section":gold_section(r["Which section of the newsletter is this for?"]),
        "agent":o.get("decision",""),"you":gold_decision(r["Include"]),
        "reason":o.get("reason","")[:40]})
res=pd.DataFrame(rows)

dec = res[res["you"]!="undecided"]
print("AGENT PROPOSAL vs YOUR ACTUAL DECISIONS\n")
with pd.option_context("display.max_colwidth",58,"display.width",240):
    print(res.to_string(index=False))
print(f"\nInclude/exclude agreement (on {len(dec)} decided): "
      f"{(dec['agent']==dec['you']).mean():.0%}")
sec = res[res["your_section"]!="(untagged)"]
print(f"Section agreement (on {len(sec)} tagged): {(sec['agent_section']==sec['your_section']).mean():.0%}")
res.to_csv("agent_draft/agent_proposal_june.csv", index=False)
print("\nsaved -> agent_draft/agent_proposal_june.csv")
