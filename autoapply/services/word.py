import asyncio
import os
import logging

from pathlib import Path
from typing import Optional

from autoapply.logging import get_logger

get_logger()
logger = logging.getLogger(__name__)


async def convert_docx_to_pdf(resume_docx: str) -> Optional[str]:
    """Convert DOCX to PDF using LibreOffice"""

    # Convert to absolute path
    docx_path = Path(resume_docx).resolve()

    # Verify file exists
    if not docx_path.exists():
        logger.error(f"DOCX file not found: {docx_path}")
        return None

    # Get output directory and expected PDF path
    output_dir = str(docx_path.parent)
    expected_pdf = str(docx_path.with_suffix(".pdf"))

    logger.debug(f"Converting: {docx_path}")
    logger.debug(f"Output dir: {output_dir}")
    logger.debug(f"Expected PDF: {expected_pdf}")

    try:
        # Create the subprocess to convert DOCX to PDF
        process = await asyncio.create_subprocess_exec(
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            str(docx_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for it to finish
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            # Verify the PDF was created
            if os.path.exists(expected_pdf):
                logger.debug(f"Successfully converted to PDF: {expected_pdf}")
                return expected_pdf
            else:
                logger.error(
                    f"Conversion reported success but PDF not found: {expected_pdf}"
                )
                return None
        else:
            error_msg = stderr.decode().strip()
            logger.error(f"LibreOffice conversion failed: {error_msg}")
            logger.error(f"Return code: {process.returncode}")
            return None

    except FileNotFoundError as e:
        logger.error(f"LibreOffice not found: {e}")
        logger.error("Make sure LibreOffice is installed in Docker")
        return None
    except Exception as e:
        logger.error(f"Exception during PDF conversion: {e}", exc_info=True)
        return None
