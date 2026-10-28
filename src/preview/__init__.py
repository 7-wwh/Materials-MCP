"""
Materials-MCP preview package.

Provides headless offscreen 3D visualization of STEP CAD models.
All rendering is done using matplotlib's Agg backend — no X11 or
display server required.

Public API:
    render_step_preview(step_path, output_path, semantic_faces, ...) -> bool
"""

from .renderer import render_step_preview

__all__ = ["render_step_preview"]
