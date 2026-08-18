from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
from pathlib import Path

from app.models import RunCreated, RunSummary, SimulationConfig
from app.services.run_manager import create_run, get_run, list_runs, run_demo_simulation
from app.services.dat_parser import parse_dat_file, generate_preview

app = FastAPI(title="CFD Visualizer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/runs", response_model=list[RunSummary])
def runs():
    return list_runs()


@app.post("/api/runs", response_model=RunCreated, status_code=202)
def start_run(config: SimulationConfig, background_tasks: BackgroundTasks):
    run = create_run(config)
    background_tasks.add_task(run_demo_simulation, run.id)
    return RunCreated(id=run.id, status=run.status, message="Simulation queued")


@app.get("/api/runs/{run_id}", response_model=RunSummary)
def run_details(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run


@app.get("/api/runs/{run_id}/artifacts/{artifact_name}")
def artifact(run_id: str, artifact_name: str):
    from fastapi.responses import FileResponse
    from app.services.run_manager import get_artifact_path

    path = get_artifact_path(run_id, artifact_name)
    if not path:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path)

@app.post("/api/analysis/preview")
def upload_dat_preview(file: UploadFile = File(...)):
    import uuid
    # Create temp directory
    temp_id = str(uuid.uuid4())
    temp_dir = Path(f"runs/temp_{temp_id}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = temp_dir / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        parsed = parse_dat_file(file_path)
        preview_image = temp_dir / "preview.png"
        plot_var = generate_preview(parsed, preview_image)
        
        return {
            "id": temp_id,
            "filename": file.filename,
            "variables": parsed["variables"],
            "zones_count": len(parsed["zones"]),
            "i": parsed["zones"][0]["i"],
            "j": parsed["zones"][0]["j"],
            "preview_url": f"/api/analysis/{temp_id}/preview.png",
            "plotted_variable": plot_var
        }
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/analysis/{temp_id}/{filename}")
def analysis_artifact(temp_id: str, filename: str):
    from fastapi.responses import FileResponse
    path = Path(f"runs/temp_{temp_id}/{filename}")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Analysis artifact not found")
    return FileResponse(path)

@app.post("/api/analysis/{temp_id}/thermal")
def run_thermal_analysis(temp_id: str):
    from app.services.thermal_analysis import analyze_thermal_blobs
    try:
        results = analyze_thermal_blobs(temp_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/analysis/{temp_id}/vortex")
def run_vortex_analysis_endpoint(temp_id: str):
    from app.services.vortex_analysis import analyze_vortices
    try:
        return analyze_vortices(temp_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
