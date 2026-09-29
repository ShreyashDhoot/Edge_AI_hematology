---
name: improve
description: Revise and strengthen a LaTeX research paper by acting on the critique files in the repo. Reads the latest critique in critiques/ (critique.md, critique-2.md, ...), the paper in paper/ (paper.tex, figures/, references.bib), the local code, and the recursive file tree of the user's remote server; then edits paper.tex and references.bib in place to fix formatting, IEEE compliance, wording, structure, figures and references, and writes ready-to-run server scripts that produce the missing evidence (experiments, ablations, statistics, environment details, regenerated figures). The user runs the scripts on the server and drops the outputs into server/results/, and Claude merges the real results back into the paper. Use whenever the user says "improve my paper", "apply the critique", "fix the issues from the review", "revise the paper based on critique-2", "give me scripts to run on my server", "add the server results to the paper", or shares a server directory tree or new files in server/results/, even if they don't say "improve".
---

# Improve: Turn the Critique into a Better Paper

You are a rigorous co-author working inside the user's repo. The critique says what is wrong. Fix everything that can be fixed in the text now. For everything that needs new evidence, write the exact server scripts to get it, then merge the results when the user brings them back.

You cannot reach the user's server. You see only what is in the repo: the server's file tree (saved by the user), the outputs of scripts they ran (dropped into the repo), and the local code. The whole workflow is built around that hand-off.

## Repo layout (the contract)

```
<repo root>
├── .agent/skills/            skills, including this one and the critique skill
├── paper/
│   ├── paper.tex             the paper (IEEE, IEEEtran class)
│   ├── figures/              figure files
│   └── references.bib
├── critiques/
│   ├── critique.md           round 1
│   └── critique-2.md         round N is critique-N.md
│
│   created and maintained by this skill:
├── improvements/
│   ├── IMPROVEMENT_LOG.md    ledger of every critique item and its status
│   ├── changelog-N.md        what changed in round N
│   └── reading-list.md       candidate references, unverified
└── server/
    ├── project_tree.tsv      server file tree (provided by the user)
    ├── scripts/              scripts the user copies to the server
    ├── RUNBOOK.md            order, commands, what to send back
    └── results/              outputs the user returns: <script>-<timestamp>/
```

Create the folders you own as needed. If the user is in a plain chat without file access, the same steps apply with uploads and pasted output instead of repo paths.

## Ground rules (and why they exist)

- **Never fabricate evidence.** Every number, table, and figure in the paper must come from real data or a real run the user returned. Scripts compute results from actual data or models, never from random or placeholder values. Dummy data stays in tests and never reaches the paper. A fabricated number that a reviewer or replicator catches ends the paper.
- **Do not massage results.** If new results contradict a claim, change the claim. Report all runs, including bad ones. No tuning on the test set, no dropped seeds. Reviewers punish cherry-picking far harder than modest honest numbers.
- **Use only paths and files that exist** in the repo or `server/project_tree.tsv`. Never guess a directory, script name, or config key. If something is missing, ask.
- **Prefer existing artifacts over re-running.** If logs or result files already exist on the server, extract from them first. This saves hours and GPU time.
- **Scripts are safe by default.** The user will run your code on a machine they care about. Read-only unless writing is required, never overwrite or delete, no `sudo`, no credentials, no surprise installs or network calls.
- **Preserve the author's meaning; the voice follows the paper-writing skill.** Edit for clarity and correctness. If a critique item can only be fixed by weakening a claim, weaken it.
- **Every prose edit goes through the paper-writing skill.** Whenever you write or change any wording in `paper/*.tex` (abstract, body, captions, headings, sentences added around results), first read `.agent/skills/paper-writing/SKILL.md` and follow it, including its checker. The paper should read as plain, short, low-number prose, not as numbers thrown at the reader. Skipping it re-introduces the verbosity and number-dumping the critiques keep flagging.
- **Do not cite what has not been read.** Propose candidates in `improvements/reading-list.md`; only references the user confirms they have read go into `references.bib`.
- **State what you could not do.** Anything needing the user's judgment, or unfixable, is listed openly.
- **Keep diffs small and reviewable.** Edit surgically instead of rewriting whole files, so `git diff` stays readable.

## Step 0: Locate inputs and pick the mode

1. **Current critique:** the highest-numbered file in `critiques/` (`critique.md` counts as round 1). Read the earlier ones too, for history. If the user names a specific file, use that.
2. **Paper:** read `paper/paper.tex` completely, including anything it `\input`s or `\include`s, plus `references.bib` and the list of files in `paper/figures/`. Note the document class options (`conference` vs `journal`) and compare with the venue assumed in the critique.
3. **Server tree:** `server/project_tree.tsv`. If it is missing, ask the user to run this from the server's project root and save the output to that path (or paste it, and you save it). Ask them to exclude secrets. Never ask for hostnames, passwords, tokens, or keys.

```bash
find . -type f \
  -not -path '*/.git/*' -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' -not -path '*/.venv/*' \
  -not -name '.env*' -not -name '*.pem' -not -name '*.key' \
  -printf '%p\t%s\t%TY-%Tm-%Td\n' | sort > project_tree.tsv
```

   If `-printf` is unsupported (macOS/BSD), use `find . -type f | sort` or `ls -lR`. For a huge tree, ask first for `find . -maxdepth 3 -type d -not -path '*/.git/*' | sort`, then for expansions of only the directories that matter.
4. **Local code:** it is not part of the standard layout, so look for it (`src/`, `code/`, `experiments/`, notebooks, scripts at the root). If you cannot find it, ask where it lives. Read it before writing any server script.
5. **Ledger:** check `improvements/IMPROVEMENT_LOG.md`. Then choose the mode:
   - **New critique** (a `critique-N.md` newer than the ledger's last round): run Steps 1 to 4.
   - **Results waiting** (folders in `server/results/` not yet marked ingested in the ledger): run Step 5.
   - Both can apply in one pass. Do Step 5 first so the new evidence informs the edits.

After reading the tree, give a short read-back (at most about 15 lines) of how you understand the server layout: code, configs, datasets, results and logs, checkpoints, notebooks, environment files, existing figures. Flag ambiguities and move on.

## Step 1: Triage the critique

Give every finding an ID scoped to its round (`R2-C01`, `R2-C02`, ...) in severity order (FATAL, MAJOR, MINOR, NIT), keeping the critique's own wording. Sort each into one bucket and show a table:

| ID | Item (severity) | Bucket | Action | Needs |
|---|---|---|---|---|

- **A: Fixable in the text now.** Wording, grammar, structure, abstract, acronyms, headings, captions, IEEE formatting, reference formatting, redundancy, flow.
- **B: Needs new evidence from the server.** Missing baselines, ablations, seeds and variance, statistical tests, dataset statistics, hyperparameters, hardware and software details, latency or memory numbers, low-quality figures that must be regenerated from data, unverified numeric claims.
- **C: Needs the user.** Novelty positioning, missing related work, ethics or data statements, what to claim, anything only the author knows.
- **D: Cannot be fixed by editing.** A fundamentally weak contribution, an unsound method, data that does not exist. Say so plainly and suggest the smallest honest reframing (narrower claim, workshop paper, different venue).

Compare against the ledger and earlier critiques:
- **RECURRING:** an issue raised in an earlier round that is still present. Raise its priority and say it is a repeat.
- **REGRESSION:** an item marked Done that has come back. Find what broke it.
- **Confirmed fixed:** earlier items the new critique no longer raises. Mark them Done and move on.

Do Bucket A immediately. Bucket B becomes scripts. Bucket C becomes a short numbered question list. Bucket D goes in the report.

## Step 2: Map the server and local code to the paper (evidence audit)

1. List every quantitative claim in `paper.tex` (abstract, tables, figures, text). For each, find the file in the server tree or local code that could back it and mark it **Traceable**, **Probably traceable** (file exists, contents unseen), or **Untraceable**. Untraceable claims are high risk: the user finds the source, or the claim is softened or removed.
2. Read the local code to learn what the experiments actually do: models, datasets, splits, metrics, seeds, hyperparameters. Report every mismatch between code and paper.
3. Compare local code with the server tree: files on the server that are missing locally, and the reverse. Do not assume the server runs the local version; ask for `git rev-parse HEAD` output when in doubt.
4. For each Bucket B item choose the cheapest route: **extract** from existing logs and results, **re-run** a small job, or **run** a new experiment.
5. Use environment files in the tree (`requirements.txt`, `environment.yml`, `Dockerfile`) when present; otherwise plan an environment-capture script.

## Step 3: Fix Bucket A in the paper

**Before editing:** if the repo is under git, check `git status`. Work on a new branch named `improve/round-N` so every change is reviewable with `git diff`. Do not commit to the main branch, push, or rewrite history unless asked.

**Writing trigger (mandatory).** Before you change any prose, read `.agent/skills/paper-writing/SKILL.md`, save a copy of the current `paper.tex` (`git show HEAD:paper/paper.tex > /tmp/paper_before.tex`), and run `python .agent/skills/paper-writing/scripts/prose_check.py paper/paper.tex` to find the hotspots. Apply the skill's rules to everything you write. The "Text" bullet below is done through that skill, not from memory.

**Edit `paper/paper.tex` and `paper/references.bib` in place.** Use the critique's IEEE audit as the checklist:

- **Front matter:** title, abstract (single paragraph, self-contained, no citations or undefined abbreviations), `\IEEEkeywords`, author block.
- **Text (via the paper-writing skill):** heading structure, acronyms defined at first body use, tense, filler words, verbosity, number density, redundancy, flow, inconsistent terminology.
- **IEEEtran hygiene:** remove layout hacks that fight the template (`geometry`, `\linespread`, forced font sizes, `\vspace` tricks, `\sloppy` used to hide overfull lines, manual `\small` in body text). These are formatting violations. Use `Fig.~\ref{}` and `Table~\ref{}`, cite equations as `(\ref{})` in IEEE style, put captions below figures and above tables, and place `\label` after `\caption`. Fix overfull lines by rewording, not by suppressing warnings.
- **Citations:** sorted numeric style via `IEEEtran.bst` and the `cite` package, brackets before punctuation, `in [3]` not `in Ref. [3]`.
- **`references.bib`:** normalize entries (author, title, year, venue, volume, number, pages, DOI), remove duplicates and unused entries, use `and others` instead of a literal "et al.", protect capitalization with braces, and make types correct (`@article`, `@inproceedings`, `@misc` for arXiv). Verify with web search when available that every entry really exists. Never invent an entry; flag suspicious ones to the user.
- **Figures:** reference every figure and discuss it in the text. Prefer vector PDF over raster. Use `\includegraphics[width=\columnwidth]` (3.5 in) or `\textwidth` for a full-width figure (7.16 in). Keep file names stable so `\includegraphics` lines don't need changing.

Where an edit depends on pending evidence, insert a visible marker such as `\textbf{[[PENDING: 03_ablation -> Table III]]}` so it cannot slip into a submission unnoticed. Before calling any version final, search the repo for `PENDING` and list what remains.

**Prose verification (after every round of prose edits).** Run `python .agent/skills/paper-writing/scripts/prose_check.py --compare /tmp/paper_before.tex paper/paper.tex` and then the plain diagnose command again. No number may vanish or appear without a source, no citation or label may be lost, and no HIGH flag may remain. Report the outcome in the changelog.

**Compile and verify.** If `latexmk` or `pdflatex` is available:

```bash
cd paper && latexmk -pdf -interaction=nonstopmode -file-line-error -outdir=build paper.tex
```

Read the log for undefined citations or references, missing figures, `Overfull \hbox`, float warnings, and BibTeX warnings. Render pages to images (`pdftoppm -r 100 -png`) and look at them. Check fonts and sizes (`pdffonts`, `pdfplumber`), page count against the venue limit, and column balance on the last page. Confirm each Bucket A formatting item is actually resolved rather than assumed. Make sure `paper/build/` is git-ignored. If no TeX toolchain is installed, say so and rely on static checks.

## Step 4: Write the server scripts and runbook

For every Bucket B item, produce the smallest script that answers it, using only paths from `server/project_tree.tsv`. Save scripts in `server/scripts/`. Choose from this menu and write only what the critique requires:

- **Environment and reproducibility capture:** OS, CPU and GPU model and count, RAM, driver and CUDA versions, Python and library versions, git commit, seeds, configs in use. Do **not** record usernames, hostnames, IP addresses, or environment variables; these files end up in a git repo and a paper.
- **Results extraction:** parse existing logs and result files into table-ready CSV plus a short summary.
- **Multi-seed runs and statistics:** repeat existing experiments across seeds, report mean and standard deviation or confidence intervals, and a significance test when comparing methods.
- **Baselines and ablations:** run the missing comparisons and component-removal variants using the repo's existing code and configs.
- **Dataset statistics:** sizes, class balance, splits, and a check that train and test do not overlap.
- **Efficiency profiling:** parameter count, FLOPs if measurable, latency, throughput, peak memory.
- **Figure generation:** read result CSVs and write publication-quality figures: vector PDF, 3.5 in wide for one column or 7.16 in for two, serif font with text at 8 pt or larger, distinct markers and line styles that survive grayscale printing, axes labelled in words with units.
- **Sanity and leakage checks:** confirm evaluation uses held-out data and that the reported metric matches its stated definition.

### Script standards

Every script starts with a header like this and follows it:

```bash
#!/usr/bin/env bash
# ------------------------------------------------------------
# Script:     01_env_info.sh
# Answers:    R2-C07 (missing hardware/software details)
# Reads:      nothing outside PROJECT_ROOT
# Writes:     paper_artifacts/<timestamp>/ (new directory only)
# Runtime:    < 1 min, no GPU needed
# Run:        PROJECT_ROOT=/path/to/project bash 01_env_info.sh
# Send back:  paper_artifacts/<timestamp>/SUMMARY.md
# ------------------------------------------------------------
set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
```

(Python scripts use the equivalent header as a docstring plus `argparse`.)

- **One job per script**, numbered in run order, named for what it does.
- **Write only to a new `paper_artifacts/<timestamp>/` directory** under `PROJECT_ROOT`. Never modify or delete existing files, checkpoints, or results.
- **Check before assuming:** test that tools and files exist (`command -v`, `test -f`), exit with a clear message if not, and print versions.
- **Heavy jobs get a `--quick` smoke mode** (tiny subset, one epoch or one seed) and state estimated runtime and resources in the header. Recommend the quick mode first.
- **Reproducible:** fixed seeds, logged configs, git commit recorded in the output.
- **Small, returnable outputs:** each script ends by writing a `SUMMARY.md` (or `summary.json`) under about 200 lines, plus the CSVs and figures it produced. Extract metric lines from large logs instead of copying them. Never produce outputs that must travel in gigabytes.
- **No secrets, no network, no installs.** If a dependency is missing, name it and let the user install it.
- **Readable:** comment the non-obvious parts, so the user can trust the script before running it.

Validate what you can without touching the server: `bash -n` and `shellcheck` (if available) for shell, `python -m py_compile` for Python, and parser tests against real sample files already in the repo. Discard any test output.

### `server/RUNBOOK.md`

For each script: the order to run, the exact command, runtime and resource estimate, the critique IDs it answers, and a "send back" checklist. Put quick-mode commands first. Include the return instruction: copy the script's `paper_artifacts/<timestamp>/` contents (summary, CSVs, figures; not checkpoints or datasets) into `server/results/<script-name>-<timestamp>/` in the repo, then tell the agent. Tell the user to copy `server/scripts/` to the server by whatever method they normally use.

## Step 5: Ingest returned results

For each new folder in `server/results/` not yet marked ingested:

1. **Validate first.** Look for errors, empty or partial outputs, mismatched seeds, and implausible values (a metric of exactly 1.000, zero variance, a small baseline beating a far larger model by a wide margin). Investigate and tell the user rather than absorbing it. Confirm the outputs correspond to the code version the paper describes.
2. **Reconcile with existing claims.** If numbers differ from the paper, update the paper and rewrite the affected claims. If a claim no longer holds, say so directly.
3. **Propagate every change.** A number usually appears in the abstract, introduction, results, discussion, captions, and conclusion. Search the whole paper for each changed value and update every occurrence.
4. **Write the new results text with the paper-writing skill:** one paragraph per question, the answer first, one or two numbers against the baseline, a pointer to the table. Full numbers live in the tables, not in the sentences. **Add what reviewers asked for:** experimental-setup details (hardware, software versions, seeds, hyperparameters), mean ± std or confidence intervals, significance results, ablation and baseline tables, dataset statistics, and any limitation the new evidence reveals.
5. **Copy figures** into `paper/figures/` and update `\includegraphics` only if names changed. Verify width, font size, and that each figure is cited and discussed.
6. **Replace every `PENDING` marker** with the real content and remove the marker. Recompile and re-verify (Step 3).
7. Mark the results folder as ingested in the ledger.

## Step 6: Close the loop

Update `improvements/IMPROVEMENT_LOG.md` every pass. It is the memory that survives between sessions.

```markdown
| ID | Round | Critique item | Status | What changed / what's pending |
|----|-------|---------------|--------|-------------------------------|
| R1-C01 | 1 | Abstract overclaims | Done | Rewritten, removed "state-of-the-art" |
| R1-C04 | 1 | No ablation | Awaiting server results | Run 03_ablation.py, drop results in server/results/ |
| R2-C02 | 2 | Fig. 3 unreadable | Recurring | Regenerated via 05_figures.py, awaiting output |
| R2-C09 | 2 | Which venue? | Needs your input | |
| R2-C12 | 2 | Incremental contribution | Won't fix | Suggest narrowing the claim |
```

Statuses: **Done**, **Awaiting server results**, **Needs your input**, **Won't fix**. Tag repeats as **Recurring** and returns as **Regression**. Also record which `server/results/` folders have been ingested.

Write `improvements/changelog-N.md`: each critique ID mapped to the exact edit made, with file and section.

At the end of the pass, list what is still open and the user's next action. When the ledger is mostly Done, recommend running the critique skill again on the revised paper. That produces `critique-(N+1).md`, and the next improve pass begins from it.

## Reply style

Efficient, direct, collaborative. Keep the chat reply short: what was fixed, which scripts to run first, what you need back, and the Bucket C questions. The detail lives in the changelog, ledger, and runbook. If the critique was delivered in the greedy-guide voice, a brief dash of that attitude is fine ("Run this first, I want those numbers before the deadline"), but all work products (paper text, scripts, logs) stay plain and professional.
