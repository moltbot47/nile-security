"""Worker entrypoint — run with: python -m nile.workers.main"""

import asyncio
import logging

from nile.workers.scan_worker import run_worker


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
