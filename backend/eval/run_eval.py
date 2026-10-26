"""
End-to-end evaluation of the live check pipeline.

Sends every claim in claims.jsonl to POST /check/stream, exactly as the
extension does, and measures what a user would see: the verdict, how often
it says "uncertain", whether sources and fact-checks were found, and how
long the first source and the verdict took.

    python eval/run_eval.py                       # local backend
    python eval/run_eval.py --api https://...     # any deployment
    python eval/run_eval.py --limit 20            # quick run

Writes eval/results/<timestamp>.jsonl (one row per claim) and
eval/results/summary.json, and prints a Markdown table.
"""
import argparse
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))


def token_for(api, email, password):
    with httpx.Client(timeout=20) as c:
        r = c.post(f"{api}/auth/login", json={"email": email, "password": password})
        if r.status_code == 401:
            r = c.post(f"{api}/auth/signup", json={"email": email, "password": password, "name": "Eval"})
        r.raise_for_status()
        return r.json()["token"]


def check(api, token, claim):
    """Stream one check and return what happened, with timings in ms."""
    row = {"verdict": None, "sources": 0, "factcheck": False, "cached": False,
           "grounded": False, "first_source_ms": None, "verdict_ms": None, "error": None}
    t0 = time.monotonic()
    ms = lambda: round((time.monotonic() - t0) * 1000)
    seen = set()
    try:
        with httpx.Client(timeout=60) as c, c.stream(
                "POST", f"{api}/check/stream", json={"message": claim, "check": True, "fresh": True},
                headers={"Authorization": f"Bearer {token}"}) as r:
            r.raise_for_status()
            event = None
            for line in r.iter_lines():
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:])
                    if event == "sources":
                        if row["first_source_ms"] is None and data["items"]:
                            row["first_source_ms"] = ms()
                        seen.update(i.get("url") for i in data["items"])
                    elif event == "factcheck":
                        row["factcheck"] = True
                    elif event == "verdict":
                        row["verdict_ms"] = ms()
                        row["verdict"] = data["verdict"]
                        row["confidence"] = data.get("confidence")
                        row["cached"] = bool(data.get("cached"))
                        row["grounded"] = bool(data.get("grounded"))
                        row["basis"] = data.get("basis", "sources")
                        row["memory"] = bool(data.get("memory"))
                        row["model"] = data.get("model")
                        row["explanation"] = data.get("explanation")
                        row["top_sources"] = [a.get("source") for a in data.get("evidence_articles", [])[:3]]
                        seen.update(a.get("url") for a in data.get("evidence_articles", []))
                    elif event == "error":
                        row["error"] = data.get("message")
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
    row["sources"] = len(seen - {None})
    return row


def pct(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return xs[min(len(xs) - 1, round(p / 100 * (len(xs) - 1)))]


def summarize(rows):
    n = len(rows)
    done = [r for r in rows if r["verdict"]]
    decided = [r for r in done if r["verdict"] != "uncertain"]
    correct = [r for r in decided if r["verdict"] == r["label"]]
    fresh = [r for r in done if not r["cached"]]
    by_topic = {}
    for r in done:
        t = by_topic.setdefault(r["topic"], {"n": 0, "correct": 0, "uncertain": 0})
        t["n"] += 1
        t["correct"] += r["verdict"] == r["label"]
        t["uncertain"] += r["verdict"] == "uncertain"
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "claims": n,
        "completed": len(done),
        "errors": n - len(done),
        "accuracy_when_decided": round(len(correct) / len(decided), 3) if decided else None,
        "accuracy_overall": round(len(correct) / n, 3) if n else None,
        "uncertain_rate": round((len(done) - len(decided)) / len(done), 3) if done else None,
        "wrong_rate": round((len(decided) - len(correct)) / n, 3) if n else None,
        "with_sources": round(sum(r["sources"] > 0 for r in done) / len(done), 3) if done else None,
        "with_factcheck": round(sum(r["factcheck"] for r in done) / len(done), 3) if done else None,
        "grounded": round(sum(r["grounded"] for r in done) / len(done), 3) if done else None,
        "from_knowledge": sum(r.get("basis") == "knowledge" for r in done),
        "from_memory": sum(bool(r.get("memory")) for r in done),
        "first_source_ms_p50": pct([r["first_source_ms"] for r in fresh], 50),
        "first_source_ms_p95": pct([r["first_source_ms"] for r in fresh], 95),
        "verdict_ms_p50": pct([r["verdict_ms"] for r in fresh], 50),
        "verdict_ms_p95": pct([r["verdict_ms"] for r in fresh], 95),
        "by_topic": by_topic,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=os.getenv("TRUVANTA_API", "http://127.0.0.1:8000"))
    ap.add_argument("--email", default=os.getenv("EVAL_EMAIL", "eval@truvantaai.tech"))
    ap.add_argument("--password", default=os.getenv("EVAL_PASSWORD", "eval-password-123"))
    ap.add_argument("--claims", default=os.path.join(HERE, "claims.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--pace", type=float, default=0,
                    help="seconds between claims, to stay inside free model rate limits")
    args = ap.parse_args()

    with open(args.claims, encoding="utf-8") as f:
        items = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        items = items[:args.limit]

    token = token_for(args.api, args.email, args.password)

    def run(item):
        if args.pace:
            time.sleep(args.pace)
        row = {**item, **check(args.api, token, item["claim"])}
        mark = "ok " if row["verdict"] == item["label"] else ("?  " if row["verdict"] == "uncertain" else "BAD")
        print(f"{mark} {row['verdict'] or row['error']!s:9} {row['verdict_ms'] or '-':>6} ms  {item['claim'][:70]}",
              flush=True)
        return row

    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run, items))

    out = os.path.join(HERE, "results")
    os.makedirs(out, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(os.path.join(out, f"{stamp}.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    s = summarize(rows)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)

    def p(x):
        return "-" if x is None else f"{x * 100:.1f}%"
    print(f"\n| Metric | Value |\n|---|---|"
          f"\n| Claims | {s['claims']} ({s['errors']} errors) |"
          f"\n| Accuracy when it gives a verdict | {p(s['accuracy_when_decided'])} |"
          f"\n| Says Uncertain | {p(s['uncertain_rate'])} |"
          f"\n| Wrong verdict | {p(s['wrong_rate'])} |"
          f"\n| Found sources | {p(s['with_sources'])} |"
          f"\n| Matched a published fact-check | {p(s['with_factcheck'])} |"
          f"\n| First source, median / p95 | {s['first_source_ms_p50']} / {s['first_source_ms_p95']} ms |"
          f"\n| Verdict, median / p95 | {s['verdict_ms_p50']} / {s['verdict_ms_p95']} ms |")


if __name__ == "__main__":
    main()
