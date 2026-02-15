from typing import Literal, Optional, Dict, Any, Type, List
from pydantic import BaseModel, Field


def get_tool_schema(
    model: Type[BaseModel], name: str, description: str
) -> Dict[str, Any]:
    """
    Converts a Pydantic model to an OpenAI function calling schema.
    """
    schema = model.model_json_schema()
    # Remove titles from schema to keep it clean for LLM
    if "title" in schema:
        del schema["title"]
    if "properties" in schema:
        for prop in schema["properties"].values():
            if "title" in prop:
                del prop["title"]

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema,
            "strict": True,
        },
    }


# --- Shared Models ---


class FormField(BaseModel):
    name: str = Field(..., description="Human-readable field name")
    ref: str = Field(
        ..., description="Exact target field reference from the page snapshot"
    )
    type: Literal["textbox", "checkbox", "radio", "combobox", "slider"] = Field(
        ..., description="Type of the field"
    )
    value: str = Field(
        ...,
        description="Value to fill in the field. If the field is a checkbox, the value should be 'true' or 'false'. If the field is a combobox, the value should be the text of the option.",
    )


# --- Tool Argument Models ---


class BrowserClickArgs(BaseModel):
    ref: str = Field(
        ..., description="Exact target element reference from the page snapshot"
    )
    element: Optional[str] = Field(
        None,
        description="Human-readable element description used to obtain permission to interact with the element",
    )
    doubleClick: bool = Field(
        False, description="Whether to perform a double click instead of a single click"
    )
    button: Literal["left", "right", "middle"] = Field(
        "left", description="Button to click, defaults to left"
    )
    modifiers: Optional[
        List[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]]
    ] = Field(None, description="Modifier keys to press")


class BrowserCloseArgs(BaseModel):
    pass


class BrowserConsoleMessagesArgs(BaseModel):
    level: Literal["error", "warning", "info", "debug"] = Field(
        "info",
        description="Level of the console messages to return. Each level includes the messages of more severe levels.",
    )
    filename: Optional[str] = Field(
        None,
        description="Filename to save the console messages to. If not provided, messages are returned as text.",
    )


class BrowserDragArgs(BaseModel):
    startElement: str = Field(
        ...,
        description="Human-readable source element description used to obtain the permission to interact with the element",
    )
    startRef: str = Field(
        ..., description="Exact source element reference from the page snapshot"
    )
    endElement: str = Field(
        ...,
        description="Human-readable target element description used to obtain the permission to interact with the element",
    )
    endRef: str = Field(
        ..., description="Exact target element reference from the page snapshot"
    )


class BrowserEvaluateArgs(BaseModel):
    function: str = Field(
        ...,
        description="() => { /* code */ } or (element) => { /* code */ } when element is provided",
    )
    element: Optional[str] = Field(
        None,
        description="Human-readable element description used to obtain permission to interact with the element",
    )
    ref: Optional[str] = Field(
        None, description="Exact target element reference from the page snapshot"
    )


class BrowserFileUploadArgs(BaseModel):
    paths: Optional[List[str]] = Field(
        None,
        description="The absolute paths to the files to upload. Can be single file or multiple files. If omitted, file chooser is cancelled.",
    )


class BrowserFillFormArgs(BaseModel):
    fields: List[FormField] = Field(..., description="Fields to fill in")


class BrowserHandleDialogArgs(BaseModel):
    accept: bool = Field(..., description="Whether to accept the dialog.")
    promptText: Optional[str] = Field(
        None, description="The text of the prompt in case of a prompt dialog."
    )


class BrowserHoverArgs(BaseModel):
    ref: str = Field(
        ..., description="Exact target element reference from the page snapshot"
    )
    element: Optional[str] = Field(
        None,
        description="Human-readable element description used to obtain permission to interact with the element",
    )


class BrowserNavigateArgs(BaseModel):
    url: str = Field(..., description="The URL to navigate to")


class BrowserNavigateBackArgs(BaseModel):
    pass


class BrowserNetworkRequestsArgs(BaseModel):
    includeStatic: bool = Field(
        False,
        description="Whether to include successful static resources like images, fonts, scripts, etc. Defaults to false.",
    )
    filename: Optional[str] = Field(
        None,
        description="Filename to save the network requests to. If not provided, requests are returned as text.",
    )


class BrowserPressKeyArgs(BaseModel):
    key: str = Field(
        ...,
        description="Name of the key to press or a character to generate, such as `ArrowLeft` or `a`",
    )


class BrowserResizeArgs(BaseModel):
    width: float = Field(..., description="Width of the browser window")
    height: float = Field(..., description="Height of the browser window")


class BrowserRunCodeArgs(BaseModel):
    code: str = Field(
        ...,
        description="A JavaScript function containing Playwright code to execute. It will be invoked with a single argument, page, which you can use for any page interaction. For example: `async (page) => { await page.getByRole('button', { name: 'Submit' }).click(); return await page.title(); }`",
    )


class BrowserSelectOptionArgs(BaseModel):
    ref: str = Field(
        ..., description="Exact target element reference from the page snapshot"
    )
    values: List[str] = Field(
        ...,
        description="Array of values to select in the dropdown. This can be a single value or multiple values.",
    )
    element: Optional[str] = Field(
        None,
        description="Human-readable element description used to obtain permission to interact with the element",
    )


class BrowserSnapshotArgs(BaseModel):
    filename: Optional[str] = Field(
        None,
        description="Save snapshot to markdown file instead of returning it in the response.",
    )


class BrowserTabsArgs(BaseModel):
    action: Literal["list", "new", "close", "select"] = Field(
        ..., description="Operation to perform"
    )
    index: Optional[float] = Field(
        None,
        description="Tab index, used for close/select. If omitted for close, current tab is closed.",
    )


class BrowserTakeScreenshotArgs(BaseModel):
    type: Literal["png", "jpeg"] = Field(
        "png", description="Image format for the screenshot. Default is png."
    )
    filename: Optional[str] = Field(
        None,
        description="File name to save the screenshot to. Defaults to `page-{timestamp}.{png|jpeg}` if not specified. Prefer relative file names to stay within the output directory.",
    )
    element: Optional[str] = Field(
        None,
        description="Human-readable element description used to obtain permission to screenshot the element. If not provided, the screenshot will be taken of viewport. If element is provided, ref must be provided too.",
    )
    ref: Optional[str] = Field(
        None,
        description="Exact target element reference from the page snapshot. If not provided, the screenshot will be taken of viewport. If ref is provided, element must be provided too.",
    )
    fullPage: bool = Field(
        False,
        description="When true, takes a screenshot of the full scrollable page, instead of the currently visible viewport. Cannot be used with element screenshots.",
    )


class BrowserTypeArgs(BaseModel):
    ref: str = Field(
        ..., description="Exact target element reference from the page snapshot"
    )
    text: str = Field(..., description="Text to type into the element")
    element: Optional[str] = Field(
        None,
        description="Human-readable element description used to obtain permission to interact with the element",
    )
    submit: bool = Field(
        False, description="Whether to submit entered text (press Enter after)"
    )
    slowly: bool = Field(
        False,
        description="Whether to type one character at a time. Useful for triggering key handlers in the page. By default entire text is filled in at once.",
    )


class BrowserWaitForArgs(BaseModel):
    time: Optional[float] = Field(None, description="The time to wait in seconds")
    text: Optional[str] = Field(None, description="The text to wait for")
    textGone: Optional[str] = Field(
        None, description="The text to wait for to disappear"
    )


# --- Legacy/FlowTest Specific Models ---


class NavigateArgs(BaseModel):
    url: str = Field(
        ..., description="The full URL to navigate to (e.g., https://example.com)."
    )


class GetPageStateArgs(BaseModel):
    include_html: bool = Field(
        False,
        description="If True, returns simplified HTML alongside the accessibility tree.",
    )


class PlaywrightTestArgs(BaseModel):
    code: str = Field(
        ...,
        description="The final Playwright (JavaScript) test script that reproduces the successful path. Must include 'await' statements and end with an 'expect' assertion.",
    )
    summary: Optional[str] = Field(
        None,
        description="A brief natural language summary of what the test achieved (e.g., 'Successfully logged in and verified dashboard').",
    )


class ValidateTestArgs(BaseModel):
    code: str = Field(
        ...,
        description="The Playwright (JavaScript) code to validate. It will be executed in a temporary test runner to check for errors.",
    )


class AssertArgs(BaseModel):
    ref: Optional[str] = Field(
        None,
        description="The element reference (ref) from get_page_state to assert on.",
    )
    selector: Optional[str] = Field(
        None,
        description="The CSS selector or text selector to assert on (if ref is not used).",
    )
    condition: Literal["visible", "hidden", "contains_text", "url_contains"] = Field(
        ..., description="The condition to check."
    )
    value: Optional[str] = Field(
        None,
        description="The expected text or URL fragment (required for 'contains_text' and 'url_contains').",
    )


class WaitArgs(BaseModel):
    seconds: float = Field(
        ..., description="Number of seconds to wait (use sparingly, max 5s)."
    )


class ScrollArgs(BaseModel):
    direction: Literal["up", "down", "top", "bottom"] = Field(
        "down", description="Direction to scroll."
    )
    amount: Optional[int] = Field(
        500, description="Pixel amount to scroll (ignored for 'top'/'bottom')."
    )


class KeyPressArgs(BaseModel):
    key: str = Field(
        ...,
        description="The key to press (e.g., 'Enter', 'Escape', 'Tab', 'ArrowDown').",
    )

class ReplaceArgs(BaseModel):
    search_text: str = Field(description="Exact string value to replace in the document")
    replace_text: str = Field(description="New string value to replace with")