"""
gpt_agent.py
Handles GPT prompt construction and OpenAI call.
"""
import os
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def build_prompt(user_prompt, df_head):
    """Builds a prompt for GPT using user input and a preview of the DataFrame."""
    return f"""You are a Python data analyst. Given the following data preview and user request, generate Python code to accomplish the task.

IMPORTANT: 
- Return ONLY the Python code, without any markdown formatting, comments, or explanations.
- Use the existing DataFrame variable 'df' that is already in scope - DO NOT create a new DataFrame.
- The DataFrame 'df' contains your data and is ready to use.

For charts: Use matplotlib.pyplot (plt) to create clear, professional charts. Set appropriate titles, labels, and formatting.

Data Preview (from DataFrame 'df'):
{df_head}

User Request:
{user_prompt}

Generate Python code using the existing 'df' DataFrame:"""

def get_code_from_gpt(user_prompt, df_head, model="gpt-3.5-turbo", temperature=0.2, max_tokens=1024):
    """Takes a user prompt and DataFrame preview, returns generated Python code."""
    prompt = build_prompt(user_prompt, df_head)
    return call_gpt(prompt, model, temperature, max_tokens)

def call_gpt(prompt, model="gpt-3.5-turbo", temperature=0.2, max_tokens=1024):
    """Calls OpenAI GPT with the constructed prompt."""
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content
