# Thirst Project sponsor ranking

An explainable 0–100 **outreach priority** score for Thirst Project's student-led clean-water mission and gala. It ranks sponsors with comparable public evidence and gives the team a reason, the underlying sources, and the best public outreach route we found. It does not estimate the probability of a sponsorship or send outreach.

## Run it

From the repository root, with Python 3.10 or later:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,history]'
python -m pytest
python -m scoring.cli --input data/sample_sponsors.csv
python -m scoring.cli --output results/ranked.csv
python -m scoring.cli --sponsor 'UTA'
```

Known names and aliases look up immediately. For a new name, review one row of public evidence and compare it against the ranked baseline:

```sh
python -m scoring.cli --sponsor 'Example Company' --template results/prospect.csv
# Fill the evidence CSV from public sources, using the anchors below.
python -m scoring.cli --sponsor 'Example Company' --candidate results/prospect.csv
```

Optionally, with an OpenAI API key in the environment, research a new name and produce a provisional score and placement against the verified benchmark in one command. This sends the name and optional domain hint to OpenAI and uses billable API web search. The output includes source URLs; confirm the facts and contact before using it. If the evidence is insufficient or the entity is ambiguous, the model withholds placement.

```sh
python -m scoring.cli --sponsor 'Example Company' --research \
  --domain example.com --save-evidence results/research-draft.csv
```

Set `OPENAI_RESEARCH_MODEL` to a web-search-capable model available to your API account if you need to override the default. See the [official web search documentation](https://developers.openai.com/api/docs/guides/tools-web-search). After reviewing the evidence and correcting the row, clear `evidence_status` and rerun with `--candidate`. Add approved rows to `data/public_evidence.csv` to update the benchmark.

## Research handoff

Use this schema in a spreadsheet, then export as UTF-8 CSV. The five real rows in `data/sample_sponsors.csv` illustrate complete and missing evidence. Research-track signoff is pending; treat this as the proposed v1 contract.

| Input | What to enter |
| --- | --- |
| `sponsor`, `aliases`, `website` | Current operating entity, alternate spellings separated by `\|`, and official site. Keep parent and brand separate when the records distinguish them. |
| `gen_z_*`, `cause_*`, `industry_*` | For each: `level` (integer 0–5 or blank), `reason` (one factual sentence), `url` (public primary evidence; separate multiple URLs with `\|`). |
| `outreach_email`, `contact_type`, `contact_url` | A public organizational email, its stated function, and the page that publishes it. If there is no suitable email, leave it blank and record an official contact route. Check that the route accepts this type of request. |
| `eligibility`, `evidence_status` | Blank or `eligible` for normal review; `review` for policy/identity concerns; `exclude` for an out-of-scope candidate. `provisional` flags evidence awaiting human review. |

Use official corporate reports, company announcements, filings, and named nonprofit partner pages. Record business-unit or successor relationships in the evidence. Youth audiences include documented student or young-adult engagement; popular products and social media use alone do not establish a Gen Z audience. A missing datum is blank or `NA`. A zero needs affirmative evidence for the zero anchor.

## Rubric and weights

Based on the [reference scoring rubric](https://docs.google.com/document/d/1GQ66Itbgv1ImtMm08o_62PW-8xdCbA5e5lLLImeU0Os/edit?tab=t.0). V1 uses three public criteria; industry fit captures a concrete route to help or activate a partnership. Capacity, CRM relationships, and nonfinancial resources can be added later once Thirst confirms the ask and the research track agrees on consistent measures. Review eligibility and reputation separately.

| Level | Gen Z / student audience (30%) | Cause-marketing / nonprofit history (45%) | Industry fit (25%) |
| --- | --- | --- | --- |
| 0 | Documented lack of youth focus | Verified no eligible partnership | Documented lack of credible fit |
| 1 | Broad adult audience | One unrelated nonprofit | Peripheral connection |
| 2 | Youth-inclusive offering | Multiple unrelated nonprofits | Generic activation or limited route |
| 3 | Youth-focused campaign | One water, youth or education nonprofit | Credible delivery, distribution or visibility |
| 4 | Active student program | Multiple relevant nonprofits | Strong gala activation or water adjacency |
| 5 | Multiple ongoing student initiatives | Recurring support for relevant nonprofits | Core offering directly enables clean water or youth activation |

The score is `20 × Σ(weight × level) / Σ(weight)`. Edit `scoring/weights.json` to adjust weights. Complete eligible rows earn a competition rank (1, 1, 3); alphabetical order only breaks display ties. With cause history and at least two criteria covering 70% of weight, an incomplete eligible row can get an observed-evidence score. It is provisional and stays out of the official rank. The score interval shows what the missing criteria could change. Outreach contacts never affect the score.

## Reproduce the gala check

Download or export the original source workbook **read-only** to a local path. Keep the history and outputs out of Git. The test accepts the workbook or its verbatim CSV export with the original two data headers.

```sh
python -m scoring.gala --history /path/to/gala_history.xlsx --output results/gala_history_scored.csv
```

The historical roster contributes no weighted features. Where published, separately documented non-gala Thirst partnerships can establish cause history. Paramount and Paramount Pictures are matched for this review; Viacom and Nickelodeon remain distinct credits. SunTrust maps to its successor Truist for present-day scoring, while the original gift name remains intact. Heather Hay Miller as an individual remains distinct from her foundation.

The 2018–2026 roster has 41 gift entries totaling $334,000 and two no-amount event notes. Of the gift entries, 32 have a ranked sponsor and 35 match researched entities. Among 16 ranked historical entities, Mattel and Paramount Pictures share rank 1 at 95, and UTA shares rank 4 at 89. In the full 18-entity ranked benchmark with two prospective comparators, UTA shares rank 5. These are retrospective checks on known sponsors. The roster has no set of approached prospects who declined, and public evidence is not frozen as of each gala date, so this is not a prospective accuracy test. For the next iteration, log every approached prospect, the outreach date, the ask, and the response; freeze evidence and weights before testing on later outcomes.
