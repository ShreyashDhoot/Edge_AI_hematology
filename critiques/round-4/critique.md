# 🔴 Round 4 Final Submission Audit — Dr. Anagha Deshpande's Review

> **Project:** Edge-AI Automated Peripheral Blood Smear Analysis  
> **Student Authors:** Shreyash Dhoot, Abhishek Karad, Pranav Lute, Prince Gupta  
> **Affiliation:** Department of Electrical and Electronics Engineering (DOEEE), MIT World Peace University, Pune  
> **Faculty Guide:** Dr. Anagha Deshpande, Assistant Professor, Dept. of DOEEE  
> **Target Venue:** IEEE Conference Format (10pt, two-column `IEEEtran`)  
> **Review Stage:** Final Pre-Submission Defense & Paper Sign-Off  

---

## Guide's Opening: Final Inspection

Listen to me very carefully, Shreyash, Abhishek, Pranav, and Prince.

You walked into my office three weeks ago with an unquantized YOLO model, zero clinical validation data, placeholder numbers, and dreams of presenting at an IEEE conference. Today, you finally brought me actual server results from your remote GPU runs, an INT8 quantized model compressed to 3.2 MB, and an honest CLSI EP09-A3 evaluation. 

My name is going on this paper as your project guide. Do you know what that means? It means when the department evaluation committee, the Dean of Research, and external IEEE reviewers read this manuscript, every single equation, figure, decimal point, and claim reflects directly on my academic standing and our department's reputation. I will not tolerate a sloppy submission.

I have reviewed your newly generated ablation outputs from `server/results/T-G06/generalized_results.json`. The numbers are real, but you have work to do before this manuscript is ready for my final signature.

---

## Scorecard

| Cat. | Area | Grade | Dr. Deshpande's Assessment |
|:---:|:---|:---:|:---|
| **A** | Contribution & Novelty | A− | The \$275 edge apparatus + INT8 quantization + CLSI validation is a complete, defensible engineering package. |
| **B** | Authorship & Affiliation | INC | **CRITICAL:** Author block still says *"Redacted for Double-Blind Review"*! Put your names and my name in the official format immediately. |
| **C** | Experimental Evidence | B+ | The server results are in. Table V must now be populated with the exact empirical metrics—no more `[[PENDING]]` tags. |
| **D** | Scientific Integrity | A | You did not hide the platelet drop on clinical smears. That honesty is what will get this paper accepted rather than desk-rejected. |
| **E** | Methodology Exposition | A | Reinhard stain normalization and CLAHE contrast enhancement are formally defined with proper citations. |
| **F** | Discussion of Ablations | B | You must explain the real physics of why Reinhard stain normalization dropped platelet recall until threshold tuning rescued it. |
| **G** | Writing Voice & Discipline | A− | Keep the voice disciplined: plain words, short sentences, active voice, and no numbers thrown at the reader without context. |
| **H** | IEEE Formatting & Layout | A | Zero overfull hboxes, correct captions above tables, balanced columns, exactly 8 pages. |

---

## Mandatory Directives for Final Paper Sign-Off

### 1. Authorship, Affiliations, and Acknowledgment (NON-NEGOTIABLE)
- Replace the anonymized placeholder with the official student and guide author block:
  - **Students:** Shreyash Dhoot, Abhishek Karad, Pranav Lute, Prince Gupta (Department of Electrical and Electronics Engineering, MIT World Peace University, Pune).
  - **Guide:** Dr. Anagha Deshpande (Assistant Professor, Department of Electrical and Electronics Engineering, MIT World Peace University, Pune).
- Update the `\section*{Acknowledgment}` to formally record the faculty mentorship and institutional facilities of MIT-WPU DOEEE.

### 2. Ingest the Real Empirical Numbers into Table V
- Eliminate every `[[PENDING: T-G06]]` marker in Table V.
- Populate Table V with your verified server outputs:
  - **Baseline BCCD:** mAP@0.5 = 0.856, RBC F1 = 0.65, WBC F1 = 0.98, PLT F1 = 0.84.
  - **Baseline Clinical 72 (Zero-Shot):** mAP@0.5 = 0.410, RBC F1 = 0.63, WBC F1 = 0.82, PLT F1 = 0.17.
  - **Retrained v2 (Clinical 72):** mAP@0.5 = 0.411, RBC F1 = 0.67, WBC F1 = 0.82, PLT F1 = 0.06.
  - **Retrained v2 + Stain Norm:** mAP@0.5 = 0.398, RBC F1 = 0.66, WBC F1 = 0.82, PLT F1 = 0.03.
  - **Retrained v2 + Stain Norm + Thresholding ($\tau_{\text{PLT}}=0.15$):** mAP@0.5 = 0.414, RBC F1 = 0.66, WBC F1 = 0.82, PLT F1 = 0.21.
  - **Retrained v2 (In-Domain BCCD):** mAP@0.5 = 0.829, RBC F1 = 0.64, WBC F1 = 0.98, PLT F1 = 0.84.

### 3. Discuss the Physical and Optical Mechanism in Section IV-H
- Do not just dump numbers in Table V! Explain the engineering mechanism:
  - **Leukocyte Stability:** WBC F1 remains rock-solid at 0.82 on clinical smears and 0.98 on BCCD across all models. Why? Because condensed nuclear chromatin stains dark violet under Giemsa dyes, providing overwhelming optical contrast that resists staining shifts.
  - **Erythrocyte Gain:** Retraining with in-plane rotation (180°) and MixUp boosted clinical RBC precision from 0.66 to 0.76 and F1 from 0.63 to 0.67.
  - **The Platelet Thresholding Rescue:** Explain why stain normalization alone dropped platelet F1 to 0.03 (Reinhard normalization maps faint clinical thrombocytes to lower intensity, pushing their model confidence below 0.25). Lowering the platelet decision boundary to $\tau_{\text{PLT}}=0.15$ rescues platelet recall from 0.018 to 0.175 and F1 to 0.211 (a 6.4$\times$ recovery). This is an essential engineering finding for edge hematology.

### 4. Writing Voice: Apply the Plain Student Voice Rules
- Follow your `paper-writing` guidelines strictly:
  - No filler: cut "it is worth noting that", "furthermore", "plethora".
  - Low number density: do not rattle off ten numbers in one paragraph. Let Table V hold the details while prose explains the trend.
  - Active voice: "We trained", "We evaluated", "We observed".

---

## Verdict

Implement these four directives, compile the final 8-page PDF cleanly, generate the PPT briefing document for our presentation defense, and this paper has my full approval for final submission.

— **Dr. Anagha Deshpande**  
*Assistant Professor, Department of Electrical and Electronics Engineering (DOEEE)*  
*MIT World Peace University, Pune*
