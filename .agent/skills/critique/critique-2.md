# 🔴 CRITIQUE — Prof. [Guide]'s Markup

> **Paper:** "Edge-AI Automated Peripheral Blood Smear Analysis: A YOLOv8n Deployment on Raspberry Pi 4 for Resource-Constrained Haematology Screening"
>
> **Assumed venue:** IEEE conference (two-column, `IEEEtran` class, `10pt,conference`). If this is going somewhere else, tell me now before I audit the wrong template.

---

## Opening

No. I am not putting my name on this. Not today.

You have built something genuinely interesting — a \$275 microscope-Pi rig that counts white blood cells with moderate-to-good ICC — and then you wrapped it in a paper that will get desk-rejected on formatting alone, torpedo'd by Reviewer 2 on the RBC results, and laughed out of the room for citing "our advisor" in the body text of a published manuscript. *My* name. On a paper that thanks me in the methodology section like I'm a character in the story. Do you know what my rival down the corridor would do with that?

Let me be specific about what needs to happen before this leaves my inbox.

---

## Scorecard

| Cat. | Area | Grade | One-line reason |
|:----:|------|:-----:|-----------------|
| A | Contribution & novelty | C+ | Real contribution (dual-tier framework) but overclaimed and partially undelivered (OOD results missing) |
| B | Problem & motivation | B | Well-motivated, clear gap identified, but introduction wanders into too much hardware shopping |
| C | Related work | D+ | 15 references total, 5 with wrong BibTeX types, no classical baselines, nothing from 2023–2026 |
| D | Methodology | B− | Reproducible in principle; marred by unjustified hyperparameters and missing ablations |
| E | Experiments & results | D | RBC ICC = 0.112 presented as a feature not a bug; no OOD results; no INT8 measurements; no significance tests |
| F | Discussion & limitations | C | Honest about some problems, dishonest about others; no consolidated limitations section |
| G | Writing & language | C− | Mixed British/American (36 vs 8), "our advisor" in body text, overclaiming adjectives, tech-report style |
| H | Structure & IEEE conventions | D | "Acknowledgements" misspelled per IEEE, "Figure" not "Fig.", keywords not alphabetized, headings not small-caps Roman |
| I | Layout & typography | C | Coloured hyperlinks for B&W print, inconsistent figure widths, `\balance` unused, cannot fully verify without rendered PDF |
| J | Figures & tables | C− | No system diagram, no qualitative detections, 6 generated figures never included, RBC Bland-Altman is self-incriminating |
| K | Equations & math | B+ | Few equations, all correct; notation consistent |
| L | References | D | 5/15 wrong entry types, no DOIs, too few (15 for this scope), BCCD citation wrong |
| M | Integrity & risk | C | No ethics statement, no data availability, "released under open licence" with no URL |

---

## Findings

### A. Contribution and Novelty

**[FATAL] Contribution #4 (72-image OOD benchmark) is undelivered.** You list four contributions in Section I. Contribution #4 promises "a 72-image, independently hand-labelled out-of-distribution benchmark." Your `results.json` shows `n_clin = 0`. You evaluated zero clinical images. You mention this benchmark in the abstract, Section I, Section III-C, Section V-C — four separate locations — and present no results. A reviewer will read this as either incompetence or dishonesty. Neither is acceptable.

*Fix: run `paper_eval.py --clinical_dir data/clinical_72` with correct paths and add the results, or surgically remove every mention of the 72-image set. Every. Single. One.*

**[MAJOR] The "dual-tier" framework is the actual contribution — but you bury it.** The novel part of this work is not YOLOv8n (off-the-shelf) or Raspberry Pi (commodity hardware). It is the evaluation methodology: applying CLSI EP09c clinical method-comparison to an edge detector. This is stated in the contributions but never foregrounded in the title or abstract. The title reads like a deployment report.

**[MINOR] Is this really novel?** Applying an existing detector to an existing dataset and measuring standard metrics is, at best, a "systems paper." The dual-tier framework pushes it above that line, but only if the clinical-tier results are trustworthy — and the RBC results (§E below) undermine the entire framework.

---

### B. Problem and Motivation

**[MINOR] Introduction paragraph 1 has a cost range problem.** You write "\$30,000–\$200,000" for analysers. Citation needed for the upper bound. The Sysmex XN-9100 (the specific model you name) lists closer to \$100,000–\$150,000 depending on configuration. \$200,000 is a fully automated line (XN-9100 + SP-50 stainer-slidemaker). If you want \$200,000, cite a specific configuration.

**[NIT]** Section I, paragraph 2: "since at least 2017" — what happened in 2017? The citation is `liang2018`. Either cite the actual 2017 work or say 2018.

---

### C. Related Work

**[MAJOR] 15 references is anaemic for this scope.** You span clinical hematology, deep learning, edge deployment, quantisation, and clinical statistics. That is five sub-fields. Three references per sub-field is not a literature review; it is a gesture. A serious paper in this space has 25–40 references. Missing:

- CLSI EP09c standard document itself (you name-drop the framework throughout but never cite the actual standard)
- Any classical image-processing baseline (watershed segmentation, Hough circle detection, CellProfiler — these are the methods your system replaces and you never mention them)
- Any 2023–2026 blood cell detection work (YOLO11, RT-DETR, attention-based detectors)
- Any other Raspberry Pi medical imaging papers
- TinyML / MCUNet edge deployment literature
- Your own `weights/yolo26n.pt` suggests you tried YOLO26n — why is this not discussed?

**[MAJOR] The related work is a list, not an analysis.** "X did A. Y did B. Z did C. None did D." That is not positioning; that is a catalogue. Where is the table that directly compares your features against each prior method? Where is the sentence that says "Unlike [5] which required a Jetson Nano at 12W, our system runs on 3.4W because..."?

**[MINOR]** You cite Kc et al. [kc2021] for both YOLOv3 (mAP 0.82) and Faster R-CNN (mAP 0.78). Did they report these on the exact same BCCD split as yours? If the splits differ, these numbers are not comparable, and you must say so.

---

### D. Methodology

**[MAJOR] No justification for confidence threshold 0.25.** Hardcoded in `paper_eval.py`. Why 0.25 and not 0.15, 0.30, or 0.50? What is the threshold's effect on precision-recall trade-off for RBC? Given that RBC precision is 0.496, threshold tuning could be the single most impactful improvement. You never discuss this.

**[MAJOR] "Trained on an NVIDIA GPU" — which GPU?** Reproducibility requires the actual hardware. V100? A100? RTX 3060? Training time? Total GPU-hours? These are basic details.

**[MINOR]** Section III-B: "Model weights occupy 6.3 MB (FP32) / 3.2 MB (INT8), fitting comfortably in on-chip L3 cache." The RPi 4's Cortex-A72 has 1 MB shared L3 cache. 6.3 MB does not fit "comfortably" in 1 MB. This is factually wrong.

**[MINOR]** Section III-E, Tier 2: You list seven method-comparison statistics. That is impressive. You report Deming regression slope and intercept in `results.json` but omit them from Table II. The Deming slope for RBC is 0.876 — which tells a very different story from the P-B slope of 1.000. Cherry-picking which regression you display is a form of selective reporting.

**[NIT]** Section III-B: "Python 3.11," "ONNX Runtime 1.17," "OpenCV 4.8," "ReportLab (PDF report generation)" — version numbers and PDF-generation libraries are not methodology. They are a requirements.txt. Move to a footnote or supplementary.

---

### E. Experiments and Results — Where the Wheels Come Off

**[FATAL] RBC ICC = 0.112 and MAPE = 101% are unpublishable without proof of annotation error.** Let me say this plainly: your model produces 4,042 false positive RBC detections against 3,978 true positives. The FP/TP ratio is 1.016. More than half of all RBC detections are wrong. You then compute ICC between your inflated count and the annotation count and get 0.112 — "poor" by the very Koo & Li scale you cite.

You explain this as "ground-truth incompleteness": BCCD annotations miss many overlapping RBCs, so your high-recall model finds cells that were never labelled. This may well be true. **But you never prove it.** Where is the figure showing an example image with model detections overlaid on the ground-truth boxes, demonstrating that the "false positives" are real cells? Where is a manual recount of 10 images confirming the annotation is incomplete? You have the hypothesis but not the evidence.

Without that evidence, a reviewer reads ICC = 0.112 and concludes your model is broken. And they would be right to.

*Fix: either (a) manually recount 10–15 images and show the annotation is indeed incomplete, (b) apply border-exclusion and NMS tuning to reduce FP, or (c) restrict the clinical-comparison claim to WBC and Platelets and explicitly exclude RBC from the agreement analysis. Option (c) takes 15 minutes. Option (a) takes 2 hours and makes the paper genuinely strong.*

**[FATAL] "Better than human" claim has zero empirical support.** The abstract says: "positioning this system substantially above published human-labeller baselines." Section IV-C says the system "is expected to exceed typical human-versus-human inter-rater agreement."

You cite Rümke 1985 (a 41-year-old paper) for human ICC of 0.45–0.60. But Rümke studied the *differential leukocyte count* — classifying WBC subtypes into 5 categories out of 100 cells observed. Your task is *detecting and bounding-boxing individual WBCs in an image*. These are different tasks with different error profiles. The ICC numbers are not directly comparable.

Your `paper_eval.py` has a `--second_annotator_dir` flag specifically designed to measure human-vs-human agreement on the same images and same task. You left it empty. The script even prints: "THIS IS THE KEY TABLE for the 'better than a human' claim." The code is begging you to do the experiment. You refused.

*Fix: get a second annotator to label 20–30 images (3 hours), run the comparison, or rewrite every "better than human" sentence to say "approaches the upper range of published inter-rater ICC for differential counting, though direct comparison requires a paired inter-annotator study on the same task."*

**[FATAL] INT8 mAP is estimated.** Table III: "Ours (YOLOv8n INT8) ≈ 0.84." The ≈ symbol is an admission of laziness. You have the INT8 ONNX model. You have the test images. You have the evaluation script that supports ONNX. Run it. Report the actual number. This takes 10 minutes.

**[MAJOR] No ablation study.** What does mosaic augmentation contribute? What if you change confidence from 0.25 to 0.35? What about image size 416 vs 640? What about the effect of COCO pre-training? Without ablations, you cannot claim your design choices are justified.

**[MAJOR] Passing-Bablok slope = 1.000 for all three classes is degenerate.** WBC counts per image in BCCD are mostly 0 or 1 (mean = 1.02). Platelet counts are similarly small integers. When you compute Passing-Bablok on integer data with a range of 0–4, the pairwise slopes collapse to exact integer ratios and the median snaps to 1.0. This is a statistical artefact, not a meaningful result. You report it as "confirms no proportional bias." No. What it confirms is that P-B is the wrong test for your data distribution.

Meanwhile, your Deming slopes tell a different story:
- RBC: 0.876 (14% proportional under-estimation relative to reference)
- WBC: 1.149 (15% proportional over-estimation)
- Platelets: 1.012 (fine)

You compute these but hide them. A reviewer who checks `results.json` will find them.

*Fix: report Deming slopes alongside P-B, and note that P-B is unreliable for narrow-range integer data.*

**[MAJOR] WBC ICC 95% CI spans [0.38, 0.72].** You call this "moderate-to-good." The lower bound is 0.38 — firmly in the "poor" range. A reviewer will say: "The confidence interval includes poor agreement; the authors' characterisation is misleading." Say "moderate (95% CI: poor-to-good)."

**[MAJOR] Spearman ρ is computed but omitted from Table II.** You compute Spearman in `agreement_bundle()` and store it in `results.json` (RBC: 0.461, WBC: 0.583, Platelets: 0.843) but never report it. The Methodology section promises Spearman ρ as one of the seven statistics. Table II drops it silently. Either add a column or remove the promise.

**[MINOR] Single train/test split, single seed, no variance.** All numbers are point estimates. No cross-validation, no multi-seed runs, no standard deviations. A single unlucky split can shift mAP by ±0.03.

**[MINOR] No significance tests on SOTA comparison.** Table III: your mAP (0.856) vs YOLOv3 (0.82). Is this difference significant? You don't know.

---

### F. Discussion and Limitations

**[MAJOR] No consolidated "Limitations" subsection.** Limitations are scattered across three subsections. A dedicated "Limitations" subsection is increasingly expected and signals scientific maturity. Consolidate: single dataset, single split, no paired clinical reference, no second annotator, annotation incompleteness unproven, no RPi thermal profiling, English-only, single staining protocol.

**[MAJOR] Section V-B: "Our advisor correctly identified the core epistemological challenge."** I am going to say this once, and I want you to hear me: *you do not cite your project guide in a published paper*. This is not a thesis report. This is not a viva defence. This is a manuscript submitted for blind review. The phrase "our advisor" appears twice in the paper. A reviewer does not care who raised the question; they care about the answer. Rephrase to "A fundamental epistemological challenge in cross-modality validation is that..."

Do you understand how this looks? It looks like a student project. It looks like you wrote a thesis chapter and forgot to revise it for publication. It looks like my name is on an undergraduate report. Fix it now.

**[MINOR]** Section V-D claims "approximately 3.4 W under full load, enabling 6+ hours of operation on a 20 Wh battery pack." 20 Wh / 3.4 W = 5.88 hours, which rounds to "approximately 6 hours," not "6+ hours." Do not round in your favour on battery claims. Rural health workers will rely on this number.

---

### G. Writing and Language

**[MAJOR] British/American spelling inconsistency.** I counted: **36 British spellings** (haematology ×10, analyser ×6+, labelled, generalisation, normalised...) vs **8 American spellings** (hematology ×2, analyzer ×1, optimized ×1, color ×4). The title uses "Haematology" (British), the first sentence of the abstract uses "hematology" (American), then back to "haematology." This is not stylistic flexibility; it is sloppiness. IEEE house style uses American English. Pick American and do a global find-replace.

**[MAJOR] Abstract is 245 words.** IEEE conference abstracts should be 150–200 words. You are 25% over. The abstract front-loads system description and buries the key ICC numbers in sentence 7 of 8. Restructure: problem (2 sentences) → method (2 sentences) → key results (2 sentences) → significance (1 sentence). Cut to 180 words.

**[MINOR] Overclaim words:**
- "state-of-the-art" (1×) — used correctly in context (referring to existing methods), but watch it
- "significant" (2×) — used in "clinically significant" context, acceptable if quantified
- "remarkable" (1×, Conclusion: "a remarkable result") — let the reviewer say this, not you
- "superior" (1×, Section IV-E: "remains practically superior") — to what? Vague comparator

**[MINOR]** Sentence length. Several sentences exceed 50 words. The abstract's first sentence is 42 words with two em-dashes and two parenthetical asides. Break it up.

**[NIT]** "fitting comfortably" — anthropomorphising model weights is informal for a research paper.

---

### H. Structure and IEEE Conventions

**[MAJOR] "Acknowledgements" is misspelled per IEEE.** IEEE spells it **"Acknowledgment"** (no 'e', singular). Your `\section*{Acknowledgements}` has both an extra 'e' and an extra 's'. This seems trivial. It is not. It signals that you did not read the template instructions.

**[MAJOR] Figure references use "Figure" instead of "Fig."** IEEE style requires "Fig." in all contexts, including at the start of a sentence. Your paper uses "Figure~\ref{}" (found 3 instances). Replace all with "Fig.~\ref{}".

**[MAJOR] Index Terms / Keywords are not alphabetised.** Your keywords: "haematology, blood cell detection, YOLOv8, edge AI, Raspberry Pi, Bland–Altman, CLSI EP09c, point-of-care diagnostics, INT8 quantization." IEEE requires alphabetical order. Correct order: Bland–Altman, blood cell detection, CLSI EP09c, edge AI, haematology, INT8 quantization, point-of-care diagnostics, Raspberry Pi, YOLOv8.

**[MINOR] Section headings are not in the IEEE prescribed format.** IEEE conference headings should be Roman-numeral numbered and SMALL CAPS centered for Level 1 (e.g., "I. INTRODUCTION"). The `IEEEtran` class handles this automatically, so if you're compiling correctly this should be fine — but verify in the rendered PDF that headings render as "I. Introduction" (small caps) and not "1 Introduction" (arabic).

**[MINOR]** Missing `\IEEEpeerreviewmaketitle` after the abstract block. Required for conference peer-review submissions.

---

### I. Layout and Typography

**[MAJOR] Coloured hyperlinks.** Your `\hypersetup` uses `colorlinks=true` with blue, green, and cyan links. IEEE conference proceedings are printed in **black and white**. These will render as indistinguishable shades of grey. Change to `\hypersetup{hidelinks}` for camera-ready.

**[MINOR] Figure widths are inconsistent.** Fig. 1: `0.9\columnwidth`. Fig. 3: `\columnwidth`. Fig. 5: `0.85\columnwidth`. Use `\columnwidth` throughout for visual consistency.

**[MINOR] `\usepackage{balance}` loaded but `\balance` never called.** The last page columns are likely unbalanced. Add `\balance` before `\bibliographystyle`.

**[NIT]** Cannot fully verify margins, font sizes, gutter width, or column overflow without rendering the PDF and measuring. If you are using `\documentclass[10pt,conference]{IEEEtran}` unmodified, these should be correct. Verify visually.

---

### J. Figures, Diagrams, and Tables

**[FATAL] No system architecture diagram.** Every edge-deployment paper has a figure showing: sample slide → microscope → camera → Raspberry Pi → screen/PDF. Yours does not. This is the single most important figure for a non-expert reader (and most reviewers are semi-expert at best). It takes one hour to draw in any diagram tool. Its absence screams "student project."

**[MAJOR] No qualitative detection examples.** Where are the images showing predicted bounding boxes on blood smears? One good detection, one failure case. This is table stakes for any object detection paper. Your `train.py` already generates `val_batch0_pred.jpg` and `val_batch0_labels.jpg`. Include them. A reviewer who sees only numbers and no visual examples will question whether the system actually works.

**[MAJOR] Six generated figures are never included.** `make_paper_figs.py` produces `fig_icc_bar.pdf`, `fig_mAP_compare.pdf`, `fig_cost_vs_icc.pdf`, `fig_ba_annotated_BCCD.pdf`, `fig_quantisation.pdf`, and `fig_pr_summary.pdf`. None appear in `main.tex`. The ICC bar chart and cost-vs-ICC scatter are *exactly* the figures that sell this paper's story. Why generate them and not include them?

**[MAJOR] Table II is `table*` (two-column) unnecessarily.** It has 8 columns with short entries. It can fit in a single-column `table` with `\tabcolsep` of 3pt. Two-column floats disrupt reading flow and should only be used when truly necessary.

**[MINOR] The RBC row in the Bland-Altman figure (fig_ba_BCCD.pdf) is self-incriminating.** Every point is shifted +10.6 above zero. A reviewer looking at this figure instantly sees that RBC counting is broken. If you include it without the annotation-completeness proof (see §E), it damages the paper. Either add the proof, exclude RBC from the BA figure, or add an inset annotation explaining the systematic offset.

**[MINOR] No training convergence plot.** Loss vs. epoch is basic. Your `train.py` generates `results.png`. Include it.

**[NIT] Figure captions should be self-explanatory.** Fig. 1 caption is good. Fig. 3 caption is good. Fig. 5 caption ("Reliability (calibration) diagram. Perfect calibration lies on the diagonal. ECE = 0.134.") could add: "model is over-confident at lower confidence thresholds."

---

### K. Equations and Math

**[NIT]** Few equations in the paper. Those present (Wilson CI, ICC(2,1), Bland-Altman) are in the code but not the paper, which is fine for a conference paper. The bias formula in Section III-E is correct. No issues found.

---

### L. References

**[FATAL] 5 out of 15 BibTeX entries have wrong entry types.** This will produce incorrectly formatted citations in the IEEE bibliography:

| Key | Current type | Correct type | Reason |
|-----|-------------|-------------|--------|
| `liang2018` | `@inproceedings` | `@article` | IEEE Access is a journal, not proceedings |
| `kc2021` | `@inproceedings` | `@article` | Multimedia Tools and Applications is a journal |
| `shakarami2021` | `@inproceedings` | `@article` | Biomedical Signal Processing and Control is a journal |
| `jacob2018` | `@article` | `@inproceedings` | CVPR is conference proceedings |
| `platt1999` | `@article` | `@incollection` | "Advances in Large Margin Classifiers" is an edited volume |

Reviewer 2 will open the reference list first. Five type errors in fifteen references is a 33% error rate. This is humiliating.

**[MAJOR] No DOIs.** Not a single reference has a DOI. IEEE requires DOIs where available. `briggs2009`, `koo2016`, `passing1983`, `liu2022`, `liang2018`, `kc2021` all have DOIs in CrossRef. Add them.

**[MAJOR] BCCD citation is incorrect.** `@misc{bccd, author = {Shenggan}}` — "Shenggan" is a GitHub username, not an author name. The BCCD dataset was contributed by multiple contributors. Provide the full repository name, access date, and a DOI or permanent URL.

**[MINOR] Too few references (15).** For a paper spanning clinical haematology, deep learning, edge deployment, quantisation, and clinical statistics, 15 references is thin. Target 25–30. See §C for specific gaps.

**[NIT]** Citation order: IEEE numbered style requires citations in order of first appearance. Verify this after bibtex sorting.

---

### M. Integrity and Risk

**[MAJOR] No ethics statement.** Medical AI papers increasingly require one. Even with public datasets: "This study used publicly available anonymised datasets and did not involve human subjects. No IRB/ethics committee approval was required."

**[MAJOR] No data availability statement.** The abstract says "released under an open licence." Where? No GitHub URL. No Zenodo DOI. No licence name. This is a promise, not a statement.

**[MINOR]** No disclosure of AI tool usage. If any part of this paper or code was generated with assistance from LLMs or AI tools, most IEEE venues now require disclosure. If tools were used, add a statement. If not, add "No AI tools were used in the preparation of this manuscript" to be safe.

---

## IEEE Compliance Audit

| Check | Status | Measured / Note |
|-------|:------:|-----------------|
| Document class | ✅ Pass | `10pt,conference,IEEEtran` |
| Page size | ⚠ Cannot verify | Depends on compilation; IEEEtran defaults to US Letter |
| Body font/size | ⚠ Cannot verify | IEEEtran defaults to 10pt Times; should be correct |
| Title size | ⚠ Cannot verify | IEEEtran handles automatically |
| Abstract word count | ❌ Fail | **245 words** (limit ~200 for conference) |
| Keywords alphabetised | ❌ Fail | 9 keywords in random order |
| "Acknowledgment" spelling | ❌ Fail | **"Acknowledgements"** (extra 'e', extra 's') |
| Figure cross-references | ❌ Fail | Uses **"Figure"** not **"Fig."** (3 instances) |
| Table cross-references | ✅ Pass | Uses "Table" (never abbreviated) |
| Citation style [n] | ✅ Pass | Numbered brackets |
| Coloured links | ❌ Fail | **Blue/green/cyan links** in B&W print venue |
| `\IEEEpeerreviewmaketitle` | ❌ Fail | Missing |
| `\balance` before bibliography | ❌ Fail | Package loaded, never called |
| Heading style (small caps, Roman) | ⚠ Cannot verify | IEEEtran should handle; verify in PDF |
| BibTeX entry types correct | ❌ Fail | **5/15 wrong** (33% error rate) |
| DOIs in references | ❌ Fail | **0/15 have DOIs** |
| Consistent language variant | ❌ Fail | **36 British, 8 American** — mixed |

**Result: 4 Pass, 5 Cannot Verify, 8 Fail.** This is not camera-ready.

---

## What Is Actually Good

*Grudgingly:*

The dual-tier evaluation framework — applying CLSI EP09c method-comparison statistics alongside standard CV metrics — is a genuinely smart idea that I have not seen in other student papers. If the RBC issue is resolved and the claims are tightened, this framework alone is a publishable contribution. The platelet ICC of 0.862 is legitimately excellent and, at \$275, is a story worth telling.

The code is also surprisingly well-structured. `paper_eval.py` is a competent, modular evaluation suite with proper bootstrap CIs, ICC implementation, Passing-Bablok, and Deming regression. The fact that it even has a `--second_annotator_dir` flag shows someone thought about what a real clinical evaluation looks like. They just didn't follow through.

---

## Reviewer 2 Preview

> *"The authors present an interesting evaluation framework but fail to deliver on several of their stated contributions. Most critically: (1) The 72-image OOD benchmark is described extensively but no results are presented on it (n_clin = 0 in their own evaluation output). (2) The RBC agreement statistics (ICC = 0.112, MAPE = 101%) indicate that the counting system is non-functional for erythrocytes, yet the authors attribute this to 'ground-truth incompleteness' without evidence — no manual recount, no visual examples of missed annotations, no comparison with an independently exhaustive annotation. (3) The claim of being 'substantially above published human-labeller baselines' rests on a 1985 study of WBC differential counting, a fundamentally different task from bounding-box detection, and no inter-annotator study was conducted on the actual task. (4) The INT8 mAP is estimated (≈0.84) rather than measured, despite the model and evaluation code being available. (5) The reference list contains five incorrect BibTeX entry types and no DOIs. The evaluation framework is promising but the execution and presentation fall short of the standard required for publication. **Reject; encourage major revision and resubmission.**"*

---

## Top 10 Fixes, Ranked by Impact on Acceptance

| # | Fix | Effort | Impact |
|:-:|-----|:------:|:------:|
| 1 | **Prove RBC annotation incompleteness** (manual recount of 10–15 images with visual evidence) OR restrict clinical claims to WBC/Platelets only | 2 hrs or 15 min | Saves the paper from instant reject |
| 2 | **Do the second-annotator study** (20–30 images, even a classmate re-labelling blind) to support or withdraw the "better than human" claim | 3 hrs | Turns the biggest weakness into the biggest strength |
| 3 | **Run OOD evaluation on clinical_72 images** and present the results, or remove all mentions | 30 min | Delivers an undelivered contribution |
| 4 | **Measure actual INT8 mAP** by running `paper_eval.py` with the ONNX model | 10 min | Eliminates an ≈ that screams laziness |
| 5 | **Fix all 5 BibTeX entry types**, add DOIs, fix BCCD citation | 30 min | Prevents Reviewer 2 killing your credibility on page 8 |
| 6 | **Add a system architecture diagram** (microscope → camera → Pi → output) | 1 hr | Makes the hardware contribution visible |
| 7 | **Remove all "our advisor" references**, fix "Acknowledgements" → "Acknowledgment", fix "Figure" → "Fig.", alphabetise keywords | 15 min | Prevents desk-reject on formatting |
| 8 | **Standardise to American English** (global find-replace), cut abstract to ≤200 words, remove overclaim words | 30 min | Professionalism |
| 9 | **Include the best supplementary figures** (ICC bar, cost-vs-ICC, detection examples) and add references to them | 30 min | Visual storytelling |
| 10 | **Add ethics statement, data availability (with URL), consolidated limitations subsection, and 10–15 more references** | 2 hrs | Completeness and compliance |

**Total estimated effort for all 10 fixes: 8–10 hours of focused work.**

---

## Verdict and Deadline

**NOT READY.** Not remotely.

The paper has a B-tier idea wrapped in D-tier execution. If you fix items 1–5, it becomes a solid regional conference paper (IEEE INDICON, ICCCNT, or a national-level symposium). If you fix all 10, it is competitive for a mid-tier IEEE international conference. It is not, in its current state or any near-future state, competitive for a top venue (MICCAI, CVPR workshops, IEEE TMI) — the dataset is too small, the model is off-the-shelf, and the clinical validation is incomplete.

That is fine. For a capstone project, a well-executed regional IEEE conference paper with genuine clinical method-comparison statistics is *better* than most final-year projects I supervise. But "better than most" is not good enough for my name. I want "the best this year."

**Revised draft on my desk by Friday. All red items resolved, all bibliography entries corrected. I will not review a third draft.**

— Prof. [Guide]

*P.S. — If you had spent the 3 hours on the second-annotator study instead of the 3 hours formatting coloured hyperlinks nobody asked for, this paper would be ready now. Priorities.*
