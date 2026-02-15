import logging

from autoapply.env import MODEL
from autoapply.services.llm.agent import Agent
from autoapply.services.llm.models import get_tool_schema
# Import all browser tool argument models
from autoapply.services.llm.models import (
    BrowserClickArgs,
    BrowserCloseArgs,
    BrowserConsoleMessagesArgs,
    BrowserDragArgs,
    BrowserEvaluateArgs,
    BrowserFileUploadArgs,
    BrowserFillFormArgs,
    BrowserHandleDialogArgs,
    BrowserHoverArgs,
    BrowserNavigateArgs,
    BrowserNavigateBackArgs,
    BrowserNetworkRequestsArgs,
    BrowserPressKeyArgs,
    BrowserResizeArgs,
    BrowserRunCodeArgs,
    BrowserSelectOptionArgs,
    BrowserSnapshotArgs,
    BrowserTabsArgs,
    BrowserTakeScreenshotArgs,
    BrowserTypeArgs,
    BrowserWaitForArgs,
    GetPageStateArgs,
    ReplaceArgs
)
from docx.document import Document as DocumentObject
from autoapply.services.llm.tools import BrowserTools, DocumentTools
from autoapply.models import (
    Resume,
    TailoredResume,
    ApplicationAnswers,
)

logger = logging.getLogger(__name__)

# Import system prompts
from autoapply.services.llm.prompts import (
    SYSTEM_PROMPT_TAILOR,
    SYSTEM_PROMPT_PARSE,
    SYSTEM_PROMPT_APPLICATION_QS,
    SYSTEM_PROMPT_APPLY,
)


class JobApplicationAgent(Agent):
    """
    Agent for automatically filling and submitting job applications.

    Uses Playwright browser automation tools to:
    - Navigate to job application pages
    - Fill form fields with candidate data
    - Answer application questions
    - Submit applications
    """

    def __init__(
        self,
        browser_tools: BrowserTools,
        model: str = MODEL,
    ):
        """
        Initialize job application agent with ALL 22 browser automation tools.

        Args:
            browser_tools: BrowserTools instance with Playwright page
            model: OpenRouter model ID
        """
        # Define all 22 tools efficiently
        tool_definitions = [
            # Core navigation & page inspection
            (GetPageStateArgs, "get_page_state", "Get current page state with interactive elements and their refs. ALWAYS call this first to understand what's on the page."),
            (BrowserNavigateArgs, "browser_navigate", "Navigate to a URL"),
            (BrowserNavigateBackArgs, "browser_navigate_back", "Go back to the previous page in browser history"),

            # Interaction tools
            (BrowserClickArgs, "browser_click", "Click an element using its ref from page state"),
            (BrowserTypeArgs, "browser_type", "Type text into an input field using its ref"),
            (BrowserFillFormArgs, "browser_fill_form", "Fill multiple form fields at once (more efficient than typing one by one)"),
            (BrowserSelectOptionArgs, "browser_select_option", "Select option(s) in a dropdown using its ref"),
            (BrowserHoverArgs, "browser_hover", "Hover over an element (useful for revealing hidden menus)"),
            (BrowserDragArgs, "browser_drag", "Drag and drop between two elements"),
            (BrowserPressKeyArgs, "browser_press_key", "Press a key on the keyboard (e.g., Tab, Enter, Escape, Arrow keys)"),

            # File & dialog handling
            (BrowserFileUploadArgs, "browser_file_upload", "Upload files (e.g., resume, cover letter)"),
            (BrowserHandleDialogArgs, "browser_handle_dialog", "Handle browser dialogs (alert, confirm, prompt)"),

            # Waiting & timing
            (BrowserWaitForArgs, "browser_wait_for", "Wait for time to pass, text to appear, or text to disappear"),

            # Advanced execution
            (BrowserEvaluateArgs, "browser_evaluate", "Evaluate JavaScript expression on page or element"),
            (BrowserRunCodeArgs, "browser_run_code", "Run custom Playwright code for complex interactions"),

            # Debugging & inspection
            (BrowserTakeScreenshotArgs, "browser_take_screenshot", "Take a screenshot for debugging or verification"),
            (BrowserSnapshotArgs, "browser_snapshot", "Get accessibility snapshot of current page"),
            (BrowserConsoleMessagesArgs, "browser_console_messages", "Get browser console messages for debugging"),
            (BrowserNetworkRequestsArgs, "browser_network_requests", "Get network requests made by the page"),

            # Browser management
            (BrowserResizeArgs, "browser_resize", "Resize the browser window"),
            (BrowserTabsArgs, "browser_tabs", "List, create, close, or select browser tabs"),
            (BrowserCloseArgs, "browser_close", "Close the browser page"),
        ]

        # Generate tool schemas
        tools = [
            get_tool_schema(args_model, name, description)
            for args_model, name, description in tool_definitions
        ]

        # Map tool names to BrowserTools methods
        tool_functions = {
            "get_page_state": browser_tools.get_page_state,
            "browser_navigate": browser_tools.browser_navigate,
            "browser_navigate_back": browser_tools.browser_navigate_back,
            "browser_click": browser_tools.browser_click,
            "browser_type": browser_tools.browser_type,
            "browser_fill_form": browser_tools.browser_fill_form,
            "browser_select_option": browser_tools.browser_select_option,
            "browser_hover": browser_tools.browser_hover,
            "browser_drag": browser_tools.browser_drag,
            "browser_press_key": browser_tools.browser_press_key,
            "browser_file_upload": browser_tools.browser_file_upload,
            "browser_handle_dialog": browser_tools.browser_handle_dialog,
            "browser_wait_for": browser_tools.browser_wait_for,
            "browser_evaluate": browser_tools.browser_evaluate,
            "browser_run_code": browser_tools.browser_run_code,
            "browser_take_screenshot": browser_tools.browser_take_screenshot,
            "browser_snapshot": browser_tools.browser_snapshot,
            "browser_console_messages": browser_tools.browser_console_messages,
            "browser_network_requests": browser_tools.browser_network_requests,
            "browser_resize": browser_tools.browser_resize,
            "browser_tabs": browser_tools.browser_tabs,
            "browser_close": browser_tools.browser_close,
        }

        # Map tool names to their Pydantic schemas for validation
        tool_schemas = {
            "get_page_state": GetPageStateArgs,
            "browser_navigate": BrowserNavigateArgs,
            "browser_navigate_back": BrowserNavigateBackArgs,
            "browser_click": BrowserClickArgs,
            "browser_type": BrowserTypeArgs,
            "browser_fill_form": BrowserFillFormArgs,
            "browser_select_option": BrowserSelectOptionArgs,
            "browser_hover": BrowserHoverArgs,
            "browser_drag": BrowserDragArgs,
            "browser_press_key": BrowserPressKeyArgs,
            "browser_file_upload": BrowserFileUploadArgs,
            "browser_handle_dialog": BrowserHandleDialogArgs,
            "browser_wait_for": BrowserWaitForArgs,
            "browser_evaluate": BrowserEvaluateArgs,
            "browser_run_code": BrowserRunCodeArgs,
            "browser_take_screenshot": BrowserTakeScreenshotArgs,
            "browser_snapshot": BrowserSnapshotArgs,
            "browser_console_messages": BrowserConsoleMessagesArgs,
            "browser_network_requests": BrowserNetworkRequestsArgs,
            "browser_resize": BrowserResizeArgs,
            "browser_tabs": BrowserTabsArgs,
            "browser_close": BrowserCloseArgs,
        }

        super().__init__(
            system_prompt=SYSTEM_PROMPT_APPLY,
            tools=tools,
            tool_functions=tool_functions,
            tool_schemas=tool_schemas,  # Pass schemas for validation
            model=model,
            temperature=0.3,  # Lower temperature for more deterministic form filling
        )

    async def apply_to_job(
        self,
        job_url: str,
        candidate_data: dict,
        max_iterations: int = 50
    ):
        """
        Apply to a job at the given URL.

        Args:
            job_url: URL of the job application page
            candidate_data: Dict with candidate information (name, email, resume, etc.)
            max_iterations: Maximum number of steps to take

        Returns:
            AgentResult with success status and details
        """
        # Build the query with candidate data
        query = f"""
Apply to the job at: {job_url}

Use this candidate data to fill the application:
{candidate_data}

Steps:
1. Navigate to the job URL
2. Call get_page_state() to see the application form
3. Fill all required fields with candidate data
4. Answer any questions based on the candidate's resume
5. Submit the application
6. Verify success (look for confirmation message)
"""

        result = await self.run(query, max_iterations=max_iterations)
        return result


class ResumeTailorAgent(Agent):
    """
    Agent for tailoring resumes to job descriptions.

    Analyzes a candidate's resume against a job description and rewrites
    the resume to maximize ATS compatibility and keyword matching.
    """

    def __init__(
        self, 
        document_tools: DocumentTools,
        model: str = MODEL
    ):
        tool_definitions = [
            (ReplaceArgs, "replace", "Replace the exact string in resume"),
        ]

        # Generate tool schemas
        tools = [
            get_tool_schema(args_model, name, description)
            for args_model, name, description in tool_definitions
        ]

        tool_schemas = {
            "replace": ReplaceArgs
        }

        # Map tool names to BrowserTools methods
        tool_functions = {
            "replace": document_tools.replace,
        }
        self.document = document_tools.document

        super().__init__(
            system_prompt=SYSTEM_PROMPT_TAILOR,
            response_format=TailoredResume,
            model=model,
            tools=tools,
            tool_functions=tool_functions,
            tool_schemas=tool_schemas,
            temperature=0.7,
        )

    async def tailor_resume(
        self,
        job_description: str
    ) -> TailoredResume:
        """
        Tailor a resume to a specific job description.

        Args:
            resume: Original resume (Resume model)
            job_description: Target job description text

        Returns:
            TailoredResume with optimized content
        """
        query = f"""
Resume starts here
---
{"\n".join([paragraph.text for paragraph in self.document.paragraphs])}
---
Resume ends here

Job description starts here
---
{job_description}
---
Job description ends here

Analyze the resume against the job description and create a tailored version using the tools you have available.
"""

        result = await self.run(query, max_iterations=10)
        return result.output


class ResumeParserAgent(Agent):
    """
    Agent for parsing resumes into structured data.

    Extracts information from resume text and returns it in a
    structured Resume format.
    """

    def __init__(self, model: str = MODEL):
        super().__init__(
            system_prompt=SYSTEM_PROMPT_PARSE,
            response_format=Resume,
            model=model,
            temperature=0.1,  # Very low temperature for accurate parsing
        )

    async def parse_resume(self, resume_text: str) -> Resume:
        """
        Parse resume text into structured Resume object.

        Args:
            resume_text: Raw text of the resume

        Returns:
            Resume object with extracted fields
        """
        query = f"""
Resume starts here
---
{resume_text}
---
Resume ends here

Parse this resume and extract all fields.
"""

        result = await self.run(query, max_iterations=1)
        return result.output


class ApplicationQuestionAgent(Agent):
    """
    Agent for answering job application questions.

    Generates high-quality answers to application questions based on
    a candidate's resume and the job description.
    """

    def __init__(self, model: str = MODEL):
        super().__init__(
            system_prompt=SYSTEM_PROMPT_APPLICATION_QS,
            response_format=ApplicationAnswers,
            model=model,
            temperature=0.7,
        )

    async def answer_questions(
        self,
        resume: str,
        job_description: str,
        questions: list[str]
    ) -> ApplicationAnswers:
        """
        Answer application questions based on resume and JD.

        Args:
            resume: Resume text or JSON
            job_description: Job description text
            questions: List of questions to answer

        Returns:
            ApplicationAnswers with generated responses
        """
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])

        query = f"""
Resume starts here
---
{resume}
---
Resume ends here

Job description starts here
---
{job_description}
---
Job description ends here

Application questions:
{questions_text}

Answer each question professionally and authentically based on the resume.
"""

        result = await self.run(query, max_iterations=1)
        return result.output
