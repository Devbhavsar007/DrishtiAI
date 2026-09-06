import sys
from openai import OpenAI

prompt = """
Write a complete, robust python script using python-pptx to edit a presentation named "DrishtiAI_SIH2026_Pitch_Maitri-style.pptx". The script should save the output to "DrishtiAI_SIH2026_Pitch_Final.pptx".

Requirements:
1. Replace all text occurrences of "OptiGemma" with "DrishtiAI" across all slides, shapes, tables, and text frames, carefully preserving the text formatting at the run level.
2. On Slide 3 (slide index 2), identify an existing picture/image shape that corresponds to the "first row, 2nd column" (you can sort shapes by their top and left coordinates to find the one in the top-right).
3. Replace that specific picture shape with a new image from the local file "pipeline.png", keeping the same position and roughly the same size as the original image. You may need to insert a new picture shape at those coordinates and delete the old one.

Output ONLY the raw Python code. Do not wrap it in markdown code blocks like ```python. Just output the python code directly.
"""

client = OpenAI(base_url="http://localhost:8081/v1", api_key="sk-not-needed")
print("Handing off to gemini-3.5-flash-thinking@think=0 ...")
response = client.chat.completions.create(
    model="gemini-3.5-flash-thinking@think=0",
    messages=[{"role": "user", "content": prompt}]
)

code = response.choices[0].message.content.strip()

# Cleanup just in case it still adds markdown
if code.startswith("```python"):
    code = code.split("```python", 1)[1].rsplit("```", 1)[0].strip()
elif code.startswith("```"):
    code = code.split("```", 1)[1].rsplit("```", 1)[0].strip()

with open("edit_pptx_generated.py", "w", encoding="utf-8") as f:
    f.write(code)

print("The thinking model has generated the script: edit_pptx_generated.py")
