import asyncio
import logging
import json
import httpx

from autoapply.env import GEMINI_API_KEY
from autoapply.models import LLMResponse, get_gemini_compatible_schema
from autoapply.logging import get_logger

get_logger()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
    You are a Senior Technical Resume Strategist and ATS Optimizer. Your job is to analyze a candidate's resume against a Job Description (JD), score the fit, and then **rewrite the resume to perfection**.

    ### GOAL:
    Produce a rewritten resume that is **visually dense, technically exhaustive, and fills exactly one full page (approx. 600+ words)**. You must strictly preserve the user's existing skills while aggressively adding JD keywords.

    ### INPUT DATA:
    1. Candidate's Original Resume
    2. Target Job Description (JD)

    ### PART 1: SCORING & ANALYSIS
    Before rewriting, analyze the input:
    - **Tool Match:** Compare tools mentioned in the JD vs. the Resume. High score if coverage is >90%.
    - **Role Match:** Compare JD responsibilities vs. Resume experience. High score if direct "Problem-Solution" matches exist.
    - **Score:** Assign a score out of 100.

    ### PART 2: REWRITE EXECUTION RULES (STRICT):

    1. **The "Additive" Skills Strategy (CRITICAL):**
    * **Rule #1 (Preservation):** You are **strictly FORBIDDEN** from removing any technical skills, tools, or languages listed in the Original Resume. If the user lists a niche tool (e.g., 'Ray Serve', 'Go'), you MUST keep it.
    * **Rule #2 (Expansion):** Scan the JD for missing high-value keywords and **ADD** them to the list.
    * **Rule #3 (Categorization):** Group the final merged list into these 6 categories:
        1. Languages
        2. Big Data & Streaming
        3. Cloud & Infrastructure
        4. Databases & Storage
        5. DevOps & CI/CD
        6. Concepts & Protocols

    2. **The "Vertical Volume" Experience Strategy:**
    * **Recent Role:** Generate **5-6 bullet points**.
    * **Previous Role:** Generate **4-5 bullet points**.
    * **Oldest Role:** Generate **4-5 bullet points**.
    * **Length Constraint:** Every bullet point must be **1.5 to 2 lines long**. Use the "Context-Action-Result" structure (e.g., "Deployed X using Y to achieve Z...").
    * **Tech Stack Footer:** At the very bottom of *each* job entry, add a specific field: "Tech Stack: [List tools used in this job]".

    3. **Professional Summary:**
    * Write a dense exactly 3 line paragraph merging the candidate's background with the specific JD focus (e.g., Energy, Finance, Security).
"""


async def extract_details(title: str, content: str, resume: str) -> LLMResponse:
    logger.debug("Starting to extract details from the content using LLM")
    message = f"""
        Resume starts here
        ---
        {resume}
        ---
        Resume ends here

        Job description starts here
        ---
        {title}
        {content}
        ---
        Job description ends here
    """
    return await chat_with_gemini(message)


async def chat_with_gemini(
    message: str,
    system_prompt: str = SYSTEM_PROMPT,
    model_name: str = "gemini-3-pro-preview", 
) -> LLMResponse:
    logger.debug(f"Sending message to Gemini REST API (Model: {model_name})")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Use v1beta (Standard for Previews)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}
    clean_schema = get_gemini_compatible_schema(LLMResponse)

    payload = {
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": clean_schema,
             # Optional: Control reasoning depth for Gemini 3 (low/high)
             "thinkingConfig": { "thinkingLevel": "high" } 
        },
    }

    # Fallback (1.0 & 3.0 Reasoning): Merge System Prompt into User Message
    final_user_message = f"System Instructions: {system_prompt}\n\nUser Query: {message}"

    # Construct Contents
    payload["contents"] = [
        {
            "role": "user",
            "parts": [{"text": final_user_message}]
        }
    ]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            response_json = response.json()

            if "candidates" in response_json and len(response_json["candidates"]) > 0:
                candidate = response_json["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    text_content = candidate["content"]["parts"][0]["text"]
                    logger.debug(f"LLM response: {text_content}")
                    data = json.loads(text_content)
                    return LLMResponse(**data)

            logger.error(f"Unexpected response structure: {response_json}")
            raise ValueError("Invalid response structure from Gemini API")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        raise ValueError(f"Gemini API Error: {e}")
    except Exception as e:
        logger.error(f"LLM Call failed: {e}")
        raise ValueError(f"LLM Error: {e}")

if __name__ == "__main__":
    # Example usage for testing
    async def main():
        try:
            result = await extract_details(
                title="Software Engineer",
                content="Required: Python, AWS, Docker.",
                resume="Experienced Python Developer with AWS skills.",
            )
            print(result)
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
