# Code Explanation (beginner-friendly)

This document walks through the actual code in this project, in plain
language, so you can explain it to someone else without having to re-derive
it from the C source. Every number and function name below is copied from
the real files — nothing here is a simplified stand-in.

> **Note on "six states":** the implementation has **five** trust states
> (`NORMAL, SUSPECT, EXCLUDED, PROBATION, RECOVERED`), not six. This matches
> both the code (`rpl_trust_state_t` in `rpl-trust.h`) and the original
> design brief this project followed. If your professor's materials mention
> six states, that is a mismatch worth asking about — this document
> describes what is actually built and tested.

---

## 1. The big picture: what is a WSN/RPL network, and what's the attack?

A **Wireless Sensor Network (WSN)** here is simulated in Cooja as 16 "motes"
(simulated sensor nodes): one **root** (the data sink, like a gateway) and
15 **clients**. Each client periodically sends a small UDP message to the
root and expects an echo reply back. Because most clients are too far from
the root to reach it directly (radio range is limited), their messages hop
through intermediate nodes that **forward** traffic on their behalf — this
is what RPL (Routing Protocol for Low-Power and Lossy Networks) organizes.

**The attack**: one specific node, **node 6**, sits in the middle of the
tree (it has several nodes using it as their next hop toward the root).
Instead of faithfully forwarding every packet it receives for others, it
silently drops about 20% of them. This is called **selective forwarding**
(RFC terminology: a "grey hole" — not total refusal like a blackhole, just
some loss) — a classic WSN attack where a compromised relay quietly
degrades traffic without ever behaving badly enough to look obviously
broken.

## 2. Where the attack actually lives in the code

File: `os/net/ipv6/uip6.c`, inside the IPv6 forwarding function (`uip_process`).
This is the function every Contiki-NG node runs whenever it needs to decide
"this packet isn't for me — pass it along":

```c
#if SELECTIVE_FORWARDING_ATTACK_CONF_ENABLE
if(linkaddr_node_addr.u8[7] == SELECTIVE_FORWARDING_ATTACK_CONF_NODE) {   // "is this me, node 6?"
  if((random_rand() % 10) < SELECTIVE_FORWARDING_ATTACK_CONF_RATE_TENTHS) { // 20% of the time
    printf("SF drop node=%u rate=%u0%%\n", ...);
    UIP_STAT(++uip_stat.ip.drop);
    goto drop;                         // throw the packet away
  }
}
#endif
UIP_STAT(++uip_stat.ip.forwarded);
goto send;                             // otherwise, forward it like normal
```

`linkaddr_node_addr.u8[7]` is just "the last byte of my own node ID" — this
project's convention for identifying a node throughout the code.
`SELECTIVE_FORWARDING_ATTACK_CONF_ENABLE` is a build-time switch (added in
this project) that lets you compile the attack **in** or **out** — pass
`DEFINES=SELECTIVE_FORWARDING_ATTACK_CONF_ENABLE=0` at build time for a
genuinely attack-free baseline, or leave it unset (defaults to 1) to keep
every existing scenario exactly as it was before.

**Important nuance**: this attack only ever fires when node 6 is actually
*forwarding someone else's packet*. If nobody has chosen node 6 as their
relay, the attack code never triggers — which is why the topology (who ends
up near/below node 6) matters for whether the attack has any effect at all.

There are also **app-layer** attack variants (`udp-client-sf10.c`,
`udp-client-sf40.c`, `udp-client-blackhole.c`) that make node 6 refuse to
send its *own* outgoing packets (10%, 40%, or 100% of the time). These are
a different, simpler kind of misbehavior — refusing to originate your own
traffic, not refusing to relay someone else's — and they run *underneath*
the always-present IP-layer attack above (since `SELECTIVE_FORWARDING_
ATTACK_CONF_ENABLE` defaults to on unless overridden).

## 3. Packet flow, step by step

1. **Client sends** (`udp-client.c`, every ~10 seconds ± jitter): builds a
   string like `"hello 42"`, calls `simple_udp_sendto()` toward the root.
2. **IP layer routes it** (`uip6.c`): if the client isn't the root's direct
   neighbor, the packet passes through one or more relay nodes. Each relay
   calls the forwarding code above; node 6, if it's the relay, has a 20%
   chance of dropping it right there.
3. **Root receives and echoes** (`udp-server.c`): whatever arrives, it
   immediately sends the exact same bytes back to the sender.
4. **Client's reply callback fires** (`udp_rx_callback` in `udp-client.c`):
   increments its received-packet counter. This is also where trust
   evidence gets reported (see §5).
5. **RPL continuously maintains the tree in the background**: every node
   picks a "preferred parent" — the neighbor it currently uses as its next
   hop toward the root — based on the **MRHOF** objective function
   (§6), which this project also modified to consult the trust engine.

## 4. ETX and MRHOF — how RPL normally picks a relay (and why that alone can't catch this attack)

**ETX** (Expected Transmission Count) is a per-link quality number: `1.0`
means "every packet gets through on the first try", higher means more
retransmissions are typically needed. Contiki-NG computes it automatically
from link-layer ACK success rates (`os/net/link-stats.c`) — this project
doesn't change how ETX itself is computed, only how it's *used*.

**MRHOF** (Minimum Rank with Hysteresis Objective Function,
`rpl-mrhof.c`) is RPL's built-in algorithm for choosing the best path to
the root: sum up ETX along the whole path (the "path cost"), and prefer the
neighbor with the lowest path cost, with some hysteresis (stickiness) so
the tree doesn't reshuffle every time a reading flickers.

**Why ETX can't see this attack**: ETX only measures whether a single
radio hop's packets get a link-layer acknowledgement. Node 6's attack drops
packets *after* they're already successfully received over the radio and
acknowledged — at the IP forwarding step, one layer above where ETX is
measured. This project's own captured data confirms it:
`results/csv/etx_samples_adaptive.csv` shows node 6's ETX staying in a
normal 128–137 range (≈1.0–1.07) throughout the entire attack. **This is
exactly why a brand-new detection mechanism (the trust engine) was needed
— ETX genuinely cannot see this class of attack.**

`rpl-mrhof.c`'s `nbr_is_acceptable_parent()` function is where this project
plugs in:

```c
static int
nbr_is_acceptable_parent(rpl_nbr_t *nbr)
{
  uint16_t path_cost = nbr_path_cost(nbr);
  uint16_t etx = nbr_link_metric(nbr);
  ...
  int usable = nbr_has_usable_link(nbr) && path_cost <= MAX_PATH_COST;   // the original RPL/MRHOF check
  printf("ETX by=%u node=%u etx=%u pc=%u ok=%d\n", ...);                // logged for every candidate, every evaluation

  if(!usable) return 0;
  if(node_id != 0xFF && !rpl_trust_is_acceptable_parent(node_id)) return 0;   // <- the new trust check
  return 1;
}
```

So a neighbor must pass **both** the original ETX/path-cost sanity check
**and** the trust engine's verdict to be eligible as a parent. Before this
project, there was a third, much blunter check here instead of the trust
call: `if(lladdr->u8[7] == 6) return 0;` — a permanent, hardcoded blacklist
of node 6, with zero actual detection logic. That hardcoded check still
exists, intentionally, as `RPL_TRUST_MODE_STATIC` — kept only as a
comparison baseline (see §9).

## 5. How "evidence" reaches the trust engine

The trust engine never looks at radio packets directly — it only learns
from what `udp-client.c` tells it, through two calls:

```c
uint8_t rpl_trust_get_current_parent_id(void);           // "who is relaying for me right now?"
void    rpl_trust_report_outcome(uint8_t node_id, int success);  // "here's what happened"
```

Each client keeps two small variables: `pending_reply` (did my last
request get a reply yet?) and `pending_parent_id` (who was my parent when I
sent it?). Right before sending a **new** request, the code checks: did the
*previous* request ever get a reply?

```c
if(pending_reply) {
  rpl_trust_report_outcome(pending_parent_id, 0);   // no reply arrived in time -> report a MISS
  pending_reply = 0;
}
pending_parent_id = rpl_trust_get_current_parent_id();  // snapshot the CURRENT parent
pending_reply = 1;
... simple_udp_sendto(...) ...
```

And in the reply callback:

```c
if(pending_reply) {
  rpl_trust_report_outcome(pending_parent_id, 1);  // a reply DID arrive -> report a SUCCESS
  pending_reply = 0;
}
```

**Why this is the best evidence available here, and its real limits**: the
project investigated a true "watchdog" (a node secretly listening to
confirm its neighbor actually retransmitted a packet it was handed) and
found Contiki-NG's default MAC layer (CSMA) silently throws away any radio
frame not addressed to you — so a node literally cannot overhear its
neighbor's traffic without a custom radio driver, which was judged too
risky to build safely in this pass. Instead, each node uses its own
send-and-wait-for-echo pattern as an indirect signal. The catch: a missed
reply could mean the parent dropped it, **or** the echo got lost on the way
back, **or** the root was briefly busy, **or** the node's own radio link
had a bad moment. The trust engine (§7) is built entirely around managing
that uncertainty honestly, rather than pretending it isn't there.

## 6. The trust engine — data it keeps, per neighbor

File: `os/net/routing/rpl-lite/rpl-trust.c`. For every neighbor node it has
ever heard about, it keeps:

| Field | Meaning |
|---|---|
| `trust` | integer score, 0 (fully distrusted) to 100 (fully trusted), starts at **70** |
| `state` | one of the 5 states (§8) |
| `window_outcomes`, `window_fails` | how many send/reply results have been collected so far this "round", and how many of those were misses |
| `good_window_streak` | how many good rounds in a row |
| `total_bad_windows` | how many bad rounds this node has ever had (lifetime, used to require *multiple* pieces of evidence before excluding anyone) |
| `probation_good_windows` | good rounds counted specifically while on probation |
| `state_since`, `last_probe` | timestamps, used for the dwell-time and probing rules |

This table is a brand-new, separate data structure — it is deliberately
**not** stored inside RPL's existing neighbor table, because that table
wipes a node's memory (via C's `memset`) every time the node is temporarily
dropped and re-added (e.g. after a brief signal loss). If trust lived
there, a node could "launder" a bad reputation just by dropping off the
network for a moment and rejoining.

### Why evidence is grouped into "windows" of 10

The very first version of this engine reacted to *individual* missed
replies (specifically, 2 misses in a row). Testing it against the real 20%
attack showed this doesn't work: with only a 1-in-5 chance of any single
packet being dropped, two drops *in a row* is rare (about 1-in-25), so the
occasional isolated miss gets outweighed by the much more frequent
individual successes, and trust actually drifts *upward* overall — the
attack was never detected. The fix was to stop judging single events and
instead judge the **rate** over a batch of 10 outcomes:

```c
fail_rate_pct = 100 * window_fails / 10;          // what % of the last 10 attempts failed?
good_window   = fail_rate_pct <= 10;              // 10% or less is treated as "normal noise"
```

A window only closes (and only then can trust change) once 10 outcomes
have been collected — a single bad reply never moves anything by itself.

## 7. The trust score formula (exact)

Computed once, when a window of 10 closes:

**Confidence** — how much to trust this particular piece of evidence:

```c
confidence = LOW (30)     if the link's ETX is unusually high (> 320, i.e. "noisy link"),
                           or the reporting node is more than 3 hops from the root
           = MEDIUM (60)  otherwise
```

(`HIGH = 100` exists in the code as a constant but is never actually
produced — it's reserved for a future real watchdog, which could report
with much higher certainty than this indirect method.)

The second condition (hop distance) was added after testing revealed a real
bug: a node 3+ hops from the root was blaming its own innocent parent for
problems actually caused by node 6 further up the chain, because end-to-end
evidence can't tell *which* hop on a multi-hop path actually failed. Nodes
far from the root now get discounted confidence as a direct, disclosed
response to that limitation — not a cover-up of it.

**Trust update**:

```c
good window, not on probation:  trust += (4  * confidence) / 100     // +2 at MEDIUM, +1 at LOW
good window, while on probation: trust += (3  * confidence) / 100    // +1 at MEDIUM,  0 at LOW
bad window (either case):       trust -= (15 * confidence) / 100     // -9 at MEDIUM, -4 at LOW
trust = clamp(trust, 0, 100)
```

Notice the asymmetry: losing trust (`15`) happens about **3.75x faster**
than gaining it back (`4`) at the same confidence — a deliberate design
choice (misbehavior should cost more than good behavior earns back) coded
directly as the ratio between these two numbers.

## 8. The five states and exactly what moves between them

```
            bad window                    trust < threshold
            (any 1 window)                AND >= 3 bad windows total
  NORMAL ───────────────────► SUSPECT ───────────────────────────► EXCLUDED
    ▲                            │                                    │  ▲
    │      3 good windows        │                                    │  │ 1 bad window
    └────────────────────────────┘                     dwell >=30s    │  │ (immediate,
                                                         AND trust     │  │  no soft step)
                                                         margin OK     ▼  │
                                                                   PROBATION
                                                                        │
                                                         3 good windows on probation
                                                         AND trust margin OK
                                                                        ▼
                                                                   RECOVERED
```

- **NORMAL** — default, trusted, eligible as a parent.
- **SUSPECT** — one bad window happened; still eligible as a parent while
  being watched more closely. Falls back to NORMAL after 3 good windows in
  a row, or escalates to EXCLUDED if enough bad evidence piles up.
- **EXCLUDED** — this project's RPL routing code will refuse to pick this
  node as anyone's parent (in `ADAPTIVE` mode — see §9). Reached only once
  **both** conditions are true at the same time: trust has actually fallen
  below the current threshold, **and** at least 3 separate bad windows have
  been recorded over this node's lifetime (so one unlucky batch can't
  exclude someone — see §10 for why "3" and "threshold" specifically).
- **PROBATION** — a cautious re-trial period for a formerly excluded node,
  entered only once it has dwelled excluded for 30+ seconds **and** has
  rebuilt enough trust margin through real good windows (not a timer
  alone). Still not a full parent yet; one bad window here sends it
  straight back to EXCLUDED, no second chances mid-probation.
- **RECOVERED** — fully reinstated after 3 good windows *while on
  probation* and enough trust margin. Functionally equal to NORMAL for
  routing purposes, but kept as a separately-labeled state so the logs can
  show "this node was excluded and genuinely earned its way back" instead
  of looking identical to a node that was never flagged.

## 9. Prevention — three modes, compared honestly

`rpl_trust_is_acceptable_parent()` is called from MRHOF and behaves
differently depending on a compile-time setting
(`RPL_TRUST_CONF_MITIGATION_MODE`, default `ADAPTIVE`):

| Mode | What happens |
|---|---|
| `NONE` (0) | Always says "yes, acceptable" — the trust engine still runs and logs in the background, but nothing is ever actually blocked. This is the true unmitigated-attack baseline. |
| `STATIC` (1) | Hardcoded: reject node 6, always, from the very first second — regardless of whether it's actually misbehaving. This is **not detection** — it's an oracle that already knows the answer. It's kept only as a best-case comparison point, and the log line it prints says so explicitly ("static legacy mode, not trust-based detection"). |
| `ADAPTIVE` (2) | The real contribution of this project: reject a node only once its own `EXCLUDED` state (built from real evidence) says so. |

This is why the measured results (§11) show the static mode achieving
nearly perfect delivery — it isn't "better at detecting", it never had to
detect anything, it simply never allowed node 6 to be a relay for anyone
from the start. The adaptive mode has to spend real time (tens of seconds,
measured in this project's logs) accumulating evidence before it can act,
which is the price of actually detecting rather than assuming.

### The probing mechanism (why recovery can even be tested)

Once a node is `EXCLUDED`, normal RPL routing will never pick it as a
parent again — meaning nobody would ever send traffic through it again,
meaning no new evidence about it could ever arrive, meaning recovery would
be permanently impossible by construction. To avoid that dead end, every 60
seconds the excluded node is treated as "acceptable" again for a brief
2-second window. If, during that window, it's still genuinely the best
routing option for some node (lowest path cost), that node may re-select it
and generate fresh evidence; if a better alternate parent already exists,
RPL's own stability rules usually keep that alternate instead (confirmed in
this project's logs — see §12).

## 10. The dynamic (adaptive) threshold

A node is excluded when its trust drops below `active_threshold` — but that
threshold itself moves, within bounds `[35, 60]`, based on how *reliable*
the evidence being collected lately has been overall (not based on any one
node's behavior):

```c
confidence_ema = confidence_ema + (confidence - confidence_ema) / 4   // smoothed average, updates a little each window
target = 35 + confidence_ema * (60 - 35) / 100                        // map that average onto [35, 60]
active_threshold moves toward target by at most 2 points per update   // never jumps
```

If evidence has recently been mostly MEDIUM confidence (confidence_ema near
60), the threshold drifts toward the stricter end (60) — the network is
"seeing clearly", so it's safe to be decisive. If evidence has recently
been mostly LOW confidence (lots of noisy links or deep-tree reports), the
threshold relaxes toward 35 — be more forgiving, since the available
evidence is less trustworthy right now. This computation uses confidence
values gathered from **every** node's evidence, not just one node's —
specifically so a single attacker, who only controls its own behavior,
cannot manipulate the shared threshold in its own favor.

## 11. How the Python scripts turn raw logs into the numbers and graphs

### `metrices/metrics.py`

Takes one simulation log file and counts plain text patterns:

```python
if "PACKET SENT" in line:                              sent += 1
if "CLIENT NODE" in line and "RECEIVED RESPONSE" in line: received += 1
m = re.search(r'Packet Size\s*:\s*(\d+)', line)         # adds up bytes sent
```

Then it computes:

```python
packet_loss = sent - received
pdr = received / sent * 100
throughput = total_bytes / simulation_time    # simulation_time now comes from argv[2] if given, else 100.0
```

and writes those six numbers to `results.csv`. (The `simulation_time`
argument was added in this project — the original script hardcoded `100.0`
seconds, which would have silently produced an 18x-too-high throughput
number for this project's 1800-second runs; passing the real duration as a
second command-line argument fixes that without changing the script's
behavior for anyone who calls it the old way.)

### `final_graphs.py` (original) / the `results/graphs/` generation (this project)

Reads a CSV with one row per scenario and draws four `matplotlib` bar
charts: PDR, packet loss, throughput, and sent-vs-received side by side.
This project generated `results/csv/comparison_summary.csv` in the same
column format as the original script expects, and used the same plotting
logic (bar charts, same four metrics) to produce the four PNGs in
`results/graphs/` — so the graphs you see are a direct, literal rendering
of the numbers in that CSV. (Verified by hand: every bar's height matches
its row's number.)

## 12. What was actually observed happening, in order, during the main test run

From `results/csv/state_transitions_adaptive.csv` (a real run, not a
hypothetical):

1. `t=17103ms` — node 10 sees its first bad window involving node 6 → node
   6 enters **SUSPECT** (from node 10's point of view).
2. `t=17783ms` — node 9 independently also flags node 6 as **SUSPECT**.
3. `t=55983ms` — node 10 has now accumulated 4 bad windows and node 6's
   trust (44) has dropped below node 10's active threshold (48) → node 6
   becomes **EXCLUDED**, from node 10's perspective. ("Detection latency"
   here: 55983 − 17103 = 38880ms ≈ **39 seconds**.)
4. `t=126405ms` — node 8 independently reaches the same conclusion
   (**EXCLUDED**) about node 6, about 66 seconds after its own first
   suspicion.
5. Over the rest of the run, node 6 gets brief "probe" windows (every 60s)
   but — confirmed by the logs — never actually gets re-selected as a real
   parent by either node again, so it never progresses to **PROBATION** or
   **RECOVERED**. See the README's "Recovery: implemented but not observed
   completing" section for why, and why that is reported honestly rather
   than glossed over.

**One important subtlety, also worth being able to explain**: each node
keeps its *own* independent opinion about node 6. Node 10 and node 9 and
node 8 each run their own copy of this whole trust engine and reach their
own conclusions from their own observations — there is no shared "global"
trust score. This matches how a real distributed network has to work (no
node can read another node's memory), and it's why the logs show multiple,
separate `EXCLUDED` events for the same target node, from different
reporters, at different times.
