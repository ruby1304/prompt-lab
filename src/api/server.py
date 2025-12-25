"""
API Server Startup Script

This script starts the FastAPI server using uvicorn.
It can be run directly or imported for programmatic server control.
"""

import uvicorn
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.config import get_settings


def start_server(
    host: str = None,
    port: int = None,
    reload: bool = None,
    workers: int = None,
    log_level: str = None
):
    """
    Start the FastAPI server.
    
    Args:
        host: Server host address (default from settings)
        port: Server port (default from settings)
        reload: Enable auto-reload on code changes (default from settings)
        workers: Number of worker processes (default from settings)
        log_level: Logging level (default from settings)
    """
    settings = get_settings()
    
    # Use provided values or fall back to settings
    config = {
        "app": "src.api.app:app",
        "host": host or settings.host,
        "port": port or settings.port,
        "reload": reload if reload is not None else settings.reload,
        "workers": workers or settings.workers,
        "log_level": (log_level or settings.log_level).lower(),
    }
    
    # If reload is enabled, workers must be 1
    if config["reload"]:
        config["workers"] = 1
    
    print(f"Starting Prompt Lab API server on {config['host']}:{config['port']}")
    print(f"Documentation available at: http://{config['host']}:{config['port']}/docs")
    print(f"Workers: {config['workers']}, Reload: {config['reload']}")
    
    uvicorn.run(**config)


if __name__ == "__main__":
    # Start server with default settings
    # For development, you can enable reload:
    # start_server(reload=True)
    start_server()
