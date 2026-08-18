from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.models import RunStatus, RunSummary, SimulationConfig
from app.services.demo_solver import generate_demo_artifacts

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
_runs: dict[str, RunSummary] = {}
_lock = Lock()


def create_run(config: SimulationConfig) -> RunSummary:
    run_id = uuid4().hex[:12]
    run = RunSummary(
        id=run_id,
        status=RunStatus.queued,
        progress=0,
        config=config,
        created_at=datetime.now(UTC).isoformat(),
        message="Waiting for worker",
    )
    with _lock:
        _runs[run_id] = run
    (RUNS_DIR / run_id).mkdir(parents=True, exist_ok=False)
    return run


def get_run(run_id: str) -> RunSummary | None:
    with _lock:
        return _runs.get(run_id)


def list_runs() -> list[RunSummary]:
    with _lock:
        return sorted(_runs.values(), key=lambda run: run.created_at, reverse=True)


def update_run(run_id: str, **changes) -> None:
    with _lock:
        run = _runs[run_id]
        for key, value in changes.items():
            setattr(run, key, value)


def run_demo_simulation(run_id: str) -> None:
    """Temporary deterministic visual pipeline. Replace with compiled solver runner."""
    run = get_run(run_id)
    if not run:
        return
    try:
        update_run(run_id, status=RunStatus.running, progress=10, message="Preparing geometry")
        artifact_names = generate_demo_artifacts(
            run.config,
            RUNS_DIR / run_id,
            progress=lambda value, text: update_run(run_id, progress=value, message=text),
        )
        update_run(
            run_id,
            status=RunStatus.completed,
            progress=100,
            message="Demo field and visualizations generated",
            artifact_names=artifact_names,
        )
    except Exception as error:  # expose failure state to UI without killing API worker
        update_run(run_id, status=RunStatus.failed, message=str(error))


def get_artifact_path(run_id: str, artifact_name: str) -> Path | None:
    if Path(artifact_name).name != artifact_name:
        return None
    path = RUNS_DIR / run_id / artifact_name
    return path if path.is_file() else None
