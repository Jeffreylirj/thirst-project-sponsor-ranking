"""Run a batch, compare a sponsor by name, or prepare a prospect for research."""
import argparse
import csv
import json
from pathlib import Path
import sys

import pandas as pd

from .model import INPUT, compare_prospect, index_names, load_weights, name_key, rank_sponsors, read_evidence


def write_template(path, row):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=INPUT)
        writer.writeheader()
        writer.writerow(row)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/public_evidence.csv")
    parser.add_argument("--weights", default=str(Path(__file__).with_name("weights.json")))
    parser.add_argument("--output", help="Write ranked data or the selected sponsor to a CSV")
    parser.add_argument("--sponsor", help="Sponsor name or reviewed alias")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--candidate", help="One-row reviewed prospect CSV to compare to the baseline")
    group.add_argument("--research", action="store_true", help="Research an unknown name using the OpenAI API")
    group.add_argument("--template", help="Create a blank prospect CSV at this path")
    parser.add_argument("--domain", default="", help="Official website hint for --research")
    parser.add_argument("--save-evidence", help="Save provisional --research output to a new evidence CSV")
    args = parser.parse_args(argv)
    if (args.candidate or args.template or args.research) and not args.sponsor:
        parser.error("--candidate, --template and --research require --sponsor")
    if (args.save_evidence or args.domain) and not args.research:
        parser.error("--save-evidence and --domain require --research")
    try:
        if args.template:
            if not name_key(args.sponsor):
                raise ValueError("Enter a sponsor name")
            write_template(args.template, {"sponsor": args.sponsor})
            print(f"Created evidence template: {args.template}")
            return 0
        weights, minimum = load_weights(args.weights)
        evidence = read_evidence(args.input)
        names = index_names(evidence)
        baseline = rank_sponsors(evidence, weights, minimum)
        selected = baseline
        if args.sponsor:
            key = name_key(args.sponsor)
            if not key:
                raise ValueError("Enter a sponsor name")
            if args.candidate:
                candidate = read_evidence(args.candidate)
                if len(candidate) != 1 or key not in index_names(candidate):
                    raise ValueError("--candidate must have one row matching --sponsor or its alias")
            elif key in names:
                selected = baseline[baseline["sponsor"].eq(evidence.iloc[names[key]]["sponsor"])].copy()
                candidate = None
            elif args.research:
                from .research import research_sponsor
                row = research_sponsor(args.sponsor, args.domain)
                if args.save_evidence:
                    write_template(args.save_evidence, row)
                candidate = pd.DataFrame([row], columns=INPUT).fillna("")
            else:
                raise ValueError("Unknown sponsor. Use --research or --template, then --candidate")
            if candidate is not None:
                benchmark = baseline[~baseline["sponsor"].eq(evidence.iloc[names[key]]["sponsor"])] if key in names else baseline
                selected = rank_sponsors(candidate, weights, minimum)
                val = selected.iloc[0]["score"]
                tentative = selected.iloc[0]["provisional_score"]
                selected["rank"] = compare_prospect(val, benchmark) if pd.notna(val) else pd.NA
                selected["provisional_placement"] = (compare_prospect(tentative, benchmark)
                                                     if pd.notna(tentative) else pd.NA)
                selected["benchmark_ranked_sponsors"] = int(benchmark["score"].notna().sum())
        if args.output:
            target = Path(args.output)
            if target.resolve() in {Path(p).resolve() for p in (args.input, args.candidate, args.weights, args.save_evidence) if p}:
                raise ValueError("--output cannot overwrite an input or the saved evidence")
            target.parent.mkdir(parents=True, exist_ok=True)
            selected.to_csv(target, index=False)
        if args.sponsor:
            print(json.dumps(json.loads(selected.to_json(orient="records"))[0],
                             indent=2, ensure_ascii=False))
        elif not args.output:
            print(selected[["rank", "sponsor", "score", "status", "outreach_email"]].to_string(index=False))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
