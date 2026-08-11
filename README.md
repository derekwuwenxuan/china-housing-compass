# China Housing Compass

**中国楼市分析与住宅购买评估开源工具**

China Housing Compass is an open-source Codex skill and local Python toolkit that combines China housing-market analysis, home-purchase due diligence, transparent valuation, and private local tracking. It separates official records, developer quotes, resale listings, platform-reported transactions, rents, court-auction results, appraisals, field observations, and assumptions instead of blending them into one misleading “market price.”

Status: **alpha**. The toolkit supports structured research and conditional scenarios. It does not provide a guaranteed bottom, guaranteed return, legal opinion, or substitute for checking original government records, contracts, financing terms, and the physical property.

## Why this project exists

The project began when a photographer and operations practitioner—not a professional software developer—started preparing to buy a home. Sales talking points and developer promises were often difficult to reconcile with filing records, inventory, transactions, rents, contracts, construction progress, and infrastructure delivery. The project was built through **vibe coding with AI assistance** to make those checks repeatable and easier to audit.

That origin story is context, not evidence. The creator's occupation, personal experience, supplied prices, and market opinions never enter source grades, formulas, scenario factors, or recommendations. Public examples are fictional and synthetic. Vibe coding also does not replace review: changes are covered by automated tests, source-provenance rules, and privacy checks.

## What it does

- Analyzes city, district, submarket, project, building, unit, and time scope separately.
- Compares new-home filing and quoted prices with resale listings, platform-reported transactions, verified comparables, rents, judicial auctions, and inspectable bank appraisals.
- Tracks five-year market history and builds China-first one-to-three-year scenarios from policy, employment, income, population, credit, supply, inventory, absorption, land, delivery capacity, and infrastructure realization.
- Checks developer brand and legal project company separately, together with permits, escrow, contract rights, contractor, construction, model-home evidence, and delivery risk.
- Classifies infrastructure as operating, under construction, approved, conceptual, or developer-only.
- Uses attributed social-post and comment samples for issue discovery without treating them as proof or representative consensus.
- Separates exact-parcel history, nearby history, environmental evidence, and cultural or feng-shui acceptance.
- Builds an append-only local SQLite evidence database and self-contained offline HTML dashboard.
- Keeps RMB calculations transparent with Decimal arithmetic and visible assumptions.

## Installation

Python 3.9 or newer is required.

```bash
git clone https://github.com/derekwuwenxuan/china-housing-compass.git
cd china-housing-compass
python3 -m pip install -e .
china-housing-compass --help
```

To install the Codex skill, copy or link `skills/china-housing-compass` into your Codex skills directory. Invoke it with `$china-housing-compass`.

## Quick start

Create a private local workspace and import the fictional example:

```bash
china-housing-compass init housing-research
china-housing-compass import housing-research examples/synthetic-river-garden/evidence.json
china-housing-compass status housing-research
china-housing-compass dashboard housing-research
```

Open `housing-research/dashboard/index.html` locally. The database, imported snapshots, and generated reports remain on your computer and are excluded from Git by default.

Save an assessment after deriving a source-backed maximum price:

```bash
china-housing-compass valuate housing-research 1 \
  --risk-adjusted-max-price 1550000 \
  --monthly-rent 4000 \
  --annual-income 300000
```

Refresh from normalized saved snapshots:

```bash
china-housing-compass refresh housing-research 1 \
  --provider official_project=snapshots/official-project.json \
  --provider rent=snapshots/rent.json
```

Successful categories append normally. If a source fails, older evidence remains visible and that category is marked stale rather than silently erased.

## Core formulas

The three-video framework and supporting purchase metrics include:

```text
chargeable GFA = land area × FAR
floor land price = land transaction total / chargeable GFA
land-to-home ratio = floor land price / home sale unit price

gross rental yield = monthly rent × 12 / all-in acquisition cost
rent-supported price = monthly rent × 12 / target yield

project profit = sales revenue
                 - land - construction - finance - tax - marketing costs

price-to-income = all-in home price / annual household disposable income
absorption = sold units / released units
inventory months = comparable inventory / recent monthly transactions
```

For presales:

```text
delivery value = current comparable value × city × submarket × project × product factors

maximum price today = delivery net value / (1 + required return)^T
                      - purchase costs - financing costs - risk reserve
```

Land cost indicates developer cost pressure; it is not a resale floor. An assumed rent is a scenario, not rent evidence. A rent-supported value is an investment lens, not a guaranteed bottom. Conditional scenario results are not probabilities.

## Evidence model

- **A:** inspectable primary official record.
- **B:** attributable professional or primary commercial evidence with a disclosed method.
- **C:** dated field observation, developer quote, intermediary listing or rent page, or user-supplied input.
- **D:** unverified salesperson, forum, social post, or anonymous claim.

A user summary that says “official” remains grade C pending verification until the primary source, exact identity, scope, and date are inspectable. Asking prices, platform-reported transaction prices, verified closings, auction prices, appraisal prices, and rents stay as different price types.

## Social, parcel-history, and cultural evidence

Social evidence is an attributed sample for discovering issues and liquidity concerns. It is not proof of a transaction, defect, violation, contamination finding, or platform-wide consensus. The workflow records platforms, dates, access modes, sample counts, captured comment counts, commercial-content caveats, and disagreement. If comments cannot be inspected, it reports zero captured comments.

The skill can ask for permission to inspect visible public content through an already logged-in browser. It never requests credentials, automates login, bypasses CAPTCHA or access controls, assumes access, or reads private content.

Exact-parcel, approximately 500 m, approximately 1 km, and broader-area land history remain separate. Former farms, burial grounds, industry, and chemical activity are research leads until primary evidence establishes exact scope and an applicable mechanism. Feng-shui concerns are presented as cultural acceptance, personal fit, and possible resale-liquidity sensitivity—not as scientific fact or an automatic price discount.

## Codex skill

Invoke `$china-housing-compass` for:

- quick valuation;
- full market and purchase due diligence;
- creation of a private local tracker;
- refresh of saved evidence and dashboards.

The skill returns a fixed 13-section report covering decision, identity, price types, valuation ranges, formulas, five-year context, developer and delivery, social reputation and captured comments, parcel history and infrastructure, affordability, conditional scenarios, evidence freshness, and next actions.

## Synthetic public example

[`examples/synthetic-river-garden`](examples/synthetic-river-garden) is a completely fictional **合成示例**. Its city, project, companies, prices, inventory, rent, land, construction, social, and source records are invented only to exercise the workflow. Every source uses the reserved `example.test` domain and carries a synthetic marker.

It must not be cited as evidence about a real city, developer, project, or market. No user quote, personal visit, screenshot, contact detail, private database, or prior real-property conclusion is included.

## Privacy and conclusion independence

This public repository contains code, documentation, and synthetic fixtures only. Do not commit personal contact data, usernames, private visit notes, raw social captures, restricted pages, contracts, credentials, cookies, browser state, generated dashboards, or `housing.sqlite`.

User-supplied prices and opinions are stored as attributed, dated, case-scoped inputs. A user's forecast remains zero-weight by default and never becomes a reusable skill assumption. Creator biography and project motivation are excluded from valuation calculations and recommendation logic.

## 中文使用说明

China Housing Compass 是一个面向中国楼市分析和住宅购买评估的开源 Codex Skill 与本地工具。它把官方备案、开发商报价、二手挂牌、平台披露成交、可核验成交、租金、法拍、银行评估、现场观察和假设分开保存，再结合交付时间、开发商与项目公司、合同、施工、配套、人口、收入、供需、政策和五年走势给出条件区间。

### 项目缘起

项目发起人是一名摄影师兼运营从业者，并非专业程序员。因为近期准备买房，发现销售话术、开发商承诺与可核验的备案、库存、成交、租金、合同、施工和配套兑现之间经常存在信息差，于是通过 **vibe coding 与 AI 辅助**开发了这个项目，希望把核查过程做成可以重复、可以追溯的工具。

这段经历只用于说明项目缘起，不参与任何结论。发起人的职业、个人体验、询价和楼市观点不会进入证据评级、公式、情景参数或推荐逻辑。公开仓库只使用虚构合成案例；AI 生成的代码同样需要测试、来源审查和隐私检查。

### 安装与初始化

```bash
python3 -m pip install -e .
china-housing-compass init housing-research
```

### 导入、查看与刷新

```bash
china-housing-compass import housing-research examples/synthetic-river-garden/evidence.json
china-housing-compass status housing-research
china-housing-compass dashboard housing-research
china-housing-compass refresh housing-research 房源ID --provider 租金=租金快照.json
```

本地 HTML 可以直接打开；数据库和生成报告默认不会进入公开 Git 仓库。刷新失败不会清空旧数据，而会保留历史并标明过期类别。

### 使用边界

输出必须区分可比成交合理区间、租金支持价、交付日情景、风险调整后的今日最高承受价、总持有成本、支付能力和严重流动性压力。严重的监管账户、合同权利、产品不可核验或库存话术冲突，可以优先触发“等待/放弃”，不能被一个看似便宜的公式结果覆盖。

本项目提供的是条件分析，不是保底价格、收益承诺、法律意见或替代现场验房。重大购房决定前，请重新核验原始官方页面、合同、房号、付款路径和贷款条件。

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under the [MIT License](LICENSE).
