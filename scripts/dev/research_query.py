import sys
from openai import OpenAI

prompt = """
Below is an official Smart India Hackathon (SIH) problem statement overview and analysis for a MATLAB-based retinal image analysis pipeline for automated Diabetic Retinopathy (DR) screening:

<SIH_PROBLEM_STATEMENT>
What They're Asking For
Design a MATLAB-based retinal image analysis pipeline for automated DR screening addressing real-world deployment challenges: 1. Image Quality Assessment and Enhancement: Automatically evaluate fundus images for adequacy (focus, illumination, field of view). Apply adaptive enhancement (CLAHE, illumination normalization, denoising) for borderline images; reject ungradeable ones with recapture feedback. 2. Retinal Structure Segmentation: Extract clinically relevant structures - optic disc/fovea localization, vessel segmentation, microaneurysm detection, exudate segmentation, hemorrhage classification, and neovascularization detection. 3. DR Severity Grading: Classify using the International Clinical DR severity scale (Levels 0-4, from no DR to proliferative DR) with clinically acceptable sen
Tools: Image Processing Toolbox, Computer Vision Toolbox, Deep Learning Toolbox, Medical Imaging Toolbox, Simulink, Statistics and Machine Learning Toolbox
Analysis - Innovation Scope
Breakthrough: Uses advanced/emerging tech (computer vision), not just a digitization task.
Invention Effort: Low. Effort score: 2
Competitive Landscape: Medium Crowding (2 of 226 similar PS). Most teams will lean on imaging, illumination and severity-style builds. How to stand out: The official text calls for computer vision, build it properly instead of skipping it.
SWOT:
Strengths: Genuine modern-tech core. Single clean build path.
Weaknesses: Expected Solution is thin in official text.
Opportunities: Be upfront about model's accuracy under real conditions. Only 2 PS share this theme.
Threats: Most teams will build standard versions.
Evaluator likely to ask: Where is input/training data from? Why is tech right call? What happens when connectivity drops/hardware fails? How holds up with real production-scale data? Who benefits and how measured?
</SIH_PROBLEM_STATEMENT>

Below is a summary of the user's project `OptiGemma` (aka `DrishtiAI`) from its README:
<OPTIGEMMA_PROJECT>
DrishtiAI is an end-to-end clinical platform (React frontend, Flask backend) for DR screening.
Key Features:
- Dual-Model Diagnostic Engine: PyTorch (EfficientNet-B3) & TensorFlow (Tanwar-12) fallback, >98% accuracy on APTOS 2019.
- Explainable AI: Raw Autofocus Fundus, Multi-Scale Frangi Microvascular Mask, Grad-CAM.
- Gemma-4 Medical Intelligence for plain-language reports.
- Multilingual Audio Counseling (Web Speech Synthesis).
Pipeline matches PS exactly:
1. Image Quality Gate: ACCEPT/ENHANCE/REJECT (recapture feedback).
2. Retinal Structure Segmentation: optic disc/fovea, Frangi vessel segmentation, lesions.
3. Calibrated DR Grading: ordinal probabilities, referable binary flag, confidence.
4. Explainability & Reports (Offline mode available).
MATLAB Hybrid Architecture: Uses MATLAB for clinical core (assessQuality.m, enhanceImage.m, importModels.m, runDRScreening.m, Simulink for throughput simulation).
Addresses real-world challenges: Offline Mode for rural deployments, fallback low-compute model (Tanwar-12 runs on single-core CPU).
</OPTIGEMMA_PROJECT>

Based on this, please provide a detailed analysis:
1. What the user's project (OptiGemma/DrishtiAI) is doing and what it currently provides relative to the problem statement.
2. What "serious and unique propositions" other teams are likely to choose and implement.
3. How the user's project stacks up against these likely competitor propositions, and what they can do to stand out even more to the judges based on the evaluator scorecard and questions.
"""

client = OpenAI(base_url="http://localhost:8081/v1", api_key="sk-not-needed")
print("Sending query to gemini-3.5-flash-thinking...")
response = client.chat.completions.create(
    model="gemini-3.5-flash-thinking",
    messages=[{"role": "user", "content": prompt}]
)

with open("analysis_output.md", "w", encoding="utf-8") as f:
    f.write(response.choices[0].message.content)
print("Analysis complete. Saved to analysis_output.md")
