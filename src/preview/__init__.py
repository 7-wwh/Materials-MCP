"""
Materials-MCP preview package.

Provides headless offscreen multi-view 3D visualization of STEP CAD models.
All rendering is done using matplotlib's Agg backend — no X11 or
display server required.

Public API:
    render_step_preview(step_path, output_path, ...) -> bool
    SUPPORTED_VIEW_MODES -> tuple[str, ...]
"""

from .renderer import render_step_preview, SUPPORTED_VIEW_MODES

__all__ = ["render_step_preview", "SUPPORTED_VIEW_MODES"]
