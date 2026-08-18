from enum import Enum
from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class SimulationConfig(BaseModel):
    cylinders_x: int = Field(default=3, ge=0, le=20, description="Cylinder count along streamwise X; zero disables this axis")
    cylinders_y: int = Field(default=4, ge=0, le=20, description="Cylinder count along transverse Y; zero disables this axis")
    cylinders_z: int = Field(default=3, ge=0, le=20, description="Cylinder count along spanwise Z; zero disables this axis")
    cylinder_diameter: int = Field(default=12, ge=8, le=128, description="Lattice nodes")
    gap_ratio: float = Field(default=0.5, ge=0.1, le=10.0, description="Surface gap / diameter")
    reynolds_number: float = Field(default=100, gt=1, le=5000)
    prandtl_number: float = Field(default=0.71, gt=0.01, le=100)
    richardson_number: float = Field(default=0.0, ge=0.0, le=10.0)
    inlet_temperature: float = Field(default=0.0)
    cylinder_temperature: float = Field(default=1.0)
    inlet_velocity: float = Field(default=0.05, gt=0.001, le=0.15)
    time_steps: int = Field(default=10000, ge=100, le=10_000_000)
    snapshot_interval: int = Field(default=500, ge=10, le=100_000)
    include_temperature: bool = True
    include_pressure: bool = True

    @computed_field
    @property
    def total_cylinders(self) -> int:
        counts = (self.cylinders_x, self.cylinders_y, self.cylinders_z)
        return max(self.cylinders_x, 1) * max(self.cylinders_y, 1) * max(self.cylinders_z, 1)

    @computed_field
    @property
    def active_axes(self) -> list[str]:
        return [axis for axis, count in zip(("x", "y", "z"), (self.cylinders_x, self.cylinders_y, self.cylinders_z)) if count > 0]

    @field_validator("snapshot_interval")
    @classmethod
    def valid_interval(cls, value: int) -> int:
        if value % 10:
            raise ValueError("Snapshot interval must be a multiple of 10 steps")
        return value

    @model_validator(mode="after")
    def valid_temperature_difference(self):
        if self.include_temperature and self.cylinder_temperature == self.inlet_temperature:
            raise ValueError("Cylinder and inlet temperatures must differ when thermal analysis is enabled")
        return self

    @model_validator(mode="after")
    def supported_array_size(self):
        if not self.active_axes:
            raise ValueError("At least one of X, Y, or Z must contain one or more cylinders")
        if self.total_cylinders > 1_000:
            raise ValueError("Cylinder array is limited to 1,000 cylinders per run")
        return self


class RunSummary(BaseModel):
    id: str
    status: RunStatus
    progress: int = Field(ge=0, le=100)
    config: SimulationConfig
    created_at: str
    message: str | None = None
    artifact_names: list[str] = []


class RunCreated(BaseModel):
    id: str
    status: RunStatus
    message: str
