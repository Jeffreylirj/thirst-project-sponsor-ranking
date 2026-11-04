"""Public evidence goes in; auditable fit scores come out."""
from dataclasses import dataclass
import json
import math
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

CRITERIA = {
    "gen_z": ("no youth focus", "broad adult audience", "youth-inclusive offering",
              "youth-focused campaign", "active student program", "multiple ongoing student initiatives"),
    "cause": ("verified no eligible partnerships", "one unrelated nonprofit",
              "multiple unrelated nonprofits", "one water, education or youth nonprofit",
              "multiple relevant nonprofits", "recurring support for relevant nonprofits"),
    "industry": ("documented lack of fit", "peripheral connection", "generic activation",
                 "credible delivery or visibility", "strong gala or water-adjacent activation",
                 "core offering directly enables clean water or youth activation"),
}
INPUT = ["sponsor", "aliases", "website",
         *[f"{k}_{f}" for k in CRITERIA for f in ("level", "reason", "url")],
         "outreach_email", "contact_type", "contact_url", "eligibility", "evidence_status"]


@dataclass(frozen=True)
class Criterion:
    score: int | None
    reason: str


def valid_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return (not any(ch.isspace() for ch in value) and parsed.scheme in {"http", "https"}
                and "." in (parsed.hostname or "") and not parsed.username and not parsed.password)
    except ValueError:
        return False


def _criterion(row, key):
    level = str(row.get(f"{key}_level", "")).strip()
    reason = " ".join(str(row.get(f"{key}_reason", "")).split())
    url = str(row.get(f"{key}_url", "")).strip()
    if not level or level.upper() == "NA":
        return Criterion(None, reason or "No qualifying public evidence recorded.")
    if level not in {"0", "1", "2", "3", "4", "5"}:
        raise ValueError(f"{row.get('sponsor')}: {key}_level must be an integer 0–5 or blank")
    if not reason or not url or not all(valid_url(s.strip()) for s in url.split("|")):
        raise ValueError(f"{row.get('sponsor')}: {key} needs a reason and public source URL(s)")
    return Criterion(int(level), reason)


def gen_z_audience(row):
    return _criterion(row, "gen_z")


def cause_marketing_history(row):
    return _criterion(row, "cause")


def industry_fit(row):
    return _criterion(row, "industry")


SCORERS = dict(zip(CRITERIA, (gen_z_audience, cause_marketing_history, industry_fit)))


def name_key(name):
    return "".join(c for c in unicodedata.normalize("NFKC", name).casefold() if c.isalnum())


def load_weights(path):
    config = json.loads(Path(path).read_text())
    weights = config["weights"]
    if set(weights) != set(SCORERS) or any(
        isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) or x <= 0
        for x in weights.values()
    ):
        raise ValueError("Give each of gen_z, cause and industry a finite positive weight")
    minimum = config.get("minimum_coverage", .70)
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not 0 < minimum <= 1:
        raise ValueError("minimum_coverage must be between 0 (exclusive) and 1")
    return weights, minimum


def read_evidence(path):
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if "sponsor" not in df:
        raise ValueError("Evidence CSV requires a sponsor column")
    return df.reindex(columns=INPUT, fill_value="").apply(lambda col: col.str.strip())


def index_names(df):
    result = {}
    for i, row in df.reset_index(drop=True).iterrows():
        sponsor_key = name_key(row["sponsor"])
        if not sponsor_key:
            raise ValueError("Each evidence row needs a sponsor name")
        for label in [row["sponsor"], *row.get("aliases", "").split("|")]:
            key = name_key(label)
            if not key:
                continue
            if key in result and result[key] != i:
                raise ValueError(f"Ambiguous sponsor or alias: {label!r}")
            result[key] = i
    return result


def _contact(row):
    email = row.get("outreach_email", "")
    url = row.get("contact_url", "")
    category = row.get("contact_type", "")
    if email and (not re.fullmatch(r"[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+", email)
                  or not valid_url(url) or not category):
        raise ValueError(f"{row['sponsor']}: outreach email needs a public source and contact type")
    if url and not valid_url(url):
        raise ValueError(f"{row['sponsor']}: invalid contact URL")
    return email, category or "No public route recorded", url


def _score(row, weights, minimum):
    results = {key: func(row) for key, func in SCORERS.items()}
    active = {k: v for k, v in results.items() if v.score is not None}
    known_weight = sum(weights[k] for k in active)
    total_weight = sum(weights.values())
    coverage = known_weight / total_weight
    points = 20 * sum(weights[k] * v.score for k, v in active.items())
    complete = len(active) == len(weights)
    provisional = "cause" in active and len(active) >= 2 and coverage + 1e-10 >= minimum
    eligibility = row.get("eligibility", "") or "eligible"
    if eligibility not in {"eligible", "exclude", "review"}:
        raise ValueError(f"{row['sponsor']}: invalid eligibility")
    review = row.get("evidence_status", "") == "provisional"
    eligible = eligibility == "eligible"
    status = ("Out of scope" if eligibility == "exclude" else "Identity/policy review"
              if not eligible else "Provisional: verify research" if review and complete
              else "Ranked" if complete else "Provisional: incomplete" if provisional
              else "Needs public evidence")
    email, contact_type, contact_url = _contact(row)
    # Reasons are retained separately; the summary is one sentence and keeps the evidence gaps visible.
    detail = []
    for k, label in (("gen_z", "Audience"), ("cause", "Cause history"), ("industry", "Industry")):
        value = results[k].score
        if value is None:
            detail.append(f"{label}: NA")
        else:
            reason = results[k].reason.rstrip(".!?")
            detail.append(f"{label}: {value}/5 ({reason})")
    summary = "; ".join(detail) + "."
    return {
        "sponsor": row["sponsor"], "status": status,
        "score": points / total_weight if eligible and complete and not review else None,
        "provisional_score": points / known_weight
        if eligible and (provisional or complete) and (not complete or review) else None,
        "evidence_coverage": coverage,
        "score_floor": points / total_weight if eligible else None,
        "score_ceiling": (points + 100 * (total_weight - known_weight)) / total_weight if eligible else None,
        "reason": summary, "outreach_email": email, "contact_type": contact_type,
        "contact_url": contact_url, "website": row.get("website", ""),
        **{f"{k}_score": result.score for k, result in results.items()},
        **{f"{k}_reason": result.reason for k, result in results.items()},
        **{f"{k}_url": row.get(f"{k}_url", "") for k in results},
    }


def rank_sponsors(evidence, weights, minimum=.70):
    evidence = evidence.reset_index(drop=True)
    index_names(evidence)
    if evidence.empty:
        raise ValueError("No sponsors in the evidence file")
    out = pd.DataFrame(_score(row, weights, minimum) for row in evidence.to_dict("records"))
    out["score"] = pd.to_numeric(out["score"])
    out["provisional_score"] = pd.to_numeric(out["provisional_score"])
    out["score"] = out["score"].round(8)
    out.insert(0, "rank", out["score"].rank(method="min", ascending=False).astype("Int64"))
    out["name_sort"] = out["sponsor"].map(name_key)
    return (out.sort_values(["rank", "provisional_score", "name_sort"], ascending=[True, False, True])
            .drop(columns="name_sort").reset_index(drop=True))


def compare_prospect(score, baseline):
    """A provisional placement against complete reviewed scores, with ties sharing rank."""
    return 1 + int(baseline["score"].gt(round(float(score), 8)).sum())
