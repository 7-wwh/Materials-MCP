# Agent Operational Guide: Materials-MCP

Welcome, AI Agent. This document defines the engineering standards, architecture rules, and development protocols you MUST follow when working on the **Materials-MCP** codebase.

---

## 1. System Philosophy & Ground Rules

Materials-MCP is a **headless, self-hosted Finite Element Analysis (FEA) engine** exposed via the Model Context Protocol (MCP).

### Non-Negotiable Invariants:
1. **`src/` is STATIC Code Only**:
   * Never write user-generated scripts, CAD models, mesh files, or simulation results into `src/`.
   * `src/` contains only permanent, version-controlled library code.
2. **`artifacts/` is the DYNAMIC Run Repository**:
   * Every execution must reside in an isolated, timestamped folder created via `src.paths.get_run_directory()`:
     `artifacts/run_YYYYMMDD_HHMMSS/`
3. **The JSON-to-Script Invariant**:
   * When handling CAD generation, the server **writes a standalone, readable `model.py` directly into the run folder** and executes it there (`cwd=run_dir`).
   * This guarantees that every run is 100% self-contained, auditable, and manually runnable via `python model.py`.
4. **Human-in-the-Loop (HITL) Visual Verification**:
   * FEA simulations must never run "blind".
   * Stage 1 generates the CAD model and an offscreen 3D isometric screenshot (`preview.png`) with semantic faces labeled (`FACE_MIN_X`, `FACE_MAX_X`).
   * The user must visually confirm the geometry and boundary conditions before Stage 2 (meshing and CCX solve) executes.
5. **Context Window Protection (Progressive Disclosure)**:
   * Do not flood the agent context with 50 geometry tool schemas.
   * Provide a lightweight catalog search (`list_geometry_templates`) and fetch schemas on demand (`get_template_schema`).
   * Consolidate shapes into 4 topological primitive families: Extrusion, Revolution, Plate & Hole, Bent Bracket.
6. **Pure Headless Operation**:
   * No X11, display servers, or GUI dependencies.
   * Visualizations are rendered offscreen using `matplotlib` with the headless `Agg` backend.

---

## 2. Directory & Component Architecture

```
Materials-MCP/
├── src/                          <-- ENGINE MODULES (Static, read-only at runtime)
│   ├── paths.py                  <-- Run directory resolution & symlink management
│   ├── cad/                      <-- build123d script generator & runner
│   │   ├── generator.py          <-- Writes model.py into artifacts/run_.../
│   │   └── catalog.py            <-- Template catalog & on-demand schema registry
│   ├── preview/                  <-- Headless offscreen 3D visualizer
│   │   └── renderer.py           <-- Renders geometry.step -> preview.png
│   ├── meshing/                  <-- Gmsh orchestration (second-order C3D10 tets)
│   ├── deck/                     <-- CalculiX .inp deck builder
│   ├── solver/                   <-- CalculiX ccx CLI execution manager
│   ├── results/                  <-- .dat / .frd parser & safety factor evaluator
│   ├── reporting/                <-- PDF engineering report builder (ReportLab)
│   └── server.py                 <-- FastMCP Streamable HTTP server (Port 8000)
│
├── artifacts/                    <-- RUN STORAGE & AUDIT PACKAGES
│   ├── latest -> run_.../        <-- Symlink to most recent run
│   └── run_YYYYMMDD_HHMMSS/      <-- Self-contained run package
│       ├── model.py              <-- Generated CAD Python script
│       ├── geometry.step         <-- Exported STEP CAD model
│       ├── preview.png           <-- 3D isometric visual verification screenshot
│       ├── metadata.json         <-- Parameters, dimensions, semantic faces
│       ├── mesh.msh              <-- Gmsh finite element mesh
│       ├── simulation.inp        <-- CalculiX input deck
│       ├── simulation.dat        <-- Solver numerical results
│       └── report.pdf            <-- Formal engineering PDF report
│
├── tests/                        <-- Automated unit and integration tests
├── INTENT.md                     <-- High-level system mission & boundaries
└── MCP_INTENT.md                 <-- Detailed protocol specifications & JSON schemas
```

---

## 3. The 2-Stage Execution Lifecycle

```
[User Request]
       │
       ▼
[Agent: Clarifies load, support, and material constants]
       │
       ├─► Stage 1: Call generate_cad_model(template, parameters)
       │   ├─ Server creates artifacts/run_YYYYMMDD_HHMMSS/
       │   ├─ Server writes artifacts/run_.../model.py
       │   ├─ Server runs model.py -> exports geometry.step
       │   ├─ Server renders preview.png (isometric view + dimensions)
       │   └─ Returns run_id, preview.png, dimensions, semantic_faces
       │
       ▼
[User: Inspects preview.png & confirms boundary faces]
       │
       ├─► Stage 2: Call run_static_fea(run_id, material, boundary_faces, load)
       │   ├─ Server meshes STEP with Gmsh (second-order C3D10 elements)
       │   ├─ Server generates simulation.inp
       │   ├─ Server executes CalculiX ccx
       │   ├─ Server parses simulation.dat -> Von Mises, displacement, Safety Factor
       │   ├─ Server generates report.pdf
       │   └─ Returns engineering verdict (PASS/FAIL), SF, and report path
       ▼
[User receives engineering report]
```

---

## 4. Testing & Verification Protocols

When making changes to the codebase, always verify against the automated test suite:

1. **Virtual Environment**:
   Always execute using the project's virtual environment:
   `/home/ubuntu/Personal Projects/Materials-MCP/.venv/bin/python`

2. **Run All Tests**:
   ```bash
   /home/ubuntu/Personal\ Projects/Materials-MCP/.venv/bin/python -m unittest discover tests -v
   ```

3. **Verify Dependencies**:
   * CalculiX solver: `ccx -v`
   * Gmsh CLI: `gmsh --version`
   * Python modules: `build123d`, `gmsh`, `matplotlib`

4. **Test Run Cleanliness**:
   * Tests creating mock run folders in `artifacts/` must clean up after themselves in `tearDown()` or `finally` blocks unless verifying persistence specifically.

---

## 5. Key Documentation References
* **[INTENT.md](file:///home/ubuntu/Personal%20Projects/Materials-MCP/INTENT.md)**: Master project mission, non-goals, and phased evolution roadmap.
* **[MCP_INTENT.md](file:///home/ubuntu/Personal%20Projects/Materials-MCP/MCP_INTENT.md)**: Exact JSON request/response contracts, MCP prompts, and error recovery tables.
