"""Entry point for running the NILE backend."""

import uvicorn

from nile.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "nile.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
