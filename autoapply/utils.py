import json
import logging
import nltk
import re
import yaml


from autoapply.db import Txc
from autoapply.logging import get_logger
from autoapply.save import save_page_as_markdown
from datetime import date
from nltk.corpus import stopwords
from pypdf import PdfReader
from typing import Union

nltk.download('stopwords')

get_logger()
logger = logging.getLogger(__name__)

async def process_url(idx: int, url: str, total: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    company_name = await get_company_name(url)
    success = await save_page_as_markdown(url, company_name)
    with Txc() as tx:
        tx.insert_job(url, date.today().isoformat())
    return success


def read(file: str) -> dict | str:
    with open(file, "r") as f:
        if file.endswith(".json"):
            return json.load(f)
        elif file.endswith(".yaml"):
            return yaml.safe_load(f)
        else:
            return f.readlines()



async def read(file: str) -> Union[str, dict]:
    with open(file, "r") as f:
        if file.endswith(".json"):
            return json.load(f)
        elif file.endswith(".yaml"):
            return yaml.safe_load(f)
        elif file.endswith(".pdf"):
            page = PdfReader(file).pages[0]
            return page.extract_text()
        return f.read()

async def clean(text: str) -> str:
    text = text.lower()
    return re.sub(r'[^a-zA-Z0-9 \n]', '', text)

async def get_company_name(url: str) -> str:
    if (
        url.startswith("https://jobs.ashbyhq.com")
        or url.startswith("https://ats.rippling.com")
        or url.startswith("https://jobs.lever.co")
        or url.startswith("https://jobs-boards.greenhouse.io")
        or url.startswith("https://job-boards.greenhouse.io")
        or url.startswith("https://boards.greenhouse.io")
        or url.startswith("https://jobs.smartrecruiters.com")
        or url.startswith("https://jobs.jobvite.com")
        or url.startswith("https://apply.workable.com")
    ):
        company_name = url.split("/")[3]
    elif (
        url.split("/")[2].split(".")[1] == "applytojob"
        or url.split("/")[2].split(".")[1] == "eightfold"
        or url.split("/")[2].split(".")[-2] == "oraclecloud"
    ):
        company_name = url.split("/")[2].split(".")[0]
    elif url.startswith("https://careers"):
        if "icims" in url:
            company_name = url.split("/")[2].split(".")[0].split("-")[1]
        else:
            company_name = url.split("/")[2].split(".")[1]
    elif "myworkdayjobs" in url:
        company_name = url.split("/")[2].split(".")[0]
    elif url.split("/")[3] == "careers":
        company_name = url.split("/")[2].split(".")[1]
    else:
        # remove https://
        # replace all special characters with space
        # split at space and remove generic words and keep non generic words only
        clean_url = "".join(url.split("/")[2:])
        clean_url = re.sub(r"[^a-zA-Z0-9]+", " ", clean_url).strip()
        clean_company_name = []
        for word in clean_url.split(" "):
            if word not in [
                "board",
                "us2",
                "com",
                "careers",
                "en",
                "sites",
                "Data",
                "Engineer",
            ]:
                clean_company_name.append(word)
        company_name = "_".join(clean_company_name)
    return company_name.replace("/", "")

async def get_words(file: str) -> set:
    text = await read(file)
    if isinstance(text, dict):
        text = json.dumps(text)
    clean_text = await clean(text)
    words = set(clean_text.split())
    stop_words = set(stopwords.words('english'))
    filtered_words = {word for word in words if word not in stop_words}
    return filtered_words

async def get_resume_match(jd_file: str, resume_file: str) -> float:
    jd_words = await get_words(jd_file)
    resume_words = await get_words(resume_file)

    matched_words = jd_words.intersection(resume_words)
    score = len(matched_words)

    print(f"{jd_file} has {score} with the {resume_file}")
    return float(score)


