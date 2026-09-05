"""Produce an advisory candidate screen; do not mutate governed study eligibility."""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PUB = ROOT / 'site/public/data/v1'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

events = read(PUB / 'treatments/county-first-entry/candidate-events.json')
adjudications = {x['county_first_entry_adjudication_id']: x for x in read(PUB / 'treatments/county-first-entry/adjudications.json')}
inventory = {x['entity_id']: x for x in read(PUB / 'facilities/index.json')}
panels = {}
for path in (PUB / 'panels/county-economic-history/by-state').glob('*.json'):
    panels.update({x['county_fips']: x for x in read(path)})
sources = {}
for path in (ROOT / 'data/silver/infrastructure').glob('*.json'):
    data = read(path)
    if isinstance(data, dict):
        sources.update({x['source_id']: x for x in data.get('collections', {}).get('source', [])})
sources.update({x['source_id']: x for x in read(PUB / 'treatments/county-first-entry/evidence-sources.json')})

# Selection is an advisory review of identifiable private commercial projects with
# useful development histories. No economic outcome values are used in selection.
# Date labels deliberately distinguish opening, completion, and observed operation.
choices = [
 ('37161','Meta Forest City','2012-04-19 opening','Hyperscale','Construction-to-operation history; later expansion and recurring local revenue.'),
 ('19153','Meta Altoona','2014-11-14 online','Hyperscale','Long operating history with separately mapped campus buildings; phase-level investment research.'),
 ('48439','Meta Fort Worth','Operating by 2017-12-11','Hyperscale','Construction, operating employment, and metro-area supplier activity; refine first traffic date.'),
 ('35061','Meta Los Lunas','2019-02-07 grand opening','Hyperscale','Development, recurring employment, and local fiscal receipts; ceremony date needs commissioning alignment.'),
 ('51087','Meta Henrico','2020-08-05 serving traffic','Hyperscale','Documented transition to operation and four later panel years.'),
 ('49049','Meta Eagle Mountain','Operating by 2021-07-14','Hyperscale','Construction and early operations; three later panel years.'),
 ('41013','Apple Prineville','2012-05 opening','Hyperscale','Campus investment and recurring activity; separate Apple phases from nearby Meta development.'),
 ('32031','Apple Washoe County campus','2012-12 campus opening','Hyperscale','State economic-development board packet is a fiscal/incentive research lead; map first-building timing separately.'),
 ('37035','Apple Maiden','Operating by 2012','Hyperscale','County financial report identifies the constructed, operating facility; fiscal and capital-investment research.'),
 ('04013','Apple Mesa','2017-03 service date','Hyperscale','Conversion/reuse and subsequent operation; separate predecessor investment from Apple investment.'),
 ('19155','Google Council Bluffs','2009 campus-level anchor','Hyperscale','Long operating history and multiple mapped buildings; validate campus/phase opening chronology.'),
 ('01071','Google Bridgeport / Jackson County','2018 opening','Hyperscale','Documented campus opening; construction and longer-term community outcomes.'),
 ('47125','Google Clarksville','Employment documented by 2019-04-10','Hyperscale','Operating employment evidence; reconstruct construction and commissioning before assigning an event date.'),
 ('45015','Google Berkeley County','2007 campus-history anchor','Hyperscale','Long investment history; distinguish original announcement, construction and commissioning.'),
 ('53025','Microsoft Quincy','2007 first data center','Hyperscale','Long operating and expansion history; pre-2001 data may be needed for initial construction analysis.'),
 ('48029','Microsoft San Antonio','Operating by 2013-11-04','Hyperscale','Regional investment and expansion research; establish exact building and phase chronology.'),
 ('32029','Switch Citadel / Tahoe Reno 1','2017-02-15 opening','Colocation / campus','Clear opening event; investigate construction payroll, recurring activity and fiscal agreements.'),
 ('32003','Switch Las Vegas NAP7','2008 construction; 2009 debut','Colocation / campus','Stored county filing and operator history support distinct construction and operating phases.'),
 ('18089','Digital Crossroad DX-1, Hammond','2020-10-31 operational','Colocation','Exact-facility operational event; construction, redevelopment, permanent jobs and tax-base research.'),
 ('37119','TierPoint Charlotte CL4','2014-03-03 opening','Colocation','Clear commercial opening event and ten later panel years.'),
 ('05119','TierPoint / Windstream Little Rock','2012-04-12 opening','Colocation','Clear commercial opening event and twelve later panel years.'),
 ('27019','Flexential / Stream Chaska','2014-06 completion','Colocation','Construction completion provides a development anchor; confirm operating ramp and local contracts.'),
 ('26163','Quicken Loans Technology Center, Corktown','2015-06-30 grand opening','Private enterprise','Purpose-built corporate technology investment; verify computing scope and separate office employment.'),
 ('25017','Markley Lowell','Phase One operating by 2015-11-23','Colocation','Phase opening and customer occupancy support investment and staged growth research.'),
 ('26125','EdgeConneX DET01, Southfield','Vacant shell in 2012-13; operating by 2015-03-11','Colocation','Documented shell-to-data-center conversion offers construction and operational chronology.'),
 ('06085','NTT Silicon Valley SV1','2021-04-13 opening','Colocation','Exact opening and three later panel years; nearby developments require explicit treatment.'),
 ('55079','Expedient Milwaukee / Franklin','2021-10-20 opening','Colocation','Clear opening and three later panel years; reconstruct prior building use and construction.'),
 ('48339','Stream Houston I / The Woodlands','Operating since 2013','Colocation','Exact-address campus history; recurring operating activity and property-tax research.'),
 ('53033','Equinix Seattle SE3','2013-03-14 opening','Colocation','Commercial expansion within an existing network hub; study incremental project effects.'),
 ('20091','State Farm Olathe','2016 construction; lease began 2016-11-03','Private enterprise','SEC property evidence links capital asset, lease, and later occupancy; lease date is not commissioning.'),
 ('34003','NYSE Mahwah','2010 operational','Private enterprise','Dedicated financial-market computing facility with a long operating history.'),
]

by_fips = {x['county_fips']: x for x in events}
assert len(by_fips) == len(events), 'County anchor assumption changed'
recommendations = []
for fips, label, timing, kind, purpose in choices:
    event = by_fips[fips]
    assert event['facility_id'] in inventory
    adjudication = adjudications[event['county_first_entry_adjudication_id']]
    source_ids = list(dict.fromkeys([event['source_id']] + adjudication.get('source_ids', [])))
    panel = panels[fips]
    recommendations.append({
        'study_label': label, 'inventory_entity_id': event['facility_id'],
        'inventory_name': inventory[event['facility_id']]['display_name'],
        'existing_review_name': event['canonical_name'],
        'county_fips': fips, 'county_name': event['county_name'], 'state_abbr': event['state_abbr'],
        'proposed_study_group': kind, 'candidate_status': 'development_history_candidate',
        'documented_timing': timing, 'research_value': purpose,
        'original_anchor': event['when'], 'original_anchor_post_years_through_2024': event['available_post_periods'],
        'county_panel_coverage': panel['coverage_status'], 'county_panel_complete_year_count': panel['complete_year_count'],
        'existing_first_entry_rationale': adjudication['rationale'],
        'evidence_sources': [{'source_id': sid, 'title': sources.get(sid, {}).get('title'), 'url': sources.get(sid, {}).get('url')} for sid in source_ids],
    })

campuses = [
 ('cam_im3_campus_00009474864','Google Lenoir','Campus identity; commissioning chronology needs reconstruction','https://www.datacenters.google/locations/'),
 ('cam_im3_campus_00019988712','Meta Prineville','First dedicated Prineville facility documented in 2011; link campus phases','https://www.prnewswire.com/news-releases/facebook-launches-open-compute-project-to-share-custom-engineered-highly-efficient-server-and-data-center-technology-with-the-world-119415214.html'),
 ('cam_im3_campus_00231769626','Google The Dalles','Campus identity; commissioning chronology needs reconstruction','https://www.datacenters.google/locations/oregon/'),
 ('cam_im3_campus_00578435601','Google Douglas County','Campus identity; commissioning chronology needs reconstruction','https://www.datacenters.google/locations/'),
 ('cam_im3_campus_00675108684','Microsoft Boydton','Operator reports ten years of operation in August 2020; reconstruct phases','https://local.microsoft.com/blog/celebrating-10-years-in-boydton/'),
]
for ident,label,timing,url in campuses:
    inv = inventory[ident]
    panel = panels[inv['primary_county_fips']]
    recommendations.append({
        'study_label':label,'inventory_entity_id':ident,'inventory_name':inv['display_name'],
        'county_fips':inv['primary_county_fips'],'county_name':panel['county_name'],'state_abbr':panel['state_abbr'],
        'proposed_study_group':'Hyperscale','candidate_status':'campus_history_candidate',
        'documented_timing':timing,
        'research_value':'Already represented as a campus in the inventory. Review at project/campus level; do not require an individually mapped building to start historical research.',
        'county_panel_coverage':panel['coverage_status'],'county_panel_complete_year_count':panel['complete_year_count'],
        'evidence_sources':[{'url':url,'title':'Operator-authored site/history evidence inspected during this screen'}],
    })

screened_ids = {x['inventory_entity_id'] for x in recommendations}
assert len(screened_ids) == len(recommendations)
appendix = []
for event in events:
    adjudication = adjudications[event['county_first_entry_adjudication_id']]
    appendix.append({
        'facility_id':event['facility_id'],'name':event['canonical_name'],
        'county_fips':event['county_fips'],'county_name':event['county_name'],'state_abbr':event['state_abbr'],
        'recorded_anchor':event['when'],'original_evidence_gate':event['evidence_threshold_status'],
        'original_period_gate':event['period_requirement_status'],
        'included_in_advisory_priority_list':event['facility_id'] in screened_ids,
        'existing_rationale':adjudication['rationale'],
        'note':'Not being prioritized here is not exclusion. Public/institutional/crypto scope, private ownership, and event semantics need separate screening.'
    })

report = {
 'screen_date':'2026-09-03','status':'advisory_research_candidates_not_impact_findings',
 'selection_basis':'Private commercial identity, documented development history or identifiable campus, and linked county panel. No economic outcome values used.',
 'scope':'Review of the existing dated evidence layer, verified lifecycle results, and additional named campus records. Not an exhaustive classification of every inventory entity.',
 'counts':{'source_inventory_objects':len(inventory),'dated_county_anchors_reviewed':len(events),'prioritized_projects':len(recommendations),
           'existing_dated_project_candidates':len(choices),'additional_campus_candidates':len(campuses)},
 'notices':[
   'Research candidacy does not establish positive impact or authorize a causal model.',
   'The old county-first-entry exclusions are preserved. Broader project-event eligibility must be defined separately.',
   'Operating-by observations, leases, completion dates, grand openings, and region launches are not automatically commissioning dates.',
   'Reported post periods refer to the stored anchor, not necessarily the true opening date. The outcome panel ends in 2024.',
   'Financial benefits still need project payroll, local supplier spending, recurring employment, actual taxes, incentives and public costs. These are research questions, not observed results in this report.',
   'Campus dates cannot be assigned to every building; campuses and child buildings must not double count a project.',
 ],
 'recommendations':recommendations,'dated_evidence_appendix':appendix,
}
(OUT/'candidate-screen.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

lines=['# Existing inventory: private-sector economic-study candidates','',
 'Advisory screen, 3 September 2026. This report identifies research candidates; it does not change the governed inventory, first-entry adjudications, or model eligibility.','',
 f"Reviewed {len(events)} dated county anchors, the lifecycle review outputs, and selected additional campus records. Identified {len(choices)} projects with useful stored development histories and {len(campuses)} additional campus candidates. This is a research-priority list, not a fixed sample size or exhaustive list of qualifying private facilities.",'',
 'Selection uses identity and historical evidence, not favorable economic outcomes. The purpose is to reconstruct capital spending, construction employment, local supplier and household spending, permanent employment, tax receipts, and subsequent investment.','',
 '## Candidates with development-history evidence','',
 '| Project | County / state | Evidence already available | Why investigate |',
 '|---|---|---|---|']
for r in recommendations[:len(choices)]:
    urls=[x['url'] for x in r['evidence_sources'] if x.get('url')]
    name=f"[{r['study_label']}]({urls[0]})" if urls else r['study_label']
    lines.append(f"| {name} | {r['county_name']}, {r['state_abbr']} | {r['documented_timing']} | {r['research_value']} |")
lines += ['', '## Additional campus records already in the inventory','',
 '| Project | County / state | Evidence and remaining work |','|---|---|---|']
for r in recommendations[len(choices):]:
    lines.append(f"| [{r['study_label']}]({r['evidence_sources'][0]['url']}) | {r['county_name']}, {r['state_abbr']} | {r['documented_timing']} |")
lines += ['', 'These five are campus entities. A facility-only queue can miss this useful level of project identification. Their presence supports research candidacy, while campus/phase timing and primary financial records still require collection.','',
 '## Interpretation and immediate evidence needs','']
lines += ['- '+n for n in report['notices']]
lines += ['', 'All prioritized county panels: '+str(dict(Counter(x['county_panel_coverage'] for x in recommendations)))+'.', '',
 'Additional existing candidates include commercial acquisitions and conversions, banks and insurers, and newer developments. For example, H5 Minneapolis, CyrusOne Somerset and TierPoint Sioux Falls West carry acquisition observations rather than opening dates. Meta Gallatin, DeKalb and Kansas City have recent operating evidence; xAI Colossus has a 2024 operating-by anchor. These can support construction and early-operation work, but their recorded dates do not yet support long post-operation analysis in the 2001–2024 panel. Recent operating-by observations do not prove a recent opening.', '',
 'Government, university, nonprofit institutional, tribal-government and crypto-mining records should receive explicit separate scope decisions. Examples include IU Bloomington, NCSA, NCAR, state data centers, Syracuse, Kaiser, and IONIC Cedarvale. These are not excluded from the inventory.', '',
 '## Complete dated-evidence appendix','',
 'The JSON companion retains every existing dated record, its stable facility ID, original gates, and full rationale. Entries below are not automatically private-sector or study-eligible. An empty/late chronology is an evidence gap, not proof of a late opening.','',
 '| Existing reviewed name | County / state | Recorded anchor | Priority list |','|---|---|---|---|']
for r in appendix:
    when=r['recorded_anchor']; date=when.get('date',str(when.get('year','unknown')))
    lines.append(f"| {r['name']} | {r['county_name']}, {r['state_abbr']} | {date} ({when['precision']}) | {'Yes' if r['included_in_advisory_priority_list'] else 'Not prioritized in this screen'} |")
lines += ['', '## Repository inputs','',
 '- `site/public/data/v1/facilities/index.json`',
 '- `site/public/data/v1/treatments/county-first-entry/candidate-events.json`',
 '- `site/public/data/v1/treatments/county-first-entry/adjudications.json`',
 '- `site/public/data/v1/treatments/county-first-entry/evidence-sources.json`',
 '- `site/public/data/v1/lifecycle/*results.json` (review context)',
 '- `site/public/data/v1/panels/county-economic-history/by-state/*.json`',
 '- `data/silver/infrastructure/*.json` (source metadata)', '']
(OUT/'candidate-screen.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'counts':report['counts'],'panel_coverage':dict(Counter(x['county_panel_coverage'] for x in recommendations)),
                  'sources_missing_url':sorted({x.get('source_id','') for r in recommendations for x in r['evidence_sources'] if not x.get('url')})}))
