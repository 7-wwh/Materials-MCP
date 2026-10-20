# Project Intent & System Boundaries: Materials-MCP

## 1. Executive Summary & Mission
**Materials-MCP** is a self-hosted, headless Finite Element Analysis (FEA) execution engine wrapped in the Model Context Protocol (MCP).

Its purpose is to give on-field engineers and designers immediate, engineering-grade structural and fatigue sanity checks directly within AI chat harnesses (Claude Desktop, Cursor, Gemini, GPT).

---

## 2. The Core Separation of Responsibilities

A key architectural rule of this system is the strict division between **Reasoning** and **Computation**:

```
[ User / On-Field Engineer ]
            │ (Plain English: "Will a 300x25x15mm 6061-Al beam hold 800N?")
            ▼
[ External AI Harness: Claude / GPT / Gemini ]
    ├─ Understands context & design intent
    ├─ Researches/validates material properties (E, ν, Yield Strength, etc.)
    ├─ Selects template & dimensions
    └─ Formulates clean tool parameters
            │
            ▼ (MCP Streamable HTTP)
[ Materials-MCP Server (Inside Docker) ]
    ├─ 1. Parametric 3D Modeling (build123d)
    ├─ 2. Finite Element Meshing (gmsh)
    ├─ 3. Physics & Solver Execution (CalculiX ccx via SPOOLES/ARPACK)
    ├─ 4. Results Parsing & Safety Factor Evaluation
    └─ 5. PDF Engineering Report Generation
            │
            ▼ (Returns: Stress, Displacement, Safety Factor, PDF Path)
[ External AI Harness ]
            │ (Explains results clearly to engineer)
            ▼
[ User / On-Field Engineer ]
```

---

## 3. Explicit Non-Goals (What This Server Does NOT Do)

To keep the system lean, reliable, and decoupled:

* **NO Web Scraping or Search on Server**: The server does not query Google, Tavily, or materials databases. The client-side AI harness handles material research.
* **NO Internal LLMs / API Keys**: The server requires zero external API keys (no OpenAI, no Anthropic, no Gemini keys on the server). It operates 100% offline once the container is built.
* **NO Custom Web UI**: There is no custom HTML/React frontend to build or maintain. The user's AI client *is* the user interface.
* **NO GUI / Display Dependencies**: The server does not install X11, OpenGL, or graphical pre/post-processors (`cgx`). It uses the pure CLI solver (`ccx`).

---

## 4. Exposed MCP Tools (The Contract)

The server exposes two primary tools over **Streamable HTTP** (`/mcp`):

### A. `run_static_fea`
* **Purpose**: Determine if a part will yield or deflect excessively under a single static load.
* **Inputs**:
  * Material: `material_name`, `E_gpa`, `nu`, `yield_strength_mpa`, `density_kg_m3`
  * Geometry: `template` (`beam`), `length_mm`, `width_mm`, `height_mm`
  * Loading: `load_n`, `load_direction` (`transverse`, `axial`)
  * Target: `safety_factor_target` (default: 2.0)
* **Outputs**: Max Von Mises stress (MPa), max displacement (mm), safety factor, verdict (`PASS`/`FAIL`), summary text, and path to generated PDF report.

### B. `run_fatigue_fea`
* **Purpose**: Determine how many cycles a part will survive under alternating or pulsating loads (high-cycle fatigue using Basquin's S-N approach).
* **Inputs**:
  * Material: All static properties + `ultimate_strength_mpa`
  * Geometry: Same geometry parameters
  * Loading: `load_max_n`, `load_min_n`, `target_cycles`
* **Outputs**: Stress amplitude (MPa), stress ratio $R$, estimated cycles to failure, verdict (`PASS`/`FAIL`), summary text, and path to generated PDF report.

---

## 5. Technical Requirements & Standards

* **Accuracy Standard**: Target is **engineering-grade** ($\pm 10\%$ agreement with classical analytical beam/shaft formulas).
* **Isolation**: All solvers, libraries, and runtimes live strictly inside a Docker container. Host system remains 100% untouched.
* **Transport**: MCP Streamable HTTP on port `8000` (compatible with Claude, Gemini, OpenAI, and modern IDEs).
* **Auditability**: Every run produces a persistent artifacts folder containing:
  * `geometry.step` (CAD model)
  * `mesh.msh` (Finite element mesh)
  * `simulation.inp` (CalculiX input deck)
  * `simulation.dat` / `.frd` (Raw solver results)
  * `report.pdf` (Formal engineering report)

---

## 6. Phased Evolution

* **Phase 1 (Current MVP)**:
  * Single-service container on local arm64 server.
  * `beam` geometry template.
  * Static & fatigue analysis tools.
  * Automated PDF report generation.
* **Phase 2**:
  * Additional geometric templates (`plate`, `cylinder`, `bracket`).
  * Stress contour visualizations embedded in the PDF report.
* **Phase 3**:
  * Multi-platform image distribution (`linux/arm64` and `linux/amd64`).
  * Concurrent job queueing.
  * Natural-language to custom `build123d` geometry agent.
