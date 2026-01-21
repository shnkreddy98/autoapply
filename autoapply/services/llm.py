import asyncio
import logging
import json

from google import genai
from google.genai import types

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
    """
    Sends a message to the Gemini API with a system prompt and returns the response.
    """
    logger.debug("Sending message to LLM")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in the environment.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model=model_name,
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=LLMResponse.model_json_schema(),
        ),
    )

    if response and response.text:
        logger.debug(f"LLM response: {response.text}")
        data = json.loads(response.text)
        return LLMResponse(**data)

    error = "No response received from Gemini."
    logger.error(error)
    raise ValueError(error)


if __name__ == "__main__":
    print(asyncio.run(extract_details(message="Hello There!")))
