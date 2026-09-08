# Clinical Limitations & Operational Boundaries

## Scope of Clinical Application
DrishtiAI is an automated assistive screening platform designed for Diabetic Retinopathy (DR) triage in primary care and tele-ophthalmology settings. It is NOT an autonomous diagnostic replacement for a certified ophthalmologist.

## Key Limitations
1. **Field of View & Image Quality**: Requires at least 45° field-of-view posterior-pole fundus photographs. Poorly focused, low-illumination, or cataract-obscured images will trigger the Image Quality Assessment (IQA) gate and request re-capture.
2. **Co-morbidities & Differential Diagnosis**: DrishtiAI focuses primarily on diabetic retinopathy lesions (microaneurysms, hemorrhages, hard/soft exudates, neovascularization). Incidental pathologies (glaucoma, retinal vein occlusion, AMD) are evaluated via general anomaly detection but must be confirmed by an eye care professional.
3. **Hardware Variations**: Camera sensor variation, smartphone adapters, and pupil dilation status may alter colorimetry and resolution. Models are calibrated across heterogeneous datasets, but device drift is continuously monitored.
4. **Pediatric and Non-Diabetic Retinopathy**: DrishtiAI is calibrated exclusively for adult patients diagnosed with Type 1 or Type 2 diabetes.
