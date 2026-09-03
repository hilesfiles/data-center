# Codex Bootstrap Prompt — U.S. Data Center Community Impact Observatory

**Working repository name:** `data-center-community-impact-observatory`  
**Working product name:** **U.S. Data Center Community Impact Observatory (DCCIO)**  
**Target deployment:** GitHub Pages  
**Primary development model:** local-first, reproducible, open-source, static-site deployment  
**Geographic unit:** U.S. county/county-equivalent, with facility/project points and state/national aggregates  
**Initial historical scope:** 2000 through present, with economic series extending earlier where available  
**Research cutoff for this bootstrap specification:** 2026-08-31

---

## 0. Your role

You are Codex operating as a senior data engineer, geospatial engineer, econometrician, research software engineer, and front-end data-visualization engineer.

Build a production-quality open-source research application that reconstructs the historical development of U.S. data centers from publicly available evidence, joins those facilities and project events to public county-level economic, demographic, fiscal, housing, utility, environmental, political, and public-opinion data, performs transparent statistical analysis, and publishes the results as an interactive national map on GitHub Pages.

This is not a toy dashboard and not merely a collection of scraped articles. The core product is a **provenance-tracked historical data center evidence database plus reproducible statistical analysis**.

The site must help answer four distinct questions:

1. **Where and when have data centers been proposed, built, expanded, delayed, rejected, canceled, sold, or closed?**
2. **What measurable economic changes occur in communities after data-center entry or expansion, relative to credible counterfactual communities?**
3. **What measurable community costs or pressures accompany data-center development?**
4. **How does local opposition evolve, and how does opposition relate to measurable economic benefits and costs?**

The application must never imply causation from a simple before/after correlation. Descriptive results, matched-counterfactual results, and formal causal estimates must be separately labeled.

---

# 1. Non-negotiable scientific and engineering principles

## 1.1 Evidence before assertion

Never invent or infer a facility fact merely because it seems plausible. Every material facility/project/event attribute must be traceable to one or more source records.

The system should represent this distinction explicitly:

> A source **makes a claim**. A claim is not automatically a canonical fact.

The canonical database is produced by resolving claims according to source quality, corroboration, date precision, conflict status, and human review.

## 1.2 Preserve conflicting evidence

Do not delete conflicting claims. Keep all claims and resolve one canonical value only when justified. The UI must be able to expose conflicting or uncertain values.

## 1.3 Never overwrite observed values with imputed values

Every numerical field that may be modeled or imputed must have an explicit provenance/status field, e.g.:

- `observed`
- `derived`
- `estimated`
- `imputed`
- `unknown`

Observed MW and estimated MW must never share an indistinguishable field.

## 1.4 Separate discovery from verification

News archives and search indexes are excellent discovery layers. They are not automatically authoritative.

Prefer source types in this rough order for resolving a specific factual claim:

1. government permit, zoning, assessor, tax, utility, regulatory, or court record;
2. SEC filing or other legally filed disclosure;
3. government incentive agreement or economic-development contract;
4. operator/developer first-party announcement;
5. local government press release;
6. local newspaper or business journal;
7. reputable national media;
8. specialist data-center trade publication;
9. secondary aggregator;
10. unverified social-media claim.

Do not blindly convert this ordering into a universal truth score. A source may be authoritative for one field and weak for another.

## 1.5 Reproducibility

Every acquisition and transformation must be reproducible from code and documented inputs wherever licensing permits.

Record:

- source URL;
- archive URL when available;
- publication date;
- retrieval timestamp;
- content hash when a local artifact is retained;
- source type;
- parser/extractor version;
- model version for ML/LLM classifications;
- transformation code version / Git commit when practical.

## 1.6 Public site must not redistribute copyrighted news archives

The public repository/site may store:

- article metadata;
- URLs;
- archived URLs;
- short legally appropriate snippets;
- extracted factual claims;
- classification labels;
- hashes;
- derived features.

Do **not** commit wholesale copyrighted article bodies from Common Crawl, newspaper sites, or other publishers into the public repository. If full text is needed locally for extraction, place it in a gitignored cache such as `data/raw_local/`.

## 1.7 Static deployment

GitHub Pages cannot run Python, DuckDB server processes, or a database backend at request time.

Therefore:

- all ETL, entity resolution, statistics, indices, uncertainty intervals, and map data must be generated **before deployment**;
- the site consumes versioned static JSON/GeoJSON/Parquet-derived assets;
- GitHub Actions builds and deploys the front end;
- heavyweight historical crawling should normally run locally or in a separately invoked workflow, not on every Pages deployment.

## 1.8 Be explicit about uncertainty

Every county/index/facility view must expose data quality and analytic uncertainty when relevant.

A missing value is preferable to a fabricated precision.

---

# 2. Core product concepts

Create four primary analytical families.

## 2.1 DCOI — Data Center Opposition Index

Measures local political/community opposition to data-center development.

It must be decomposable into constituent signals rather than presented as a magical opaque number.

## 2.2 DCEDI — Data Center Economic Dividend Index

Measures the estimated local economic dividend associated with data-center entry/expansion **relative to a counterfactual**, not ordinary raw growth.

## 2.3 DCCCI — Data Center Community Cost Index

Measures observable community burdens/pressures associated with data-center development, including electricity-price pressure, housing affordability pressure, water-resource context, environmental/grid externality context, and other measurable costs where credible data exist.

## 2.4 BSG — Benefit–Sentiment Gap

A derived measure:

\[
BSG_{c,t}=DCEDI_{c,t}-DCOI_{c,t}
\]

Range is naturally approximately -100 to +100 if both source indices are 0–100.

Interpretation:

- high positive BSG: measured economic dividend substantially exceeds local opposition score;
- high negative BSG: opposition is high relative to measured local economic dividend;
- near zero: economic dividend and opposition are similar in index terms.

Also compute a separate **Net Community Balance**:

\[
NCB_{c,t}=DCEDI_{c,t}-DCCCI_{c,t}
\]

Do not conflate BSG with NCB.

---

# 3. Deliverables

At completion, the repository must contain:

1. a canonical historical data-center facility/project/event database;
2. a provenance/claims database;
3. a county-year analytical panel;
4. data acquisition adapters and cached manifests;
5. reproducible statistical-analysis scripts;
6. generated national/state/county index outputs;
7. a static interactive web application;
8. automated tests and data-quality checks;
9. research methodology documentation;
10. source/licensing documentation;
11. GitHub Actions for tests, front-end build, and GitHub Pages deploy;
12. instructions for local refresh and publication.

The repository must be usable even when optional API credentials are not present. Credential-dependent adapters should fail gracefully and leave documented gaps.

---

# 4. Recommended technical stack

Use this stack unless a concrete technical reason requires a change.

## 4.1 Data / analytics

- Python 3.12+
- `uv` for Python dependency/environment management
- DuckDB as the local analytical database/query engine
- Parquet as the canonical analytical interchange/storage format
- Polars and/or Pandas for tabular processing
- PyArrow
- GeoPandas
- Shapely
- PyProj
- HTTPX or Requests
- BeautifulSoup / lxml
- `warcio` for WARC processing
- `trafilatura` or equivalent for article-text extraction in local caches
- Pydantic for validated extraction schemas
- scikit-learn
- SciPy
- NumPy
- statsmodels
- PyFixest for fixed-effects / staggered event-study analysis
- optional `differences` Python package or R `did` package for Callaway–Sant’Anna validation; do not make the entire build depend on R

## 4.2 Web application

- Node.js 22+
- React
- TypeScript
- Vite
- MapLibre GL JS
- Apache ECharts for analytical charts
- CSS modules or a simple utility CSS approach; do not introduce a giant UI framework unless necessary

The web app must remain lightweight and legible. The map is the central interaction, not a decorative element.

## 4.3 Geospatial delivery

Start with simplified Census county GeoJSON appropriate for national rendering.

If bundle size becomes excessive, migrate county geometry and large point layers to PMTiles/vector tiles as an optimization, not as a blocker for v0.1.

---

# 5. Repository structure

Create approximately this structure:

```text
/
├─ README.md
├─ LICENSE
├─ CITATION.cff
├─ .gitignore
├─ .env.example
├─ Makefile
├─ pyproject.toml
├─ uv.lock
├─ package.json                     # optional root workspace commands
├─ docs/
│  ├─ methodology.md
│  ├─ data-dictionary.md
│  ├─ sources.md
│  ├─ licensing.md
│  ├─ causal-inference.md
│  ├─ index-methodology.md
│  ├─ data-quality.md
│  └─ contributing-data.md
├─ config/
│  ├─ sources.yml
│  ├─ source-quality.yml
│  ├─ event-taxonomy.yml
│  ├─ opposition-taxonomy.yml
│  ├─ index-weights.yml
│  └─ jurisdictions/
├─ schemas/
│  ├─ facility.schema.json
│  ├─ project.schema.json
│  ├─ event.schema.json
│  ├─ source.schema.json
│  ├─ claim.schema.json
│  └─ county_year.schema.json
├─ data/
│  ├─ raw_public/                   # redistributable public-source downloads where license permits
│  ├─ raw_local/                    # gitignored copyrighted/local caches
│  ├─ staging/
│  ├─ canonical/
│  ├─ analytical/
│  ├─ exports/
│  ├─ manifests/
│  └─ review/
├─ src/dccio/
│  ├─ acquire/
│  ├─ parse/
│  ├─ extract/
│  ├─ resolve/
│  ├─ geocode/
│  ├─ transform/
│  ├─ econometrics/
│  ├─ indices/
│  ├─ quality/
│  ├─ export/
│  └─ cli.py
├─ scripts/
│  ├─ bootstrap_data.py
│  ├─ build_facility_panel.py
│  ├─ build_county_panel.py
│  ├─ run_econometrics.py
│  ├─ build_indices.py
│  ├─ build_site_exports.py
│  └─ validate_all.py
├─ notebooks/
│  └─ exploratory/                  # not source of truth
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ data_quality/
│  └─ fixtures/
├─ site/
│  ├─ package.json
│  ├─ vite.config.ts
│  ├─ src/
│  └─ public/data/
└─ .github/workflows/
   ├─ test.yml
   ├─ pages.yml
   └─ data-refresh-manual.yml
```

Notebooks may explore; production logic must live in tested modules/scripts.

---

# 6. Geographic and temporal model

## 6.1 Canonical geographic identifiers

Use five-character county FIPS as the main geographic key.

Maintain crosswalks for:

- county FIPS;
- state FIPS;
- state abbreviation;
- county-equivalent names;
- Census region/division;
- CBSA where applicable;
- metro/nonmetro classification;
- utility service territories where derivable;
- ISO/RTO/balancing-authority context where derivable.

Do not use county names as keys.

## 6.2 Boundary changes

County-equivalent boundaries and names can change. Maintain a geography crosswalk and document how historical observations are harmonized to a chosen reference geography.

For v0.1, prefer a contemporary county geography for the map while retaining original source FIPS when available.

## 6.3 Time grain

Canonical analytical panel:

```text
county_fips × calendar_year
```

Facility/project events should preserve exact date precision when possible.

Create fields:

- `event_date`
- `event_year`
- `event_date_lower`
- `event_date_upper`
- `date_precision` = `day|month|year|range|inferred`

Do not create fake January 1 dates for year-only evidence without recording that the precision is `year`.

---

# 7. Canonical relational data model

The minimum model must contain the following entities.

## 7.1 `facilities`

A facility represents a persistent physical data-center site or campus, independent of operator changes.

Required/recommended fields:

```text
facility_id
canonical_name
latitude
longitude
address
city
county_fips
state
parcel_id
campus_id
facility_type
status
first_operational_year
last_operational_year
current_operator_id
pnnl_source_id
osm_source_id
geometry_type
building_sqft_observed
campus_sqft_observed
data_quality_score
created_at
updated_at
```

Never use operator/name as the primary key.

## 7.2 `operators`

```text
operator_id
canonical_name
parent_company
company_type
website
aliases_json
```

## 7.3 `projects`

A facility can contain multiple development phases/projects.

```text
project_id
facility_id
project_name
project_alias
project_status
announced_capex_usd
announced_jobs
announced_mw
announced_sqft
actual_capex_usd
actual_jobs
actual_mw
actual_sqft
value_status fields for each metric
```

## 7.4 `events`

Event taxonomy should include at least:

```text
PROPOSED
LAND_ACQUIRED
ANNOUNCED
ZONING_FILED
ZONING_APPROVED
ZONING_DENIED
PERMIT_APPLIED
PERMIT_ISSUED
CONSTRUCTION_STARTED
ENERGIZATION_REQUESTED
ENERGIZED
OPERATIONAL
EXPANSION_ANNOUNCED
EXPANSION_CONSTRUCTION_STARTED
EXPANSION_OPERATIONAL
SOLD
ACQUIRED
OPERATOR_CHANGED
MORATORIUM_AFFECTED
LEGAL_CHALLENGE
DELAYED
WITHDRAWN
CANCELLED
CLOSED
```

Fields:

```text
event_id
facility_id
project_id
event_type
event_date
event_date_lower
event_date_upper
date_precision
canonical_status
confidence_score
review_status
```

## 7.5 `sources`

```text
source_id
source_type
publisher
agency
jurisdiction
title
url
archive_url
publication_date
retrieved_at
content_hash
license
robots_notes
copyright_storage_policy
```

Source types should include:

```text
federal_dataset
state_record
local_government_record
planning_record
zoning_record
permit_record
assessor_record
utility_filing
regulatory_filing
court_record
sec_filing
incentive_agreement
operator_release
local_news
national_news
trade_press
news_archive
legislative_record
poll
petition
advocacy_site
other
```

## 7.6 `claims`

Every source assertion that may affect the canonical data should be stored as a claim.

```text
claim_id
source_id
entity_type
entity_id
attribute
raw_value
normalized_value
unit
claim_date
extraction_method
extractor_version
source_quality_score
claim_confidence
conflict_group
review_status
notes
```

Examples:

```text
facility DC-VA-00127 operational_year = 2014
project P-VA-00127-03 announced_capex_usd = 750000000
project P-VA-00127-03 announced_mw = 48
facility DC-VA-00127 operator = Amazon Web Services
```

## 7.7 `facility_operator_history`

```text
facility_id
operator_id
start_date
end_date
source_claim_id
confidence_score
```

## 7.8 `county_year`

This is the final joined analytical panel. It must be generated, not hand-edited.

Include:

- exposure measures;
- economic outcomes;
- demographic covariates;
- housing outcomes;
- utility outcomes;
- fiscal outcomes;
- opposition variables;
- policy variables;
- environmental/resource context;
- index scores;
- uncertainty / completeness flags.

---

# 8. Historical data-center dataset construction

The historical facility database is the unique core asset of the project.

Use a two-pass strategy.

## 8.1 Pass A — reverse reconstruction from known present-day facilities

Seed the database from the **IM3 Open Source Data Center Atlas** from PNNL/DOE.

Official dataset:

https://www.osti.gov/dataexplorer/biblio/dataset/2550666

PNNL description:

https://www.pnnl.gov/publications/mapping-future-data-centers-new-public-tool-illuminates-whats-next

Reference implementation:

https://github.com/IMMM-SFA/datacenter-atlas

The Atlas contains U.S. data-center locations derived from OpenStreetMap and includes point/building/campus layers, county/state mapping, facility/operator/name where present, and polygon square footage for building/campus geometries. It is licensed under ODbL.

Ingest each layer while preserving original IDs and source geometry.

Then, for every seeded facility, search backward for:

- first announcement;
- land acquisition;
- zoning filing/approval;
- permit issuance;
- construction start;
- energization;
- opening/operational date;
- expansions;
- operator/ownership changes;
- capex;
- MW;
- square footage;
- jobs;
- incentives;
- property-tax information.

## 8.2 Pass B — forward discovery from historical public evidence

Present-day inventories create survivorship bias. They miss:

- closed facilities;
- cancelled projects;
- rejected projects;
- projects stopped by moratoria;
- facilities that changed names or operators;
- proposals that never became operational.

Therefore build a forward historical discovery process from approximately 2000 onward.

Search for terminology such as:

```text
"data center"
"data centre"
datacenter
"server farm"
"server facility"
"cloud campus"
"cloud data center"
"colocation facility"
"co-location facility"
hyperscale
"computing campus"
```

Combine with event vocabulary:

```text
announce
announced
proposal
proposed
rezoning
zoning
permit
approved
denied
construction
break ground
groundbreaking
open
opened
operational
energized
expansion
expanded
megawatt
MW
acre
square feet
investment
million
billion
jobs
moratorium
lawsuit
opposition
withdrawn
cancelled
canceled
```

Every discovery becomes a candidate source/claim, not an automatic canonical facility.

---

# 9. News/archive acquisition strategy

## 9.1 Common Crawl CC-NEWS

Use CC-NEWS as a major bulk news-discovery corpus from 2016 onward.

Official description:

https://commoncrawl.org/blog/news-dataset-available

CC-NEWS publishes WARC files daily under the `crawl-data/CC-NEWS/` hierarchy.

Do not download the entire corpus blindly. Implement targeted processing strategies:

1. maintain publisher/domain allowlists for local newspapers, business journals, trade publications, and major national sources;
2. filter URL/domain metadata before expensive text extraction when possible;
3. stream WARC files rather than materializing unnecessary data;
4. cache only relevant local text in `data/raw_local/`;
5. publish only metadata/claims, not full copyrighted text.

## 9.2 GDELT

Use GDELT for article/event discovery, entity/geography hints, and public-discourse time series.

Official data page:

https://gdeltproject.org/data.html

GDELT 2.0 Event and Global Knowledge Graph data can help identify candidate URLs, organizations, places, and topic coverage. Treat automated GDELT tone/entity output as a feature, not ground truth.

## 9.3 Internet Archive / Wayback Machine

Use archived captures to recover:

- deleted operator announcements;
- old local-government project pages;
- historic utility pages;
- old developer/project pages;
- operator facility directories that have been replaced.

CDX query entry point:

https://web.archive.org/cdx/search/cdx

Record the live URL and archive URL separately.

## 9.4 Direct public web pages

Create polite, rate-limited per-domain fetchers respecting site terms and robots requirements.

Do not build an aggressive generic crawler.

Prefer explicit source registries and search/discovery APIs.

---

# 10. Government and first-party verification layers

## 10.1 Granicus Legistar

Many local governments use Granicus Legistar for legislative and meeting data.

API documentation:

https://webapi.legistar.com/Help

Create a registry of known Legistar client codes and search event items / matters / attachments for data-center terms.

Potentially extract:

- case number;
- applicant;
- parcel;
- acreage;
- rezoning request;
- building area;
- generators;
- substation references;
- water demand;
- project phases;
- planning vote;
- council/board vote;
- public comments;
- attached staff reports.

Do not assume every jurisdiction uses Legistar.

## 10.2 County/city planning and zoning systems

Create adapter interfaces for other public systems.

The first version does not need nationwide perfect coverage. Maintain a jurisdiction registry with:

```text
jurisdiction_id
county_fips
platform
base_url
search_method
api_available
parser
coverage_start
last_checked
```

## 10.3 Assessor/property records

Where legally/publicly accessible, extract:

- parcel owner;
- sale/purchase date;
- sale price;
- land assessed value;
- improvement assessed value;
- construction year;
- building square footage;
- property tax.

Keep assessor-specific schemas behind adapters because systems vary dramatically.

## 10.4 Operator/developer sources

Track first-party announcements from major operators/developers, including but not limited to:

- Amazon/AWS;
- Microsoft;
- Google/Alphabet;
- Meta;
- Oracle;
- Digital Realty;
- Equinix;
- QTS;
- CyrusOne;
- Vantage;
- NTT;
- STACK;
- EdgeConneX;
- CoreSite;
- Iron Mountain;
- Compass;
- Aligned;
- CloudHQ;
- Switch;
- other regional operators.

Keep aliases and acquisitions in the operator table.

## 10.5 SEC / public filings

Use SEC EDGAR where relevant for property portfolios, capex, square footage, acquisitions/dispositions, construction commitments, and risk disclosures.

## 10.6 Utility/regulatory filings

Search public utility commission, ISO/RTO, integrated-resource-plan, load-interconnection, and tariff filings for large-load/data-center information.

These are especially useful for MW validation and community-cost analysis.

## 10.7 Incentive records

Collect state/local incentive agreements where public:

- sales/use-tax exemptions;
- property-tax abatements;
- PILOTs;
- TIF agreements;
- job/investment credits;
- clawback requirements;
- minimum investment/job thresholds.

Separate `announced_incentive_value` from actually realized subsidy/tax expenditure.

---

# 11. Entity resolution

Entity resolution is a first-class research function.

The same physical facility may be called:

```text
Project Nova
Microsoft West Des Moines
DSM05
Microsoft Iowa Cloud Campus
Project Osmium
```

Build candidate matching with explainable features.

For candidate facilities \(a,b\):

\[
M(a,b)=w_g G+w_o O+w_p P+w_t T+w_n N+w_s S
\]

where:

- \(G\): geospatial proximity score;
- \(O\): operator/owner compatibility;
- \(P\): parcel/address compatibility;
- \(T\): time compatibility;
- \(N\): name/alias similarity;
- \(S\): scale/project-description compatibility.

Default priority:

```text
geography > parcel/address > operator > timeline > name > scale
```

Do not auto-merge ambiguous candidates above a broad threshold alone. Implement:

- `auto_match` for extremely high-confidence duplicates;
- `review_match` queue for ambiguous candidates;
- `do_not_match` records.

Create a review CSV/JSON and optional local review UI.

---

# 12. Claim/source confidence and facility data quality

## 12.1 Source-quality configuration

Maintain configurable base quality values by source type rather than hardcoding them throughout the code.

Illustrative starting priors, subject to revision:

```text
permit/assessor/court/regulatory record    0.98
SEC filing                                 0.98
incentive agreement                        0.96
operator release                           0.92
local government release                   0.92
local newspaper/business journal           0.82
national reputable media                   0.80
trade press                                0.78
industry aggregator                        0.55
advocacy claim without primary evidence    0.45
social post                                0.30
```

## 12.2 Corroboration

If independent sources support the same normalized value, increase confidence but cap at 0.99.

One transparent heuristic is:

\[
C=1-\prod_{s\in S}(1-q_s r_s)
\]

where:

- \(q_s\) is base source quality;
- \(r_s\) is relevance/precision for that particular claim.

Because source independence may be imperfect, cap corroboration gains and flag likely source copying where multiple articles trace to one press release.

## 12.3 Date-precision factor

Suggested multipliers:

```text
day       1.00
month     0.95
year      0.80
range     0.65
inferred  0.45
```

## 12.4 Facility Data Quality Score

Calculate a 0–100 DQS:

\[
DQS=100(0.25L+0.25T+0.15S+0.20E+0.15C)
\]

where each component is 0–1:

- \(L\): location certainty;
- \(T\): timeline certainty;
- \(S\): scale certainty (sqft/MW/capex where applicable);
- \(E\): source/evidence quality and redundancy;
- \(C\): completeness of core fields.

Suggested grade labels:

```text
A  90–100
B  80–89
C  70–79
D  50–69
P  <50 provisional
```

Do not hide low-quality records. Expose quality and allow analytical filters to require minimum quality.

---

# 13. Minimum viable historical facility record

A record is sufficient for first-pass county treatment analysis when it has:

```text
facility_id
county_fips
first_operational_year
operational-year confidence
```

Call this **Tier A historical completeness**.

Additional tiers:

### Tier B

```text
announcement date
construction date
opening date
footprint
```

### Tier C

```text
MW
capex
jobs
incentives
assessed value / property tax where available
```

### Tier D

```text
utility/load
water
public comments
opposition
legal/political events
```

Do not block early econometric work waiting for every facility to reach Tier D.

---

# 14. Public economic and demographic datasets

Build source adapters with manifests, versioning, and explicit variable mappings.

## 14.1 BLS QCEW — employment, wages, establishments

Official downloadable files:

https://www.bls.gov/cew/downloadable-data-files.htm

Availability documentation:

https://www.bls.gov/cew/about-data/data-availability.htm

QCEW downloadable county data extend back to 1975; NAICS detail is strongest from 1990 onward.

Ingest annual county measures including:

- total private employment;
- total employment;
- establishment count;
- annual wages;
- average annual pay;
- construction employment and wages;
- information-sector variables;
- NAICS 518210 where published and not suppressed.

Do not equate NAICS 518210 directly with physical data-center employment. It includes broader computing infrastructure/data-processing activities.

Preserve suppression/disclosure flags.

## 14.2 BLS LAUS — labor force and unemployment

Official tables/data information:

https://www.bls.gov/lau/tables.htm

County annual averages are available back to 1990.

Ingest:

- labor force;
- employed;
- unemployed;
- unemployment rate.

## 14.3 BEA Regional Economic Accounts — county GDP and income

GDP by county:

https://www.bea.gov/data/gdp/gdp-by-county

API landing page:

https://apps.bea.gov/api/

Use county GDP and county personal-income series. The BEA Regional API documents county GDP tables such as CAGDP1/CAGDP9 beginning around 2001.

Ingest, where available:

- nominal GDP;
- real GDP;
- real GDP growth;
- population;
- personal income;
- per-capita personal income;
- earnings by industry where suitable.

## 14.4 Census County Business Patterns

API documentation:

https://www.census.gov/data/developers/data-sets/cbp-zbp/cbp-api.html

CBP provides county industry-level establishments, employment, first-quarter payroll, and annual payroll.

Use it for:

- establishment counts;
- industry structure;
- data-processing-related industry context;
- construction/business-services context.

## 14.5 Census Business Dynamics Statistics

API:

https://www.census.gov/data/developers/data-sets/business-dynamics.html

BDS time series cover 1978–2023 in the current release and provide job creation/destruction, establishment births/deaths, firm startup/shutdown measures.

Use BDS to test whether data-center entry is associated with broader local business dynamism.

## 14.6 IRS SOI county income

Official county data:

https://www.irs.gov/statistics/soi-tax-stats-county-data

County income data are available from tax year 1989 onward.

Ingest:

- returns;
- exemptions / population proxy where useful;
- adjusted gross income;
- wages and salaries;
- interest;
- dividends.

Prefer per-return and per-capita derived measures in addition to aggregate levels.

## 14.7 IRS migration

Official migration page:

https://www.irs.gov/statistics/soi-tax-stats-migration-data

County-to-county inflow/outflow series extend back to the early 1990s, with methodological breaks documented by IRS.

Create:

- in-migrant returns;
- out-migrant returns;
- net returns;
- net exemptions/person proxy;
- net AGI migration;
- inflow/outflow AGI per return.

Flag methodology-series breaks; do not treat 2010→2011 and 2011→2012 as perfectly identical series without review.

## 14.8 Census ACS 5-year

Use ACS 5-year county data for:

- median household income;
- population;
- poverty;
- housing costs;
- rent;
- owner costs;
- educational attainment;
- commuting and demographic controls.

API examples:

https://api.census.gov/data/2024/acs/acs5/profile.html

ACS variables and vintages change; maintain a variable registry.

## 14.9 Census Building Permits Survey

Official page:

https://www.census.gov/construction/bps/index.html

County residential permit data are available annually and can proxy residential-development response. Do not misrepresent residential permits as commercial data-center construction permits.

The national nonresidential permit series was discontinued in 1995, so data-center permit timing must come from local records.

## 14.10 FHFA House Price Index

Official dataset:

https://www.fhfa.gov/data/house-price-index

Use county annual HPI where available.

Compute housing appreciation and combine with income to construct affordability pressure.

## 14.11 Census state/local government finances

Official program/API:

https://www.census.gov/programs-surveys/gov-finances.html

https://www.census.gov/programs-surveys/gov-finances/data/api.html

Current time-series API:

https://www.census.gov/data/developers/data-sets/govslocalfin.html

Use for broad fiscal context:

- general revenue;
- property-tax revenue;
- expenditure;
- debt;
- selected capital spending.

Direct data-center fiscal attribution will usually require local assessor/budget/incentive records and must be stored separately.

---

# 15. Utility, resource, and environmental datasets

## 15.1 EIA Form 861

Official files:

https://www.eia.gov/electricity/data/eia861/index.php

EIA-861 contains utility-level sales, revenue, customer counts, utility attributes, and service-territory information. Utility data extend to 1990; county service-territory files are available from 2001 onward.

Use EIA data to create:

- utility-sector average retail electricity price;
- residential/commercial/industrial price;
- sales/load context;
- utility-county crosswalk;
- balancing authority / RTO context where available.

Important: utility service territories may span many counties. Never assign a utility-wide price shock to a single county as though it were directly observed there. Preserve the mapping uncertainty and coverage share.

## 15.2 USGS water use

National county water-use downloads:

https://water.usgs.gov/watuse/data/

2015 county dataset:

https://www.usgs.gov/data/estimated-use-water-united-states-county-level-data-2015

USGS provides historical five-year county water-use datasets for multiple periods. Use these as **resource-context** measures, not as direct facility water-use measurements unless facility-specific evidence exists.

## 15.3 EPA eGRID

Official dataset:

https://www.epa.gov/egrid

Use eGRID for grid-region emissions and generation-mix context.

Do not attribute a grid-region average emissions rate to a specific facility as exact operational emissions. Label it as regional electricity-system context.

---

# 16. Opposition and political-mobilization data

The opposition layer must be built from multiple signals because no single public source captures local sentiment.

## 16.1 Public-news discourse

For every data-center article/event, classify:

```text
stance = support | neutral | concern | opposition | mixed
```

And issue themes:

```text
electricity_price
grid_capacity
water
noise
air_pollution
generators
land_use
farmland
housing
property_values
tax_incentives
jobs
local_tax_revenue
secrecy_transparency
zoning
environment
climate
construction
traffic
other
```

Separately classify **who** is expressing the stance:

```text
resident
opposition_group
developer
local_official
state_official
utility
business_group
labor_group
environmental_group
journalist/editorial
unknown
```

An article describing opposition is not itself necessarily anti-data-center. Separate article tone from quoted stakeholder stance.

## 16.2 Civic/public-hearing activity

For zoning/planning/board/council records, capture where possible:

- total public comments;
- opposing comments;
- supporting comments;
- neutral comments;
- speakers for/against;
- meeting duration;
- continuances;
- vote;
- project outcome.

Store denominators. Raw opposition counts are not comparable across communities without participation/project normalization.

## 16.3 Grassroots groups and petitions

Discover named local opposition organizations and petitions from public sources.

For petitions, store only public campaign-level metadata such as:

- petition URL;
- title;
- target;
- location;
- launch date when known;
- public signature count snapshots;
- issue tags.

Do not scrape/store supporter names or personal details.

## 16.4 State legislation

Use Open States / Plural Open for state legislative data.

Documentation:

https://docs.openstates.org/

Bulk data:

https://open.pluralpolicy.com/data/

Search data-center-related bills and classify:

```text
facilitative
neutral_study_reporting
ratepayer_protection
resource_restriction
local_control
moratorium
incentive_reform
restrictive_other
```

Store bill actions/status separately from classification.

## 16.5 Google Trends — optional state-level signal

Google Trends API alpha documentation:

https://developers.google.com/search/apis/trends

The alpha API currently exposes a rolling five-year window with consistently scaled data but access is limited.

Implement this as an optional adapter. If credentials/access are absent, the project must still build.

Because Trends geography may be state/subregion rather than county, do not fabricate county-level values from state-level interest. Render a state layer or label county inheritance explicitly if used.

Potential opposition query basket:

```text
"data center opposition"
"stop data center"
"data center moratorium"
"data center protest"
"data center noise"
"data center water"
"data center power bill"
"data center electricity rates"
```

General-interest denominator basket:

```text
"data center"
"AI data center"
"data center development"
```

## 16.6 National surveys for calibration

National polling is valuable for trend calibration but generally should not be copied into every county as though it were local polling.

Useful 2026 reference series include:

Annenberg Public Policy Center:

https://www.annenbergpublicpolicycenter.org/opposition-to-local-data-centers-rises-sharply-annenberg-survey-finds/

Gallup:

https://news.gallup.com/poll/709772/americans-oppose-data-centers-area.aspx

Pew Research Center:

https://www.pewresearch.org/short-reads/2026/03/12/how-americans-view-data-centers-impact-in-key-areas-from-the-environment-to-jobs/

Use repeated same-question series for longitudinal change. Use different pollsters as cross-sectional validation, not as a naive concatenated time series.

---

# 17. News/stance classifier design

Build a classifier pipeline that is auditable.

## 17.1 Candidate extraction

For each document:

1. determine whether it is actually about a physical data center project/industry;
2. identify candidate facilities/projects/locations/operators;
3. identify events;
4. identify factual numeric claims;
5. identify stakeholder stances;
6. identify issue themes.

## 17.2 Human-labeled validation set

Before trusting classifier aggregates, manually label a stratified sample of at least 500 relevant passages/documents if feasible.

Stratify across:

- years;
- regions;
- local/national/trade media;
- positive/neutral/negative coverage;
- project lifecycle stage.

Measure:

- precision;
- recall;
- F1;
- confusion matrix;
- inter-rater agreement for a smaller double-coded subset.

Do not publish opposition-index components built on an unvalidated classifier without prominently marking them experimental.

## 17.3 LLM usage

If an LLM API is available, use structured-output extraction into Pydantic schemas.

But implement a deterministic baseline that can run without a paid API.

Store:

```text
extraction_method
model_name
model_version
prompt_version
run_timestamp
```

Never let an LLM-generated claim become canonical without its source passage/source record.

---

# 18. County-year data-center exposure variables

Generate the following treatment/exposure measures for every county-year.

## 18.1 Binary first entry

Let \(G_c\) be the first year county \(c\) has a sufficiently verified operational data center.

\[
D_{c,t}=1[t\ge G_c]
\]

Maintain minimum DQS threshold configurable, initially e.g. 70.

## 18.2 Active facility count

\[
F_{c,t}=\sum_i 1[i\text{ active in county }c\text{ at }t]
\]

## 18.3 New facility count

\[
N_{c,t}=\sum_i 1[\text{facility }i\text{ becomes operational in }t]
\]

## 18.4 Active square footage

\[
SQFT_{c,t}=\sum_i sqft_{i,t}
\]

Use only observed/defensibly derived area in the default observed exposure variable.

## 18.5 Active MW

Maintain two fields:

\[
MW^{obs}_{c,t}
\]

and

\[
MW^{model}_{c,t}
\]

Never silently combine them.

If an aggregate exposure using modeled MW is built, name it explicitly.

## 18.6 Capital investment

Separate:

- announced capex;
- verified/realized capex where available;
- assessed real-property improvement;
- taxable personal property where obtainable.

## 18.7 Construction exposure

Build:

```text
projects_under_construction
construction_sqft
construction_capex_announced
```

This lets the analysis distinguish construction-phase economic effects from operational-phase effects.

---

# 19. Statistical-analysis philosophy

The analytics layer must contain three levels of evidence.

## Level 1 — descriptive

Raw and normalized time-series comparisons.

Examples:

- employment growth in treated county;
- opposition article ratio;
- data centers per 100k residents;
- tax revenue per resident.

Label as descriptive.

## Level 2 — matched/counterfactual

Estimate what likely would have happened in a treated county using comparable untreated/not-yet-treated counties.

Label as quasi-experimental / counterfactual estimate.

## Level 3 — formal causal panel estimators

Use modern staggered-treatment event-study / difference-in-differences estimators with diagnostics and uncertainty.

Label results as causal estimates only when identifying assumptions are stated and diagnostics are acceptable.

---

# 20. Outcome transformations

For positive-valued economic outcomes such as employment, GDP, AGI, wages, establishments, HPI:

\[
y_{c,t}=\ln(Y_{c,t})
\]

For coefficients estimated in logs, convert to percent effect as:

\[
\%\Delta =100(e^{\hat\beta}-1)
\]

For rates already expressed as percentages, e.g. unemployment rate, use level/percentage-point specifications unless another transformation is explicitly justified.

For zero-valued count outcomes, consider `log1p` or Poisson models and document the choice.

Inflation-adjust dollar series before comparing across time. Prefer agency-provided real series when available; otherwise use a documented national deflator.

---

# 21. Pre-treatment covariates

Candidate matching / conditional trends covariates should include only pre-treatment values and trends.

At minimum:

- log population;
- urban/metro status;
- pre-treatment employment level and trend;
- pre-treatment GDP level and trend;
- median household income;
- unemployment rate;
- industry composition;
- construction share;
- information/data-processing share;
- housing-price trend;
- population growth;
- educational attainment;
- pre-existing electricity price / utility context;
- Census division;
- pre-existing fiber/infrastructure variables if public data are incorporated.

Never use a post-treatment variable to construct the primary propensity/matching model.

---

# 22. Primary formal panel estimator — staggered adoption event study

Data centers enter counties at different dates. A naive two-way-fixed-effects event study can produce biased weighting when treatment effects are heterogeneous.

Therefore use a modern staggered-treatment estimator as the primary event-study framework.

PyFixest supports saturated/Sun–Abraham-style event studies:

https://pyfixest.org/difference-in-differences.html

Define relative event time:

\[
k=t-G_c
\]

Estimate dynamic effects over a standard window such as:

```text
k = -10 ... +15
```

with bins for more distant leads/lags if sample size requires.

Reference period:

```text
k = -1
```

Conceptual saturated specification:

\[
y_{ct}=\alpha_c+\lambda_t+\sum_g\sum_{k\ne -1}\beta_{gk}
1[G_c=g]1[t-g=k]+\epsilon_{ct}
\]

Aggregate cohort-specific \(\beta_{gk}\) into event-time effects using transparent cohort weights.

Primary outputs:

- event-time ATT estimate;
- standard error;
- 95% confidence interval;
- number of treated counties contributing;
- pre-trend joint test;
- overall post-treatment ATT;
- 1–3 year ATT;
- 4–7 year ATT;
- 8+ year ATT where data support it.

Run separately for:

- first operational entry;
- major expansion events when defensible;
- construction-start treatment.

Do not combine construction and operational treatment into one unlabeled event.

---

# 23. Callaway–Sant’Anna validation

Where tooling permits, validate primary results with a group-time ATT estimator following Callaway and Sant’Anna.

Conceptually estimate:

\[
ATT(g,t)=E[Y_t(1)-Y_t(0)\mid G=g]
\]

for treatment cohort \(g\) and time \(t\), using never-treated or not-yet-treated units as valid controls.

Aggregate to event time:

\[
ATT(k)=\sum_g w_{gk}ATT(g,g+k)
\]

The R `did` package is the canonical implementation:

https://bcallaway11.github.io/did/

An optional Python implementation exists via the `differences` package.

This validation path must be optional so a Python-only user can still build the core project.

---

# 24. Matched county / synthetic counterfactual model

The public-facing county detail page needs an intuitive local counterfactual even when the national panel estimator is the stronger research design.

For each treated county \(c\), construct an eligible donor pool of counties that:

- are never treated during the relevant horizon, or not treated until after the required post window;
- have sufficient pre-treatment data;
- are not immediate geographic spillover counties where exclusion is required;
- pass minimum data completeness.

## 24.1 Matching distance

Standardize pre-treatment feature vector \(X_c\).

Compute Mahalanobis distance:

\[
d(c,j)=\sqrt{(X_c-X_j)^T S^{-1}(X_c-X_j)}
\]

Also calculate propensity score as a diagnostic, not the sole matching criterion.

Use calipers on critical variables such as population scale and pre-trend.

## 24.2 Synthetic weights

For selected donor set \(J\), solve nonnegative weights:

\[
\min_{w_j}\sum_{t\in Pre}
\left(Y_{c,t}-\sum_{j\in J}w_jY_{j,t}\right)^2
+\lambda\sum_j w_j^2
\]

subject to:

\[
w_j\ge0,\qquad \sum_jw_j=1
\]

Use ridge regularization to reduce unstable extreme weights.

Do this for key outcomes individually or use a multivariate pre-fit objective.

## 24.3 Counterfactual effect

\[
\Delta_{c,t}=Y_{c,t}-\hat Y^0_{c,t}
\]

where:

\[
\hat Y^0_{c,t}=\sum_jw_jY_{j,t}
\]

Report:

- pre-period RMSPE;
- donor counties and weights;
- post-treatment gap;
- placebo/permutation distribution where feasible;
- uncertainty/sensitivity.

Do not produce a DCEDI causal score for a county with poor pre-treatment fit.

Suggested initial fit rule:

```text
minimum 5 years pre-treatment
minimum 3 years post-treatment for first published dividend score
pre-fit RMSPE below configurable threshold
at least 5 valid donor counties
```

---

# 25. Continuous-intensity panel models

Binary entry does not capture 1 facility versus 40 facilities.

Estimate continuous treatment models using exposures such as:

- `log1p(active_facilities)`;
- `log1p(active_sqft)`;
- observed MW where sufficient;
- construction exposure.

Baseline fixed-effects model:

\[
y_{ct}=\alpha_c+\lambda_t+\beta X_{ct}+\gamma Z_{ct}+\epsilon_{ct}
\]

where \(X_{ct}\) is data-center exposure and \(Z_{ct}\) includes limited defensible time-varying controls.

Treat these as association/fixed-effects estimates unless a credible instrument or exogenous design is implemented.

Do not promote a fixed-effects association coefficient to causal merely because county/year fixed effects are present.

---

# 26. Advanced IV research lane

The May 2026 NBER working paper **Data Centers and Local Economies in the Age of AI: A Shift–Share Approach** provides an important research benchmark:

https://www.nber.org/papers/w35194

The authors combine a proprietary facility panel with county outcomes and use shift-share instruments based on pre-existing fiber-node proximity and historical college population shares combined with external data-center growth shocks.

Do not pretend to replicate their IV exactly without equivalent inputs.

Create an `advanced_iv/` research lane that can later explore public alternatives, but keep it out of the headline index until identification is validated.

A second 2026 research benchmark uses a Callaway–Sant’Anna staggered entry design:

https://journals.aom.org/doi/10.5465/AMPROC.2026.15909abstract

Use these studies to validate research direction, not to hard-code their reported coefficients into our outputs.

---

# 27. Inference and robustness

For formal models:

1. cluster standard errors at the county level where appropriate;
2. run state-clustered robustness because neighboring counties within a state can share policy/economic shocks;
3. with only ~50 state clusters, use wild cluster bootstrap for important state-clustered robustness when supported;
4. report 95% confidence intervals;
5. run joint pre-trend tests;
6. run alternative treatment timing definitions;
7. run alternative minimum DQS thresholds;
8. exclude mega-clusters such as Northern Virginia in sensitivity runs;
9. stratify metro vs nonmetro;
10. stratify early cloud/hyperscale/AI-era cohorts;
11. run placebo treatment dates;
12. test donor-pool sensitivity;
13. evaluate spillover radii.

Publish robustness metadata, not only the preferred estimate.

---

# 28. Spillovers

Data-center effects can spill across county boundaries through:

- employment commuting;
- electricity service territories;
- housing markets;
- construction labor markets;
- tax competition;
- water systems.

Create distance/exposure variables:

```text
dc_within_25mi
dc_within_50mi
dc_within_100mi
neighbor_county_active_facilities
neighbor_active_mw_observed
```

For primary binary-entry DiD, run sensitivity excluding counties within configurable radii of treated counties from the control group.

For utility-price analysis, use utility service territory rather than county alone wherever possible.

---

# 29. Economic outcome families

Analyze at minimum:

## Employment

- total employment;
- private employment;
- construction employment;
- NAICS 518210 employment where observable;
- information-sector employment;
- unemployment rate.

## Wages/income

- total wages;
- average pay;
- IRS total AGI;
- IRS AGI per return;
- IRS wages per return;
- BEA personal income;
- ACS median household income.

## Business activity

- total establishments;
- establishment births/deaths;
- firm startup/shutdown measures;
- industry-specific establishment change.

## Output

- real GDP;
- real GDP per capita;
- selected sectoral GDP where stable.

## Population/migration

- population;
- IRS net migration;
- net migrant AGI;
- ACS demographic shifts.

## Housing

- FHFA HPI;
- residential permit activity;
- affordability measures.

## Fiscal

- broad county/local government revenue/expenditure context;
- direct data-center property tax/incentive metrics only where primary local records exist.

---

# 30. Observed Economic Momentum vs Data Center Economic Dividend

Create two separate products.

## 30.1 OEM — Observed Economic Momentum

For every county-year, describe actual recent economic change independent of data-center causality.

This may use weighted standardized growth in:

- employment;
- real GDP;
- income;
- establishments;
- migration.

Label clearly as **Observed Economic Momentum**.

## 30.2 DCEDI — Data Center Economic Dividend Index

Only produce for treated counties with an acceptable counterfactual fit.

For outcome \(j\), county \(c\), and horizon \(H\), define average post-treatment abnormal log outcome:

\[
d_{c,j,H}=\frac{1}{H}\sum_{h=1}^{H}
\left[\ln Y_{c,G_c+h}-\ln \hat Y^0_{c,G_c+h}\right]
\]

Default horizon for initial published score:

```text
H = min(5, available post-treatment years), minimum 3
```

Create component effects for:

- employment;
- real GDP;
- household/resident income;
- wages;
- establishments;
- migration/business dynamism where coverage supports.

Do not put housing-price appreciation directly into the positive economic dividend because it is ambiguous: it increases owner wealth but can reduce affordability.

---

# 31. Robust index scaling

Do not use min-max scaling because one outlier can reshape the entire historical index.

Use a fixed calibration/reference distribution.

For raw component \(x\), calculate robust z-score:

\[
z=\frac{x-\operatorname{median}(X_{ref})}
{1.4826\operatorname{MAD}(X_{ref})}
\]

where:

\[
MAD=\operatorname{median}(|X-\operatorname{median}(X)|)
\]

Winsorize:

\[
z^*=\max(-3,\min(3,z))
\]

Convert to 0–100 using the standard normal CDF:

\[
Score=100\Phi(z^*)
\]

This yields an interpretable percentile-like scale and avoids annual rescaling that would make historical values move merely because new years were added.

Freeze a calibration period once v1.0 is declared, e.g. the complete historical reference sample available at that release. Version the calibration metadata.

---

# 32. DCEDI construction

Initial component weights should be explicit and configurable.

Suggested starting weights:

```text
employment effect                 0.25
real GDP effect                   0.20
resident income effect            0.20
wage effect                       0.15
establishment/business effect     0.15
migration/dynamism effect         0.05
```

For available component scores \(S_j\):

\[
DCEDI=\frac{\sum_{j\in A}w_j S_j}{\sum_{j\in A}w_j}
\]

where \(A\) is the set of components meeting quality thresholds.

Publish:

- score;
- components;
- coverage share \(\sum_{j\in A}w_j\);
- data quality;
- confidence interval/sensitivity range.

If available weight coverage is below 0.60, do not publish a headline DCEDI; return `insufficient_data`.

Create a separate **Data Center Fiscal Dividend Index (DCFDI)** when enough direct local fiscal evidence exists rather than forcing weak fiscal proxies into DCEDI.

---

# 33. Data Center Fiscal Dividend Index

Where local fiscal evidence exists, calculate variables such as:

\[
TaxPerCapita_{ct}=\frac{DC\ attributable\ tax\ revenue}{population}
\]

\[
DCRevenueShare_{ct}=\frac{DC\ attributable\ tax\ revenue}{total\ local\ revenue}
\]

\[
NetFiscalDividend=DCRevenue-DCRelatedPublicCosts-IncentiveCost
\]

Also report:

- taxable assessed value;
- incentive commitments;
- realized abatements where obtainable;
- residential tax-rate trend;
- public capital expenditures plausibly related to the project.

Do not label announced investment or announced tax benefits as realized fiscal effects.

---

# 34. Data Center Community Cost Index — DCCCI

The cost index should emphasize measurable pressure, not advocacy claims.

Candidate components:

```text
electricity price pressure
housing affordability pressure
water-resource pressure/context
grid/emissions externality context
public subsidy/incentive burden
land/noise/environmental impact where nationally comparable data become available
```

## 34.1 Electricity-price pressure

Estimate treated-vs-counterfactual change at the most defensible geography.

Because EIA prices are utility-level, create utility-year analysis and then county exposure mappings.

Never imply precise county price causality where a utility spans many counties.

## 34.2 Housing affordability

Create:

\[
AffordabilityRatio=\frac{HousingCostIndex}{HouseholdIncomeIndex}
\]

or equivalent rent/home-value-to-income measures.

Analyze counterfactual divergence after treatment.

## 34.3 Water context

Use USGS county withdrawal/supply indicators as baseline scarcity/use context and facility-specific water claims only where sourced.

A data center in a water-intensive county is not proof that the facility itself caused water stress.

## 34.4 Environmental electricity context

Use eGRID emission rates to estimate regional electricity-system externality context only when combined with a defensible facility load estimate.

Keep observed MW and modeled MW scenarios separate.

## 34.5 DCCCI scaling

Use the same robust z → normal-CDF scaling framework as DCEDI, with directionality set so **higher score means higher community cost/pressure**.

Publish component coverage.

---

# 35. Data Center Opposition Index — local DCOI

Build a county-year local index from signals that actually vary locally.

Suggested components:

```text
news/public-discourse opposition          0.20
civic/public-hearing opposition           0.25
grassroots mobilization                   0.15
project resistance/outcomes               0.25
restrictive policy/legal activity         0.15
```

Google Trends may be displayed as a state-level supplementary signal and incorporated into a state index, but do not inject state search values into county DCOI without explicit labeling.

## 35.1 News Opposition Ratio

Let:

- \(O_{ct}\) = relevant articles/passages containing verified stakeholder opposition;
- \(A_{ct}\) = all relevant data-center articles/passages.

Use smoothed ratio:

\[
NOR_{ct}=\frac{O_{ct}+\alpha}{A_{ct}+\alpha+\beta}
\]

with weak Beta prior such as \(\alpha=1,\beta=1\), to avoid extreme values in counties with one article.

Also calculate article volume separately.

## 35.2 Civic Opposition Rate

Where public comments are countable:

\[
COR_{ct}=\frac{OpposingComments+1}
{Opposing+Supporting+Neutral+3}
\]

Participation intensity:

\[
PI_{ct}=\ln\left(1+\frac{TotalComments}{Population}\times10000\right)
\]

Combine standardized COR and PI rather than treating a 5–0 hearing the same as a 5,000–200 hearing.

## 35.3 Grassroots Mobilization

Create separate standardized variables:

- active opposition groups;
- petition count;
- public signature count snapshots;
- protest events;
- protest attendance only when reliably reported.

Avoid arbitrary raw-unit addition. Standardize each component before aggregation.

## 35.4 Project Resistance

For proposed projects in a county-year, classify outcomes:

```text
approved
approved_with_conditions
delayed
litigated
withdrawn
denied
cancelled
```

Initial severity weights, configurable:

```text
approved                  0.00
approved_with_conditions  0.15
delayed                   0.35
litigated                 0.50
withdrawn                  0.75
denied                     1.00
cancelled_due_opposition   1.00
```

Calculate:

\[
PRI_{ct}=\frac{\sum_p severity_p}{\max(1,N^{proposed}_{ct})}
\]

Do not attribute every cancellation to opposition. Require evidence linking opposition/regulatory resistance to the outcome.

## 35.5 Restrictive policy activity

Assign documented bill/local-action weights by type/status, separately tracking proposal and enactment.

For example, an introduced moratorium bill is not equivalent to an enacted moratorium.

Standardize counts by project exposure or population where appropriate.

## 35.6 DCOI composite

Robust-scale each component to 0–100 and calculate weighted mean across available components.

Require at least 0.50 weight coverage for a provisional local DCOI and at least 0.70 for a normal published score.

Expose `coverage` and `confidence` alongside score.

---

# 36. National DCOI

National public opinion deserves a separate calibrated index.

Construct national DCOI from:

- repeated survey opposition;
- national aggregated news opposition;
- national project resistance;
- national mobilization;
- policy activity.

Because poll questions differ, maintain poll-series IDs and estimate within-series changes first.

Do not average 70% Gallup opposition and 61% Annenberg opposition as though they were the same question.

Possible model:

\[
SurveyLatent_t=\mu_t+\delta_{pollster/question}+\epsilon
\]

A hierarchical/meta-analytic model may later estimate a common latent national sentiment level, but v0.1 may simply show each poll series separately and use the repeated Annenberg measure for change calibration.

---

# 37. Normalization for industry growth

This is essential.

Raw opposition events will rise mechanically if the number of proposed data centers rises.

Always publish denominator-aware measures such as:

\[
OppositionIncidence_t=
\frac{ProjectsFacingOrganizedOpposition_t}
{ProjectsProposed_t}
\]

\[
ResistanceSuccess_t=
\frac{Blocked+Denied+Withdrawn+OppositionLinkedCancellation}
{ProjectsFacingOpposition_t}
\]

\[
OppositionPerMW_t=
\frac{OppositionEvents_t}{ProposedMW_t}
\]

only where proposed MW coverage is sufficient.

Also report raw counts because denominators and counts answer different questions.

---

# 38. Vintage/cohort analysis

Create development cohorts:

```text
2000–2004  early internet/hosting
2005–2014  cloud emergence
2015–2022  hyperscale cloud
2023–present AI infrastructure era
```

Treat labels as analytical conventions, not universal industry definitions.

Compare:

- facility scale;
- capex per job;
- jobs per MW;
- economic dividend per MW;
- tax dividend per MW;
- opposition incidence;
- community cost per MW;
- construction vs operational effects.

Version the cohort definitions in config.

---

# 39. Capacity-normalized metrics

Where MW coverage is adequate, calculate:

\[
JobsPerMW=\frac{Jobs}{MW}
\]

\[
TaxRevenuePerMW=\frac{DC\ attributable\ tax\ revenue}{MW}
\]

\[
EconomicDividendPerMW=\frac{Estimated\ economic\ effect}{MW}
\]

\[
OppositionEventsPerMW=\frac{OppositionEvents}{Proposed\ or\ active\ MW}
\]

Use observed MW by default. Modeled-MW metrics must be labeled `modeled` and excluded from main score unless methodology is validated.

---

# 40. Missing data and suppression

Do not zero-fill suppressed or unavailable government data.

Maintain flags:

```text
observed
suppressed
not_applicable
not_available
not_yet_released
parser_error
```

For QCEW/CBP suppressed data, preserve suppression and use aggregate industry levels only where methodologically defensible.

Index component availability must propagate to index coverage.

---

# 41. Inflation and real-dollar treatment

Store nominal and real values separately.

If source provides real chained-dollar series, preserve them.

If deflating nominal local values, document:

- deflator series;
- base year;
- formula.

For example:

\[
RealValue_t=NominalValue_t\times\frac{P_{base}}{P_t}
\]

Do not add chained-dollar components as if ordinary additive dollars where the source warns against it.

---

# 42. Uncertainty for composite indices

Where component values derive from estimated treatment effects, propagate uncertainty.

For each county/index, use bootstrap or simulation:

1. draw component effect from its sampling distribution or bootstrap distribution;
2. repeat robust scaling using frozen calibration parameters;
3. calculate composite;
4. repeat 500–2,000 times depending runtime;
5. store median, 2.5th percentile, 97.5th percentile.

For source-data uncertainty such as uncertain opening year, run sensitivity scenarios:

- earliest plausible year;
- canonical year;
- latest plausible year.

Publish an `index_stability` flag if classification changes materially.

---

# 43. National map UX

The homepage should open to a national county map.

## 43.1 Map layers

Selectable choropleths:

- DCEDI Economic Dividend;
- DCOI Opposition;
- DCCCI Community Cost;
- BSG Benefit–Sentiment Gap;
- NCB Net Community Balance;
- Observed Economic Momentum;
- active facility count;
- active square footage;
- observed MW where covered;
- opposition incidence;
- project resistance;
- data quality/coverage.

Point layers:

- operating facilities;
- under-construction projects;
- proposed projects;
- cancelled/denied projects;
- opposition events/groups where publishable.

## 43.2 Time control

Provide year slider, initially 2000–latest complete analytical year.

Facilities/events must change with the selected year.

Economic data lags must be visible. If 2026 facility data exist but 2026 GDP does not, do not silently carry forward GDP as though current.

## 43.3 Filters

At minimum:

- year;
- state;
- facility status;
- operator;
- project stage;
- facility cohort;
- minimum DQS;
- metro/nonmetro;
- index data coverage.

## 43.4 County tooltip

Show concise values:

```text
County, State
Active facilities
First verified DC year
DCEDI
DCOI
DCCCI
BSG
Data quality
```

Do not overload tooltip with methodology.

## 43.5 County detail panel/page

Show:

1. facility/project timeline;
2. all facilities/projects;
3. index cards with uncertainty and coverage;
4. actual vs counterfactual employment chart;
5. actual vs counterfactual GDP chart;
6. actual vs counterfactual income chart;
7. event-study context;
8. opposition timeline;
9. project outcomes;
10. electricity/housing/resource context;
11. source list;
12. data-quality details;
13. donor counties/synthetic weights;
14. caveats.

## 43.6 Facility detail

Show:

- canonical name;
- aliases;
- operator history;
- location;
- project phases;
- event timeline;
- capex/MW/sqft/jobs with observed/estimated status;
- source/evidence records;
- DQS.

---

# 44. Map geometry

Use U.S. Census cartographic boundary files.

Current source page:

https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html

A 1:5,000,000 or 1:20,000,000 county layer is suitable for national rendering. Preserve county FIPS.

Generate a simplified GeoJSON in the build pipeline.

Do not use a third-party boundary layer without a reason when official Census data are available.

---

# 45. Static site export contract

Generate small, versioned files such as:

```text
site/public/data/metadata.json
site/public/data/counties.geojson
site/public/data/county-index-latest.json
site/public/data/county-index-by-year.json
site/public/data/facilities.min.json
site/public/data/projects.min.json
site/public/data/national-timeseries.json
site/public/data/state-timeseries.json
site/public/data/methodology-summary.json
site/public/data/data-version.json
```

For large detail datasets, shard by state or county FIPS:

```text
site/public/data/county/51059.json
site/public/data/state/VA.json
```

Do not force the browser to download every source claim in the nation on initial page load.

Include:

```json
{
  "data_version": "YYYY-MM-DD+gitsha",
  "built_at": "ISO8601",
  "latest_facility_year": 2026,
  "latest_economic_year": 2025,
  "methodology_version": "0.1.0"
}
```

---

# 46. Data acquisition manifests

Each downloader must write a manifest with:

```text
source_name
source_url
request_url
retrieved_at
http_status
etag
last_modified
sha256
local_path
license
parser_version
```

If unchanged by hash/ETag, allow refresh to skip reprocessing.

Never rely solely on mutable URLs without recording retrieval metadata.

---

# 47. CLI

Create a coherent CLI, for example:

```bash
uv run dccio sources list
uv run dccio acquire pnnl
uv run dccio acquire qcew --years 2000:2025
uv run dccio acquire bea --years 2001:2025
uv run dccio acquire cbp --years 2000:2024
uv run dccio acquire irs-county --years 2000:2023
uv run dccio acquire irs-migration --years 2000:2023
uv run dccio acquire fhfa
uv run dccio acquire eia861
uv run dccio acquire boundaries
uv run dccio discover news --from 2016 --to 2026
uv run dccio resolve facilities
uv run dccio build facility-panel
uv run dccio build county-panel
uv run dccio analyze event-study
uv run dccio analyze synthetic-controls
uv run dccio build indices
uv run dccio export site
uv run dccio validate
```

Commands should be resumable and idempotent where possible.

---

# 48. Makefile / top-level workflow

Create convenience targets:

```bash
make setup
make bootstrap
make acquire-core
make build-data
make analyze
make site-data
make site
make test
make validate
make publish-ready
```

`make publish-ready` must fail if critical data-validation or site-build tests fail.

---

# 49. Configuration, credentials, and graceful degradation

`.env.example` may contain placeholders such as:

```text
CENSUS_API_KEY=
BEA_API_KEY=
OPENSTATES_API_KEY=
GOOGLE_TRENDS_API_KEY=
LLM_API_KEY=
```

Do not require optional keys for core local build.

Census currently requires API keys for many API queries; where bulk downloads exist, prefer bulk files for reproducible historical acquisition and use APIs as an alternative.

Never commit credentials.

---

# 50. GitHub Actions

## 50.1 Test workflow

On pull request/push:

- Python lint/type/tests;
- unit tests;
- schema tests;
- a small fixture-based ETL integration test;
- site TypeScript/build test.

## 50.2 Pages workflow

On push to `main`:

- install Node dependencies;
- verify required pre-generated site data exists;
- build Vite site with correct GitHub Pages base path;
- deploy artifact to GitHub Pages.

Do not run multi-gigabyte Common Crawl ingestion in Pages deploy.

## 50.3 Manual data refresh

Provide `workflow_dispatch` for modest public API datasets if desired, but document that the full historical news/facility reconstruction is expected to run locally because of network/storage/runtime constraints.

---

# 51. Testing and data-quality requirements

## 51.1 Schema tests

Assert:

- unique primary IDs;
- valid FIPS;
- lat/lon ranges;
- event date ranges;
- valid event taxonomy;
- no impossible negative MW/sqft/capex;
- no operational date after closure without an intervening reopen event;
- `observed` values always have source claims.

## 51.2 Temporal consistency

Flag sequences such as:

```text
OPERATIONAL before ANNOUNCED
CLOSED before OPERATIONAL
EXPANSION_OPERATIONAL before EXPANSION_ANNOUNCED
```

Do not automatically delete them because sources can describe retroactive events; send to review.

## 51.3 Duplicate detection

Test for facilities within small geographic distance with highly similar aliases/operators.

## 51.4 County panel integrity

Assert one row per `county_fips, year`.

## 51.5 Statistical unit tests

Use simulated data to test that:

- zero-treatment-effect DGP returns approximately zero effects;
- known synthetic treatment effects are recovered within tolerance;
- pre-trend diagnostics detect intentionally violated trends;
- index scaling maps reference median near 50;
- higher cost values monotonically increase DCCCI component scores.

## 51.6 Golden fixtures

Create a small hand-verified set of facilities across several states with known events and sources. Use as regression tests for parsers/entity resolution.

---

# 52. Human review workflow

The project cannot responsibly automate every historical identity and event decision.

Generate review files:

```text
data/review/facility_matches.csv
data/review/conflicting_claims.csv
data/review/low_confidence_dates.csv
data/review/project_outcome_attribution.csv
data/review/opposition_classification_sample.csv
```

Each decision should be importable back into the canonical build through an override file committed to version control, e.g.:

```text
config/manual_resolution.yml
```

Manual overrides must cite evidence and never silently edit generated Parquet files.

---

# 53. Copyright, licensing, and attribution

Create `docs/licensing.md` before public data publication.

Important starting points:

- PNNL/IM3 Data Center Atlas is ODbL because it is derived from OpenStreetMap; preserve required attribution and review share-alike obligations for adapted databases.
- U.S. federal statistical datasets are generally public government data, but preserve source attribution and dataset terms.
- Open States bulk data states that almost all data are available under public-domain dedication unless otherwise noted; verify the downloaded dataset.
- Common Crawl contains third-party copyrighted pages; do not treat the archive as permission to republish article bodies.
- News/publisher copyright remains with publishers.
- Wayback captures do not remove underlying copyright.

Add source acknowledgments in the site methodology/about page.

Do not choose the repository software/data license until the ODbL implications of the combined database are reviewed. It may be appropriate to separate software licensing from database licensing.

---

# 54. Performance and storage strategy

Do not commit enormous raw source archives.

Recommended:

```text
Git repo:
  code
  schemas
  configs
  canonical compact Parquet/CSV if reasonably sized
  site-ready JSON/GeoJSON
  source metadata and claims

Local/gitignored:
  WARC bodies
  copyrighted article text
  huge intermediate extracts
  temporary assessor downloads when redistribution is unclear
```

If canonical Parquet grows beyond practical Git size, evaluate Git LFS or release assets only after the schema stabilizes. Do not introduce LFS prematurely.

---

# 55. Research provenance in the UI

Every county/facility page should have a **Sources & Method** section.

For each headline metric expose:

- underlying source datasets;
- data year;
- whether observed/derived/estimated;
- model version;
- uncertainty interval;
- data coverage;
- last refresh.

A sophisticated user should be able to trace a number without reading source code.

---

# 56. Suggested UI information architecture

## Main navigation

```text
Map
Trends
Facilities
Projects
Opposition
Economics
Methodology
Data
About
```

## Map legend

Always show:

- selected metric;
- value range;
- latest year available;
- uncertainty/data-coverage indicator.

## Trends page

National time series:

- active facilities;
- new openings;
- proposed projects;
- opposition incidence;
- project resistance rate;
- national polling series;
- national DCOI;
- median DCEDI among treated counties by cohort;
- electricity/housing cost indicators.

## Compare page or compare interaction

Allow 2–5 counties to be compared on:

- facility history;
- economic outcomes;
- counterfactual gaps;
- opposition;
- cost;
- index components.

---

# 57. Methodology disclosure language

The site should state, in substance:

> The Observatory combines public facility/project evidence with public economic and civic datasets. Descriptive associations do not establish causality. Where the site reports estimated data-center economic effects, it uses matched-control and/or staggered-treatment panel methods intended to estimate a counterfactual trajectory. These estimates rely on assumptions including comparable pre-treatment trends and absence of unmodeled shocks. Confidence intervals and diagnostics are provided where feasible.

Do not bury this in legal boilerplate.

---

# 58. Phased build plan

Do not attempt the entire national historical reconstruction before producing a working vertical slice.

## Phase 0 — repository and reproducibility scaffold

Build:

- repo structure;
- environments;
- schemas;
- source registry;
- CLI;
- DuckDB/Parquet conventions;
- Census county boundaries;
- Vite/React/MapLibre shell;
- GitHub Pages workflow.

Acceptance: blank but functional county map deploys from local generated data.

## Phase 1 — present-day facility atlas

Ingest PNNL/IM3 Atlas.

Build:

- facilities table;
- county assignments;
- facility point layer;
- county facility counts;
- DQS scaffold.

Acceptance: map displays current facility inventory with source attribution.

## Phase 2 — historical Tier A reconstruction pilot

Choose 3–5 major markets with different histories, e.g.:

- Northern Virginia;
- Phoenix;
- Dallas/Fort Worth;
- Columbus/Central Ohio;
- Iowa/Nebraska or Oregon as a contrasting market.

Reconstruct operational year and project events using public sources.

Acceptance: reliable event timelines and entity-resolution workflow exist.

## Phase 3 — national Tier A historical expansion

Use reverse reconstruction + news discovery to build national operational-year coverage.

Acceptance: enough treated counties exist for first event-study panel.

## Phase 4 — core public economic panel

Ingest:

- QCEW;
- LAUS;
- BEA;
- CBP;
- BDS;
- IRS county;
- IRS migration;
- ACS;
- FHFA;
- EIA 861;
- Census boundaries.

Acceptance: county-year panel 2000 onward with documented completeness.

## Phase 5 — first economic analysis

Run:

- descriptive plots;
- staggered event study;
- pre-trend diagnostics;
- local matched/synthetic counterfactual for pilot counties;
- DCEDI v0.1.

Acceptance: site can show actual vs counterfactual trajectories and formal aggregate results.

## Phase 6 — opposition reconstruction

Add:

- GDELT/news metadata;
- local civic records;
- state legislation;
- project resistance outcomes;
- opposition groups/petitions;
- classifier validation.

Acceptance: DCOI v0.1 with coverage/confidence.

## Phase 7 — community cost

Add:

- EIA utility-price analysis;
- housing affordability;
- water context;
- eGRID;
- incentive/fiscal data where available.

Acceptance: DCCCI v0.1.

## Phase 8 — national integrated release

Publish:

- DCEDI;
- DCOI;
- DCCCI;
- BSG;
- NCB;
- national map;
- methodology;
- downloadable data.

---

# 59. Initial source registry

Create `config/sources.yml` containing at least these sources and metadata.

## Facility / infrastructure

### IM3 Open Source Data Center Atlas — PNNL/DOE

https://www.osti.gov/dataexplorer/biblio/dataset/2550666

License: ODbL.  
Role: present-day facility seed, geometry, county, operator/name, area where available.

### PNNL Data Center Atlas overview

https://www.pnnl.gov/publications/mapping-future-data-centers-new-public-tool-illuminates-whats-next

### IM3 Atlas code

https://github.com/IMMM-SFA/datacenter-atlas

## Economic

### BLS QCEW

https://www.bls.gov/cew/downloadable-data-files.htm

https://www.bls.gov/cew/about-data/data-availability.htm

### BLS LAUS

https://www.bls.gov/lau/tables.htm

### BEA Regional / GDP by County

https://www.bea.gov/data/gdp/gdp-by-county

https://apps.bea.gov/api/

### Census CBP

https://www.census.gov/data/developers/data-sets/cbp-zbp/cbp-api.html

### Census BDS

https://www.census.gov/data/developers/data-sets/business-dynamics.html

### IRS county income

https://www.irs.gov/statistics/soi-tax-stats-county-data

### IRS migration

https://www.irs.gov/statistics/soi-tax-stats-migration-data

### ACS

https://api.census.gov/data.html

### Census Building Permits

https://www.census.gov/construction/bps/index.html

### FHFA HPI

https://www.fhfa.gov/data/house-price-index

### Census State & Local Government Finances

https://www.census.gov/programs-surveys/gov-finances.html

https://www.census.gov/programs-surveys/gov-finances/data/api.html

## Utility / environment

### EIA-861

https://www.eia.gov/electricity/data/eia861/index.php

### USGS water use

https://water.usgs.gov/watuse/data/

### EPA eGRID

https://www.epa.gov/egrid

## Civic / political / public discourse

### Granicus Legistar API

https://webapi.legistar.com/Help

### Open States / Plural Open

https://docs.openstates.org/

https://open.pluralpolicy.com/data/

### Common Crawl CC-NEWS

https://commoncrawl.org/blog/news-dataset-available

### GDELT

https://gdeltproject.org/data.html

### Wayback CDX

https://web.archive.org/cdx/search/cdx

### Google Trends API alpha

https://developers.google.com/search/apis/trends

## National survey calibration

### Annenberg

https://www.annenbergpublicpolicycenter.org/opposition-to-local-data-centers-rises-sharply-annenberg-survey-finds/

### Gallup

https://news.gallup.com/poll/709772/americans-oppose-data-centers-area.aspx

### Pew

https://www.pewresearch.org/short-reads/2026/03/12/how-americans-view-data-centers-impact-in-key-areas-from-the-environment-to-jobs/

## Research-method validation

### NBER — Alvarez, Argente, Chow & Van Patten (2026)

https://www.nber.org/papers/w35194

### Zeng & Yue — Local Economic Effects of Data Center Entry (2026 abstract)

https://journals.aom.org/doi/10.5465/AMPROC.2026.15909abstract

### PyFixest staggered DiD/event-study documentation

https://pyfixest.org/difference-in-differences.html

### Callaway–Sant’Anna `did`

https://bcallaway11.github.io/did/

---

# 60. First implementation tasks — execute now

After reading this bootstrap specification, do not merely restate the plan. Begin implementation.

Perform the following in order.

## Task 1 — initialize repository

Create the repo structure, README, Python/Node project files, `.gitignore`, `.env.example`, configs, schemas, test directories, and GitHub workflows.

## Task 2 — write methodology stubs

Create substantive first versions of:

- `docs/methodology.md`
- `docs/data-dictionary.md`
- `docs/sources.md`
- `docs/licensing.md`
- `docs/causal-inference.md`
- `docs/index-methodology.md`

Do not leave empty TODO-only files.

## Task 3 — implement source registry and manifest framework

Implement reusable downloader utilities with caching, hash manifests, retry/backoff, user-agent identification, and rate limiting.

## Task 4 — ingest Census county boundaries

Produce a map-ready county GeoJSON with FIPS.

## Task 5 — ingest PNNL/IM3 Atlas

Download/ingest current facility layers, preserve source IDs, build initial `facilities.parquet`, and document ODbL attribution.

## Task 6 — build the first county facility exposure table

Produce:

```text
county_fips
current_facility_count
current_building_sqft_observed
current_campus_sqft_observed
```

Avoid double-counting overlapping PNNL campus/building representations. Create explicit logic distinguishing campus and building layers and document it.

## Task 7 — build first site

Render:

- county boundaries;
- facility points;
- facility-count choropleth;
- county tooltip;
- data-source attribution;
- data-version indicator.

Deployable build must work under the GitHub Pages repository base path.

## Task 8 — add one economic vertical slice

Ingest one complete economic source first, preferably QCEW, for a limited recent year range to validate county joins.

Render an economic metric layer in the UI.

## Task 9 — create historical enrichment scaffold

Implement source/claim/event schemas and an enrichment command that can accept a manually supplied URL/article and extract candidate facility events into `claims` without automatically promoting them to canonical facts.

## Task 10 — tests

Add tests for all of the above before expanding scope.

At the end of this first implementation pass, update `README.md` with:

- what works;
- commands to reproduce it;
- current data coverage;
- known gaps;
- next build priority.

---

# 61. Definition of done for v0.1

Do not call v0.1 complete until all are true:

- [ ] GitHub Pages deploys successfully.
- [ ] National county map renders without a server backend.
- [ ] PNNL/IM3 current facilities are ingested with attribution.
- [ ] Historical facility/event schema exists.
- [ ] Source and claim provenance work end-to-end.
- [ ] At least a meaningful subset of facilities has historical operational-year evidence.
- [ ] County-year economic panel exists for at least 2000 onward for core sources where available.
- [ ] Aggregate staggered event study runs for at least employment and one income/output outcome.
- [ ] Pre-trend diagnostics are generated.
- [ ] At least 10 treated counties have matched/synthetic-control detail views with acceptable pre-fit.
- [ ] DCEDI v0.1 is calculated only for counties meeting quality thresholds.
- [ ] Initial DCOI is built from at least two independent local signal families, with coverage exposed.
- [ ] DCCCI has at least electricity and housing components for a defensible subset.
- [ ] BSG and NCB are rendered only where required inputs exist.
- [ ] Every headline score exposes methodology version, data coverage, and uncertainty/quality.
- [ ] Downloadable CSV/Parquet outputs are generated.
- [ ] Tests pass.
- [ ] No copyrighted full-news corpus is committed.
- [ ] Licensing/attribution documentation exists.

---

# 62. Research questions the application should eventually answer

Design the data so future analysis can answer:

1. Does first data-center entry increase local employment relative to comparable counties?
2. Is the effect concentrated in construction and data-processing employment?
3. How long do construction effects persist?
4. Do establishments increase after entry?
5. Does resident AGI increase?
6. Does per-capita or per-return income increase, or only aggregate county income?
7. Does migration respond?
8. Do house prices rise relative to income?
9. Does local electricity pricing change in the relevant utility territory?
10. Are economic dividends different in metro and nonmetro counties?
11. Are hyperscale/Big Tech projects different from colocation projects?
12. Have economic dividends per MW changed across development eras?
13. Has opposition incidence increased after normalizing for project volume?
14. Which concerns most strongly predict project delays/denials?
15. Does opposition rise before economic costs appear, after they appear, or independently?
16. Are high-benefit counties less opposed?
17. Are high-cost/low-benefit counties more opposed?
18. Does direct local fiscal revenue reduce opposition?
19. Do incentive-heavy projects produce lower net fiscal dividends?
20. Which local policy structures are associated with successful development versus project resistance?

The schema must not prevent these future analyses.

---

# 63. Final instruction to the local agent

Build incrementally, commit frequently, and keep the application runnable after each phase.

When confronted with incomplete historical evidence:

1. preserve the candidate;
2. record the source;
3. record the claim;
4. score confidence;
5. place ambiguity in review;
6. do not invent the missing fact.

When confronted with statistical ambiguity:

1. prefer transparent assumptions;
2. publish diagnostics;
3. distinguish descriptive from counterfactual from causal;
4. report uncertainty;
5. never let the desire for a complete national map create false precision.

The long-term objective is an open, auditable national research infrastructure capable of showing **where data centers are, when they arrived, what changed economically, what costs emerged, how communities reacted, and how confidently we know each of those things**.

Begin the implementation now from **Task 1** and progress through the first vertical slice without waiting for further clarification unless a genuinely blocking credential or legal restriction prevents execution.
