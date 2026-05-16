"""
run_weekly.py

Weekly pipeline: sync new articles from Supabase → run inference → write results.

Usage:
  python run_weekly.py

Designed to run as a GitHub Action or manually after the weekly scrape completes.
"""

import subprocess
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


def run_step(description: str, command: list[str]) -> bool:
    """Run a subprocess step and return True if successful."""
    logger.info("── %s ──", description)
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            logger.info(result.stdout[-500:])  # last 500 chars
        return True
    except subprocess.CalledProcessError as e:
        logger.error("FAILED: %s", description)
        if e.stdout:
            logger.error("stdout: %s", e.stdout[-500:])
        if e.stderr:
            logger.error("stderr: %s", e.stderr[-500:])
        return False


def main():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("WEEKLY PIPELINE — %s", start.strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 60)

    # Step 1: Sync from Supabase
    if not run_step("Sync from Supabase", [sys.executable, "sync_from_supabase.py"]):
        logger.error("Sync failed. Aborting.")
        sys.exit(1)

    # Step 2: Run weekly inference (all three countries, new weeks only)
    if not run_step("Weekly inference", [
        sys.executable, "-m", "model_pipeline.inference.batch_runner", "--mode", "inference_weekly"
    ]):
        logger.error("Inference failed. Aborting.")
        sys.exit(1)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=" * 60)
    logger.info("WEEKLY PIPELINE COMPLETE — %.0f seconds", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
