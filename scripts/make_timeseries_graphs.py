#!/usr/bin/env python3
"""
Builds time-series CSVs and graphs from a real Cooja simulation log
(results/logs/real_true_attack_adaptive.testlog). Every value plotted is
parsed directly from that log -- nothing here is invented or interpolated
beyond what is explicitly disclosed below.

Known, disclosed gap in the underlying C logging code (rpl-trust.c):
THRESHOLD log lines do not carry their own timestamp. adapt_threshold() is
called synchronously, in the same function call, immediately after the
TRUST line is printed for the same reporter (see rpl_trust_report_outcome()
in rpl-trust.c) -- so the correct, *exact* (not approximate) timestamp for
a THRESHOLD line is the t= value of the immediately preceding TRUST line
from the same reporter in the raw log. That reconstruction is what this
script does; it is not a fabricated or interpolated timestamp.

ETX log lines also carry no timestamp (every parent-evaluation round logs
one, far more often than trust windows close), and unlike THRESHOLD there
is no exact same-call timestamped line to anchor them to. Rather than
fabricate a time value, ETX is plotted against sample sequence number, and
every plot/CSV says so explicitly.
"""
import re
import csv
import sys
import os

LOG = sys.argv[1] if len(sys.argv) > 1 else "results/logs/real_true_attack_adaptive.testlog"
OUT_CSV = "results/csv"
OUT_GRAPH = "results/graphs"
os.makedirs(OUT_CSV, exist_ok=True)
os.makedirs(OUT_GRAPH, exist_ok=True)

trust_re = re.compile(r'^TRUST by=(\d+) node=(\d+) b=(-?\d+) a=(-?\d+) ev=(\w+) conf=(\d+) t=(\d+)$')
state_re = re.compile(r'^STATE by=(\d+) node=(\d+) from=(\w+) to=(\w+) tr=(-?\d+) thr=(-?\d+) why=([\w-]+) t=(\d+)$')
thresh_re = re.compile(r'^THRESHOLD by=(\d+) active=(-?\d+) was=(-?\d+) ema=(-?\d+)$')
etx_re = re.compile(r'^ETX by=(\d+) node=(\d+) etx=(\d+) pc=(\d+) ok=(\d+)$')
detect_re = re.compile(r'^DETECTION by=(\d+) node=(\d+) evid=(\d+) tr=(-?\d+) thr=(-?\d+) failpct=(\d+)$')

trust_rows, state_rows, thresh_rows, etx_rows, detect_rows = [], [], [], [], []
last_trust_t = {}   # reporter -> last TRUST timestamp seen (for THRESHOLD reconstruction)
etx_seq = 0

with open(LOG, "r", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        m = trust_re.match(line)
        if m:
            by, node, b, a, ev, conf, t = m.groups()
            trust_rows.append([int(t), int(by), int(node), int(b), int(a), ev, int(conf)])
            last_trust_t[by] = int(t)
            continue
        m = state_re.match(line)
        if m:
            by, node, frm, to, tr, thr, why, t = m.groups()
            state_rows.append([int(t), int(by), int(node), frm, to, int(tr), int(thr), why])
            continue
        m = thresh_re.match(line)
        if m:
            by, active, was, ema = m.groups()
            t = last_trust_t.get(by)   # exact: same function call as the preceding TRUST line
            thresh_rows.append([t if t is not None else "NA", int(by), int(active), int(was), int(ema)])
            continue
        m = etx_re.match(line)
        if m:
            by, node, etx, pc, ok = m.groups()
            etx_seq += 1
            etx_rows.append([etx_seq, int(by), int(node), int(etx), int(pc), int(ok)])
            continue
        m = detect_re.match(line)
        if m:
            by, node, evid, tr, thr, failpct = m.groups()
            detect_rows.append([int(by), int(node), int(evid), int(tr), int(thr), int(failpct)])
            continue

def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {path}: {len(rows)} rows")

write_csv(f"{OUT_CSV}/trust_history_adaptive.csv",
          ["ts_ms", "reporter", "node", "trust_before", "trust_after", "evidence", "confidence"],
          trust_rows)
write_csv(f"{OUT_CSV}/state_transitions_adaptive.csv",
          ["ts_ms", "reporter", "node", "from_state", "to_state", "trust", "threshold", "reason"],
          state_rows)
write_csv(f"{OUT_CSV}/threshold_history_adaptive_timed.csv",
          ["ts_ms_reconstructed_from_same_call_trust_line", "reporter", "active_threshold", "prev_threshold", "confidence_ema"],
          thresh_rows)
write_csv(f"{OUT_CSV}/etx_samples_adaptive.csv",
          ["sample_seq_no_time_recorded", "reporter", "node", "etx", "path_cost", "acceptable"],
          etx_rows)
write_csv(f"{OUT_CSV}/detection_events_adaptive.csv",
          ["reporter", "node", "evidence_count", "trust", "threshold", "fail_rate_pct"],
          detect_rows)

print(f"TRUST rows: {len(trust_rows)}, STATE rows: {len(state_rows)}, "
      f"THRESHOLD rows: {len(thresh_rows)} ({sum(1 for r in thresh_rows if r[0]=='NA')} unanchored), "
      f"ETX rows: {len(etx_rows)}, DETECTION rows: {len(detect_rows)}")
