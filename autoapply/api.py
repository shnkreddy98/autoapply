import asyncio
import logging
import shutil
import os

from datetime import date
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from autoapply.logging import get_logger
from autoapply.save import (
    get_application_answers,
    process_url,
    parse_resume,
    list_resume,
)
from typing import Optional

from autoapply.services.scrape_google_results import GoogleSearchAutomation
from autoapply.services.db import Txc
from autoapply.models import (
    ApplicationAnswers,
    Job,
    PostJobsParams,
    UploadResumeParams,
    Resume,
    SearchParams,
    QuestionRequest,
)

get_logger()
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/applytojobs")
async def apply_to_jobs(params: PostJobsParams):
    # TODO: Currently sync waits for complition, make this asynchronous
    batch_size = 5
    total = len(params.urls)

    all_results = []

    # Process in batches
    for batch_idx in range(0, total, batch_size):
        # Get the current batch of URLs
        urls_batch = params.urls[batch_idx : batch_idx + batch_size]

        logger.info(
            f"Processing batch {batch_idx // batch_size + 1} of {(total + batch_size - 1) // batch_size}"
        )

        # Create tasks for this batch
        tasks = [
            process_url(batch_idx + idx, url, total, params.resume_id, params.tailor)
            for idx, url in enumerate(urls_batch)
        ]

        # Wait for all tasks in this batch to complete
        results = await asyncio.gather(*tasks)
        all_results.extend(results)

        logger.info(f"Batch {batch_idx // batch_size + 1} completed")

    return all_results


@app.get("/jobs")
async def get_jobs(date: Optional[date] = None) -> list[Job]:
    with Txc() as tx:
        jobs = tx.list_jobs(date=date)
    return [Job(**job) for job in jobs]


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        upload_dir = "data/resumes"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"path": file_path}
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-resume")
async def upload_resume(params: UploadResumeParams) -> int:
    return await parse_resume(params.path)


@app.get("/get-details")
async def get_resume_details(resume_id: int) -> Resume:
    try:
        logger.debug(f"Getting data for {resume_id}")
        data = await list_resume(resume_id)
        return data
    except RuntimeError as e:
        raise HTTPException(
            status_code=404, detail=f"Resume not found or resume_id cannot be None: {e}"
        )


@app.get("/list-resumes")
async def list_resume_ids() -> list[int]:
    with Txc() as tx:
        saved_resumes = tx.list_resumes()
    return [resume["id"] for resume in saved_resumes]


@app.post("/application-question")
async def get_answers(params: QuestionRequest) -> ApplicationAnswers:
    return await get_application_answers(params.url, params.questions)


@app.post("/search-jobs")
async def run_search(params: SearchParams) -> list[str]:
    google = GoogleSearchAutomation(cache_duration_hours=24)

    if not params.ats_sites:
        # Popular job sites
        sites = [
            "greenhouse.io", "myworkdayjobs.com", "ashbyhq.com", "icims.com", 
            "oraclecloud.com", "adp.com", "smartrecruiters.com", "taleo.net", 
            "applytojob.com", "lever.co", "ultipro.com", "workable.com", 
            "rippling.com", "paylocity.com", "dayforcehcm.com", "jobvite.com"
        ]
    else:
        sites = params.ats_sites


    # Build search query parts, filtering out empty values
    parts = [params.role]
    if params.company:
        parts.append(params.company)
    for site in sites:
        parts.append(f"site:{site} OR")

    search = " ".join(parts)
    search = search.strip("OR")
    return await google.auto_search(search, params.force, params.pages)

