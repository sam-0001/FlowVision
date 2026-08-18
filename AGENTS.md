# CFD Visualizer Workspace

## Structure

- `frontend/`: React + Vite client application.
- `backend/`: FastAPI service, simulation-run orchestration, analysis, and plot generation.
- `backend/runs/`: generated local run artifacts; never commit its contents.

## Development rules

- Keep the CFD solver separate from the API layer. The API must run jobs asynchronously and never block request handlers.
- Validate all simulation settings at the API boundary. Derived values such as viscosity must be calculated by the backend, not trusted from the client.
- Use `run_id`-scoped directories for every result. Do not overwrite a previous run's fields, plots, or metadata.
- Treat a 3D or buoyancy-enabled solver as a separately validated feature; do not present it as supported until a numerical implementation and validation cases exist.
- The current demo solver produces synthetic fields only, clearly labelled `demo`. Replace only `backend/app/services/demo_solver.py` when connecting the compiled LBM solver.
- Prefer HDF5/NumPy for full numerical snapshots and write Tecplot `.dat` as an export format, not as the main internal format.

## Commands

Backend: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000`

Frontend: `cd frontend && npm install && npm run dev`
