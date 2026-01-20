import asyncio
import logging

from datetime import date
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from autoapply.models import ListJobsResponse, PostJobsParams
from autoapply.logging import get_logger
from autoapply.utils import process_url
from typing import Optional

from autoapply.db import Txc

get_logger()
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/applytojobs")
async def apply_to_jobs(params: PostJobsParams):
    #TODO: Currently sync waits for complition, make this asynchronous
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
            process_url(batch_idx + idx, url, total)
            for idx, url in enumerate(urls_batch)
        ]

        # Wait for all tasks in this batch to complete
        results = await asyncio.gather(*tasks)
        all_results.extend(results)

        logger.info(f"Batch {batch_idx // batch_size + 1} completed")

    return all_results

@app.get("/jobs")
async def get_jobs(date: Optional[date] = None) -> list[ListJobsResponse]:
    with Txc() as tx:
        jobs = tx.list_jobs(date=date)
    return [ListJobsResponse(**job) for job in jobs]

