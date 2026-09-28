# 🔴 Paper Critique — Prof. [Guide Name]'s Markup

> **Paper:** "Edge-AI Automated Peripheral Blood Smear Analysis: A YOLOv8n Deployment on Raspberry Pi 4 for Resource-Constrained Haematology Screening"
>
> **Verdict: NOT READY for submission.** Significant methodological gaps, scientific dishonesty by omission, formatting violations, and weak experimental coverage. Fix *everything* below before I put my name on this.

---

## 1. FATAL SCIENTIFIC PROBLEMS

### 1.1 The RBC Results Are an Embarrassment — You Cannot Publish ICC = 0.112

- **RBC Precision = 0.496.** This means your model produces *more false positives than true positives*. That is coin-flip performance. You buried this in gentle language ("lower precision owing to dense packing") and then hid behind a "ground-truth incompleteness" hypothesis that you **never actually validate**.
- **RBC ICC = 0.112, MAPE = 101%.** This is "poor" agreement by the very Koo & Li scale you cite. You cannot publish this and then say "this is not a clinical error but a benchmarking limitation" without proving it. **Where is the proof?** You claim the BCCD annotations are incomplete — show me. Count cells manually in 10 images, compare to BCCD annotations, and prove the ground truth is wrong. Otherwise this is just handwaving to excuse bad performance.
- **The RBC bias is +10.6 cells/image against a mean reference of 11.4 cells.** Your model nearly *doubles* the count. You literally overcount by ~93%. And you put this in a published paper and expect a reviewer not to catch it?

> [!CAUTION]
> **Fix required:** Either (a) prove the BCCD annotations are incomplete with a manual re-count of 10+ images, OR (b) remove the RBC agreement metrics entirely and restrict the clinical-comparison claim to WBC and Platelets only, OR (c) retrain with NMS threshold tuning and border-exclusion to reduce the 4,042 false positives. You CANNOT publish RBC ICC = 0.112 and call the system "substantially above published human-labeller baselines." That claim applies to WBC/Platelets only.

### 1.2 The "Better Than Human" Claim Is Unsupported

The abstract says: *"positioning this system substantially above published human-labeller baselines."* Section IV-C says: *"expected to exceed typical human-versus-human inter-rater agreement."*

The word "expected" is doing catastrophic load-bearing work here. You **never measured** human-vs-human ICC in this study. You cite Rümke 1985 — a paper from **40 years ago** about *differential leukocyte counting* (classifying WBC subtypes into 5 categories), not about *detecting and counting WBCs in bounding boxes*, which is a fundamentally different task. The ICC numbers from Rümke's study are not directly comparable to your bounding-box counting ICC because:

1. Rümke counted cells out of 100 observed (a proportion), not absolute counts per field
2. The error source is different (morphological ambiguity vs. detection sensitivity)
3. The variance structure is different (binomial sampling vs. detector noise)

Without your own inter-annotator study (which `paper_eval.py` literally has a flag for — `--second_annotator_dir` — but you left empty), this claim is **scientifically unsupported speculation**.

> [!CAUTION]
> **Fix required:** Either (a) conduct the second-annotator study (20–30 images, 3 hours of work) and report actual human-vs-human ICC on the same task, OR (b) weaken every "better than human" claim to say "approaches the upper end of published human inter-rater ranges for *differential counting* tasks, though direct comparison is precluded by differing task definitions." Option (a) would make this a genuinely good paper. Option (b) is the coward's path.

### 1.3 No OOD Results Presented

You mention a 72-image independently annotated OOD benchmark **four separate times** in the paper. It is in the abstract. It is in Contribution #4. It is in the Dataset subsection. It is in the Discussion.

**But you never show results on it.** The `n_clin = 0` in your results JSON confirms you ran zero clinical images. What was the point of getting a bioengineering student to label 72 images if you're not going to report results on them? This will be the first thing a reviewer says: *"The authors describe an OOD benchmark but fail to present any results on it."*

> [!CAUTION]
> **Fix required:** Run `paper_eval.py` with a properly configured `--clinical_dir data/clinical_72` that actually loads images. The 72-image directory exists in your repo but evidently has no images in it (or the path is wrong). Fix the data path, regenerate results, add a table and discussion of OOD performance. If the images truly aren't available, **remove every mention of the 72-image benchmark** — don't advertise a contribution you didn't deliver.

### 1.4 INT8 mAP Is Estimated, Not Measured

Table III reports "Ours (YOLOv8n INT8) ≈ 0.84" with an approximation symbol. You have the INT8 ONNX model (`outputs/yolov8n_int8.onnx`). You have the test images. Why didn't you actually run the INT8 model through the evaluation suite? `paper_eval.py` supports ONNX models. The ≈ symbol tells every reviewer you were too lazy to run one more experiment.

> [!WARNING]
> **Fix required:** Run INT8 evaluation and report the *actual* mAP. Replace ≈ with the real number.

### 1.5 No Raspberry Pi Latency Measurements Presented

You claim 4.1 FPS and 245 ms latency on a Raspberry Pi 4B. **Where is this data?** There is no latency table, no box-and-whisker of per-frame times, no mention of warm-up, no thermal throttling analysis. `quantize_and_infer.py` has a `profile_edge_inference()` function that returns mean latency and FPS. Did you run it on actual Raspberry Pi hardware? If those numbers are from your x86 machine, they are meaningless.

> [!WARNING]
> **Fix required:** Add a table showing: model variant (FP32/INT8), model size (MB), mean latency ± std (ms), FPS, and the hardware platform. Clearly state whether measured on actual RPi 4B or simulated on x86 CPU. If you don't have RPi measurements, **say so honestly** and label the numbers as "x86 CPU emulation."

---

## 2. METHODOLOGICAL WEAKNESSES

### 2.1 Single Dataset, Single Split, No Cross-Validation

The entire paper's quantitative evidence comes from one run on one fixed train/test split of one small dataset (BCCD, 364 test images). No k-fold cross-validation. No multiple random seeds. No error bars on mAP. A single lucky or unlucky split can shift mAP by ±0.03. Without variance estimates, every number in the paper is a point estimate with unknown uncertainty.

> [!IMPORTANT]
> **Fix required (minimum):** Report results across 3 random seeds and show mean ± std for mAP and F1. Alternatively, acknowledge this as a limitation.

### 2.2 Passing-Bablok Slope = 1.00 for All Three Classes — Suspicious

All three cell types show P-B slope = 1.000. For RBC with ICC = 0.112 and bias = +10.6, having a perfect slope of exactly 1.0 is statistically implausible — it suggests the P-B regression is degenerate (likely because the count values are small integers with many ties). I checked your code: Passing-Bablok on integer-valued data with narrow range (WBC counts are mostly 0 or 1) produces degenerate slopes because there are insufficient unique pairwise slope values. **You are reporting a degenerate statistical artefact as if it were a meaningful result.**

> [!WARNING]
> **Fix required:** Either (a) note that P-B is unreliable for integer-valued data with narrow range and remove the slope from the main claims, or (b) use Deming regression slope instead (you compute it but never report it — RBC Deming slope = 0.876, which is far from 1.0 and tells a completely different story).

### 2.3 No Ablation Study

What does each design choice contribute? No ablation on:
- Augmentation strategy (mosaic on/off)
- Confidence threshold (you hardcoded 0.25 — what happens at 0.15 or 0.35?)
- Image resolution (640 vs 416 vs 320)
- NMS IoU threshold (you hardcoded 0.5)
- The effect of pre-training on COCO vs training from scratch

Without ablations, a reviewer has no idea whether your hyperparameters are reasonable or accidentally good.

### 2.4 No Statistical Significance Tests

The SOTA comparison table (Table III) shows your mAP = 0.856 vs. YOLOv3 = 0.82. Is this difference statistically significant? You don't know, because you didn't test it. Use a paired bootstrap test on per-image AP scores, or at minimum acknowledge that you can't make statistical claims from point estimates.

### 2.5 The WBC ICC Confidence Interval Is Enormous

ICC(2,1) for WBC = 0.568 with 95% CI [0.38, 0.72]. That confidence interval *includes the "poor" range* (< 0.50). You cannot honestly say "moderate-to-good" when the lower bound of your CI is 0.38. Say "moderate (95% CI includes poor-to-good)."

---

## 3. WRITING PROBLEMS

### 3.1 Abstract Is Too Long

The abstract is ~220 words. IEEE conference papers typically recommend 150–200 words. More importantly, it front-loads the system description and buries the key result (ICC numbers) in the penultimate sentence. Restructure: problem → approach → key numbers → significance.

### 3.2 Inconsistent Spelling

The paper alternates between British and American English:
- "haematology" vs "hematology" (title uses British, abstract uses both)
- "analysers" (British) vs "analyzers" (abstract, line 1)
- "optimized" (American, Section III-D) but "generalisation" (British, Section III-C)

Pick one and stick to it. IEEE uses American English by convention.

### 3.3 "Our Advisor Correctly Identified" — Remove This Immediately

Section V-B says: *"Our advisor correctly identified the core epistemological challenge."* **You do not cite your advisor in a published paper.** This is not a thesis acknowledgement. This sentence screams "undergraduate project" and will get your paper desk-rejected. Rephrase to: *"A fundamental epistemological challenge exists in cross-modality comparison..."*

Similarly, Section IV-F says: *"This is the epistemic barrier raised by our advisor."* Remove all references to "our advisor." Cite the literature, not your professor.

### 3.4 The Paper Reads Like a Technical Report, Not a Research Paper

Too many implementation details that belong in a supplement or GitHub README:
- "Python 3.11" (irrelevant)
- "ONNX Runtime 1.17, OpenCV 4.8" (version numbers are not results)
- "CSI-2 interface" (no reviewer cares about the camera bus protocol)
- "ReportLab (PDF report generation)" (this has nothing to do with the scientific contribution)

Trim Section III to focus on decisions that affect results, not shopping lists.

### 3.5 Overclaiming Language

Several phrases are too strong for the evidence:
- "near-perfect WBC agreement" — ICC = 0.568 is "moderate," not "near-perfect." The *detection* F1 is near-perfect. Don't conflate detection metrics with agreement metrics.
- "substantially above published human-labeller baselines" — unsupported (see §1.2)
- "a remarkable result" (Conclusion) — let the reviewer say that, not you.
- "positioning this system" (abstract) — this is marketing language, not scientific language.

### 3.6 Missing Training Curve

Where is the loss convergence plot? Epoch vs. training loss and validation loss is standard in any ML paper. You generate it in `train.py` (line 149–170) but never include it.

---

## 4. FORMATTING AND IEEE COMPLIANCE VIOLATIONS

### 4.1 Coloured Hyperlinks

```latex
\hypersetup{
  colorlinks=true,
  linkcolor=blue!70!black,
  citecolor=green!50!black,
  urlcolor=cyan!60!black
}
```

**IEEE conference proceedings are printed in B&W.** Coloured citation links will appear as different shades of grey and look unprofessional. Set `colorlinks=false` or use `hidelinks` for camera-ready.

### 4.2 Table II Spans Two Columns — Is This Necessary?

`table*` (two-column table) is used for Table II (agreement statistics). It has only 7 data columns. This should fit in a single-column `table` environment with slightly smaller `\tabcolsep`. Two-column tables push figures and text around and disrupt reading flow. Only use `table*` if you truly cannot fit the content.

### 4.3 Figure Sizes Are Inconsistent

- Fig. 1 (confusion): `width=0.9\columnwidth`
- Fig. 3 (BA): `width=\columnwidth`
- Fig. 5 (reliability): `width=0.85\columnwidth`

All single-column figures should use the same width for visual consistency. Use `\columnwidth` throughout.

### 4.4 The Supplementary Figures Are Never Referenced in the Paper

`make_paper_figs.py` generates `fig_icc_bar.pdf`, `fig_mAP_compare.pdf`, `fig_cost_vs_icc.pdf`, `fig_quantisation.pdf`, and `fig_pr_summary.pdf`. **None of these appear in `main.tex`.** They were generated but never `\includegraphics`'d. Either add them to the paper (with proper `\ref{}`s) or delete the script. Generating figures you don't use is sloppy.

### 4.5 `\balance` Package Loaded but Never Called

Line 20: `\usepackage{balance}`. You never call `\balance` before `\bibliography`. The last page columns are probably unbalanced. Add `\balance` before the bibliography.

### 4.6 No `\IEEEpeerreviewmaketitle`

For conference papers submitted for peer review, IEEE requires `\IEEEpeerreviewmaketitle` after the abstract. It's missing.

### 4.7 Missing DOIs in Bibliography

Not a single BibTeX entry has a DOI. IEEE requires DOIs where available. `briggs2009`, `koo2016`, `passing1983`, `liu2022` all have DOIs. Add them.

---

## 5. BIBLIOGRAPHY PROBLEMS

### 5.1 Wrong Entry Types

- `liang2018` is typed as `@inproceedings` with `booktitle = {IEEE Access}`. IEEE Access is a **journal**, not proceedings. Should be `@article`.
- `kc2021` is typed as `@inproceedings` with `booktitle = {Multimedia Tools and Applications}`. MTA is a **journal**. Should be `@article`.
- `shakarami2021` is same problem: `@inproceedings` with `booktitle = {Biomedical Signal Processing and Control}`. That's a **journal**. Should be `@article`.
- `jacob2018` is typed as `@article` with `journal = {CVPR}`. CVPR is **conference proceedings**. Should be `@inproceedings`.
- `platt1999` is typed as `@article` with `journal = {Advances in Large Margin Classifiers}`. That's a **book chapter** (edited volume). Should be `@incollection`.

**5 out of 14 references have the wrong BibTeX entry type.** This will produce incorrectly formatted citations in the IEEE bibliography style.

### 5.2 Too Few References

14 references for a paper with this scope is thin. A typical IEEE conference paper in this space has 25–40. Missing key related work:
- No CellProfiler or other classical image-processing baselines
- No mention of YOLO11 (you have `yolo26n.pt` in your weights folder)
- No attention-based detection methods (DETR, RT-DETR)
- No other edge-deployment papers (MCUNet, TinyML literature)
- No other Raspberry Pi medical imaging papers
- No CLSI EP09c standard itself (you cite the framework but not the standard document)

### 5.3 The BCCD Citation Is Wrong

`@misc{bccd}` cites `author = {Shenggan}`. The BCCD dataset was created by multiple contributors. The canonical citation (if using the GitHub repo) should include the full repository name and access date.

---

## 6. FIGURES

### 6.1 No System Architecture Diagram

There is no figure showing the physical hardware setup (microscope → camera → Pi → screen). Every edge-deployment paper has one. This is the simplest figure to make and the most impactful for non-expert readers.

### 6.2 No Example Detection Outputs

Where are the qualitative results? Show 3–4 images with predicted bounding boxes overlaid on the blood smear — one good detection, one failure case. This is table stakes for any object detection paper. Your `train.py` already generates `val_batch0_pred.jpg`. Include it.

### 6.3 No Training Convergence Plot

Already mentioned in §3.6. Loss vs. epoch is a basic figure.

### 6.4 Bland-Altman Figures — The RBC Plot Tells a Devastating Story

The RBC Bland-Altman plot (in `fig_ba_BCCD.pdf`) should show all points shifted massively above zero with bias = +10.6. If you include this figure (which you do), a reviewer will immediately see that RBC counting is broken. Either fix the model or exclude RBC from the BA plots and explain why in the text.

---

## 7. MISSING SECTIONS AND CONTENT

### 7.1 No Ethical Statement

Medical AI papers increasingly require an ethics statement. Even if IRB approval isn't required (no patient data, public dataset), you should state: *"This study used publicly available anonymised datasets and did not involve human subjects. No IRB approval was required."*

### 7.2 No Data Availability Statement

You claim to release the code and OOD benchmark. Where? No GitHub URL. No Zenodo DOI. Just "released under an open licence." That's not a data availability statement.

### 7.3 No Limitations Section

The Discussion has scattered limitations but no consolidated "Limitations" subsection. IEEE papers in medical AI increasingly require this. Consolidate: single dataset, no paired clinical reference, no second annotator, no actual RPi profiling, English-only, single staining protocol.

### 7.4 No Comparison with Classical Image Processing

Your advisor specifically asked for comparison against existing methods. You compare against deep learning methods only. What about classical approaches? Watershed segmentation + thresholding for RBC counting was the standard pre-DL approach. Including a 10-line OpenCV baseline (Otsu + watershed + contour counting) would show where DL actually helps and where it doesn't. It would take 30 minutes to implement and would add enormous credibility.

---

## 8. SUMMARY — ORDERED FIX LIST

| Priority | Issue | Effort | Impact |
|:--------:|-------|:------:|:------:|
| 🔴 | Remove/weaken "better than human" claim or do second-annotator study | 3 hrs or 5 min | Paper-killing |
| 🔴 | Fix RBC narrative — prove BCCD incompleteness or restrict claims | 2 hrs | Paper-killing |
| 🔴 | Run OOD evaluation on 72-image set or remove all mentions | 30 min | Paper-killing |
| 🔴 | Measure actual INT8 mAP (not ≈) | 10 min | Credibility |
| 🔴 | Fix 5 wrong BibTeX entry types | 10 min | Desk-reject risk |
| 🟡 | Add system architecture diagram | 1 hr | Reviewer experience |
| 🟡 | Add example detection outputs (qualitative results) | 30 min | Reviewer experience |
| 🟡 | Remove all "our advisor" references | 2 min | Professionalism |
| 🟡 | Fix British/American spelling inconsistency | 15 min | Professionalism |
| 🟡 | Include the supplementary figures or delete the script | 15 min | Completeness |
| 🟡 | Add training convergence plot | 10 min | Completeness |
| 🟡 | Reduce abstract to <200 words | 15 min | IEEE compliance |
| 🟡 | Fix coloured hyperlinks to black | 1 min | Print readiness |
| 🟡 | Add RPi latency table with proper methodology | 1 hr | Edge claim |
| 🟡 | Add classical baseline (watershed) | 30 min | Comparison depth |
| 🟢 | Add DOIs to bibliography | 20 min | Polish |
| 🟢 | Add 10–15 more references | 1 hr | Scholarship |
| 🟢 | Add ethics and data availability statements | 10 min | Compliance |
| 🟢 | Add `\balance` call and `\IEEEpeerreviewmaketitle` | 1 min | IEEE format |
| 🟢 | Standardise figure widths | 2 min | Visual consistency |
| 🟢 | Note P-B degeneracy on integer data | 5 min | Statistical honesty |

**Total estimated effort for all 🔴 fixes: 4–6 hours.**

---

> **My name is not going on this paper until the red items are resolved. The paper has a good core idea and a solid evaluation framework — that's genuinely better than most capstone projects I see. But right now it's a technical report pretending to be a research paper. Fix the scientific honesty issues first, then we can talk about submission venues.**
>
> — Prof. [Guide]
