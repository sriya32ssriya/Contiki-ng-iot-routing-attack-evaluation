# Report Validation Checklist — PROJECT_REPORT.docx

Checked against the actual implementation and results on 2026-10-21.

## Verified implementation details
- [x] Topology: 15 motes (1 root + 14 clients), confirmed by `grep -c "<id>" real_attack.csc` = 15. (An earlier draft of README.md/REPORT.md incorrectly said "16-mote / 1 root + 15 clients" — this has now been corrected in README.md, REPORT.md, `results/csv/final_comparison_table.csv`, and `results/report/comparison_table.md`, and the report text uses "fifteen-mote (one root and fourteen clients)" throughout.)
- [x] Attack mechanism description (IP-forwarding layer, node 6, ~20% drop, only triggers when relaying another node's packet) matches `os/net/ipv6/uip6.c`.
- [x] Trust engine description (windows of 10 outcomes, asymmetric update, five states, adaptive threshold within bounds, hop-depth/ETX confidence discount) matches `os/net/routing/rpl-lite/rpl-trust.{c,h}`.
- [x] Evidence source is described as indirect UDP echo evidence, explicitly **not** a radio-level watchdog, with the CSMA/custom-MAC limitation stated — matches `rpl-trust.c`'s own documented limitation and `CODE_EXPLANATION.md` §5.
- [x] Static blacklist is described only as an oracle-style reference, never as autonomous detection — matches `rpl_trust_is_acceptable_parent()`'s `STATIC` mode, which is a hardcoded node-ID check with no trust logic.
- [x] Recovery (PROBATION/RECOVERED) is explicitly reported as implemented but **not observed to complete**, with the reason given (RPL parent-switch hysteresis) — matches the confirmed finding in `README.md` / `REPORT.md`, re-checked directly against `results/csv/state_transitions_adaptive.csv` for this report (no PROBATION/RECOVERED rows present).
- [x] Black-hole scenario is described as a separate, narrower, application-layer test, not merged into the main selective-forwarding result.

## Verified numbers
All of the following were re-checked directly against `results/csv/final_comparison_table.csv` and `results/csv/state_transitions_adaptive.csv` while writing this report (not copied blind from an earlier document):
- [x] Baseline: 2468 sent / 2406 received / 62 loss / 97.49% PDR / 0 attack drops.
- [x] No mitigation: 2469 / 2262 / 207 / 91.62% / 152 attack drops.
- [x] Adaptive trust: 2469 / 2337 / 132 / 94.65% / 64 attack drops.
- [x] Static blacklist: 2468 / 2453 / 15 / 99.39% / 0 attack drops.
- [x] State transitions for node 6: node 10 SUSPECT at 17103 ms, node 9 SUSPECT at 17783 ms, node 10 EXCLUDED at 55983 ms (38.9 s detection latency), node 8 SUSPECT at 60854 ms, node 8 EXCLUDED at 126405 ms (65.6 s detection latency) — all four timestamps read directly from `state_transitions_adaptive.csv`, not estimated.
- [x] Black-hole scenario PDR (90.12%) matches `results/csv/blackhole_fixed.csv`.

## Formulas
- [x] Only PDR and packet-loss formulas are given as equations, per the user's latest instruction to simplify; the trust-update mechanism and adaptive-threshold behaviour are explained in words, not as numeric formulas, and no equation in the report was invented — both match the logic in `rpl-trust.c` even though the exact internal constants are not quoted.

## Content restrictions (per latest instruction)
- [x] No graphs or figures are embedded in `PROJECT_REPORT.docx` (including no combined-detection graph), as explicitly requested in the final revision of the instructions.
- [x] No source code listings, pseudocode, or shell/Python snippets appear anywhere in the report.
- [x] Standalone graphs in `results/graphs/` were not modified, deleted, or regenerated as part of this step.

## References
- [x] All 10 references are real, published works (IETF RFCs for RPL/6LoWPAN/MRHOF, and peer-reviewed papers on WSN routing attacks and RPL trust-based mitigation) that I am confident exist and are correctly attributed from training knowledge. No title, author, venue, or year was invented. Full bibliographic detail (exact page numbers, DOIs) was not independently re-verified against a live database in this offline environment — if exact precision is required for submission, cross-check each entry against the IETF RFC repository or the publisher's page before final submission.

## Formatting
- [x] Times New Roman used throughout (title 16pt bold centered, section headings 12pt bold, subsection headings 11pt bold, body 10pt justified).
- [x] Page numbers inserted in the footer (Word page-number field, renders correctly when opened in Word/LibreOffice).
- [x] Numbered sections (1–8) and one numbered, captioned table.

## Known gaps (stated honestly, not hidden)
- **Page count was not verified against an actual rendering engine.** No PDF converter (LibreOffice, unoconv, pandoc) is installed in this environment, and installing one requires `sudo` (interactive password), which I cannot provide. A word-count-based estimate (~3,800 words of body text across 8 sections plus one table and 10 references) suggests the document is close to, and may slightly exceed, the requested 7–8 pages, but this has not been confirmed by opening the file.
- **PROJECT_REPORT.pdf was not generated** for the same reason. To produce it and get an exact page count, run, after installing LibreOffice (`sudo apt-get install -y libreoffice`):
  ```
  soffice --headless --convert-to pdf --outdir /home/sriya/contiki-ng/tools/myproject /home/sriya/contiki-ng/tools/myproject/PROJECT_REPORT.docx
  ```
  I can run this myself and re-check pagination/formatting once LibreOffice is installed.
- The document has not been opened in Word/LibreOffice to visually inspect for orphaned headings, awkward page breaks, or table splitting across pages — only `python-docx`'s object model was checked (paragraph/table counts), which cannot detect visual layout issues.
