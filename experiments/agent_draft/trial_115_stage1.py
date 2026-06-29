"""Stage 1: build the candidate pool for the #115 trial (Tue 9 - Mon 15 June 2026)."""
import pandas as pd, re
from pathlib import Path

XL = Path("agent_draft/ERPNewsletterSubmissions.xlsx")
WIN_START, WIN_END = "2026-06-02", "2026-06-09"   # previous week up to Tue 9 June scrape (feeds #115, pub Fri 12 June)

# canonical sections (7 blocks) + display names matching the published newsletter
CANON = {
 'political_environment_key_organisations':'Political environment and key organisations',
 'what_matters_ed':'What matters in education?',
 'policy_practice_research':'Research – Practice – Policy',
 'edtech':'EdTech',
 'four_nations':'Four Nations',
 'teacher_rrd':'Teacher recruitment, retention & development',
 'update_from_pi':'Update from PI',
 'update_from_programme':'Updates from the Programme',
}
SECTION_MAP = {
 'political environment and key organisations':'political_environment_key_organisations','peko':'political_environment_key_organisations',
 'what matters in education?':'what_matters_ed',
 'research – practice – policy':'policy_practice_research','rpp':'policy_practice_research','could be rpp':'policy_practice_research',
 'edtech':'edtech',
 'four nations':'four_nations',
 'teacher recruitment, retention and development':'teacher_rrd','teacher recruitment, retention & development':'teacher_rrd',
 'updates from projects & pis':'update_from_pi',
 'updates from the programme':'update_from_programme',
}
def norm_section(v):
    if pd.isna(v): return 'unknown'
    return SECTION_MAP.get(str(v).strip().lower(), 'unknown')

df = pd.read_excel(XL, sheet_name='Sheet1').dropna(how='all')
df['Completion time'] = pd.to_datetime(df['Completion time'], errors='coerce')
df['section_canon'] = df['Which section of the newsletter is this for?'].map(norm_section)

# gold "went into #115" from the Include column
inc = df['Include'].astype(str).str.lower()
df['gold_in_115'] = inc.str.contains('115') & inc.str.contains('includ')

win = df[(df['Completion time'] >= WIN_START) & (df['Completion time'] <= WIN_END+' 23:59:59')].copy()
win = win[win['Title'].notna() & (win['Title'].astype(str).str.strip().str.lower() != 'end')]

print(f"Candidate pool {WIN_START} -> {WIN_END}: {len(win)} items")
print(f"  of which marked 'Included 115' in the Excel: {win['gold_in_115'].sum()}")
print("\nSection distribution (submitter-tagged, normalised):")
print(win['section_canon'].value_counts().to_string())
print("\nInclude-decision spread in window:")
print(win['Include'].fillna('(blank)').value_counts().head(12).to_string())

cols = ['Completion time','Title','section_canon','Include','gold_in_115','Link (website address / URL)','Short description','Submitter']
out = win[cols].rename(columns={'Link (website address / URL)':'link','Short description':'description'})
out.to_csv('agent_draft/candidate_pool_115.csv', index=False)
print(f"\nSaved {len(out)} candidates -> agent_draft/candidate_pool_115.csv")
