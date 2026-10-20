"""
Path management utility for Materials-MCP.
Centralizes workspace and artifact path resolution to guarantee
reproducible file storage for build123d, Gmsh, and CalculiX.
"""

from datetime import datetime
import os
from pathlib import Path
from typing import Optional

# Anchored to the Materials-MCP project root directory
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Base directory for all simulation runs & persistent outputs
ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts"


def get_artifacts_dir() -> Path:
    """Return base artifacts directory, ensuring it exists."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR


def get_run_directory(run_id: Optional[str] = None, update_latest: bool = True) -> Path:
    """
    Creates and returns an isolated directory for a simulation run.

    Args:
        run_id: Custom name for the run folder (e.g. 'run_001', 'latest').
                If None, defaults to timestamped 'run_YYYYMMDD_HHMMSS'.
        update_latest: If True and run_id != 'latest', updates the 'artifacts/latest'
                       symlink to point to this new run directory.

    Returns:
        Path object pointing to the created run directory.
    """
    base_dir = get_artifacts_dir()

    if run_id is None:
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if update_latest and run_id != "latest":
        latest_link = base_dir / "latest"
        try:
            if latest_link.is_symlink() or latest_link.exists():
                latest_link.unlink()
            latest_link.symlink_to(run_dir.resolve(), target_is_directory=True)
        except OSError:
            # Fallback if symlink creation is not permitted on host filesystem
            pass

    return run_dir
