---
name: paper-writing
description: Write and rewrite the prose of a LaTeX research paper in a plain, direct, modest student voice, with disciplined use of numbers and no padding. Use this skill every time any text in paper/*.tex is written or changed (abstract, introduction, related work, methods, experimental setup, results, discussion, limitations, conclusion, captions, headings), including edits made by the improve or paper-sync skills, and whenever the user says the paper is verbose, wordy, "numbers everywhere", stiff, robotic, over-polished, or should sound like a student wrote it. Not needed for pure bibliography, figure-file, or code changes with no wording involved.
---

# Paper Writing: Plain Words, Few Numbers, No Padding

The problem this skill fixes: the paper reads like numbers thrown at the reader, wrapped in long sentences that say little. The target voice is a careful, honest undergraduate who understands their own work. They use plain words, short sentences, and direct statements. They say what they did, what they saw, and what they are not sure about.

That voice is plain, not sloppy. Grammar stays correct. Never add deliberate mistakes, slang, or contractions, and never fake naivety. It also stays IEEE-appropriate: formal enough, just not inflated.

This skill is about clarity and register. It is not a way to hide who wrote the text. Follow the venue's and the university's rules on disclosing AI assistance.

## The one rule that beats every other rule

**Changing the voice must never change the facts.** A rewrite may cut words, move numbers into tables, and soften claims that the evidence does not support. It may not change what was done, what was measured, or what was found. Step 4 checks this with a tool.

## Trigger

Apply this skill whenever you write or change prose in `paper/*.tex`. That includes abstract, headings, captions, and any sentence added by another skill (for example the Methods text from paper-sync or the results text from ingesting server outputs). Text inside `\textbf{[[PENDING ...]]}` markers is left alone. Pending-result sentences still follow the voice rules.

## Step 1: Diagnose before you touch anything

1. Save the current version for comparison (`git show HEAD:paper/paper.tex > /tmp/paper_before.tex`, or copy the file).
2. Run the checker from the repo root:

```bash
python .agent/skills/paper-writing/scripts/prose_check.py paper/paper.tex
```

It prints a per-section table (words, average sentence length, numbers per 100 words) and flags long sentences, long paragraphs, number-dense sentences and paragraphs, tables restated in prose, filler phrases, overclaiming words, and headline numbers repeated many times. It is advisory: heuristics can be wrong, so read each flag. Start the rewrite with the sections that have the highest numbers-per-100-words and the longest average sentence (usually Abstract, Introduction, and Results).

## Step 2: Rewrite, in this order

For each paragraph:

1. **Decide its one point.** Write it as a single plain sentence on scratch paper. If you cannot, the paragraph needs restructuring, not polishing. Put that sentence first.
2. **Cut.** Delete every sentence that does not support the point, restates the previous sentence, or only announces what is coming ("In this section we will discuss..."). Delete summary sentences at the end of a paragraph that repeat it.
3. **Simplify words** using the table below.
4. **Fix the numbers** using the numbers policy.
5. **Match claims to evidence** using the claims policy.
6. **Read it aloud.** If you run out of breath, split the sentence. If a classmate could not follow it on the first read, rewrite it.

A first pass on a verbose section usually removes 20 to 40 percent of the words. That is a sign it is working, not a target. Never cut a detail a reader needs to reproduce or judge the work; move it to a table instead.

## Numbers policy (this is what "numbers thrown everywhere" means)

1. **Every number in prose must earn its place.** It supports the claim the sentence is making. If the reader can read it in a table, point to the table and give the pattern in words.
2. **Claim first, number second, comparison always.** A lone number means nothing. Write "The retrained model finds more platelets than the baseline (AP 0.55 vs 0.48)", not "The AP was 0.55."
3. **Limits.** At most 3 numbers in a sentence and about 5 in a paragraph. (Not counted: citation numbers, table, figure, equation and section numbers, years.) Beyond that, use a table and describe the pattern: "all three classes improve, most for platelets."
4. **Say each number once, in the right place.** Headline numbers can appear in the abstract, the results, and at most the conclusion. Do not repeat them in the introduction, methods, and discussion. The single source of truth is the table.
5. **Setup numbers go in a table.** Learning rate, batch size, epochs, split sizes, thresholds: put them in a training-configuration table or one compact sentence. Do not narrate ten hyperparameters in flowing prose.
6. **Round to what the data can support.** Use one consistent precision per metric everywhere (for example three decimals for mAP, one decimal for percentages). Do not write 0.41237. With a small evaluation set, extra decimals suggest precision the data does not have.
7. **Say what the number means.** Give the metric, the dataset or split, and the direction ("higher is better", "ms per image"). Say "percentage points" or "relative" when reporting a difference.
8. **Uncertainty.** If a value comes from one run, say so. If you give a mean, give the spread or the number of runs.
9. **Never use a number to sound rigorous.** If a sentence works without it, remove it.
10. **Do not list per-class numbers in a sentence.** Describe the ranking or the biggest difference and refer to the table.

## Concision policy

- **Sentences:** aim for 12 to 25 words; split anything past about 32. **Paragraphs:** three to six sentences, one idea each.
- **Active voice with "we"** for what the authors did ("We fine-tuned the model on 50 images"). Passive is fine when the actor does not matter ("Images were resized to 640 pixels").
- **Replace nominalizations with verbs:** "perform an evaluation of" becomes "evaluate", "give consideration to" becomes "consider".
- **Cut intensifiers** (very, highly, extremely, quite) and stacked adjectives.
- **Use one term per thing.** Do not alternate "images", "samples", "slides", and "frames" for the same object. Do not vary metric names.
- **Define each acronym once** in the body, then use it consistently.
- **Do not repeat the abstract** in the introduction or conclusion. Each has its own job (see below).

### Plain-word replacements

| Instead of | Write |
|---|---|
| utilize, leverage | use |
| in order to | to |
| due to the fact that | because |
| a large number of, a plethora of, numerous | many |
| has the ability to, is able to | can |
| with respect to, in the context of | for, in, about |
| prior to / subsequently | before / then |
| facilitate | help, allow |
| serves as | is |
| it is worth noting that, it should be noted that, it is evident that | (delete) |
| plays a crucial role in | (say what it actually does) |
| furthermore, moreover, additionally | (delete, or "also" once in a while) |
| comprehensive, holistic, seamless, cutting-edge, robust | (delete, or give the evidence) |
| impressive, remarkable, superior | (give the number against the baseline) |
| extensive experiments | (name the experiments) |
| delve into, landscape, realm | look at, area, (delete) |

Also avoid these patterns, which read as padded: "not only X but also Y", lists of three adjectives ("fast, accurate, and efficient"), and closing sentences like "This highlights the importance of..." that only restate the paragraph.

## Claims policy

- **Match the verb to the evidence.** "We found", "the results suggest", "is consistent with" for observations. Use "show" only when the result directly supports it. Avoid "prove" and "demonstrate" unless there is a proof.
- **"Significant" is a statistics word.** Use it only with a test and a p-value. Otherwise give the difference.
- **Do not write "novel", "first", or "state-of-the-art"** unless it has been verified and the comparison is named.
- **One hedge per claim.** "May possibly suggest" is three hedges. Pick one.
- **Do not generalize past the data.** A result on one dataset and one small test set is about that dataset. Say "on the clinical images", not "in clinical settings".
- **Report negative and mixed results plainly.** "The change did not help on the clinical images" is a valid sentence. Do not bury it.
- **A design reason is not evidence.** "Rotation is used because cells have no fixed orientation" is a motivation. It is not a finding that rotation helped.
- **Tense:** past for what was done and observed; present for what the paper does ("Section IV describes...") and for general facts ("Table II lists...").

## Section guide

| Section | Job | Shape |
|---|---|---|
| **Title** | Say what the paper is about | Specific and plain. No abbreviations if avoidable. |
| **Abstract** | Let a stranger decide whether to read on | Problem, what we did, the headline result with its baseline (at most 2 or 3 numbers), and the main limitation. Typically about 150 to 250 words; no citations or equations; check the venue template. |
| **Introduction** | Motivate and state the contribution | Context in two or three sentences, the gap, what we did, then at most three contributions written as things done ("We evaluate...", "We add..."), not adjectives. No results tables in prose. |
| **Related work** | Position the work | Group by theme, not by paper. End each paragraph by saying how this work differs. Do not dump citations. |
| **Method** | Let a reader repeat it | Say what, then why, then how. One paragraph per component. Define every symbol once. Put settings in a table. |
| **Experimental setup** | Make the numbers interpretable | Datasets and splits (a table), metrics defined, baselines, implementation details (a table), hardware, seeds. |
| **Results** | Answer questions with evidence | One paragraph per question. Sentence one: the answer. Sentence two: one or two numbers against the baseline with a table or figure pointer. Then one sentence of explanation only if the evidence supports it. |
| **Discussion** | Say what the results mean and do not mean | Link findings to limits; include failure cases. |
| **Limitations** | Be straight about weaknesses | Small evaluation set, few runs, bundled changes, data source, added cost. Plain prose. |
| **Conclusion** | Close | What we did, the headline finding (or none), what comes next. No new information. |
| **Captions** | Stand alone | First sentence says what is shown. Second says what to notice. Define abbreviations and units. Table captions above, figure captions below (IEEE). |

## Worked examples

These use made-up numbers only to show the pattern. **Never copy a number from these examples into the paper.**

**Number dump.**
Before: "The baseline achieved an AP of 0.61 for RBC, 0.72 for WBC and 0.48 for PLT, giving an mAP of 0.603, while the retrained model reached 0.64, 0.75 and 0.55, giving 0.647, with latencies of 12.4 ms and 15.1 ms respectively."
After: "The retrained model beats the baseline on all three cell types, most clearly for platelets (Table II). It is also slightly slower per image."

**Padded opening.**
Before: "It is worth noting that automated blood cell counting plays a crucial role in modern diagnostics, and the ability to utilize deep learning in order to facilitate this process is highly important."
After: "Counting blood cells by hand is slow and tiring, so automatic counting is useful."

**Overclaim.**
Before: "Our novel approach demonstrates superior robustness and significantly improves generalization across domains."
After: "On the clinical images, the fine-tuned model scored higher than the baseline. We only tested one clinical dataset, so we cannot say how well this holds elsewhere."

**Design reason presented as a result.**
Before: "Full rotation augmentation improves rotation invariance."
After: "We rotate training images by any angle because cells have no fixed orientation on a slide. Whether this helps is tested in Section V."

**Setup in prose.**
Before: "We trained for 100 epochs with a batch size of 16, learning rate 0.001, patience 20, mosaic closing at 15, and a 70/30 split."
After: "Table III lists the training settings."

## Step 3: Keep LaTeX intact

- Do not break `\cite`, `\ref`, `\label`, math, or `~` before references. Keep `Fig.~\ref{}` and `Table~\ref{}`.
- Edit in place and keep the file's existing line-wrapping style. Do not touch comments, `PENDING` markers, or the preamble.
- If a number moves out of prose, confirm it is in the table it now depends on.

## Step 4: Verify meaning and voice

1. Compare with the saved copy:

```bash
python .agent/skills/paper-writing/scripts/prose_check.py --compare /tmp/paper_before.tex paper/paper.tex
```

   - **Numbers that no longer appear anywhere** are a HIGH flag: a fact may have been lost or mistyped. Restore it or confirm it was deliberately removed.
   - **New numbers** must each trace to a result file, the code, or the baseline. Anything else is unsupported: remove it.
   - **Lost citation keys** and **`\ref` targets with no `\label`** must be explained or fixed.
   - The word-count line shows how much was cut.
2. Run the diagnose command again. There should be no HIGH flags. Review remaining WARN flags and fix the ones that are real. Use `--strict` to make HIGH flags a failing exit code.
3. Compile the paper and confirm the page count and layout still fit.
4. Read the abstract and the first paragraph of Results once more, out loud. If either sounds like an advertisement, revise.

## Step 5: Record it

In the changelog for the round, list which sections were rewritten, which numbers were moved into tables, and which claims were softened and why. If the checker flagged something you deliberately kept (for example a necessary long sentence), say so.
