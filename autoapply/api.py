import asyncio
import logging

from fastapi import FastAPI
from autoapply.models import Jobs
from autoapply.logging import get_logger
from autoapply.utils import process_url

get_logger()
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/applytojobs")
async def apply_to_jobs(jobs: Jobs):
    batch_size = 5
    urls = jobs.urls
    total = len(urls)

    all_results = []

    # Process in batches
    for batch_idx in range(0, total, batch_size):
        # Get the current batch of URLs
        urls_batch = urls[batch_idx : batch_idx + batch_size]

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

