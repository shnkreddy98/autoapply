import asyncio
import logging
import os

from autoapply.helpers import get_company_name, get_resume_match
from autoapply.logging import get_logger
from autoapply.save import save_page_as_markdown
from autoapply.utils import read

get_logger()
logger = logging.getLogger(__name__)


async def process_url(idx: int, url: str, total: int):
    logger.info(url)
    logger.info(f"Processing {idx + 1} of {total}")
    company_name = await get_company_name(url)
    success = await save_page_as_markdown(url, company_name)
    return success


async def main():
    url_file = "job_url.txt"
    urls = read(url_file)
    batch_size = 5
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


if __name__ == "__main__":
    # results = asyncio.run(main())
    # logger.info(f"Total successful: {sum(results)}")

    # Testing
    dir = "/home/reddy/repos/autoapply/data/applications/2026-01-16"
    resume = "/home/reddy/repos/autoapply/data/shashank_reddy.pdf"
    files = os.listdir(dir)
    for file in files:
        jd_path = os.path.join(dir, file)
        jds = os.listdir(jd_path)
        for jd in jds:
            asyncio.run(get_resume_match(os.path.join(jd_path, jd), resume))
