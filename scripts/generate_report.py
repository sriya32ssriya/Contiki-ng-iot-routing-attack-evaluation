#!/usr/bin/env python3
"""
Generates PROJECT_REPORT.docx for tools/myproject using python-docx.
Per the user's latest instruction: no graphs embedded in this report, no
combined-detection graph, simple formulas only (PDR, packet loss, trust
update explained in words), no source-code listings. All numbers below are
copied from results/csv/final_comparison_table.csv and
results/csv/state_transitions_adaptive.csv, or from the formulas actually
implemented in os/net/routing/rpl-lite/rpl-trust.{c,h} -- nothing here is
invented. Standalone graphs in results/graphs/ are left untouched.
Run from tools/myproject/.
"""
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = "Times New Roman"
doc = Document()

style = doc.styles["Normal"]
style.font.name = FONT
style.font.size = Pt(10)
rpr = style.element.get_or_add_rPr()
rFonts = rpr.find(qn('w:rFonts'))
if rFonts is None:
    rFonts = OxmlElement('w:rFonts')
    rpr.append(rFonts)
rFonts.set(qn('w:eastAsia'), FONT)

for sec in doc.sections:
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)

table_counter = [0]

def add_page_number_footer():
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin')
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = "PAGE"
    f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'end')
    run._r.append(f1); run._r.append(it); run._r.append(f2)
    run.font.name = FONT
    run.font.size = Pt(9)

def set_run_font(run, size=10, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), FONT)
    rFonts.set(qn('w:hAnsi'), FONT)
    rFonts.set(qn('w:eastAsia'), FONT)

def para(text="", size=10, bold=False, italic=False, align=None, space_after=6, space_before=0):
    p = doc.add_paragraph()
    p.alignment = align if align is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.line_spacing = 1.15
    if text:
        run = p.add_run(text)
        set_run_font(run, size, bold, italic)
    return p

def heading1(num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(f"{num}. {text}")
    set_run_font(run, 12, bold=True)
    return p

def heading2(num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(f"{num} {text}")
    set_run_font(run, 11, bold=True)
    return p

def equation(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    set_run_font(run, 10, italic=True)
    return p

def make_table(headers, rows, caption):
    table_counter[0] += 1
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(8)
    run = cap.add_run(f"Table {table_counter[0]}. {caption}")
    set_run_font(run, 9, bold=True)

    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Table Grid"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        p = hdr[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        set_run_font(run, 8.5, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(val))
            set_run_font(run, 8.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return table_counter[0]

# =====================================================================
# TITLE PAGE
# =====================================================================
for _ in range(3):
    doc.add_paragraph()

t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = t.add_run("Detection and Prevention of Selective Forwarding and\n"
                "Black Hole Attacks in RPL-Based 6LoWPAN IoT Networks\n"
                "Using Adaptive Trust Management")
set_run_font(run, 16, bold=True)
t.paragraph_format.space_after = Pt(30)

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = sub.add_run("An Undergraduate Project Report")
set_run_font(run, 12, italic=True)
sub.paragraph_format.space_after = Pt(60)

for label in ["Student Name: [Your Name]",
              "Register Number: [Your Register Number]",
              "Department: [Your Department]",
              "Institution: [Your Institution]",
              "Project Guide: [Guide Name]",
              "Academic Year: [Academic Year]"]:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(label)
    set_run_font(run, 11)
    p.paragraph_format.space_after = Pt(8)

doc.add_page_break()
add_page_number_footer()

# =====================================================================
# 1. ABSTRACT
# =====================================================================
heading1(1, "Abstract")
para(
"This project studies a selective-forwarding attack in an RPL-based 6LoWPAN network and evaluates an "
"adaptive trust-based mechanism built to detect and reduce the damage caused by it, without knowing in "
"advance which node is malicious. A fifteen-mote network (one root and fourteen clients) was simulated "
"in Cooja using Contiki-NG's RPL-lite stack. One client, node 6, was configured to drop about 20% of "
"the packets it is asked to forward for other nodes at the IP layer. A trust engine was added inside "
"RPL's objective function (MRHOF): every node keeps a trust score for its neighbours, built from "
"indirect UDP echo evidence, and moves a suspicious neighbour through a five-state process (NORMAL, "
"SUSPECT, EXCLUDED, PROBATION, RECOVERED) before rejecting it as a routing parent. A threshold that "
"adapts within fixed bounds, separate from the trust score itself, decides when a node's trust is low "
"enough to exclude it. Four scenarios were run on the same topology, duration, and random seed: no "
"attack, attack with no mitigation, attack with adaptive trust, and attack with a static blacklist used "
"only as a reference point. The adaptive mechanism improved packet delivery ratio (PDR) from 91.62% "
"(unmitigated attack) to 94.65%, and reduced the number of actual forwarding-drop events from 152 to "
"64, with no confirmed false exclusion of an honest node. Detection took between about 39 and 66 "
"seconds in the reported run. The static blacklist, which already knows the attacker in advance, "
"reached 99.39% PDR, but this is a best-case reference, not a measure of detection quality. A separate, "
"simpler black-hole test scenario was also implemented and evaluated, and is reported separately from "
"the main result. The report also states honestly where the project falls short: full recovery of an "
"excluded node was never observed to complete, and the evidence used for detection is indirect (missing "
"UDP replies), not a true radio-level watchdog."
)

doc.add_page_break()

# =====================================================================
# 2. INTRODUCTION
# =====================================================================
heading1(2, "Introduction")
para(
"The Internet of Things (IoT) connects a large number of small, battery-powered devices that usually "
"have limited memory, processing power, and radio range. 6LoWPAN allows these constrained devices to "
"use IPv6 by compressing packet headers so that they fit over low-power radios such as IEEE 802.15.4 "
"[4], [5]. Because most devices cannot reach a central gateway directly, packets usually travel through "
"several intermediate devices before reaching their destination. RPL (Routing Protocol for Low-Power "
"and Lossy Networks) is the standard routing protocol used to build this multi-hop structure. It "
"organises the network as a tree rooted at a sink node, and every node picks a preferred parent based "
"on a routing cost, most commonly computed using the Expected Transmission Count (ETX) metric through "
"the Minimum Rank with Hysteresis Objective Function, or MRHOF [1], [2], [3]."
)
para(
"Because every intermediate node in this tree is trusted to forward traffic faithfully, RPL networks "
"are exposed to attacks where a compromised relay does not forward all of the traffic it receives. This "
"project focuses on selective forwarding, where the malicious node drops only a fraction of the packets "
"it relays, which makes it harder to notice than a node that stops working completely [6]."
)

heading1(3, "Problem Statement")
para(
"In a selective-forwarding attack, a malicious node silently drops some of the packets it is supposed "
"to relay instead of forwarding them, while a black-hole attacker drops nearly all or all such packets. "
"Both attacks reduce packet delivery and increase packet loss for every node whose traffic passes "
"through the attacker, without necessarily breaking the network at the radio level. This matters "
"because the malicious node can still send and receive link-layer acknowledgements normally; the drop "
"happens one layer above, at the IP forwarding step. As a result, the ETX metric that RPL already uses "
"for choosing a parent does not change when this attack is active, since ETX is based on link-layer "
"delivery statistics, not end-to-end application delivery. A routing protocol that only looks at ETX "
"cannot see this attack at all."
)
para(
"This project investigates whether a trust score built from end-to-end delivery evidence, rather than "
"link-layer statistics, can detect a selective-forwarding attacker, and whether RPL's own "
"parent-selection logic can then be used to stop routing traffic through that node, without knowing in "
"advance which node is malicious. The project implements and evaluates this mechanism for the "
"selective-forwarding case in detail; a simpler, separate black-hole scenario is also implemented and "
"evaluated, but to a smaller extent, and the two results are not merged together. The objectives of the "
"project are to build the attack itself in a controllable way, to design a trust score and a five-state "
"detection process around indirect delivery evidence, to connect this into RPL's parent-selection logic "
"so that an excluded node is actually avoided rather than only logged, and to measure the real effect "
"of this mechanism on packet delivery using actual Cooja simulation logs, compared against an "
"unmitigated baseline and a static oracle-style blacklist."
)

doc.add_page_break()

# =====================================================================
# 4. METHODOLOGY
# =====================================================================
heading1(4, "Methodology")
para(
"The network used for this project consists of fifteen simulated Sky motes in Cooja: one DODAG root "
"acting as a UDP server, and fourteen client motes that each send a periodic UDP request toward the "
"root and expect an echoed reply back. RPL-lite builds the routing tree automatically, with each client "
"periodically receiving routing advertisements from its neighbours, computing a routing cost through "
"each candidate neighbour using ETX and MRHOF, and picking the neighbour with the lowest cost as its "
"preferred parent. Node 6 is positioned so that several other client motes naturally use it as their "
"next hop toward the root, which makes it a realistic relay for the attack to target."
)
para(
"Node 6 is configured to behave as a selective-forwarding attacker: when it is asked to relay a packet "
"on behalf of another node, it drops that packet about 20% of the time instead of forwarding it, while "
"continuing to behave normally in every other respect, including its own outgoing traffic. Because the "
"packet is dropped after it has already been received and acknowledged at the radio level, this attack "
"does not change the ETX value that RPL measures for node 6, which is the central reason a new "
"detection approach is needed."
)
para(
"Detection is built around the UDP request-and-reply pattern that the client motes already use. Each "
"client keeps track of whether its previous request received a reply before it sends its next request, "
"and which neighbour was its preferred parent at the time that request was sent. This is real, locally "
"collected evidence at each node, but it is indirect: a missing reply could mean the parent dropped the "
"packet, but it could equally mean the reply was lost on its way back, or the node's own radio link had "
"a brief problem. This is an important limitation of the project and is explained further in Section 7. "
"Individual missing replies are not acted on immediately. Instead, observations are grouped into "
"windows of ten outcomes each, and a window is only judged once it is complete, as a credible failure "
"or a credible success, based on how many of the ten outcomes were missed."
)
para(
"Based on this evidence, each node keeps a trust score, between 0 and 100, for every neighbour it has "
"observed. A neighbour's trust score goes down when a window is judged a credible failure, and goes up "
"when a window is judged a credible success, with failures reducing trust noticeably faster than "
"successes rebuild it, so that repeated bad behaviour is penalised more quickly than it can be repaired. "
"As trust changes, a neighbour moves through five possible states: NORMAL, which is the default trusted "
"state; SUSPECT, entered after the first credible failure window; EXCLUDED, reached once trust has "
"fallen below a threshold and enough failure evidence has built up; PROBATION, a cautious trial period "
"for a node that is trying to earn its way back after being excluded; and RECOVERED, reached only after "
"a node has shown enough good behaviour during probation. The threshold used to decide when a node's "
"trust is low enough for exclusion is not fixed; it adjusts gradually, within set upper and lower "
"bounds, based on how reliable the evidence collected across the network has been recently, rather than "
"reacting to any one node's behaviour alone."
)
para(
"Once a neighbour reaches the EXCLUDED state, RPL's own parent-selection logic is modified to reject it "
"as a routing parent, in addition to the normal routing-cost check it already performs. This means "
"exclusion is an actual change in routing behaviour, not just a message written to a log file. "
"Performance is measured using packets sent, packets received, packet loss, packet delivery ratio, "
"throughput, the number of real attack-drop events recorded in the simulation log, and detection "
"latency, which is the time between a node first suspecting its neighbour and that neighbour actually "
"being excluded."
)

doc.add_page_break()

# =====================================================================
# 5. IMPLEMENTATION
# =====================================================================
heading1(5, "Implementation")
para(
"The project is built on top of Contiki-NG's RPL-lite routing stack and simulated using Cooja with the "
"MSPSim emulator, targeting the Sky mote platform. Simulations were run in Cooja's headless test-runner "
"mode, which replays a simulation deterministically from a fixed random seed and produces the same mote "
"console output that would appear in the normal Log Listener window. All results reported in this "
"document come from this mode, using the same topology, the same 1800-second simulated duration, and "
"the same random seed across every scenario, so that the only difference between runs is whether the "
"attack and the mitigation are active."
)
para(
"The selective-forwarding attack and the mitigation mode are both chosen using build-time configuration, "
"rather than by editing the application source code separately for each scenario. This made it possible "
"to build a genuinely attack-free baseline, an attack with no mitigation, and an attack with the trust "
"mechanism active, all from the same underlying source files, which is what makes the comparison in "
"Section 6 a fair one. The attack itself is implemented at the point in the IPv6 forwarding code where a "
"node decides whether to relay a packet that is not addressed to it; the random drop decision is only "
"made at that point, so the attack never affects node 6's own outgoing requests."
)
para(
"A separate, simpler black-hole scenario was also implemented, at the application layer rather than the "
"IP-forwarding layer: in that scenario, node 6 itself refuses to send its own outgoing requests, instead "
"of selectively dropping packets it is relaying for others. This is a different and less representative "
"test of a true network-layer black hole, and its results, given in Section 6, should be read as a "
"separate, smaller piece of evidence rather than as full validation of black-hole detection."
)
para(
"The trust engine is implemented as a small addition to RPL's existing MRHOF objective function. For "
"every neighbour it tracks, a node keeps a trust score, a current state out of the five described in "
"Section 4, and a short window of recent outcomes. When a window of ten outcomes completes, the node "
"decides whether it was a credible success or a credible failure, updates the trust score accordingly, "
"and checks whether a state change is needed. A true radio-level watchdog, where a node overhears "
"whether its neighbour actually retransmits a packet it was handed, was considered for this project but "
"was found to be impractical to build safely within its scope: Contiki-NG's default medium-access layer "
"discards radio frames that are not addressed to the local node before the network layer ever receives "
"them, so a working watchdog would need a custom medium-access layer, which was judged too large a "
"change to implement and validate reliably here. The implementation therefore relies on the indirect UDP "
"echo evidence described in Section 4, and this should be kept in mind when reading the results."
)
para(
"When a neighbour is excluded, the implementation does not leave it excluded forever without any way "
"back. Roughly once a minute, an excluded neighbour is briefly treated as acceptable again for a few "
"seconds, purely so that it has a chance to prove itself again; a node only actually switches back to "
"using it as a parent during this window if it is still genuinely its best routing option. This is what "
"makes the PROBATION and RECOVERED states reachable in principle, although, as reported in Section 6, "
"this was not observed to complete in the experiments run for this project."
)

doc.add_page_break()

# =====================================================================
# 6. RESULTS AND DISCUSSION
# =====================================================================
heading1(6, "Results and Discussion")
para(
"Four scenarios were run on the identical fifteen-mote topology, for the same 1800-second simulated "
"duration and the same random seed: a true baseline with the attack switched off, the attack with no "
"mitigation, the attack with the adaptive trust mechanism active, and the attack with a static blacklist "
"that already knows node 6 is the attacker from the very first second of the simulation. This last "
"scenario is not a trust-based detector; it is included only as a best-case reference point, since it "
"has no detection delay at all and cannot be fooled, which is not a fair standard to compare a real "
"detection mechanism against. All figures below were checked directly against the simulation logs and "
"the corresponding CSV result files generated from them."
)
make_table(
    ["Scenario", "Sent", "Received", "Loss", "PDR (%)", "Attack Drops", "Detection Latency"],
    [
        ["Baseline (attack off)", "2468", "2406", "62", "97.49", "0", "N/A – no attack present"],
        ["Attack, no mitigation", "2469", "2262", "207", "91.62", "152", "N/A – not enforced in this mode"],
        ["Attack, adaptive trust", "2469", "2337", "132", "94.65", "64", "~39 s and ~66 s (two independent nodes)"],
        ["Attack, static blacklist", "2468", "2453", "15", "99.39", "0", "N/A – no detection logic; node 6 blocked from the start"],
    ],
    "Final Results Comparison Across the Four Evaluated Scenarios (1800 s, same seed, same topology).",
)
para(
"Packet delivery ratio and packet loss are calculated in the usual way, directly from the counted "
"events in each scenario's log:"
)
equation("PDR (%) = (Packets Received / Packets Sent) x 100")
equation("Packet Loss = Packets Sent − Packets Received")
para(
"Without any mitigation, the attack reduces PDR from the 97.49% baseline down to 91.62%, a drop of "
"5.87 percentage points, and 152 real attack-drop events are recorded in the log. With the adaptive "
"trust mechanism switched on, PDR recovers to 94.65%, meaning roughly half of the lost delivery (3.03 "
"of the 5.87 percentage points) is recovered, and the number of attack-drop events falls to 64, because "
"node 6 is excluded as a parent for part of the simulation once it is detected and therefore has fewer "
"opportunities to drop traffic. The static blacklist reaches 99.39%, slightly above even the clean "
"baseline, because it keeps node 6 out of the routing tree before it can cause any loss at all; the "
"small gap from 100% is just normal network behaviour such as route-formation delay, and is unrelated "
"to the attack. This scenario should be read as an upper bound on what is achievable with perfect, "
"instant knowledge of the attacker, not as proof that static blacklisting detects attacks better than "
"the adaptive mechanism, since it does not attempt detection at all."
)
para(
"A basic way to describe how the trust score itself is updated, without going into the exact internal "
"numbers, is that every neighbour starts with a medium level of trust, and this trust rises a small "
"amount after a window of mostly successful deliveries and falls by a larger amount after a window of "
"mostly failed deliveries. This asymmetry is intentional: it means a node that behaves badly loses "
"trust noticeably faster than a node that is simply unlucky with a few isolated losses, but a single bad "
"outcome on its own is never enough to change anything, since trust is only updated once a full window "
"of ten observations has completed. The threshold used to decide when trust is low enough for exclusion "
"moves slowly within fixed upper and lower limits, based on how reliable recent evidence across the "
"network has generally been, rather than being fixed at one number for the whole simulation or reacting "
"to a single node's behaviour."
)
para(
"In the reported adaptive-trust run, node 6 was independently flagged as SUSPECT by two different "
"neighbours: node 10 at about 17.1 seconds into the simulation, and node 9 at about 17.8 seconds. Node "
"10 then excluded node 6 at about 56.0 seconds, which is roughly 39 seconds after it first became "
"suspicious. A third node, node 8, became suspicious later, at about 60.9 seconds, and excluded node 6 "
"at about 126.4 seconds, about 66 seconds after its own first suspicion. These are separate, "
"independently reached decisions, not one shared verdict: in this implementation, each node keeps its "
"own trust information about its neighbours and reaches its own conclusion from its own observations, "
"which is how a real distributed network has to work, since no node can see another node's internal "
"state."
)
para(
"No PROBATION or RECOVERED transition was observed in this run, or in any of the other experiments "
"carried out for this project. The mechanism that gives an excluded node a short trial window to earn "
"its way back did activate several times during the simulation, but in each case the node that had "
"already found a different, reliable parent did not switch back to node 6 during that window, which is "
"the expected and correct behaviour of RPL's own parent-stability rules, not a flaw in the trust "
"mechanism. This project reports recovery as implemented, but not observed to complete, and does not "
"claim that full reinstatement was verified."
)
para(
"The separate, simpler black-hole scenario, where node 6 refuses to send its own outgoing packets "
"instead of dropping traffic it is relaying, reached 90.12% PDR with the same mitigation applied, with "
"no confirmed false exclusion of an honest node. This is an encouraging result, but it is a narrower "
"test than the main selective-forwarding evaluation: it was only run on this one topology and random "
"seed, and because it changes a different part of the code (the attacker's own outgoing traffic, not its "
"forwarding behaviour), it should not be read as full validation of black-hole detection in general."
)
para(
"Overall, the results show that grouping indirect, end-to-end delivery evidence into batches, rather "
"than reacting to single missed replies, is enough to detect a 20% selective-forwarding attack that "
"does not show up in ETX at all, and that turning this detection into an actual parent-selection "
"decision measurably improves packet delivery. The improvement is real but partial: detection still "
"takes around half a minute to a minute in this topology, during which the attack continues normally, "
"and the evidence used is indirect, so it cannot fully rule out other causes of a missing reply, such as "
"a lost return packet or a temporarily weak radio link. These limitations are discussed further in the "
"next section."
)

doc.add_page_break()

# =====================================================================
# 7. CONCLUSION AND FUTURE WORK
# =====================================================================
heading1(7, "Conclusion and Future Work")
para(
"This project implemented a selective-forwarding attack inside the IP forwarding layer of an RPL-based "
"6LoWPAN network, and built an adaptive trust mechanism that detects this attack using indirect UDP "
"delivery evidence and prevents further damage by excluding the suspicious node from RPL's "
"parent-selection process. The experiments, run on an identical topology and random seed across four "
"scenarios, showed that the attack reduces packet delivery by about 5.9 percentage points if left "
"unmitigated, that the adaptive trust mechanism recovers about half of this loss without any prior "
"knowledge of which node is malicious, and that a static, oracle-style blacklist can do better only "
"because it already knows the answer in advance. The project also confirmed, using its own ETX "
"measurements, that this particular attack does not show up in the ETX metric that RPL normally relies "
"on for parent selection, which is the main reason a separate detection mechanism was needed at all."
)
para(
"The project also has clear limitations, and these are stated here rather than left implicit. The "
"evidence used for detection is indirect: a missing UDP reply is treated as suspicious, but the project "
"cannot fully separate a dropped forward from an unrelated loss elsewhere on the path, since no "
"radio-level watchdog was implemented. Full recovery of an excluded node, through the PROBATION and "
"RECOVERED states, was never observed to complete in the topology tested, even though the individual "
"steps needed for it are implemented. The black-hole scenario was evaluated separately and more "
"narrowly than the main selective-forwarding case, and all results in this report come from a single "
"topology and a single random seed, so they should not be read as general performance guarantees across "
"other network layouts."
)
para(
"Several directions are suggested for future work. A more direct way to separate malicious drops from "
"ordinary wireless loss, such as a radio-level watchdog or acknowledgement-based forwarding check, would "
"reduce the project's current reliance on indirect evidence. Running the same experiments across "
"multiple random seeds and different network topologies would show how sensitive the results are to the "
"specific layout used here. Testing other attack intensities, beyond the 20% drop rate evaluated in this "
"project, and evaluating the black-hole scenario with the same depth as the selective-forwarding case, "
"would both broaden the evaluation. The probation and recovery process should be tested specifically in "
"a smaller topology where the excluded node is the only available parent, so that a full recovery cycle "
"can actually be observed and measured rather than assumed to work from its individual parts. Finally, "
"measuring the extra memory, processing, and message overhead that the trust mechanism adds on "
"constrained devices, and testing the approach on real or hardware-assisted IoT hardware rather than "
"only in simulation, would both be valuable next steps before this mechanism could be considered for "
"practical use."
)

doc.add_page_break()

# =====================================================================
# 8. REFERENCES
# =====================================================================
heading1(8, "References")
refs = [
'T. Winter, Ed., P. Thubert, Ed., A. Brandt, J. Hui, R. Kelsey, P. Levis, K. Pister, R. Struik, '
'J.-P. Vasseur, and R. Alexander, "RPL: IPv6 Routing Protocol for Low-Power and Lossy Networks," '
'RFC 6550, Internet Engineering Task Force (IETF), March 2012.',

'J. Vasseur, M. Kim, K. Pister, N. Dejean, and D. Barthel, "Routing Metrics Used for Path '
'Calculation in Low-Power and Lossy Networks," RFC 6551, IETF, March 2012.',

'O. Gnawali and P. Levis, "The Minimum Rank with Hysteresis Objective Function," RFC 6719, IETF, '
'September 2012.',

'G. Montenegro, N. Kushalnagar, J. Hui, and D. Culler, "Transmission of IPv6 Packets over IEEE '
'802.15.4 Networks," RFC 4944, IETF, September 2007.',

'J. Hui and P. Thubert, "Compression Format for IPv6 Datagrams over IEEE 802.15.4-Based '
'Networks," RFC 6282, IETF, September 2011.',

'C. Karlof and D. Wagner, "Secure routing in wireless sensor networks: Attacks and '
'countermeasures," Ad Hoc Networks, vol. 1, no. 2–3, pp. 293–315, 2003.',

'A. Le, J. Loo, A. Lasebae, A. Vinel, Y. Chen, and M. Chai, "The impact of rank attack on network '
'topology of routing protocol for low-power and lossy networks," IEEE Sensors Journal, vol. 13, '
'no. 10, pp. 3685–3692, 2013.',

'F. Ahmed and Y.-B. Ko, "Mitigation of black hole attacks in routing protocol for low power and '
'lossy networks," Security and Communication Networks, vol. 9, no. 18, pp. 5143–5154, 2016.',

'D. Airehrour, J. A. Gutierrez, and S. K. Ray, "SecTrust-RPL: A secure trust-aware RPL routing '
'protocol for Internet of Things," Future Generation Computer Systems, vol. 93, pp. 860–876, 2019.',

'F. Österlind, A. Dunkels, J. Eriksson, N. Finne, and T. Voigt, "Cross-level sensor network '
'simulation with COOJA," in Proc. 31st IEEE Conf. on Local Computer Networks (LCN), 2006, '
'pp. 641–648.',
]
for i, r in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.first_line_indent = Inches(-0.3)
    run = p.add_run(f"[{i}] {r}")
    set_run_font(run, 9.5)

print("Full report written OK")
doc.save("results/report/PROJECT_REPORT_partial.docx")
