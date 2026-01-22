import asyncio
import logging
import json
import httpx

from autoapply.env import GEMINI_API_KEY
from autoapply.models import LLMResponse
from autoapply.logging import get_logger

get_logger()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
    You are an ATS Resume assistant, you will be given a resume and job descriptions title and content your job is to extract the below fields from the JD and score the resume.
    To score the resume:
      - check how many tools the JD mentions and how many of them are included in the resume (higher score if all of them are included and less if none are included)
      - check the duties, role and responsibility in the job description and check the job experience section of the resume and see if there are any direct matches (higher score if most of the poitns match and less if none match)

    For the detailed explaination:
      - give the strong points, weak points of the resume for this JD
      - give some job experience points for airfold and kantar that can be used to replace the current points in resume to make the resume a stronger match for the JD 
      - the points given should be 1 sentence, with measurable impact at the end and mention a tool and responsibility. The point itself should be readable and not context heavy simple but still self-explanatory
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
    model_name: str = "gemini-2.0-flash",
) -> LLMResponse:
    logger.debug(f"Sending message to Gemini REST API (Model: {model_name})")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}

    # Construct the payload according to Gemini REST API
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": message}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": LLMResponse.model_json_schema(),
        },
    }

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
