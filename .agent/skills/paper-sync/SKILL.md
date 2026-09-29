---
name: paper-sync
description: Update a LaTeX research paper so it accurately reflects code and pipeline changes documented in a change log (e.g. change.md) and the git diff. Verifies every claim in the change log against the actual code, checks whether changed hyperparameters actually take effect, audits the new evaluation protocol for leakage and selection bias, then edits paper.tex (methods, experimental setup, evaluation protocol, limitations, cost), adds clearly marked PENDING skeletons for results that do not exist yet, reconciles SERVER_TASKS.md, and later ingests the pipeline's real outputs into the paper. Use whenever the user uploads or mentions a change log or CHANGELOG, says the code, training recipe, preprocessing, inference pipeline or evaluation changed, or asks to "update the paper according to these changes", "sync the paper with the code", "reflect the new pipeline in the methods", or "put the new results in the paper", even if they never say "sync".
---

# Paper Sync: Make the Paper Match the Code (and Claim Nothing More)

Code changes are facts about the *method*. They are not evidence about *performance*. This skill writes the first into the paper accurately and refuses to write the second until real results exist.

The typical input is a change log such as `change.md` (what was modified, why, how to run, which paper sections will be affected). Treat it as a **claim to verify**, written by whoever made the changes, not as ground truth. The code, the git diff, and returned result files are the ground truth.

## Ground rules (and why they exist)

- **Code is the source of truth.** If the change log and the code disagree, the code wins and the discrepancy goes in the sync report. Reviewers and replicators read the code, not the change log.
- **A change is not a result.** Do not write that any change "improves", "boosts", or "generalizes better" until validated results are ingested. Rationales in the change log ("full rotation invariance", "regularization to reduce memorization") are design motivations. They may appear in the paper as motivation, hedged, never as evidence.
- **Never overwrite the baseline.** The original model and its numbers stay in the paper as the labelled baseline row. New numbers are added beside them, not substituted for them. Silent replacement hides regressions and makes the comparison unauditable.
- **Never describe a feature that does not exist or has no effect.** If a setting is inactive or unverifiable, the paper must not present it as part of the method's contribution.
- **No fabricated numbers, results, or citations.** Numbers come from result files the user returned. Citations come from references you verified exist (web lookup); candidates go to `improvements/reading-list.md`, not `references.bib`.
- **The paper stays internally consistent at every commit.** Do not leave the Methods describing the new pipeline while the tables silently report the old one. Label versions everywhere (for example "baseline" and "v2") until the results are swapped in.
- **Code is read-only.** Problems you find in the code go in the sync report and `SERVER_TASKS.md`. Do not fix them unless the user has explicitly allowed code edits.
- **Work on the existing git branch**, commit after each meaningful step, never push or touch main.

## Step 0: Locate inputs

1. The change log (path given by the user; otherwise look for `change*.md` or `CHANGELOG*` at the repo root).
2. The real diff: `git log --stat` and `git diff <base>...HEAD -- <files>` for every file the change log lists, plus any file it does not list that the diff shows changed.
3. Every code file the change log names, read in full, plus what they import from the project.
4. `paper/paper.tex` (and anything it inputs), `paper/references.bib`, `paper/figures/`.
5. `SERVER_TASKS.md`, `improvements/IMPROVEMENT_LOG.md`, and the latest `critiques/round-N/`.
6. Any pipeline outputs already in the workspace (`server/results/`, or an outputs folder such as `outputs/generalized/` if it was copied locally). If none exist, this pass is methods and protocol only, and every result stays PENDING.

## Step 1: Verify the change log against the code

For every row and claim in the change log, mark it **Verified**, **Mismatch** (record what the code actually says), or **Unverifiable** (for example the file is missing or the behavior can only be seen at run time). Compare:

- hyperparameter defaults, in both the model class and the CLI (argparse names, types, defaults);
- which arguments actually reach the training call;
- the pipeline steps in the orchestration script, in order, including which weights each step evaluates;
- preprocessing parameters, thresholds, TTA transforms, the split ratio and seed, class names and order;
- output paths and file names that the paper or the tasks will refer to.

Cheap checks are fine (`python -m py_compile`, `--help`). Do not run training or evaluation.

**Effectiveness check.** For every hyperparameter or component the paper would describe, determine whether it actually does anything in the installed library version. Read the library source or docs that are available locally (for example `pip show ultralytics`, then read the relevant code under site-packages), or the run's `args.yaml` and logs if a run exists. Record **Effective**, **No effect**, or **Unknown**. Do not rely on memory of a library's behavior. In this project the change log describes some settings as detection-head regularization or object synthesis; verify in the installed version whether `dropout` applies to detection at all and whether `copy_paste` acts on box-only labels (it may depend on segmentation masks), and check what large rotation angles do to axis-aligned boxes and to mAP@0.5:0.95. If a setting has no effect or cannot be confirmed, do not present it as a contributor to any result.

## Step 2: Evaluation-validity gate (before writing anything about results)

Answer each question **from the code**, not from the change log. Each answer gets a status (OK / RISK / UNKNOWN) and a consequence.

1. **Which images does every table, figure, and ablation row evaluate on?** Trace each one through the evaluation scripts.
2. **Leakage:** is any evaluation image also in a training or fine-tuning split? For example, if the clinical images that previously formed the out-of-distribution test set are now partly used to fine-tune, any fine-tuned model must be scored only on held-out images, and it is no longer a zero-shot cross-domain result.
3. **Comparability:** are the baseline and every new configuration scored on the *same* images with the *same* protocol? Was the old headline number (for example the existing clinical mAP) computed on the same set and protocol as the new numbers? If not, the comparison is invalid until re-evaluated.
4. **Selection bias:** which set chooses the checkpoint (`best.pt`, early stopping) and which set is reported? Reporting on the set that picked the checkpoint is optimistic, especially with a tiny validation split.
5. **Provenance of tuned values:** where did the per-class thresholds, CLAHE and normalization settings, and the split seed come from? If they were chosen looking at the evaluation set, that is test-set tuning. If the origin cannot be determined, mark UNKNOWN and raise it as a human decision.
6. **Statistical adequacy:** number of images and instances per class in each evaluation set, number of seeds, whether any interval or variance is reported. A single seed on a small split supports only very cautious wording.
7. **Ablation structure:** is it cumulative (each row adds a change) or factorial? Were many changes bundled into one "retrained" row? Then gains cannot be attributed to individual components, and the text must not attribute them.
8. **Cost:** inference-time preprocessing and multi-pass TTA multiply latency. Does the paper's latency and deployment table measure the *full* pipeline?
9. **Quantization:** which data calibrates INT8, and is the quantized model evaluated on the same set as the FP32 one?

Every RISK or UNKNOWN produces (a) an honest statement of the limitation in the paper, (b) a task in `SERVER_TASKS.md` if evidence can resolve it, and (c) a human-decision flag if it is a consequential research choice.

## Step 3: Map changes to the paper

Build a table: change, paper location (verified against the real `paper.tex`, since the change log's section names or numbering may be wrong), and disposition:

- **WRITE NOW:** facts about the method or protocol that are verified in code and effective (augmentation recipe, fine-tuning protocol, preprocessing and TTA definitions, split, thresholds with their provenance).
- **PENDING:** needs results that do not exist yet.
- **LIMITATION:** the gate found a risk. State it now.
- **DO NOT WRITE:** ineffective, unverifiable, or nonexistent. Record it in the report only.

Also scan the whole paper for now-stale statements (search for terms such as `mosaic`, `flip`, `rotation`, `mixup`, `patience`, `epochs`, `augmentation`, `threshold`, `confidence`, `preprocess`, `quantiz`, `latency`, the split sizes, and every headline number). Update or relabel each one so it is correct for the version it describes.

## Step 4: Edit the paper

Follow the improve skill for IEEEtran hygiene, surgical edits, and compile-and-verify. **All prose you write here (Methods, protocol, limitations, PENDING skeleton captions, ingested results text) follows `.agent/skills/paper-writing/SKILL.md`**: plain wording, few numbers in sentences, settings in tables, claims matched to evidence. Run its checker before and after, as the improve skill describes. Specific to this skill:

- **Versioning.** Introduce the configurations explicitly (for example "baseline" and "v2") in the Methods. Existing results stay attached to the baseline. Any sentence or table that mixes versions must say which is which.
- **Methods.** Describe, in factual language ("we use", "we apply"), the training recipe (a table of the settings that are Effective), the fine-tuning protocol (initial weights, frozen layers, learning rate, epochs, which split), the inference preprocessing (normalization reference and how its statistics were computed, contrast enhancement parameters), the TTA transforms and how detections are merged, and the per-class thresholds with their provenance.
- **Experimental setup and protocol.** State exactly which images each experiment uses, the split procedure, the seed(s), the checkpoint-selection rule, and the library versions (from the environment capture if available, otherwise PENDING).
- **Results skeletons.** Add the ablation table with one row per configuration as defined in the code and every result cell visibly marked, for example `\textbf{[[PENDING: T-05]]}`. Give it a `\label`, an IEEE-style caption (table caption above), and column headings matching the metrics the evaluation script will output. Do **not** `\includegraphics` a figure file that does not exist yet; leave a commented include and a visible placeholder so the paper still compiles.
- **Limitations.** Write now the limitations the gate identified (small clinical set, held-out size, seeds, bundled and cumulative ablation, threshold provenance, added inference cost). These are true whatever the results are.
- **Cost and deployment.** Mark the latency, size, and INT8 numbers PENDING, and state that TTA and preprocessing add inference cost.
- **Abstract, introduction, conclusion.** Do not add improvement claims. You may list the pipeline components as things *studied*. Keep any existing baseline number labelled as the baseline.
- **Related work.** Where the new techniques need positioning (stain normalization, contrast enhancement, test-time augmentation, domain adaptation), collect *candidate* references in `improvements/reading-list.md` after verifying each exists. Add to `references.bib` only what has been verified.

Compile, read the log, check the pages, and grep for `PENDING` to confirm the list of open placeholders matches the tasks.

## Step 5: Reconcile `SERVER_TASKS.md`

The change log may say the tasks file was rewritten with start-to-end commands. Do not trust it blindly.

1. Check every command, argument name, and path against the code (argparse definitions, script names). Fix the wrong ones. Never invent arguments or paths.
2. Add a task for each gate failure that evidence can resolve, for example: evaluate every configuration on an identical held-out set; repeated seeds or cross-validation and bootstrap confidence intervals; end-to-end latency of the full pipeline; confirmation from training logs that the augmentations were active; re-selecting thresholds on non-evaluation data; a per-augmentation ablation only if the paper needs to attribute gains. Prefer extraction from existing outputs over re-running.
3. Tie each task to the `PENDING` markers it will fill, and give each a priority (P0 to P3). Do not add tasks the paper does not need.

## Step 6: Ingest real results (only when result files exist)

1. **Validate.** Look for errors and partial outputs. Cross-check the generated LaTeX tables against the JSON (they can disagree). Check that the weights evaluated match the configuration named. Look for implausible values (perfect scores, zero variance).
2. **Report honestly.** If the new pipeline is no better, or better in one domain and worse in another, say so and rewrite the claims. Report all configurations and all runs. Never drop the baseline row or an inconvenient seed.
3. **Adapt style.** Generated tables and figures rarely follow IEEE conventions. Fix caption placement and numbering, `Fig.` and `Table` usage, font sizes in figures (about 8 pt or larger at final size), and figure width (3.5 in single column, 7.16 in double).
4. **Propagate.** Update every occurrence of each changed number: abstract, introduction, results, discussion, captions, conclusion. Then replace the `PENDING` markers and remove them.
5. **Discussion.** Only now write the interpretation of the ablation, limited to what the evidence supports and consistent with the gate (no attribution to single components if the ablation bundled them).

## Step 7: Report and log

Write `improvements/code-sync-N.md`:

```markdown
| Change-log item | Code check | Effective? | Paper location | Edit made | Pending evidence |
|---|---|---|---|---|---|
| flipud 0.0 → 0.5 | Verified | Yes | Sec. III-B, Table II | Added to training-recipe table | (none) |
| dropout 0.1 | Verified | Unknown | (not written) | Recorded only | T-04: confirm from args.yaml |
```

Add three lists: **discrepancies between the change log and the code**, **gate results** (OK / RISK / UNKNOWN with consequences), and **human decisions needed**. Update `improvements/IMPROVEMENT_LOG.md`, then commit on the branch.

## Reply style

Short. Say what was written into the paper now, what is marked PENDING and which task fills it, which change-log claims failed verification, and what needs the user's decision. Do not describe the paper as improved. It is *updated*; whether it is *better* depends on the results.
