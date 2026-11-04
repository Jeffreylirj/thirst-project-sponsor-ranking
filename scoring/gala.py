"""Compare current public-fit scores against a separately held gala roster."""
import argparse
import json
from pathlib import Path

import pandas as pd

from .model import index_names, load_weights, name_key, rank_sponsors, read_evidence

ANCHORS = ("Paramount Pictures", "Mattel", "UTA")


def read_gala(path):
    """Accept the read-only workbook or its original three-column CSV extraction."""
    if Path(path).suffix.lower() == ".xlsx":
        raw = pd.read_excel(path, dtype=str, keep_default_na=False, sheet_name=0)
    else:
        raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    donor_col, amount_col = "SPONSOR NAME", "AMOUNT SPONSORSED"
    if not {donor_col, amount_col}.issubset(raw.columns):
        raise ValueError("Expected original gala column names SPONSOR NAME and AMOUNT SPONSORSED")
    year = None
    rows = []
    for idx, rec in raw.iterrows():
        donor, amount = str(rec[donor_col]), str(rec[amount_col]).strip()
        if not donor.strip():
            if amount:
                raise ValueError(f"Gala row {idx + 2}: amount without a donor")
            continue
        if donor.strip().isdigit() and 1900 <= int(donor) <= 2100 and not amount:
            year = int(donor)
            continue
        if year is None:
            raise ValueError(f"Gala row {idx + 2}: year header is missing")
        if amount:
            amount = float(amount.replace("$", "").replace(",", ""))
            if not 0 <= amount < float("inf"):
                raise ValueError(f"Gala row {idx + 2}: amount is invalid")
        rows.append({"gala_year": year, "source_row": idx + 2,
                     "source_label": donor, "gala_amount": amount if amount != "" else None,
                     "record_type": "Gift" if amount != "" else "Event note"})
    return pd.DataFrame(rows)


def validate_gala(events, evidence, weights, minimum):
    names = index_names(evidence)
    ranked = rank_sponsors(evidence, weights, minimum)
    lookup = ranked.set_index("sponsor")
    historical = events.copy()
    historical["sponsor"] = historical["source_label"].map(
        lambda label: evidence.iloc[names[name_key(label)]]["sponsor"] if name_key(label) in names else ""
    )
    for col in ("rank", "score", "status"):
        historical[col] = historical["sponsor"].map(lookup[col])
    gifts = historical[historical["record_type"].eq("Gift")]
    historical_pool = set(gifts.loc[gifts["sponsor"].ne(""), "sponsor"])
    gala_ranks = ranked[ranked["sponsor"].isin(historical_pool)].copy()
    gala_ranks["gala_rank"] = gala_ranks["score"].rank(method="min", ascending=False).astype("Int64")
    count = int(ranked["score"].notna().sum())
    gala_count = int(gala_ranks["score"].notna().sum())
    gala_rank_map = gala_ranks.set_index("sponsor")["gala_rank"]
    historical["gala_rank"] = historical["sponsor"].map(gala_rank_map)
    targets = {}
    for label in ANCHORS:
        i = names.get(name_key(label))
        if i is None:
            continue
        name = evidence.iloc[i]["sponsor"]
        own = gifts[gifts["sponsor"].eq(name)]
        if own.empty:
            continue
        rank = lookup.loc[name, "rank"]
        gala_rank = gala_rank_map.get(name)
        targets[name] = {"rank": int(rank) if pd.notna(rank) else None,
                         "gala_rank": int(gala_rank) if pd.notna(gala_rank) else None,
                         "score": float(lookup.loc[name, "score"]) if pd.notna(rank) else None,
                         "years_seen": int(own["gala_year"].nunique())}
    stats = {"gift_rows": len(gifts), "event_notes": len(historical) - len(gifts),
             "total_gala_amount": float(gifts["gala_amount"].sum()),
             "gift_rows_with_rank": int(gifts["rank"].notna().sum()),
             "gift_rows_with_researched_entity": int(gifts["sponsor"].ne("").sum()),
             "historical_entities_with_rank": gala_count, "ranked_benchmark_size": count,
             "repeat_sponsor_sanity_check": targets,
             "validation_limit": "Retrospective, positive-only roster; no probability or unbiased holdout."}
    return historical, stats


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--history", required=True)
    p.add_argument("--input", default="data/public_evidence.csv")
    p.add_argument("--weights", default=str(Path(__file__).with_name("weights.json")))
    p.add_argument("--output", required=True)
    args = p.parse_args()
    if Path(args.output).resolve() in {Path(x).resolve() for x in (args.history, args.input, args.weights)}:
        p.error("--output must be different from all inputs")
    history, summary = validate_gala(read_gala(args.history), read_evidence(args.input), *load_weights(args.weights))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path, index=False)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
