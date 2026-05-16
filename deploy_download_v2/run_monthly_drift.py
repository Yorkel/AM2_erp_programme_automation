"""
run_monthly_drift.py

Monthly pipeline: compute drift metrics for each country.

Usage:
  python run_monthly_drift.py

Designed to run as a GitHub Action on the 1st of each month,
or manually after reviewing the month's inference results.
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


def main():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("MONTHLY DRIFT MONITORING — %s", start.strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 60)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "model_pipeline.inference.drift_monitor"],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            logger.info(result.stdout[-1000:])
    except subprocess.CalledProcessError as e:
        logger.error("Drift monitoring failed.")
        if e.stdout:
            logger.error("stdout: %s", e.stdout[-500:])
        if e.stderr:
            logger.error("stderr: %s", e.stderr[-500:])
        sys.exit(1)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=" * 60)
    logger.info("MONTHLY DRIFT COMPLETE — %.0f seconds", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
