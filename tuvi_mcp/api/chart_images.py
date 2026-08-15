# -*- coding: utf-8 -*-
"""Chart image storage and safe path resolution."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path


# Charts directory under project tmp/charts
CHARTS_DIR = Path(__file__).parent.parent.parent / "tmp" / "charts"


def save_chart_png(source_path: str) -> str:
    """Copy PNG from temporary path to charts directory with UUID filename.
    
    :param source_path: Path to the rendered PNG file
    :return: UUID string (chart_id) without path separators
    :raises: OSError if file operations fail
    """
    # Ensure charts directory exists
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate UUID for chart filename
    chart_id = str(uuid.uuid4())
    target_path = CHARTS_DIR / f"{chart_id}.png"
    
    # Copy source PNG to target location
    shutil.copy2(source_path, target_path)
    
    return chart_id


def resolve_chart_path(chart_id: str) -> Path | None:
    """Safely resolve chart ID to file path within CHARTS_DIR.
    
    :param chart_id: UUID string or filename with .png extension
    :return: Path object if valid and exists, None otherwise
    """
    # Strip .png extension if present
    if chart_id.endswith(".png"):
        chart_id = chart_id[:-4]
    
    # Validate UUID format - only allow [a-f0-9-]{36}
    try:
        uuid.UUID(chart_id)
    except ValueError:
        return None
    
    # Resolve path within CHARTS_DIR
    chart_path = CHARTS_DIR / f"{chart_id}.png"
    
    # Ensure resolved path is actually within CHARTS_DIR (prevent path traversal)
    try:
        chart_path.resolve().relative_to(CHARTS_DIR.resolve())
    except ValueError:
        return None
    
    # Check if file exists
    if not chart_path.exists():
        return None
    
    return chart_path