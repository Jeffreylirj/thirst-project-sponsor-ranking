import json
from pathlib import Path

import pandas as pd
import pytest

from scoring.cli import main
from scoring.gala import read_gala, validate_gala
from scoring.model import INPUT, gen_z_audience, load_weights, rank_sponsors, read_evidence
from scoring.research import parse_research

ROOT = Path(__file__).parents[1]
WEIGHTS, MINIMUM = load_weights(ROOT / "scoring/weights.json")
URL = "https://example.org/evidence"


def row(name, a, c, i, **extra):
    result = dict.fromkeys(INPUT, "")
    result.update(sponsor=name, **extra)
    for key, value in zip(("gen_z", "cause", "industry"), (a, c, i)):
        if value is not None:
            result.update({f"{key}_level": str(value), f"{key}_reason": "Documented example.",
                           f"{key}_url": URL})
    return result


def test_weighted_rank_ties_and_endpoints():
    df = pd.DataFrame([row("Worst", 0, 0, 0), row("Best", 5, 5, 5),
                       row("Z", 5, 5, 4), row("A", 5, 5, 4), row("Mixed", 4, 2, 3)])
    result = rank_sponsors(df, WEIGHTS)
    assert list(result.sponsor) == ["Best", "A", "Z", "Mixed", "Worst"]
    assert list(result["rank"]) == [1, 2, 2, 4, 5]
    assert list(result.score) == [100, 95, 95, 57, 0]


def test_missing_is_not_zero_and_does_not_outrank_verified():
    result = rank_sponsors(pd.DataFrame([row("Partial", 5, 5, None), row("Zero", 0, 0, 0),
                                        row("Unknown", 5, None, 5)]), WEIGHTS).set_index("sponsor")
    assert pd.isna(result.loc["Partial", "rank"])
    assert pd.isna(result.loc["Partial", "industry_score"])
    assert result.loc["Partial", "provisional_score"] == 100
    assert result.loc["Partial", "score_floor"] == 75
    assert result.loc["Partial", "score_ceiling"] == 100
    assert pd.isna(result.loc["Unknown", "provisional_score"])
    assert result.loc["Zero", "rank"] == 1


@pytest.mark.parametrize("field,value", [("gen_z_level", "6"), ("gen_z_url", "not-a-url"),
                                        ("gen_z_reason", ""), ("gen_z_level", "4.0")])
def test_reject_bad_evidence(field, value):
    data = row("Invalid", 4, 4, 4)
    data[field] = value
    with pytest.raises(ValueError):
        gen_z_audience(data)


def test_names_can_match_aliases_but_cannot_collide(tmp_path, capsys):
    path = tmp_path / "data.csv"
    pd.DataFrame([row("United Talent Agency", 4, 5, 4, aliases="UTA")]).to_csv(path, index=False)
    assert main(["--input", str(path), "--sponsor", "u.t.a."]) == 0
    assert json.loads(capsys.readouterr().out)["sponsor"] == "United Talent Agency"
    df = pd.DataFrame([row("United Talent Agency", 4, 5, 4, aliases="UTA"), row("UTA", 2, 2, 2)])
    with pytest.raises(ValueError, match="Ambiguous"):
        rank_sponsors(df, WEIGHTS)


def test_candidate_compares_against_baseline(tmp_path, capsys):
    baseline, candidate = tmp_path / "a.csv", tmp_path / "b.csv"
    pd.DataFrame([row("High", 5, 5, 5), row("Low", 1, 1, 1)]).to_csv(baseline, index=False)
    pd.DataFrame([row("Candidate", 4, 5, 4)]).to_csv(candidate, index=False)
    assert main(["--input", str(baseline), "--sponsor", "Candidate", "--candidate", str(candidate)]) == 0
    assert json.loads(capsys.readouterr().out)["rank"] == 2


def test_gala_keeps_unmatched_gifts_and_notes_but_does_not_change_rank(tmp_path):
    p = tmp_path / "gala.csv"
    original = "SPONSOR NAME,AMOUNT SPONSORSED\n2026,\nUTA,5000\nUnresearched,500\n2022,\nNO GALA,\n"
    p.write_text(original)
    evidence = pd.DataFrame([row("United Talent Agency", 4, 5, 4, aliases="UTA"),
                             row("New prospect", 5, 5, 5)])
    ranked, stats = validate_gala(read_gala(p), evidence, WEIGHTS, MINIMUM)
    assert stats["gift_rows"] == 2 and stats["total_gala_amount"] == 5500
    assert ranked.loc[0, "rank"] == 2 and ranked.loc[0, "gala_rank"] == 1
    assert pd.isna(ranked.loc[1, "rank"]) and ranked.loc[2, "record_type"] == "Event note"
    assert p.read_text() == original


def test_research_requires_retrieved_sources_and_stays_provisional():
    draft = row("Untrusted name", 5, 5, 5, eligibility="eligible",
                outreach_email="invented@example.org", contact_url="https://example.org/unseen")
    draft["industry_url"] = "https://example.org/unseen"
    response = {"status": "completed", "output": [
        {"type": "web_search_call", "action": {"sources": [{"url": URL}]}},
        {"type": "message", "content": [{"type": "output_text", "text": json.dumps(draft)}]},
    ]}
    candidate = parse_research(response, "Actual name")
    assert candidate["sponsor"] == "Actual name"
    assert not candidate["outreach_email"] and not candidate["industry_level"]
    result = rank_sponsors(pd.DataFrame([candidate]), WEIGHTS).iloc[0]
    assert pd.isna(result["rank"])
    assert result["provisional_score"] == 100


def test_repository_fixtures_are_valid():
    sample = read_evidence(ROOT / "data/sample_sponsors.csv")
    live = read_evidence(ROOT / "data/public_evidence.csv")
    assert len(sample) == 5
    ranked = rank_sponsors(live, WEIGHTS, MINIMUM)
    assert ranked["score"].notna().sum() >= 10
