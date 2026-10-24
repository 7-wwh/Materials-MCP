# Materials-MCP Workspace Rules

These rules apply to all AI agents and subagents operating inside the `Materials-MCP` workspace.

## Core Directives:
1. **Never Write Run Data to `src/`**: All simulation runs, generated scripts (`model.py`), STEP CAD models, meshes, and FEA decks must live exclusively in `artifacts/run_YYYYMMDD_HHMMSS/` resolved by `src.paths.get_run_directory()`.
2. **The JSON-to-Script Invariant**: Always write a standalone, runnable `model.py` into the target run directory and execute it locally using subprocess. Never generate geometry purely in-memory without creating this audit file.
3. **Staged CAD-to-FEA Verification**: Never run FEA simulations directly without the CAD visual verification gate. Stage 1 generates the model and renders `preview.png` with semantic faces. Stage 2 executes the solve after user confirmation.
4. **Context Window Protection**: Never expose 50 flat tool schemas. Use the progressive disclosure catalog (`list_geometry_templates` -> `get_template_schema` -> `generate_cad_model`).
5. **Headless Offscreen Rendering**: All 3D previews must be rendered offscreen using `matplotlib` Agg. Do not introduce X11 or display server dependencies.
6. **Reference Specifications**: Follow [INTENT.md](file:///home/ubuntu/Personal%20Projects/Materials-MCP/INTENT.md) and [MCP_INTENT.md](file:///home/ubuntu/Personal%20Projects/Materials-MCP/MCP_INTENT.md) as the ultimate ground truth.
