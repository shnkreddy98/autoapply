# Export main classes
from autoapply.services.llm.agent import Agent, AgentResult
from autoapply.services.llm.agents import (
    JobApplicationAgent,
    ResumeTailorAgent,
    ResumeParserAgent,
    ApplicationQuestionAgent,
)
from autoapply.services.llm.tools import BrowserTools

# Export system prompts for reference/customization
from autoapply.services.llm.prompts import (
    SYSTEM_PROMPT_TAILOR,
    SYSTEM_PROMPT_PARSE,
    SYSTEM_PROMPT_APPLICATION_QS,
    SYSTEM_PROMPT_APPLY,
)

__all__ = [
    # Core agent classes
    "Agent",
    "AgentResult",

    # Specialized agents
    "JobApplicationAgent",
    "ResumeTailorAgent",
    "ResumeParserAgent",
    "ApplicationQuestionAgent",

    # System prompts
    "SYSTEM_PROMPT_TAILOR",
    "SYSTEM_PROMPT_PARSE",
    "SYSTEM_PROMPT_APPLICATION_QS",
    "SYSTEM_PROMPT_APPLY",

    # Browser tools
    "BrowserTools"
]
