# CFD Visualizer - Task Status

**Last updated:** 2026-08-18  
**Current truth:** The web application structure works, but its generated CFD fields and plots are labelled **demo**. They are not yet validated scientific simulation results.

## Goal

Build an application in which a user configures a heated square-cylinder array, runs a CFD simulation, receives numerical field files, and automatically obtains paper-style analysis and images.

The array must support one, two, or three active axes:

| User input | Meaning | Total cylinders |
|---|---:|---:|
| `X=3, Y=0, Z=0` | 1D array along X | 3 |
| `X=3, Y=4, Z=0` | 2D X-Y array | 12 |
| `X=3, Y=4, Z=3` | 3D X-Y-Z array | 36 |

`0` means that an axis is disabled. `X=0, Y=0, Z=0` is invalid.

---

## Task-wise status

### Task 1 - Project structure and engineering setup

**Status: Complete**

Completed:

- Created separate `frontend/` and `backend/` folders.
- Added root `AGENTS.md` with development rules and commands.
- Added `.gitignore` for generated runs, virtual environments, and frontend build files.
- Added run-scoped output folders so one simulation does not overwrite another.

Files:

- `frontend/`
- `backend/`
- `AGENTS.md`

---

### Task 2 - Frontend simulation form

**Status: Complete for configuration; not yet connected to a real solver**

Completed:

- Professional dashboard interface.
- Inputs for X, Y, and Z cylinder counts.
- Inputs for cylinder diameter, `s/d`, Reynolds number, Prandtl number, inlet velocity, inlet temperature, cylinder temperature, time steps, and snapshot interval.
- Validation of minimum/maximum input values.
- Derived display for total cylinder count, viscosity, thermal diffusivity, and estimated grid width.
- Live run status, progress indicator, result gallery, recent runs, and `.dat` download link.

Remaining:

- Add Richardson number (`Ri`) to the UI only after buoyancy physics is implemented in the solver.
- Add separate spacing controls for X, Y, and Z if the physical model requires unequal spacing.
- Add solver hardware/runtime estimate before starting a run.

---

### Task 3 - API and run management

**Status: Complete for the demo workflow**

Completed:

- FastAPI backend with health, create-run, run-status, run-list, and artifact-download endpoints.
- Background simulation job interface.
- Run-specific metadata and artifact names.
- Backend validation: at least one axis must be active; maximum supported configured array is 1,000 cylinders.

Remaining:

- Persist jobs and results in a database instead of temporary in-memory state.
- Add queued-worker support for long CFD jobs.
- Add cancel, restart-from-checkpoint, and failure-log endpoints.
- Add authentication if this will be a multi-user app.

---

### Task 4 - Current `.dat` output

**Status: Working as demo output only**

Completed:

- Generates a Tecplot-style `.dat` file containing:
  `X, Y, VX, VY, PRESS, TEMP, VORTICITY, OBST`.
- Produces per-run `config.json` and force CSV.

Important limitation:

- These current fields are synthetic preview fields, not calculated from the supplied Fortran model or a validated CFD solver.

Remaining:

- Connect the application to the actual solver.
- Store full simulation snapshots efficiently in HDF5/NumPy format.
- Export Tecplot `.dat` from those actual snapshots when required.
- Preserve time index and physical/nondimensional metadata in each output file.

---

### Task 5 - Automated visual output

**Status: Working as demo visualization only**

Completed:

- Temperature contour image.
- Pressure contour image.
- Vorticity/wake contour image.
- Velocity-streamline image.
- Lift and drag time-history image.
- Cylinder geometry, axes, colour scales, and result titles are included.

Important limitation:

- The images look like scientific figures, but they are generated from demo fields. They cannot yet be used as research results.

Remaining:

- Generate these images from actual solver output.
- Match the exact figure formats needed from the reference paper: contour levels, dimensions, colour ranges, labels, and multi-panel layouts.
- Add animation/video export across saved time steps.

---

### Task 6 - Read existing `.dat` files

**Status: Not started**

Required work:

- Upload/select existing Tecplot-style `.dat` files.
- Parse variable headers and grid dimensions.
- Support files containing temperature only, velocity/pressure only, or combined fields.
- Validate missing variables, malformed rows, and obstacle masks.
- Display the parsed field before analysis.

Acceptance check:

- A user can upload `Temperature_field.dat` or `anb903.dat` from the existing Fortran run and see a correct field preview.

---

### Task 7 - Temperature/thermal-blob analysis

**Status: Not started**

Required work:

- Choose an ambient/reference temperature.
- Detect the thermal blob from a defined temperature-excess threshold.
- Calculate its centre using a temperature-weighted centroid.
- Calculate and plot thermal strength, such as maximum temperature excess, integrated temperature excess, and blob area.
- Export the calculated centre and strength values to CSV.

Acceptance check:

- For every selected time step, the app marks the thermal-blob centre on the temperature contour and produces a strength-vs-time graph.

---

### Task 8 - Vortex and pressure analysis

**Status: Not started**

Required work:

- Calculate vorticity from `VX` and `VY`.
- Detect vortex centres using a defined method: vorticity extrema plus a velocity-based method such as swirling strength or Q-criterion.
- Do not use pressure minimum alone as proof of a vortex; pressure can support the result but velocity data is needed.
- Calculate vortex strength using circulation and/or peak vorticity.
- Plot vortex centre trajectories and vortex strength versus time.

Acceptance check:

- Vortex centres and their signs are overlaid on real vorticity contours, with a numerical strength plot for each tracked vortex.

---

### Task 9 - Integrate and optimize the supplied Fortran solver

**Status: Not started**

Findings from the supplied code:

- It is a 2D D2Q9 lattice-Boltzmann solver.
- The provided version is configured for six square cylinders, not a general X/Y/Z array.
- Reynolds number is hardcoded to 100 in the source.
- Prandtl number is hardcoded to 0.71.
- `Ri` is set to zero and is not used to apply a buoyancy force.
- Very frequent console and full-field disk output are likely major reasons for the reported 8-9 day runtime.

Required work:

1. Preserve a copy of the existing solver and reproduce a known reference result.
2. Refactor fixed constants into a configuration file/API input.
3. Remove per-step debug printing.
4. Save full fields only at a selected snapshot interval.
5. Use compiled/vectorized numerical kernels rather than a line-by-line pure-Python port.
6. Benchmark runtime and validate force coefficients, Nusselt numbers, and field contours against the current code and reference paper.

Acceptance check:

- The optimized solver reproduces agreed 2D reference cases within a documented tolerance and gives a measured runtime improvement.

---

### Task 10 - Richardson number and thermal buoyancy

**Status: Not started**

Required work:

- Implement buoyancy coupling between temperature and momentum.
- Define the nondimensionalisation and the relationship between `Ri`, `Re`, `Pr`, and thermal boundary conditions.
- Add `Ri` as a user input only after validation.
- Validate natural, forced, and mixed convection cases.

Acceptance check:

- Changing `Ri` changes the computed velocity/temperature field in physically expected and validated ways.

---

### Task 11 - True 3D solver

**Status: Not started**

Current limitation:

- The current interface accepts X/Y/Z counts, but the solver and visual preview are not a true 3D calculation. The preview is only a 2D projection/slice.

Required work:

- Implement or integrate a D3Q19/D3Q27 lattice-Boltzmann solver, or another validated 3D CFD solver.
- Build voxel geometry for all active X/Y/Z cylinder positions.
- Implement 3D boundary conditions and thermal coupling.
- Save 3D scalar/vector fields.
- Provide X-Y, X-Z, and Y-Z slices; 3D streamline/isosurface visualizations; and time animation.
- Validate small 3D cases before large arrays.

Acceptance check:

- A case such as `X=3, Y=4, Z=3` runs as a true 3D field simulation and exports 3D numerical data, not a 2D preview.

---

## Recommended execution order

1. Implement Task 6: read actual existing `.dat` files.
2. Implement Tasks 7 and 8: thermal and vortex analysis from real files.
3. Implement Task 9: optimize and integrate the 2D Fortran solver.
4. Implement Task 10: validate buoyancy and Richardson number.
5. Implement Task 11: true 3D simulation.

This order gives useful real analysis early, while avoiding an unvalidated jump from the current 2D code directly to a large 3D solver.
