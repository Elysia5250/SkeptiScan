#!/usr/bin/env python3
"""
Benchmark runner for SkeptiScan.

CSV format: url,model_output,ground_truth
  - url: product URL to analyze
  - model_output: filled by this script (scam/not_scam/error)
  - ground_truth: your manual annotation (scam/not_scam)

Usage:
    # 1. Scrape candidate URLs:
    python scrape_sources.py > raw.csv

    # 2. Fill ground_truth column manually

    # 3. Run benchmark:
    python run_benchmark.py --csv raw.csv

    # 4. Open output/benchmark_report.html
"""

import argparse
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re

import httpx


def parse_args():
    parser = argparse.ArgumentParser(description="Run benchmark")
    parser.add_argument("--csv", required=True, help="CSV with columns: url,model_output,ground_truth")
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--output", default="output/benchmark_report.html", help="Output report path")
    parser.add_argument("--timeout", type=int, default=120, help="Per-request timeout")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers")
    parser.add_argument("--threshold", type=int, default=5,
                        help="Risk level threshold (1-10). >= threshold = scam (default: 5)")
    parser.add_argument("--explanations", action="store_true", default=True,
                        help="Save detailed_analysis to output/explanations/*.md")
    return parser.parse_args()


def load_cases(csv_path):
    """Load rows, detect header by content. Supports text or url mode."""
    cases = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        # Detect mode: if first column is "text" -> use text mode
        is_text_mode = len(header) > 0 and header[0].strip().lower() == "text"

        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue
            val = row[0].strip()
            if not val:
                continue
            model_out = row[1].strip() if len(row) > 1 else ""
            ground = row[2].strip() if len(row) > 2 else ""
            case = {"input": val, "is_text": is_text_mode,
                    "model_output": model_out, "ground_truth": ground}
            cases.append(case)
    return cases


def process_one(case, api_url, timeout, threshold=6, explanations_dir=None):
    """Process a single case."""
    inp = case["input"]
    start = time.time()
    try:
        data = {"mode": "benchmark"}
        if case.get("is_text"):
            data["text"] = inp
        else:
            data["url"] = inp

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{api_url}/api/analyze", data=data)
            resp.raise_for_status()
            result = resp.json()
            report = result.get("report", {}) if result.get("success") else None
            latency = time.time() - start
            if not report:
                return {**case, "model_output": "error", "latency": round(latency, 2), "risk_level": 0, "error": True}
            level = report.get("risk_level", 0)
            # 1-10 scale: >= threshold -> scam, else not_scam
            if isinstance(level, int) and 1 <= level <= 10:
                verdict = "scam" if level >= threshold else "not_scam"
            else:
                verdict = "error"

            # Save detailed_analysis to .md
            detailed = report.get("detailed_analysis", "")
            if detailed and explanations_dir:
                safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', inp[:30])
                md_path = explanations_dir / f"case_{len(list(explanations_dir.glob('*.md')))+1:03d}_{safe_name[:20]}.md"
                md_path.parent.mkdir(parents=True, exist_ok=True)
                md_path.write_text(
                    f"# Case Analysis\n\n"
                    f"**Input:** {inp}\n\n"
                    f"**Risk Level:** {level}/10\n\n"
                    f"**Verdict:** {verdict}\n\n"
                    f"---\n\n{detailed}",
                    encoding="utf-8"
                )

            explanation = report.get("detailed_analysis", "")[:500]
            breakdown = report.get("score_breakdown", {})
            score_str = "/".join(str(breakdown.get(k, 0)) for k in
                                 ["pseudoscience", "false_medical", "fake_authority",
                                  "illegal_mlm", "deceptive_marketing", "data_fraud",
                                  "trusted_signals"])

            return {
                **case,
                "model_output": verdict,
                "latency": round(latency, 2),
                "risk_level": level,
                "error": False,
                "keywords": report.get("detected_keywords", {}).get("all_matched", []),
                "claims": report.get("suspicious_claims", []),
                "explanation": explanation,
                "score_breakdown": breakdown,
                "triggered_items": report.get("triggered_items", []),
                "score_detail": score_str,
            }
    except Exception as e:
        return {**case, "model_output": "error", "latency": round(time.time() - start, 2), "risk_level": 0, "error": True, "error_msg": str(e)[:80]}


def write_csv(path, results):
    """Write results back to CSV with score breakdown."""
    is_text = any(r.get("is_text") for r in results)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header_col = "text" if is_text else "url"
        w.writerow([header_col, "model_output", "ground_truth", "risk_level",
                     "score_breakdown", "triggered_items"])
        for r in results:
            w.writerow([
                r["input"],
                r["model_output"],
                r.get("ground_truth", ""),
                r.get("risk_level", ""),
                r.get("score_detail", ""),
                "; ".join(r.get("triggered_items", [])),
            ])
    print(f"Updated CSV: {path}")


def main():
    args = parse_args()
    cases = load_cases(args.csv)
    if not cases:
        print("ERROR: No cases found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(cases)} cases from {args.csv}")
    print(f"Workers: {args.workers}\n")

    workers = max(1, args.workers)
    threshold = args.threshold
    expl_dir = Path(args.output).parent / "explanations" if args.explanations else None
    results = []

    if workers == 1:
        for i, c in enumerate(cases):
            r = process_one(c, args.api, args.timeout, threshold, expl_dir)
            _print_status(i + 1, len(cases), r)
            results.append(r)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(process_one, c, args.api, args.timeout, threshold, expl_dir): i for i, c in enumerate(cases)}
            for f in as_completed(futures):
                i = futures[f]
                r = f.result()
                _print_status(i + 1, len(cases), r)
                results.append(r)
        results.sort(key=lambda r: cases.index(r) if r in cases else 0)

    # Write model_output back to CSV
    write_csv(args.csv, results)

    # Summary
    labeled = [r for r in results if r.get("ground_truth")]
    correct = sum(1 for r in labeled if r["model_output"] == r["ground_truth"])
    print(f"\n{'=' * 50}")
    print(f"  Total:     {len(results)}")
    print(f"  Labeled:   {len(labeled)}")
    if labeled:
        print(f"  Correct:   {correct} ({correct / len(labeled) * 100:.1f}%)")
    print(f"{'=' * 50}")

    # Report
    try:
        from reporter import generate_report
        # Map results to reporter format
        report_data = []
        for i, r in enumerate(results):
            expected = r.get("ground_truth", "")
            display = r["input"][:80]
            report_data.append({
                "id": str(i + 1),
                "url": display,
                "category": "",
                "expected": expected if expected else "",
                "predicted": r["model_output"],
                "latency": r.get("latency", 0),
                "error": r.get("error", False),
                "error_msg": r.get("error_msg", ""),
                "risk_level": r.get("risk_level", ""),
                "detected_keywords": r.get("keywords", []),
                "suspicious_claims": r.get("claims", []),
            })
        generate_report(report_data, args.output)
    except ImportError:
        print("\n[WARN] reporter.py not found, skipping HTML report.")

    print(f"\nDone. Report: {args.output}")


def _print_status(idx, total, r):
    display = r["input"][:55].replace("\n", " ")
    lat = r.get("latency", 0)
    gt = r.get("ground_truth", "")
    mo = r["model_output"]
    if r.get("error"):
        print(f"  [{idx}/{total}] {display}... ERROR ({lat:.1f}s)")
    elif gt:
        m = "✓" if mo == gt else "✗"
        print(f"  [{idx}/{total}] {display}... {m} pred={mo} gt={gt} ({lat:.1f}s)")
    else:
        print(f"  [{idx}/{total}] {display}... → {mo} ({lat:.1f}s)")


if __name__ == "__main__":
    main()
