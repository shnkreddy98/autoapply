import asyncio
import logging
import json
import httpx

from autoapply.env import GEMINI_API_KEY
from autoapply.models import (
    ApplicationAnswers,
    Resume,
    TailoredResume,
    get_gemini_compatible_schema,
)
from autoapply.logging import get_logger
from typing import Union, Optional

get_logger()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TAILOR = """
    You are a Senior Technical Resume Strategist and ATS Optimizer. Your job is to analyze a candidate's resume against a Job Description (JD), score the fit, and then **rewrite the resume to perfection**.

    ### GOAL:
    Produce a rewritten resume that is **visually dense, technically exhaustive, and fills exactly one full page (approx. 600+ words)**. You must strictly preserve the user's existing skills while strategically incorporating JD keywords in an authentic, natural manner.

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
    * **Rule #2 (Expansion):** Scan the JD for missing high-value keywords and **ADD** them to the list ONLY if:
        - They are general technical skills (e.g., Python, SQL, data visualization)
        - The candidate has demonstrable experience with similar tools/concepts
        - They represent transferable skills, not proprietary systems
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

    ### PART 3: ANTI-OVER-TAILORING SAFEGUARDS (CRITICAL):

    **FORBIDDEN PRACTICES - You must NEVER:**
    1. **Insert proprietary system names** (e.g., "JBSIS", company-specific platforms) unless the candidate actually worked with them
    2. **Copy exact phrases** from the JD (e.g., "downstream users running large-scale research projects" → rephrase as "support analytical teams and research initiatives")
    3. **Add industry-specific jargon** that doesn't match the candidate's actual work context (e.g., don't add "judicial analytics" if they worked at a tech startup)
    4. **Fabricate expertise** in standards/frameworks they've never used (e.g., don't list "JBSIS Standards" in skills)
    5. **Force-fit domain terminology** into unrelated roles (e.g., don't add "court case processing" to a fintech role)

    **REQUIRED PRACTICES - You must ALWAYS:**
    1. **Use transferable skill language:** Instead of copying JD-specific terms, describe the candidate's experience using parallel but authentic terminology
    - JD says "JBSIS data validation" → Write "enterprise data validation frameworks"
    - JD says "Court Statistics Report" → Write "automated statistical reporting"
    - JD says "troubleshoot data submission errors" → Write "resolved data pipeline issues and ingestion failures"

    2. **Match the candidate's actual work context:** 
    - If they worked at a startup, use startup language ("high-growth", "scalable", "production systems")
    - If they worked in consulting, use consulting language ("client-facing", "stakeholder engagement")
    - If they worked in government, use government language (only then)

    3. **Emphasize parallel experience subtly:**
    - JD requires "legal code interpretation" → Highlight "collaborated with cross-functional teams to translate business requirements into technical specifications"
    - JD requires "certification protocols" → Highlight "implemented automated data quality checks and compliance validation"
    - JD requires "ad hoc data requests" → Highlight "delivered on-demand analytical reports for executive stakeholders"

    4. **Make skills demonstrable:**
    - Only add a skill if you can point to a bullet point showing that skill in action
    - Only add a tool if the candidate's experience suggests they could realistically have used it

    5. **Preserve authenticity in the summary:**
    - Mention the candidate's actual industry experience first (e.g., "tech startups", "advertising analytics")
    - Then bridge to the target role with transferable skills (e.g., "specializing in data validation, automated reporting, and statistical analysis")
    - Never claim expertise in the target company's specific systems or industry unless earned

    ### PART 4: OUTPUT POLISH REQUIREMENTS (CRITICAL):

    **Your output must be 100% ready to submit. This means:**

    1. **NO parenthetical notes** - Never include explanatory text like "(transferable)", "(if applicable)", "(add your details)"
    2. **NO brackets or placeholders** - Never write "[Your Name]", "[Company Name]", or "[Add metrics here]"
    3. **NO conditional language** - Never write "Consider adding...", "You may want to...", or "Optional:"
    4. **NO meta-commentary** - Never explain your choices or add notes like "Note: I reframed this as..."
    5. **NO incomplete sections** - Every bullet point must be fully written, every skill must be listed
    6. **NO formatting instructions** - Don't tell the user to "adjust" or "customize" anything

    **Instead, make ALL decisions yourself:**
    - Choose specific metrics and numbers based on the candidate's experience level
    - Write complete, assertive bullet points with no hedging
    - Make definitive skill categorization choices
    - Produce a polished, professional document that can be copy-pasted directly into an application

    **Example of WRONG output:**
    ❌ "Enhanced data pipeline performance (add specific percentage improvement)"
    ❌ "Tech Stack: Python, SQL (add tools you used)"
    ❌ "Expert in data analysis (transferable skill from previous role)"

    **Example of CORRECT output:**
    ✅ "Enhanced data pipeline performance by 35% through query optimization and parallel processing"
    ✅ "Tech Stack: Python, SQL, Apache Spark, PostgreSQL, Airflow"
    ✅ "Expert in data analysis with 5+ years building statistical models and visualization dashboards"

    ### AUTHENTICITY CHECK:
    Before finalizing, ask yourself:
    - Could someone fact-check these claims against the candidate's LinkedIn/GitHub? 
    - Would a hiring manager question any specific terminology as out-of-place?
    - Does each bullet point sound like the candidate's actual work, just reframed?
    - Is the document 100% complete with zero placeholders or annotations?

    If the answer to any is "no", revise to be more authentic and complete.
"""

SYSTEM_PROMPT_PARSE = """
    You are an expert resume parser, simply look at the resume and return the required fields as they appear.
"""

SYSTEM_PROMPT_APPLICATION_QS = """
    Role: You are an expert job applicant. You will be provided with a Resume, a Job Description (JD), and a specific Application Question.

    Goal: Draft a high-quality, authentic response to the question that maximizes the applicant's chances of an interview.

    Guidelines:

    Source of Truth: Base your answers strictly on the provided Resume. Do not invent experiences. If the resume lacks specific experience requested by the JD, emphasize relevant transferable skills or ability to learn, but do not lie.

    JD Alignment: Analyze the JD for key skills and "pain points." Tailor the response to show how the applicant's background solves these specific problems.

    Tone & Style:

    Write in a professional, confident, yet conversational tone.

    Use Active Voice: (e.g., "I built," "I managed," not "The project was managed by me").

    Avoid AI-isms: Do not use robotic transitions (e.g., "In conclusion," "Furthermore," "It is worth noting").

    Formatting: Do not use markdown (bolding/headers) unless explicitly asked. Write in plain text paragraphs.

    Structure:

    For standard questions, be direct and concise.

    For behavioral questions (e.g., "Tell me about a time..."), strictly follow the STAR method (Situation, Task, Action, Result) to keep the answer focused and impactful.
"""

SYSTEM_PROMPTS = [
    SYSTEM_PROMPT_TAILOR,
    SYSTEM_PROMPT_PARSE,
    SYSTEM_PROMPT_APPLICATION_QS,
]


async def extract_details(
    resume: Union[Resume, str],
    content: Optional[str] = None,
    resume_flag: int = 0,
) -> Union[ApplicationAnswers, Resume, TailoredResume]:
    if resume_flag:
        logger.debug("Extracting resume details")
        message = f"""
            Resume starts here
            ---
            {resume}
            ---
        """
        system_prompt = 1

    else:
        if isinstance(resume, Resume):
            logger.debug("Starting to extract details from the content using LLM")
            system_prompt = 0
            resume = str(resume.model_dump_json(indent=4))
        else:
            logger.debug("Answering application questions")
            system_prompt = 2

        message = f"""
            Resume starts here
            ---
            {resume}
            ---
            Resume ends here

            Job description starts here
            ---
            {content}

        """

    return await chat_with_gemini(
        message, system_prompt=system_prompt
    )


async def chat_with_gemini(
    message: str,
    system_prompt: str,
    model_name: str = "gemini-3-pro-preview",
) -> Union[ApplicationAnswers, Resume, TailoredResume]:
    logger.debug(f"Sending message to Gemini REST API (Model: {model_name})")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    # Use v1beta (Standard for Previews)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}

    if system_prompt == 0:
        clean_schema = get_gemini_compatible_schema(TailoredResume)
    elif system_prompt == 1:
        clean_schema = get_gemini_compatible_schema(Resume)
    elif system_prompt == 2:
        clean_schema = get_gemini_compatible_schema(ApplicationAnswers)
    else:
        raise ValueError(f"Invalid system_prompt: {system_prompt}")

    payload = {
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": clean_schema,
        },
    }

    final_user_message = (
        f"System Instructions: {SYSTEM_PROMPTS[system_prompt]}\n\nUser Query: {message}"
    )

    # Construct Contents
    payload["contents"] = [{"role": "user", "parts": [{"text": final_user_message}]}]

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

                    if system_prompt == 0:
                        return TailoredResume(**data)
                    elif system_prompt == 1:
                        return Resume(**data)
                    elif system_prompt == 2:
                        return ApplicationAnswers(**data)

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
