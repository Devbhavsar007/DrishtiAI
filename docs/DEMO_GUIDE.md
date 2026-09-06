# DrishtiAI Hackathon Demonstration & Evaluator Script

**Purpose:** 5-Minute and 10-Minute Clinical & AI Safety Evaluation  
**Audience:** Technical Judges, Hackathon Evaluators, Clinical Specialists, Red-Team Reviewers

---

## 1. The 3-Minute Elevator Pitch

> *"Most medical AI hackathon demos make a fatal mistake: they present a black-box neural network as an 'autonomous doctor' that blindly outputs a diagnosis and fabricates continuous progression curves from a single photograph.*  
>  
> *In real clinical medicine, this fails catastrophically.*  
>  
> *DrishtiAI is fundamentally different. It is built as a **production-hardened clinical decision-support and screening platform**. It incorporates **pre-inference hygiene gates**, **anatomical landmark cross-checking**, **out-of-distribution rejection**, and an **uncompromising policy of scientific honesty** that refuses to hallucinate historical timelines without actual cohort data.*  
>  
> *Let us demonstrate how DrishtiAI behaves when things go right—and more importantly, how it defends itself when things go wrong."*

---

## 2. Live Evaluator Flow (Step-by-Step)

### Phase 1: The Golden Path (Standard Screening)
1. Navigate to **New Scan**.
2. Click **Preset: Sunita Devi (Mild NPDR)**.
3. Select **Laterality: OD (Right Eye)**.
4. Click **Run Full AI Diagnostic Analysis**.
5. **Point out to Judges:**
   - **Explainability Triptych:** Original scan, vessel segmentation map, and Grad-CAM attention heatmap proving the network is attending to microaneurysms rather than background glare.
   - **Clinical Decision Arbitration Banner:** Displays `Safety State: PASS`, `Automation Level: DECISION_SUPPORT`, and verified reason codes.
   - **Empathetic Gemma-4 Report:** Multilingual clinical communication in English, Hindi, and Gujarati with one-click screen reader audio.
   - **Honest Longitudinal Disclaimer:** Notice that DrishtiAI displays: *"Clinical Honesty Notice: Progression prediction is advisory. DrishtiAI does not fabricate temporal curves without verified historical visits."*

---

### Phase 2: Red-Teaming the Safety Gates (1-Click Demonstration)
In **Step 2**, open the **Evaluator & Red-Team Suite** panel to trigger the canonical edge-case simulations:

#### A. Scenario 5: Quality Gate (Optical Blur & Cataract Haze)
- **Action:** Click button **5. Quality Reject**.
- **Result:** Image validation gate blocks inference. Emits reason code `IMAGE_QUALITY_DEFICIENT`. Prevents garbage-in/garbage-out clinical hazard.

#### B. Scenario 7: Out-of-Distribution Non-Fundus Rejection
- **Action:** Click button **7. Non-Fundus OOD**.
- **Result:** Non-retinal photograph (e.g. skin lesion or document) is detected by the domain validation pipeline. System refuses classification without crashing.

#### C. Scenario 8: Multi-Model Consensus Disagreement
- **Action:** Click button **8. Disagreement**.
- **Result:** Primary model grades Stage 1, while secondary shadow model grades Stage 3. DrishtiAI detects high epistemic uncertainty, raises `MODEL_DISAGREEMENT`, and mandates ophthalmologist triage.

#### D. Scenario 9: Anatomical Laterality Conflict
- **Action:** Click button **9. Laterality Warning**.
- **Result:** Operator marked Right Eye (`OD`), but the anatomical locator found the optic disc on the temporal side relative to the macula (indicating Left Eye `OS`). DrishtiAI flags `LATERALITY_MISMATCH` and requires human operator confirmation.

#### E. Scenario 10: Offline Sync & Conflict-Free Ledger
- **Action:** Click button **10. Offline Sync**.
- **Result:** Demonstrates the disconnected rural camp workflow. Data queued in SQLite outbox; simultaneous doctor notes enter `CONFLICT_REQUIRES_REVIEW` rather than suffering silent data loss.

---

## 3. High-Value Defensibility Talking Points

When judges ask:

1. **"Why don't you show a 5-year progression curve?"**  
   *Answer:* "Generating a 5-year longitudinal trajectory from a single static fundus photograph is scientifically indefensible AI hallucination. DrishtiAI only computes personalized progression if two or more historically validated scans exist for that patient. Otherwise, we provide population-risk cohorts and clearly state the limitation."

2. **"Can an attacker crash your backend with a decompression bomb?"**  
   *Answer:* "No. In `engine/safety/image_validator.py`, we parse file headers with strict magic byte checking and reject any uncompressed frame exceeding 25 megapixels before full memory allocation."

3. **"Is your system autonomous?"**  
   *Answer:* "No. Under FDA Software as a Medical Device (SaMD) and Indian ICMR guidelines, DrishtiAI is architected as Class II Clinical Decision Support. All critical recommendations enforce `DECISION_SUPPORT` automation levels requiring doctor sign-off."
