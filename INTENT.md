# Project Intent & System Boundaries: Materials-MCP

## 1. Executive Summary & Mission
**Materials-MCP** is a self-hosted, headless Finite Element Analysis (FEA) execution engine wrapped in the Model Context Protocol (MCP).

Its purpose is to give on-field engineers and designers immediate, engineering-grade structural and fatigue sanity checks directly within AI chat harnesses (Claude Desktop, Cursor, Gemini, GPT) using a **staged, visually verified Human-in-the-Loop (HITL) workflow**.

---

## 2. The Core Separation of Responsibilities

A key architectural rule of this system is the strict division between **Reasoning** and **Computation**:

```
[ User / On-Field Engineer ]
            │ (Plain English: "Will a 200x25x15mm 6061-Al beam hold 500N at the tip?")
            ▼
[ External AI Harness: Claude / GPT / Gemini ]
    ├─ 1. Clarifies design intent & boundary conditions (Support type, load direction)
    ├─ 2. Validates material constants (E, ν, Yield Strength)
    ├─ 3. Discovers template schema on-demand (Progressive Disclosure)
    └─ 4. Calls CAD & FEA tools with structured parameters
            │
            ├─► Step 1: Tool call: generate_cad_model(...)
            │   ◄── Returns: run_id, preview.png, dimensions, semantic faces
            │   (Agent embeds preview.png: "Face 1 fixed, 500N on Face 2. Confirm?")
            │
            ▼ (Upon User Confirmation)
            ├─► Step 2: Tool call: run_static_fea(run_id, material, boundary_faces, load)
            │
[ Materials-MCP Server (Local / Container) ]
    ├─ Stage 1: Run Directory Creation (artifacts/run_YYYYMMDD_HHMMSS/)
    ├─ Stage 2: Standalone Script Generation (writes & runs model.py locally)
    ├─ Stage 3: Headless 3D Visualization (renders offscreen preview.png)
    ├─ Stage 4: Finite Element Meshing (Gmsh second-order C3D10 tets)
    ├─ Stage 5: Solver Execution (CalculiX ccx CLI)
    ├─ Stage 6: Safety Factor Evaluation & PDF Report Generation
    │       │
    │       ▼ (Returns: Stress, Displacement, Safety Factor, PDF Path)
[ External AI Harness ]
    │ (Presents verdict, stress margins, and PDF link to engineer)
    ▼
[ User / On-Field Engineer ]
```

---

## 3. Explicit Non-Goals (What This Server Does NOT Do)

To keep the system lean, reliable, and decoupled:

* **NO In-Process Web Scraping**: The server does not query Google, Tavily, or materials databases. The client-side AI harness handles material research.
* **NO Internal LLMs / API Keys**: The server requires zero external API keys (no OpenAI, no Anthropic, no Gemini keys on the server). It operates 100% offline once built.
* **NO Custom Web UI**: There is no custom HTML/React frontend to build or maintain. The user's AI client *is* the user interface.
* **NO GUI / Display Dependencies**: The server does not install X11 or graphical pre/post-processors (`cgx`). It uses offscreen headless visualization (`matplotlib` Agg) and the pure CLI solver (`ccx`).
* **NO Run Data Inside `src/`**: The `src/` directory is strictly static, version-controlled code. All generated scripts, models, meshes, and results live exclusively inside isolated run directories under `artifacts/`.

---

## 4. Storage Architecture & The JSON-to-Script Invariant

Every request is executed through an **auditable, self-contained run package**:

```
Materials-MCP/
├── src/                          <-- STATIC ENGINE ONLY (Read-only at runtime)
│   ├── paths.py                  <-- Run directory resolver
│   ├── cad/                      <-- build123d script generator & runner
│   ├── preview/                  <-- Headless 3D visualizer
│   ├── meshing/                  <-- Gmsh orchestration
│   ├── solver/                   <-- CalculiX ccx wrapper
│   └── server.py                 <-- FastMCP Streamable HTTP server
│
└── artifacts/                    <-- DYNAMIC AUDIT TRAIL ONLY
    ├── latest -> run_20261024_121500/
    │
    └── run_20261024_121500/      <-- Isolated Run Package
        ├── model.py              <-- Standalone build123d script generated from JSON
        ├── geometry.step         <-- 3D CAD STEP file
        ├── preview.png           <-- 3D isometric visual verification screenshot
        ├── metadata.json         <-- Parameters, dimensions, semantic faces
        ├── mesh.msh              <-- Gmsh finite element mesh
        ├── simulation.inp        <-- CalculiX input deck
        ├── simulation.dat        <-- Solver numerical results
        └── report.pdf            <-- Formal engineering PDF report
```

### The JSON-to-Script Invariant:
When the server receives a tool request with parameters (e.g., diameter, length, force), it **does not edit `src/`**. It writes a standalone, readable `model.py` directly into the designated `artifacts/run_.../` directory and executes it there. This guarantees:
1. **100% Auditability**: Every run preserves the exact Python script that built its geometry.
2. **CLI Debuggability**: Any run can be reproduced manually by typing `python model.py` inside its folder.
3. **Zero Cross-Contamination**: Multi-user and multi-session runs never collide.

---

## 5. Context Window Protection (Progressive Disclosure)

To support 50+ geometric components without bloating the agent's context window:
* **The Catalog Pattern**: The agent is not burdened with 50 tool schemas upfront.
* **Tier 1 (Discovery)**: The agent calls `list_geometry_templates(category, query)` to discover template IDs.
* **Tier 2 (Schema-on-Demand)**: The agent calls `get_template_schema(template_id)` to fetch parameters, units, and semantic faces for only the requested part.
* **Tier 3 (Execution)**: The agent calls `generate_cad_model(template, parameters)` with verified arguments.
* **Topological Families**: Under the hood, 50 catalog presets are powered by 4 parametric primitive engines:
  1. *Extrusion* (box, I-beam, T-profile, C-channel, pipe, hex bar).
  2. *Revolution* (solid cylinder, stepped shaft, hollow tube, flange).
  3. *Plate & Hole* (baseplate, gusset, mounting plate with bolt circles).
  4. *Bent Bracket* (L-bracket, U-bracket).

---

## 6. Exposed MCP Tools Contract

The server exposes tools over **Streamable HTTP** (`/mcp`) on port `8000`:

### A. `list_geometry_templates`
* **Purpose**: Query available geometry catalog templates by category or keyword (< 200 tokens).

### B. `get_template_schema`
* **Purpose**: Retrieve the exact parameter specification, limits, defaults, and semantic faces for a single template on-demand.

### C. `generate_cad_model`
* **Purpose**: Create isolated run directory, write `model.py`, export `geometry.step`, render `preview.png`, and return semantic faces for user verification.

### D. `run_static_fea`
* **Purpose**: Mesh confirmed CAD model, write `.inp`, run `ccx`, compute Von Mises stress, displacement, Safety Factor, and build `report.pdf`.

### E. `run_fatigue_fea`
* **Purpose**: Perform high-cycle fatigue calculation (Basquin S-N) for alternating/pulsating loads.

### F. `run_quick_beam_analysis`
* **Purpose**: Single-turn convenience macro for standard cantilever beam sanity checks.

---

## 7. Technical Requirements & Standards

* **Accuracy Standard**: Target is **engineering-grade** ($\pm 10\%$ agreement with classical analytical beam/shaft formulas).
* **Solvers**: CalculiX `ccx` (CLI) and Gmsh with second-order tetrahedral elements (`C3D10` / Gmsh type 11).
* **Transport**: MCP JSON-RPC 2.0 over Streamable HTTP on port `8000`.
* **Containerization**: Linux arm64 and amd64, completely headless with zero X11/display dependencies.

---

## 8. Phased Evolution

* **Phase 1 (Current Focus)**:
  * Run directory isolation and `paths.py` enhancement (`artifacts/run_.../`).
  * CAD script generator (`model.py` writer) and runner for `beam_rectangular`.
  * Headless offscreen 3D isometric visualizer (`preview.png` generator).
  * FastMCP server exposing `list_geometry_templates`, `get_template_schema`, and `generate_cad_model`.
* **Phase 2**:
  * Gmsh second-order C3D10 meshing service.
  * CalculiX `.inp` deck builder mapping semantic faces to node sets.
  * `run_static_fea` and `run_fatigue_fea` solver execution and results parser.
  * Automated PDF engineering report generator.
* **Phase 3**:
  * Additional topological families (shafts, plates, brackets).
  * Multi-user directory partitioning (`artifacts/users/{user_id}/`).

---

## 9. License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See the [LICENSE](file:///home/ubuntu/Personal%20Projects/Materials-MCP/LICENSE) file for complete terms.

