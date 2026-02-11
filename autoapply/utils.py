import json
import logging
import re
import os
import yaml


from autoapply.logging import get_logger
from pypdf import PdfReader
from typing import Literal, Union


get_logger()
logger = logging.getLogger(__name__)


async def read(file: str) -> Union[str, dict]:
    with open(file, "r") as f:
        if file.endswith(".json"):
            return json.load(f)
        elif file.endswith(".yaml"):
            return yaml.safe_load(f)
        elif file.endswith(".pdf"):
            page = PdfReader(file).pages[0]
            return page.extract_text()
        return f.readlines()


async def clean(text: str) -> str:
    text = text.lower()
    return re.sub(r"[^a-zA-Z0-9 \n]", "", text)


async def get_rough_cloud(content: str) -> Literal["aws", "azu", "gcp"]:
    logger.debug("Getting rough cloud estimator to choose resume")
    clean_content = await clean(content)
    word_count = {"azu": 0, "gcp": 0, "aws": 0}
    default = "aws"
    flag = True
    for word in clean_content.split(" "):
        if word in [
            "azure",
            "aws",
            "amazon web services",
            "google cloud platform",
            "gcp",
        ]:
            if word in ["azure"]:
                word_count["azu"] += 1
                flag = False
            elif word in ["aws", "amazon web services"]:
                word_count["aws"] += 1
                flag = False
            elif word in ["gcp", "google cloud platform"]:
                word_count["gcp"] += 1
                flag = False

    if flag:
        return default
    return max(word_count, key=word_count.get)


async def write(file: str, data: str) -> bool:
    # Make sure the directory exists
    dir = "/".join(file.split("/")[:-1])
    os.makedirs(dir, exist_ok=True)

    # Write to file based on extension
    try:
        with open(file, "w", encoding="utf-8") as f:
            if file.endswith(".json"):
                json.dump(data, f, indent=4)
                return True
            f.write(data)
            return True
    except Exception as e:
        raise ValueError(f"Error occurred while writing {file}: {e}")