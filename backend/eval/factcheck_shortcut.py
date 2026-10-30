"""
How often a published fact-check of the same claim decides the verdict without a
language model, and whether those verdicts are right.

    python eval/factcheck_shortcut.py            # all labelled claims
    python eval/factcheck_shortcut.py --limit 30

Uses the live search and the embedding backend only; no language-model calls.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(HERE), ".env"))

from app.analysis.search import factcheck_verdict, search_evidence  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    with open(os.path.join(HERE, "claims.jsonl"), encoding="utf-8") as f:
        items = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        items = items[:args.limit]

    with_fc = decided = right = 0
    for it in items:
        passages = search_evidence(it["claim"])
        has_fc = any(p.get("kind") == "fact_check" for p in passages)
        with_fc += has_fc
        v = factcheck_verdict(it["claim"], passages)
        if v:
            decided += 1
            ok = v["verdict"] == it["label"]
            right += ok
            print(f"{'ok ' if ok else 'BAD'} {v['verdict']:5} {it['claim'][:70]}  <- {v['explanation'][:70]}")
    n = len(items)
    print(f"\n{n} claims: {with_fc} had a published fact-check; "
          f"{decided} ({100 * decided / n:.0f}%) decided without a model, {right}/{decided or 1} right")


if __name__ == "__main__":
    main()
