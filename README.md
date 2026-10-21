# RPL Adaptive Trust / Dynamic Threshold / Prevention / Recovery

This project adds a per-neighbor trust engine, a dynamic trust threshold, and
a prevention + recovery state machine to Contiki-NG's RPL-lite, replacing a
static node-ID blacklist that used to be hardcoded into the objective
function. It is built on top of the existing `examples/rpl-udp` network and
the pre-existing selective-forwarding / blackhole attack simulations kept in
this directory.

**Status at a glance:** detection and exclusion are implemented and verified
with real simulation logs (not assumed). Full recovery
(`EXCLUDED -> PROBATION -> RECOVERED`) is implemented and reachable in code
but was **not observed completing** in the topology tested here — see
[Recovery: implemented but not observed completing](#recovery-implemented-but-not-observed-completing).

## Files

| File | What it is |
|---|---|
| `os/net/routing/rpl-lite/rpl-trust.{c,h}` | The trust engine (new) |
| `os/net/routing/rpl-lite/rpl-mrhof.c` | Parent-acceptance now delegates to `rpl_trust_is_acceptable_parent()`; also logs ETX/path-cost per candidate |
| `os/net/ipv6/uip6.c` | The selective-forwarding attack (node 6, configurable rate), now gated by `SELECTIVE_FORWARDING_ATTACK_CONF_ENABLE` |
| `examples/rpl-udp/udp-client.c` + `udp-client-{baseline,sf10,sf40,blackhole}.c` | App-layer traffic generator + evidence hook into the trust engine |
| `examples/rpl-udp/project-conf.h` | Sets the default mitigation mode (`ADAPTIVE`) for every scenario that doesn't override it |
| `tools/myproject/*.csc` | Cooja scenarios (originals untouched; new ones added, see below) |
| `tools/myproject/headless/*.csc` | Headless-runnable copies (original + Cooja `ScriptRunner` test-harness plugin added) |
| `tools/myproject/metrices/metrics.py` | PDR/loss/throughput parser (extended with an optional duration argument, default unchanged) |
| `tools/myproject/results/` | New, non-destructive output: `logs/`, `csv/`, `graphs/` (see below) |

## Design

### 1. Trust score (`rpl-trust.c` / `rpl-trust.h`)

Trust is an integer per neighbor, `0 <= trust <= 100` (`RPL_TRUST_MIN`/`MAX`
in `rpl-trust.h`), initialized to `RPL_TRUST_CONF_INIT = 70` the first time a
node is observed. It is stored in a small fixed-size table
(`RPL_TRUST_CONF_MAX_NODES = 16`) keyed by the last byte of the neighbor's
link-layer address — **not** inside RPL's own `rpl_nbr_t`/neighbor table,
because that table's slots are `memset` to zero on rediscovery
(`nbr-table.c`), which would silently wash out trust history if a node were
evicted and rejoined.

**Evidence window.** Each node accumulates raw outcomes (did my last request
get a reply before the next one was sent — see
[Evidence source](#evidence-source-honest-limits)) into a window of
`RPL_TRUST_CONF_WINDOW_SIZE = 10` outcomes. Nothing happens to trust until a
full window closes. On close:

```
fail_rate_pct = 100 * window_fails / WINDOW_SIZE        # WINDOW_SIZE = 10
good_window   = fail_rate_pct <= BASELINE_FAIL_RATE_PCT  # BASELINE = 10%
```

**Confidence** (`rpl_trust_report_outcome`, computed once per closed window):

```
confidence = LOW (30)    if link ETX > POOR_LINK_ETX (320)
                          or reporter_hop_count() > MAX_RELIABLE_HOPS (3)
           = MEDIUM (60) otherwise
```
`HIGH (100)` is defined but never produced by this evidence source — it is
reserved for a future hop-local watchdog (see below). ETX never changes
trust directly; it only discounts confidence.

**Trust update formula**, applied once per closed window (integer math, as
in the code):

```
good window, not on probation:   trust += (SUCCESS_GAIN(4)     * confidence) / 100
good window, on probation:       trust += (PROBATION_GAIN(3)   * confidence) / 100
bad window (either state):       trust -= (FAIL_PENALTY(15)    * confidence) / 100
trust = clamp(trust, 0, 100)
```

At `confidence = 60` (MEDIUM) this is **+2 / +1 / -9** per window; at
`confidence = 30` (LOW) it is **+1 / 0 / -4**. The ratio of
`FAIL_PENALTY : SUCCESS_GAIN = 15 : 4` is the asymmetry: a bad window hurts
roughly 3.75x more than a good window helps — this is a configured ratio of
the two `#define`s, not a separately-computed formula.

### 2. State machine

States (`rpl_trust_state_t`): `NORMAL, SUSPECT, EXCLUDED, PROBATION, RECOVERED`.
Transitions, exactly as coded in `rpl_trust_report_outcome`:

| From | Event | To | Extra condition |
|---|---|---|---|
| NORMAL | bad window | SUSPECT | none (first bad window is enough to start watching) |
| SUSPECT | good window | NORMAL | `good_window_streak >= SUSPECT_RECOVERY_STREAK (3)` |
| SUSPECT or RECOVERED | bad window | EXCLUDED | `trust < active_threshold` **and** `total_bad_windows >= MIN_EVIDENCE_EXCLUDE (3)` |
| EXCLUDED | good window | PROBATION | `now - state_since >= EXCLUDED_MIN_DWELL (30s)` **and** `trust >= active_threshold + PROBATION_ENTRY_MARGIN (5)` |
| PROBATION | good window | RECOVERED | `probation_good_windows >= PROBATION_MIN_SUCCESSES (3)` **and** `trust >= active_threshold + RECOVERY_MARGIN (10)` |
| PROBATION | bad window | EXCLUDED | immediate — any bad window during probation re-excludes, no soft downgrade |

Two distinct, increasing hysteresis margins (`PROBATION_ENTRY_MARGIN = 5`,
`RECOVERY_MARGIN = 10`) on top of a time floor (`EXCLUDED_MIN_DWELL`) are
what stop a node flapping across the threshold boundary — recovery is never
triggered by the dwell timer alone, and never by one packet or one bare
outcome, only by full evidence windows.

**DETECTION / PREVENTION logging** fires only once, at the `SUSPECT|RECOVERED
-> EXCLUDED` transition:
```
DETECTION by=<reporter> node=<target> evid=<total_bad_windows> tr=<trust> thr=<threshold> failpct=<fail_rate_pct>
PREVENTION by=<reporter> node=<target> act=reject      # only printed in ADAPTIVE mode
```
The `PREVENTION ... act=reject` line is gated to `ADAPTIVE` mode specifically
because only `rpl_trust_is_acceptable_parent()`'s `ADAPTIVE` branch actually
acts on `EXCLUDED` — in `NONE`/`STATIC` mode the state machine still runs
(for observability) but nothing is actually rejected, so claiming
`act=reject` there would misrepresent what happened. (Earlier logs
predating this fix printed the line in `NONE` mode too — see Appendix.)

### 3. Dynamic threshold

Separate state from any individual node's trust, by design (`active_threshold`,
`confidence_ema`), so the two effects can be read independently from the
logs:

```
confidence_ema' = confidence_ema + (confidence - confidence_ema) / 4     # EMA, alpha = 1/4
target          = THRESHOLD_MIN(35) + confidence_ema * (THRESHOLD_MAX(60) - THRESHOLD_MIN(35)) / 100
active_threshold moves toward target by at most THRESHOLD_STEP_MAX(2) per call
active_threshold = clamp(active_threshold, 35, 60)
```

If the same evidence event just caused a state transition, the threshold
step is skipped for that call (only the EMA updates) — so one event cannot
both flip a node's state and move the threshold, keeping the two mechanisms
separable, per the project's design requirement. `confidence_ema` is fed by
confidence values from *all* nodes' evidence, not any single node's
behavior, so one attacker cannot steer the threshold by itself.

### 4. Prevention

`rpl_trust_is_acceptable_parent()` (called from `rpl-mrhof.c`'s
`nbr_is_acceptable_parent`) is mode-gated:

- `RPL_TRUST_MODE_NONE` (0): always returns 1 — true unmitigated baseline.
- `RPL_TRUST_MODE_STATIC` (1): returns 0 iff `node_id == RPL_TRUST_CONF_STATIC_AVOID_NODE` (6) — the original hardcoded behavior, kept only as a comparison baseline, explicitly logged as *"static legacy mode, not trust-based detection"*.
- `RPL_TRUST_MODE_ADAPTIVE` (2): returns 1 if the node has never been observed, or its state isn't `EXCLUDED`; if `EXCLUDED`, returns 0 **except** inside a bounded probe window (see below).

On any transition that could change a currently-preferred parent's
eligibility, `force_parent_reeval()` calls `rpl_timers_schedule_state_update()`
directly — this is what makes exclusion an actual routing-behavior change
rather than just a log line (RPL-lite's own `rpl_dag_update_state()` is only
event-triggered, not polled; see Appendix for the trace that established this).

### 5. Recovery / probing

Because an `EXCLUDED` node is never again selected as anyone's parent under
normal MRHOF operation, nobody would ever generate further evidence about
it — recovery would be a dead code path without some way to re-test it. The
fix: every `PROBE_INTERVAL (60s)`, `rpl_trust_is_acceptable_parent()` opens a
`PROBE_WINDOW (2s)` during which an `EXCLUDED` node is treated as acceptable
again. Children only actually switch back to it if it is still their best
candidate on path cost — MRHOF's own rank/hysteresis rules are never
bypassed. A bad outcome during a probe is scored exactly like any other
credible failure.

## Evidence source: honest limits

**This is not a promiscuous watchdog.** A real watchdog (a node overhearing
whether its parent actually retransmits a packet it was given) was
investigated and found *architecturally present but not practically usable
out of the box*: Cooja's UDGM radio medium and the `cooja-radio`/`cc2420`
drivers do deliver "not-for-me" frames, but the default CSMA MAC
(`os/net/mac/csma/csma.c:87-90`) unconditionally drops any unicast frame not
addressed to the local node, regardless of `RADIO_PARAM_RX_MODE`. Building
one needs a custom thin MAC (the pattern in
`examples/serialradio/sniffer-mac.c`) and was judged too large/risky a
change to land safely across every scenario in this pass.

**What is actually used**: local end-to-end delivery confirmation. Each
client already sends a periodic request and expects an echo
(`udp-client.c`). A node locally knows (a) whether its last request got a
reply before the next send, and (b) which neighbor was its preferred parent
*at the moment it sent that request* (snapshotted, not read after the fact,
so a parent switch mid-flight doesn't misattribute the outcome). This is
real, local, cross-node-independent evidence — no shared memory, no access
to the target node's internal state — but it is **indirect**: a miss can
equally mean "my parent dropped it", "the echo was lost on the way back",
"the root was briefly unreachable", or "my own link to my parent is briefly
bad". The engine's design choices are a direct response to that:
confidence capped at MEDIUM, a full window of aggregated outcomes required
before any trust change, ETX only ever discounting confidence (never
classifying maliciousness by itself), and a hop-depth confidence discount
(below) for a confound this evidence source cannot otherwise see.

`rpl_trust_report_outcome()` is the stable integration point a real watchdog
MAC could call into later with `RPL_TRUST_CONFIDENCE_HIGH` evidence, without
needing to change the state machine, threshold logic, or logging.

## Bugs found through actual simulation runs, and fixes

Three real defects were found this way — not assumed, not left unverified:

1. **Detection never fired.** First design gated evidence on "2 consecutive
   failures". At a steady ~20% drop rate, successes are credited on almost
   every outcome while a run of 2 failures is rare (~4% of outcome pairs),
   so trust drifted *upward* overall regardless of asymmetric penalty/gain —
   confirmed by a full run showing 349 trust updates for node 6 and zero
   `DETECTION` events, trust oscillating 61-100. Fixed by switching to the
   windowed failure-*rate* test described above.
2. **False positives on innocent nodes.** After the above fix, nodes 8, 10,
   and 13 (not the attacker) were also excluded — confirmed by logs. Root
   cause: end-to-end evidence blames the immediate parent even when a
   *deeper* ancestor is the actual culprit; a node 3+ hops from the root
   cannot tell "my parent is bad" from "something above my parent is bad".
   Fixed with the hop-depth confidence discount
   (`RPL_TRUST_CONF_MAX_RELIABLE_HOPS = 3`); re-run confirmed zero false
   positives on the `real_true_attack_adaptive` run.
3. **False positives in the app-layer attack variants** (SF10/SF40/
   blackhole): node 6 itself was blaming its *own* parent for node 6's own
   decision not to send a packet, because the evidence hook armed
   "pending reply" before checking whether a send would even happen. Fixed
   by moving the arm-point to immediately before each actual
   `simple_udp_sendto()` call. Re-run on SF10 and blackhole confirmed clean
   (zero non-node-6 `DETECTION`s); SF2 40% was re-run after this fix too
   (see Results).
4. **Logging-honesty fix**: `PREVENTION ... act=reject` was printing even in
   `NONE` mode, where nothing is actually rejected. Gated to `ADAPTIVE` mode.

## Recovery: implemented but not observed completing

The state machine transitions for `EXCLUDED -> PROBATION -> RECOVERED` are
implemented, and the probe mechanism correctly makes an excluded node
"acceptable" again for its 2-second window every 60 seconds (confirmed in
logs: 22 and 14 probe grants for the two reporters that excluded node 6 in
the `real_true_attack_adaptive` run). **But no `PROBATION` or `RECOVERED`
transition was ever logged.** Cause, confirmed by inspecting the logs: zero
`TRUST`-window-close events were recorded for either reporter's view of node
6 after exclusion, despite 36 combined probe grants — meaning the probe
never actually resulted in the child re-selecting node 6 as its real
preferred parent. MRHOF's own switch hysteresis (rank-gain threshold / time
threshold in `rpl-mrhof.c`) correctly favors a stable, already-adequate
alternate parent over switching back to a merely "acceptable again" node,
and this project does not override that (recovery must respect normal RPL
parent eligibility and loop-avoidance rules, per the design requirement).

**Conclusion: do not read this as "recovery works" or "recovery is broken"
— it is implemented and its individual gating conditions are each
independently correct, but end-to-end completion of the recovery path was
not exercised in this topology/run.** A smaller, purpose-built topology
where the excluded node is the *only* viable parent during a probe would be
needed to actually witness `PROBATION`/`RECOVERED` firing; that test was not
run.

## Known pre-existing issue (not introduced here, now disclosed)

`real_attack.csc` and `real_baseline.csc` (the original two scenario files)
are byte-identical in topology — the uip6.c selective-forwarding code used
to apply unconditionally by node ID, with no scenario-level gating, so both
files have always driven the exact same attack. This is why
`real_baseline_adaptive.testlog` (an earlier run against the *old*,
ungated `real_baseline.csc`) shows attack-level loss, not baseline-level
loss — it is kept in `results/logs/` for traceability but is **superseded**
by `real_true_baseline.testlog`, which uses the new
`SELECTIVE_FORWARDING_ATTACK_CONF_ENABLE` gate and was verified
(`grep -c "selective forwarding drop"` = 0) to have the attack genuinely
off. The original `.csc` files are untouched; new `real_true_*.csc` files
were added instead (see Reproduction below).

## Results

All `real_true_*` and SF/blackhole runs: 1800s simulated, same 15-mote
topology as the original `real_attack.csc`, `random-seed=1`, headless Cooja
(`TARGET=sky`). Full CSVs/logs in `results/csv/` and `results/logs/`;
comparison graphs in `results/graphs/`.

| Scenario | Sent | Received | PDR | Loss | Attack drop events |
|---|---|---|---|---|---|
| True baseline (attack **off**, verified) | 2468 | 2406 | **97.49%** | 62 | 0 |
| Attack, no mitigation | 2469 | 2262 | **91.62%** | 207 | 152 |
| Attack, adaptive trust | 2469 | 2337 | **94.65%** | 132 | 64 |
| Attack, static blacklist (oracle) | 2468 | 2453 | **99.39%** | 15 | 0 |

Adaptive mitigation recovers about half the PDR lost to the attack
(97.49 - 91.62 = 5.87 pts lost; 94.65 - 91.62 = 3.03 pts recovered) without
any prior knowledge of which node is malicious; the static oracle recovers
essentially all of it but only because it already "knows" the answer at
compile time with zero detection latency. Detection latency, measured from
first `SUSPECT` entry to `EXCLUDED`, from this run's logs
(`results/csv/state_transitions_adaptive.csv`): reporter 10 took 38.9s,
reporter 8 took 65.6s.

App-layer attack variants (same topology, `SELECTIVE_FORWARDING_ATTACK_CONF_ENABLE`
left at its default of 1, so the ever-present IP-layer attack is also active
underneath each of these — see the known pre-existing issue above for why
that default applies everywhere):

| Scenario | Sent | Received | PDR | Loss | Note |
|---|---|---|---|---|---|
| SF1 10% (post-fix) | 2469 | 2355 | 95.38% | 114 | zero false positives confirmed |
| SF2 40% (post-fix) | 2468 | 2309 | 93.56% | 159 | zero false positives confirmed; Cooja itself threw a benign NPE in its own test-teardown code at the very end of this run (after `TEST OK`/`log.testOK()` had already recorded) — data is complete (2468 "PACKET SENT" / full 1800s simulated time present), gradle's exit code is misleading here |
| Blackhole (post-fix) | 2470 | 2226 | 90.12% | 244 | zero false positives confirmed |
| Baseline_SF0 | 892 | 889 | 99.66% | 3 | different (smaller) topology — not directly comparable to the rows above |

Supporting evidence that the trust engine is not using ETX as a proxy for
malice: node 6's ETX as observed by its children stays in the normal
128-137 band (`results/csv/etx_samples_adaptive.csv`) throughout the attack
— the selective-forwarding drop is invisible at the ETX/link-stats layer,
confirming detection is coming from the end-to-end evidence path, not ETX.

### Not measured / not run

- Recovery completion (see above).
- A real promiscuous-watchdog comparison (not implemented this pass).
- Fixed-vs-adaptive-threshold comparison under identical evidence (the
  `STATIC`/`NONE`/`ADAPTIVE` comparison exists, but a run with the
  *threshold* fixed at a constant while still using the adaptive trust
  engine was not separately run).
- Scenario 4 from a full evaluation matrix ("legitimate node experiencing
  poor link quality") — these `.csc` files use `success_ratio_tx/rx = 1.0`
  (no inherent radio loss), so no scenario here currently exercises that
  case; would need a new scenario with a degraded link on a non-attacking
  node.

## Reproduction

```bash
export PATH="/home/sriya/contiki-ng/msp430/bin:$PATH"   # msp430-gcc; already built, just not on PATH

# Build (any scenario's firmware) — from examples/rpl-udp:
cd examples/rpl-udp
make TARGET=sky clean
make TARGET=sky udp-client.sky udp-server.sky -j"$(nproc)"

# Headless Cooja run (no X11/Docker needed), from the repo root:
tools/cooja/gradlew --no-watch-fs --parallel --build-cache -p tools/cooja run \
  -Dslf4j.provider=ch.qos.logback.classic.spi.LogbackServiceProvider \
  --args="--no-gui --contiki=$(pwd) --logdir=<out-dir> --random-seed=1 \
          tools/myproject/headless/real_true_attack_adaptive_headless.csc"

# Mitigation mode / attack on-off are DEFINES=, not CFLAGS+= (CFLAGS+= on the
# command line blocks Makefile.include's own -I flags — confirmed the hard way):
make TARGET=sky udp-client.sky TARGET=sky \
  DEFINES=SELECTIVE_FORWARDING_ATTACK_CONF_ENABLE=0,RPL_TRUST_CONF_MITIGATION_MODE=2

# Metrics from a raw log:
python3 tools/myproject/metrices/metrics.py <logfile> 1800   # 1800 = actual sim seconds

# For SF10/SF40/blackhole/baseline app-layer variants, copy the variant over
# udp-client.c before building (this project's existing workflow):
cp examples/rpl-udp/udp-client-sf40.c examples/rpl-udp/udp-client.c
```

Mitigation modes: `0` = none (unmitigated), `1` = static legacy blacklist
(comparison only), `2` = adaptive (default, set in `project-conf.h`).

## Appendix: traced facts used in this design (not re-derived here)

- `nbr_is_acceptable_parent` is called from `best_parent()`, itself called
  by `rpl_neighbor_select_best()` — a full neighbor-table scan, not a
  per-DIO incremental check (`rpl-neighbor.c`).
- `rpl_neighbor_select_best()` only runs when `rpl_timers_schedule_state_update()`
  is called (DIO received, neighbor removed, link-stats update, DAG
  poisoning) — there is no independent periodic re-check of just the
  current preferred parent (`rpl-dag.c`, `rpl-timers.c`).
- `NBR_TABLE_CONF_MAX_NEIGHBORS` defaults to 16 (`contiki-default-conf.h`) —
  this is why `RPL_TRUST_CONF_MAX_NODES` is also 16.
- `nbr_table_add_lladdr()` `memset`s a reused slot to zero
  (`nbr-table.c`) — why trust state lives outside `struct rpl_nbr`.
