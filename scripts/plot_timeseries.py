#!/usr/bin/env python3
"""
Plots the graphs requested for the research results report, from the
reconstructed CSVs produced by make_timeseries_graphs.py. Every data point
plotted traces back to a real line in results/logs/real_true_attack_adaptive.testlog.
Run from tools/myproject/.
"""
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV = "results/csv"
OUT = "results/graphs"

def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

trust = read_csv(f"{CSV}/trust_history_adaptive.csv")
state = read_csv(f"{CSV}/state_transitions_adaptive.csv")
thresh = read_csv(f"{CSV}/threshold_history_adaptive_timed.csv")
etx = read_csv(f"{CSV}/etx_samples_adaptive.csv")

SEC = 1000.0  # ts_ms -> seconds

# ---------- 1. ETX vs time (no true timestamp recorded for ETX -- plotted
# vs sample sequence number instead; see script/README note) ----------
node6_etx = [(int(r["sample_seq_no_time_recorded"]), int(r["etx"]))
             for r in etx if r["node"] == "6"]
if node6_etx:
    xs, ys = zip(*node6_etx)
    plt.figure(figsize=(11, 4.5))
    plt.scatter(xs, [v / 128.0 for v in ys], s=2, alpha=0.4, color="#4C72B0")
    plt.xlabel("ETX sample sequence number (chronological log order --\n"
               "no per-sample timestamp was recorded by the logging code, see note in script)")
    plt.ylabel("ETX (link_stats units / 128 = conventional ETX scale)")
    plt.title("Node 6 ETX as observed by its children, across the attack run\n"
               "(mostly 1.0-1.1 with ordinary transient link-quality noise up to ~3; no sustained\n"
               "elevation correlated with the 20% forwarding-drop attack -- ETX cannot see this attack)")
    plt.tight_layout()
    plt.savefig(f"{OUT}/ETX_vs_time_node6.png", dpi=130)
    plt.close()
    print(f"ETX_vs_time_node6.png: {len(node6_etx)} samples, "
          f"etx range {min(ys)/128.0:.3f}-{max(ys)/128.0:.3f}")
else:
    print("WARNING: no ETX samples found for node 6 -- graph not generated")

# ---------- helper: node=6 as seen by a specific reporter ----------
def series_for(rows, reporter, node, tkey="ts_ms"):
    out = [r for r in rows if r.get("reporter") == str(reporter) and r.get("node") == str(node)]
    out.sort(key=lambda r: int(r[tkey]) if r[tkey] not in ("NA", "") else -1)
    return out

REPORTER, NODE = "10", "6"   # fastest detector of node 6, full SUSPECT->EXCLUDED cycle present

t_rows = series_for(trust, REPORTER, NODE)
s_rows = series_for(state, REPORTER, NODE)
th_rows = [r for r in thresh if r["reporter"] == REPORTER]
th_rows.sort(key=lambda r: int(r["ts_ms_reconstructed_from_same_call_trust_line"]))

# ---------- 2. Trust score vs adaptive threshold, over time ----------
if t_rows and th_rows:
    tx = [int(r["ts_ms"]) / SEC for r in t_rows]
    ty = [int(r["trust_after"]) for r in t_rows]
    thx = [int(r["ts_ms_reconstructed_from_same_call_trust_line"]) / SEC for r in th_rows]
    thy = [int(r["active_threshold"]) for r in th_rows]

    plt.figure(figsize=(11, 5))
    plt.plot(tx, ty, marker="o", markersize=3, label=f"Trust score (node {NODE}, as seen by node {REPORTER})", color="#4C72B0")
    plt.plot(thx, thy, marker="s", markersize=3, label=f"Active threshold (node {REPORTER}'s view)", color="#C44E52")
    for r in s_rows:
        plt.axvline(int(r["ts_ms"]) / SEC, color="gray", linestyle="--", alpha=0.5)
        plt.annotate(r["to_state"], (int(r["ts_ms"]) / SEC, 5), rotation=90, fontsize=8, va="bottom")
    plt.xlabel("Simulated time (s)")
    plt.ylabel("Score")
    plt.title(f"Trust score vs. adaptive threshold over time -- node {NODE}, as tracked by node {REPORTER}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUT}/trust_vs_threshold_node6_by10.png", dpi=130)
    plt.close()
    print(f"trust_vs_threshold_node6_by10.png: {len(t_rows)} trust points, {len(th_rows)} threshold points")
else:
    print(f"WARNING: insufficient data for trust-vs-threshold graph (trust={len(t_rows)}, threshold={len(th_rows)})")

# ---------- 3. Adaptive threshold vs time (reporter 10's own view, all targets it has formed an opinion on) ----------
th_all = [r for r in thresh if r["reporter"] == REPORTER]
th_all.sort(key=lambda r: int(r["ts_ms_reconstructed_from_same_call_trust_line"]))
if th_all:
    xs = [int(r["ts_ms_reconstructed_from_same_call_trust_line"]) / SEC for r in th_all]
    ys = [int(r["active_threshold"]) for r in th_all]
    plt.figure(figsize=(11, 4.5))
    plt.step(xs, ys, where="post", color="#55A868")
    plt.ylim(30, 65)
    plt.axhline(35, color="gray", linestyle=":", linewidth=1)
    plt.axhline(60, color="gray", linestyle=":", linewidth=1)
    plt.xlabel("Simulated time (s)")
    plt.ylabel("Active threshold")
    plt.title(f"Adaptive threshold over time, as computed by node {REPORTER}\n(bounds: 35-60, dotted lines)")
    plt.tight_layout()
    plt.savefig(f"{OUT}/threshold_vs_time_node10.png", dpi=130)
    plt.close()
    print(f"threshold_vs_time_node10.png: {len(th_all)} points")

# ---------- 4. Trust-state transitions (timeline / step plot) ----------
STATE_Y = {"NORMAL": 0, "SUSPECT": 1, "EXCLUDED": 2, "PROBATION": 3, "RECOVERED": 4}
if s_rows:
    # Build a step function: starts NORMAL at t=0, then each transition.
    xs = [0.0] + [int(r["ts_ms"]) / SEC for r in s_rows]
    ys = [STATE_Y["NORMAL"]] + [STATE_Y[r["to_state"]] for r in s_rows]
    plt.figure(figsize=(11, 4.5))
    plt.step(xs, ys, where="post", marker="o", color="#8172B2")
    plt.yticks(list(STATE_Y.values()), list(STATE_Y.keys()))
    plt.xlabel("Simulated time (s)")
    plt.ylabel("Trust state")
    plt.title(f"Trust-state transitions for node {NODE}, as observed by node {REPORTER}")
    for r in s_rows:
        plt.annotate(r["reason"], (int(r["ts_ms"]) / SEC, STATE_Y[r["to_state"]]),
                     fontsize=7, rotation=20, xytext=(2, 4), textcoords="offset points")
    plt.tight_layout()
    plt.savefig(f"{OUT}/state_transitions_node6_by10.png", dpi=130)
    plt.close()
    print(f"state_transitions_node6_by10.png: {len(s_rows)} transitions")
else:
    print("WARNING: no state transitions found for node 6 / reporter 10")

# ---------- 5. Combined detection analysis: two independent reporters ----------
plt.figure(figsize=(12, 6))
colors = {"8": "#C44E52", "10": "#4C72B0"}
for reporter in ["8", "10"]:
    tr = series_for(trust, reporter, NODE)
    st = series_for(state, reporter, NODE)
    if not tr:
        continue
    tx = [int(r["ts_ms"]) / SEC for r in tr]
    ty = [int(r["trust_after"]) for r in tr]
    plt.plot(tx, ty, marker="o", markersize=3, color=colors[reporter],
              label=f"Trust of node {NODE}, as tracked by node {reporter}")
    excl = [r for r in st if r["to_state"] == "EXCLUDED"]
    for r in excl:
        plt.scatter([int(r["ts_ms"]) / SEC], [int(r["trust"])], color=colors[reporter],
                    marker="X", s=150, zorder=5,
                    label=f"node {reporter} EXCLUDES node {NODE} at t={int(r['ts_ms'])/SEC:.0f}s")
plt.xlabel("Simulated time (s)")
plt.ylabel("Trust score")
plt.title(f"Combined detection analysis: two independent reporters' trust of node {NODE}\n"
          "(each X marks that reporter's own EXCLUDED decision -- no shared/global trust state)")
plt.legend(loc="upper right", fontsize=8)
plt.tight_layout()
plt.savefig(f"{OUT}/combined_detection_analysis_node6.png", dpi=130)
plt.close()
print("combined_detection_analysis_node6.png written")
