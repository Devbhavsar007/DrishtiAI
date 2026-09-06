from openai import OpenAI

# Connect to the local gemini-web2api proxy
client = OpenAI(
    base_url="http://localhost:8081/v1",
    api_key="sk-not-needed"
)

print("Connecting to Gemini API via local proxy...")

# Call the API
response = client.chat.completions.create(
    model="gemini-3.5-flash-thinking",
    messages=[
        {"role": "user", "content": "Explain quantum computing in one short sentence."}
    ]
)

print("\n--- Response ---")
print(response.choices[0].message.content)
