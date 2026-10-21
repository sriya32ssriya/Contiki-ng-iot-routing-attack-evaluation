## Final Results Comparison Table

Same topology (15-mote `real_attack` layout), same 1800s simulated duration, same `random-seed=1`, headless Cooja (`TARGET=sky`). Source: `results/csv/final_comparison_table.csv`, cross-checked directly against `results/logs/real_true_*.testlog`.

| Scenario | Sent | Received | Loss | PDR | Throughput (B/s) | Attack Drops | DETECTION Events | PREVENTION Rejects | Detection Latency |
|---|---|---|---|---|---|---|---|---|---|
| Baseline (attack off) | 2468 | 2406 | 62 | **97.49%** | 11.48 | 0 | 0 | 0 | N/A — no attack present |
| Attack, No Mitigation | 2469 | 2262 | 207 | 91.62% | 11.49 | 152 | 3 | 0 | 51.6s (reporter 10), 76.0s (reporter 9) — detected but never enforced in this mode |
| Attack, Adaptive Trust | 2469 | 2337 | 132 | **94.65%** | 11.49 | 64 | 2 | 2 | 38.9s (reporter 10), 65.6s (reporter 8) |
| Attack, Static Blacklist | 2468 | 2453 | 15 | 99.39% | 11.48 | 0 | 0 | 0 | N/A — node 6 blocked from t=0, no detection ever runs |

Notes:
- "Attack Drop Events" = count of real `SF drop node=6 rate=20%` lines in that scenario's log (the attack actually firing), not an estimate.
- "DETECTION Events" / "PREVENTION Rejects" = count of real `DETECTION` / `PREVENTION ... act=reject` lines. The trust engine's detection logic runs identically in every mode (for observability); only `PREVENTION` enforcement is mode-gated (see `REPORT.md`), which is why No-Mitigation shows detections but zero rejects.
- Detection latency = time between a reporter's first `SUSPECT` entry and its `EXCLUDED` transition for node 6, read directly from `results/csv/state_transitions_adaptive.csv`. No latency metric applies to Baseline (nothing to detect) or Static (no detection logic exists in that mode).
- Two independent reporters are shown per detecting scenario because each node runs its own independent trust table — there is no shared/global verdict (see `CODE_EXPLANATION.md` §12).
