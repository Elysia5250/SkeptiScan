"""
Generate an ECharts-based HTML benchmark report.

Usage (called from run_benchmark.py):
    generate_report(results, output_path)
"""

import json
import statistics
import math
from pathlib import Path


def _compute_metrics(results):
    """Compute all metrics from raw results."""
    valid = [r for r in results if not r.get("error")]
    errors = [r for r in results if r.get("error")]

    total = len(results)
    valid_count = len(valid)

    # Confusion matrix (scam=positive, not_scam=negative)
    tp = sum(1 for r in valid if r["expected"] == "scam" and r["predicted"] == "scam")
    fp = sum(1 for r in valid if r["expected"] == "not_scam" and r["predicted"] == "scam")
    tn = sum(1 for r in valid if r["expected"] == "not_scam" and r["predicted"] == "not_scam")
    fn = sum(1 for r in valid if r["expected"] == "scam" and r["predicted"] == "not_scam")

    accuracy = (tp + tn) / valid_count if valid_count else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    # Per-class
    scam_total = sum(1 for r in valid if r["expected"] == "scam")
    not_scam_total = sum(1 for r in valid if r["expected"] == "not_scam")

    scam_precision = tp / (tp + fp) if (tp + fp) else 0
    scam_recall = tp / (tp + fn) if (tp + fn) else 0
    scam_f1 = 2 * scam_precision * scam_recall / (scam_precision + scam_recall) if (scam_precision + scam_recall) else 0

    ns_precision = tn / (tn + fn) if (tn + fn) else 0
    ns_recall = tn / (tn + fp) if (tn + fp) else 0
    ns_f1 = 2 * ns_precision * ns_recall / (ns_precision + ns_recall) if (ns_precision + ns_recall) else 0

    # Latency
    latencies = sorted([r["latency"] for r in results])
    def percentile(data, p):
        if not data:
            return 0
        k = (len(data) - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return data[int(k)]
        return data[f] * (c - k) + data[c] * (k - f)

    return {
        "total": total,
        "valid": valid_count,
        "errors": len(errors),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "per_class": {
            "scam": {
                "precision": scam_precision, "recall": scam_recall,
                "f1": scam_f1, "support": scam_total,
            },
            "not_scam": {
                "precision": ns_precision, "recall": ns_recall,
                "f1": ns_f1, "support": not_scam_total,
            },
        },
        "latency": {
            "min": latencies[0] if latencies else 0,
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "max": latencies[-1] if latencies else 0,
            "mean": statistics.mean(latencies) if latencies else 0,
            "all": latencies,
        },
    }


def _build_html(results, metrics):
    """Build the full HTML page."""
    results_json = json.dumps(results, ensure_ascii=False)
    metrics_json = json.dumps(metrics, ensure_ascii=False)

    # Prepare confusion matrix data for ECharts heatmap
    cm = metrics["confusion_matrix"]
    cm_data = [
        [0, 0, cm["tp"]],  # Actual scam, Pred scam
        [0, 1, cm["fn"]],  # Actual scam, Pred not_scam
        [1, 0, cm["fp"]],  # Actual not_scam, Pred scam
        [1, 1, cm["tn"]],  # Actual not_scam, Pred not_scam
    ]

    pc = metrics["per_class"]
    bar_data = [
        ["scam", "Precision", round(pc["scam"]["precision"] * 100, 1)],
        ["scam", "Recall", round(pc["scam"]["recall"] * 100, 1)],
        ["scam", "F1 Score", round(pc["scam"]["f1"] * 100, 1)],
        ["not_scam", "Precision", round(pc["not_scam"]["precision"] * 100, 1)],
        ["not_scam", "Recall", round(pc["not_scam"]["recall"] * 100, 1)],
        ["not_scam", "F1 Score", round(pc["not_scam"]["f1"] * 100, 1)],
    ]

    lat = metrics["latency"]
    # Build latency histogram bins
    max_lat = max(lat["all"]) if lat["all"] else 1
    bin_count = 20
    bin_size = max(max_lat / bin_count, 0.1)
    bins = [0] * bin_count
    for v in lat["all"]:
        idx = min(int(v / bin_size), bin_count - 1)
        bins[idx] += 1
    hist_labels = [f"{i*bin_size:.1f}-{(i+1)*bin_size:.1f}s" for i in range(bin_count)]
    hist_data = [{"value": v, "label": lbl} for v, lbl in zip(bins, hist_labels)]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Benchmark Report</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f0f2f5; color: #1a1a2e; padding: 32px 24px;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
.subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 28px; }}
.kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px; margin-bottom: 28px;
}}
.kpi-card {{
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center;
}}
.kpi-card .value {{ font-size: 32px; font-weight: 800; }}
.kpi-card .value.green {{ color: #10b981; }}
.kpi-card .value.amber {{ color: #f59e0b; }}
.kpi-card .value.red {{ color: #ef4444; }}
.kpi-card .label {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
.chart-row {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;
}}
.chart-box {{
    background: #fff; border-radius: 12px; padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}}
.chart-box h3 {{ font-size: 15px; font-weight: 600; margin-bottom: 8px; color: #334155; }}
.chart-box .chart {{ width: 100%; height: 320px; }}
.chart-box.full {{ grid-column: 1 / -1; }}
.table-wrap {{
    background: #fff; border-radius: 12px; padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow-x: auto;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 10px 8px; border-bottom: 2px solid #e2e8f0;
      color: #64748b; font-weight: 600; font-size: 11px; text-transform: uppercase;
      letter-spacing: 0.5px; }}
td {{ padding: 8px; border-bottom: 1px solid #f1f5f9; color: #334155; }}
td.url {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
tr:hover {{ background: #f8fafc; }}
.badge {{
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 12px; font-weight: 600;
}}
.badge.scam {{ background: #fef2f2; color: #dc2626; }}
.badge.not_scam {{ background: #ecfdf5; color: #059669; }}
.badge.error {{ background: #f1f5f9; color: #94a3b8; }}
.match {{ color: #10b981; font-weight: 700; }}
.mismatch {{ color: #ef4444; font-weight: 700; }}
@media (max-width: 768px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
    .kpi-grid {{ grid-template-columns: 1fr 1fr; }}
}}
</style>
</head>
<body>
<div class="container">
<h1>🏋\u200d Benchmark Report</h1>
<p class="subtitle">
    {metrics["valid"]}/{metrics["total"]} cases evaluated
    {f' · {metrics["errors"]} errors' if metrics["errors"] else ''}
    · Generated by SkeptiScan Test Suite
</p>

<div class="kpi-grid" id="kpiGrid"></div>

<div class="chart-row">
    <div class="chart-box">
        <h3>Confusion Matrix</h3>
        <div class="chart" id="chartConfusion"></div>
    </div>
    <div class="chart-box">
        <h3>Per-Class Metrics</h3>
        <div class="chart" id="chartBar"></div>
    </div>
</div>

<div class="chart-row">
    <div class="chart-box full">
        <h3>Latency Distribution</h3>
        <div class="chart" id="chartLatency" style="height:280px;"></div>
    </div>
</div>

<div class="table-wrap">
    <h3 style="margin-bottom:12px;font-size:15px;font-weight:600;color:#334155;">Detail Results</h3>
    <table id="resultTable">
        <thead>
            <tr>
                <th>ID</th>
                <th>Input</th>
                <th>Score</th>
                <th>Expected</th>
                <th>Predicted</th>
                <th>Latency</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody id="tableBody"></tbody>
    </table>
</div>
</div>

<script>
var metrics = {metrics_json};
var results = {results_json};

// KPI cards
var kpiData = [
    {{ label: "Accuracy", value: (metrics.accuracy * 100).toFixed(1) + "%",
       cls: metrics.accuracy >= 0.8 ? "green" : metrics.accuracy >= 0.6 ? "amber" : "red" }},
    {{ label: "Precision", value: (metrics.precision * 100).toFixed(1) + "%",
       cls: metrics.precision >= 0.8 ? "green" : metrics.precision >= 0.6 ? "amber" : "red" }},
    {{ label: "Recall", value: (metrics.recall * 100).toFixed(1) + "%",
       cls: metrics.recall >= 0.8 ? "green" : metrics.recall >= 0.6 ? "amber" : "red" }},
    {{ label: "F1 Score", value: (metrics.f1 * 100).toFixed(1) + "%",
       cls: metrics.f1 >= 0.8 ? "green" : metrics.f1 >= 0.6 ? "amber" : "red" }},
    {{ label: "Total Cases", value: metrics.total, cls: "" }},
    {{ label: "Avg Latency", value: (metrics.latency.mean || 0).toFixed(1) + "s", cls: "" }},
];
var kpiHtml = kpiData.map(function(k) {{
    return '<div class="kpi-card"><div class="value ' + k.cls + '">' + k.value +
           '</div><div class="label">' + k.label + '</div></div>';
}}).join('');
document.getElementById("kpiGrid").innerHTML = kpiHtml;

// 1. Confusion Matrix heatmap
var chartConf = echarts.init(document.getElementById("chartConfusion"));
chartConf.setOption({{
    tooltip: {{ trigger: "item", formatter: function(p) {{
        return p.data[2] + " cases";
    }} }},
    grid: {{ left: 100, top: 40, right: 20, bottom: 40 }},
    xAxis: {{ type: "category", data: ["scam", "not_scam"], axisLabel: {{ fontSize: 12 }} }},
    yAxis: {{ type: "category", data: ["scam", "not_scam"], axisLabel: {{ fontSize: 12 }} }},
    visualMap: {{
        min: 0, max: Math.max(metrics.confusion_matrix.tp, metrics.confusion_matrix.tn, 1),
        calculable: false, orient: "horizontal", left: "center", bottom: 0,
        inRange: {{ color: ["#f1f5f9", "#6366f1"] }},
    }},
    series: [{{
        type: "heatmap",
        data: {json.dumps(cm_data)},
        label: {{ show: true, fontSize: 16, fontWeight: "bold" }},
        emphasis: {{ itemStyle: {{ shadowBlur: 10 }} }},
    }}],
}});

// 2. Per-class grouped bar
var chartBar = echarts.init(document.getElementById("chartBar"));
chartBar.setOption({{
    tooltip: {{ trigger: "axis" }},
    legend: {{ data: ["Precision", "Recall", "F1 Score"], bottom: 0 }},
    grid: {{ left: 50, right: 20, top: 20, bottom: 40 }},
    xAxis: {{ type: "category", data: ["scam", "not_scam"] }},
    yAxis: {{ type: "value", min: 0, max: 100, axisLabel: {{ formatter: "{{value}}%" }} }},
    series: [
        {{
            name: "Precision", type: "bar", data: [
                (metrics.per_class.scam.precision * 100).toFixed(1),
                (metrics.per_class.not_scam.precision * 100).toFixed(1),
            ], itemStyle: {{ color: "#6366f1" }},
        }},
        {{
            name: "Recall", type: "bar", data: [
                (metrics.per_class.scam.recall * 100).toFixed(1),
                (metrics.per_class.not_scam.recall * 100).toFixed(1),
            ], itemStyle: {{ color: "#10b981" }},
        }},
        {{
            name: "F1 Score", type: "bar", data: [
                (metrics.per_class.scam.f1 * 100).toFixed(1),
                (metrics.per_class.not_scam.f1 * 100).toFixed(1),
            ], itemStyle: {{ color: "#f59e0b" }},
        }},
    ],
}});

// 3. Latency histogram
var chartLat = echarts.init(document.getElementById("chartLatency"));
var histData = {json.dumps(hist_data)};
var histLabels = histData.map(function(d) {{ return d.label; }});
var histValues = histData.map(function(d) {{ return d.value; }});
var p50 = metrics.latency.p50;
var p95 = metrics.latency.p95;
chartLat.setOption({{
    tooltip: {{ trigger: "axis" }},
    grid: {{ left: 50, right: 60, top: 20, bottom: 50 }},
    xAxis: {{
        type: "category", data: histLabels,
        axisLabel: {{ rotate: 45, fontSize: 10, interval: 3 }},
    }},
    yAxis: {{ type: "value", name: "Count" }},
    series: [{{
        type: "bar", data: histValues, itemStyle: {{ color: "#6366f1" }},
        barWidth: "90%",
    }}],
    // Mark lines for P50/P95
    markLine: {{
        silent: true,
        data: [
            {{ xAxis: histLabels.find(function(l, i) {{
                var low = i * {bin_size};
                var high = (i + 1) * {bin_size};
                return low <= p50 && p50 < high;
            }}), label: {{ formatter: "P50: " + p50.toFixed(1) + "s" }},
               lineStyle: {{ color: "#f59e0b", type: "dashed" }} }},
            {{ xAxis: histLabels.find(function(l, i) {{
                var low = i * {bin_size};
                var high = (i + 1) * {bin_size};
                return low <= p95 && p95 < high;
            }}), label: {{ formatter: "P95: " + p95.toFixed(1) + "s" }},
               lineStyle: {{ color: "#ef4444", type: "dashed" }} }},
        ],
    }},
}});

// 4. Detail table
var tbody = document.getElementById("tableBody");
results.forEach(function(r) {{
    var expectedBadge = '<span class="badge ' + r.expected + '">' + r.expected + '</span>';
    var predictedBadge = '<span class="badge ' + r.predicted + '">' + r.predicted + '</span>';
    var statusIcon = r.error ? '<span class="badge error">ERROR</span>'
        : (r.expected === r.predicted
            ? '<span class="match">✓</span>'
            : '<span class="mismatch">✗</span>');
    var latencyDisplay = r.latency ? r.latency.toFixed(1) + "s" : "-";
    var scoreDisplay = r.risk_level ? r.risk_level + "/10" : "-";
    var row = '<tr>' +
        '<td>' + r.id + '</td>' +
        '<td class="url" title="' + r.url + '">' + r.url + '</td>' +
        '<td>' + scoreDisplay + '</td>' +
        '<td>' + expectedBadge + '</td>' +
        '<td>' + predictedBadge + '</td>' +
        '<td>' + latencyDisplay + '</td>' +
        '<td>' + statusIcon + '</td>' +
        '</tr>';
    tbody.innerHTML += row;
}});

window.addEventListener("resize", function() {{
    chartConf.resize(); chartBar.resize(); chartLat.resize();
}});
</script>
</body>
</html>
"""


def generate_report(results: list[dict], output_path: str):
    """
    Generate an HTML benchmark report.

    Args:
        results: list of dicts with keys:
            id, url, category, expected, predicted, latency, error, error_msg, risk_level
        output_path: path to write the HTML file
    """
    metrics = _compute_metrics(results)
    html = _build_html(results, metrics)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Report written to {output_path.resolve()}")
