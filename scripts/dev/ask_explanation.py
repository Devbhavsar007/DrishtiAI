import sys
from openai import OpenAI

with open("README.md", "r", encoding="utf-8") as f:
    readme_content = f.read()

prompt = f"""
Here is the README and context for the project 'OptiGemma' (also referred to as DrishtiAI):

{readme_content}

As an experienced ML engineer and analyst and teacher, explain the complete project from scratch to advanced.
Include:
- What this model does and how it does it.
- The entire workflow and architecture.
- Explain the pipeline in extreme detail. For each step, mention which popular algorithm is used, what exactly it does, and WHY that specific algorithm was chosen over others in the same category (e.g. why Frangi vessel extraction over other edge detectors, why EfficientNet-B3 over ResNet/VGG, why the Tanwar-12 custom model over MobileNet, why Grad-CAM over SHAP/LIME, why Gemma-4 over other LLMs, etc).
- Teach everything as if I am a beginner, starting from the basics and gradually moving to advanced concepts.

Provide a highly comprehensive, extremely detailed explanation. Do not omit technical details, but explain them clearly for a beginner to understand over time.
"""

client = OpenAI(base_url="http://localhost:8081/v1", api_key="sk-not-needed")
print("Sending request to gemini-3.5-flash-thinking for deep project explanation...")
response = client.chat.completions.create(
    model="gemini-3.5-flash-thinking@think=0",
    messages=[{"role": "user", "content": prompt}]
)

explanation = response.choices[0].message.content.strip()

with open("project_explanation_deep.md", "w", encoding="utf-8") as f:
    f.write(explanation)

print("Deep explanation saved to project_explanation_deep.md")
