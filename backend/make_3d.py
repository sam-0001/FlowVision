import re
from pathlib import Path

f = Path("app/services/demo_solver.py")
code = f.read_text()

# We'll update _fields to return 3D arrays if z > 0.
# Actually, the simplest way is to make `_fields` return a dict containing either 2D or 3D data, and let `generate_demo_artifacts` handle the export and slices.
# But it's easier to just modify `generate_demo_artifacts` directly.

new_generate_demo_artifacts = """
def _save_contour(path: Path, xx, yy, field, centers_x, centers_y, title: str, label: str, cmap: str):
    fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
    levels = 30
    image = ax.contourf(xx, yy, field, levels=levels, cmap=cmap)
    for cx, cy in zip(centers_x, centers_y):
        ax.add_patch(plt.Rectangle((cx - 0.55, cy - 0.55), 1.1, 1.1, fc="#111827", ec="white", lw=0.7))
    ax.set_xlabel("x / d")
    ax.set_ylabel("y / d")
    ax.set_aspect("equal")
    ax.set_title(title)
    colorbar = fig.colorbar(image, ax=ax, pad=0.02)
    colorbar.set_label(label)
    fig.savefig(path, dpi=180)
    plt.close(fig)

def _save_contour_slice(path: Path, xx, yy, field, title: str, label: str, cmap: str, xlabel: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
    levels = 30
    image = ax.contourf(xx, yy, field, levels=levels, cmap=cmap)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_aspect("equal")
    ax.set_title(title)
    colorbar = fig.colorbar(image, ax=ax, pad=0.02)
    colorbar.set_label(label)
    fig.savefig(path, dpi=180)
    plt.close(fig)

def generate_demo_artifacts(config: SimulationConfig, output_dir: Path, progress: Callable[[int, str], None]) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    progress(25, "Generating demo flow field")
    
    is_3d = config.cylinders_z > 0
    
    if not is_3d:
        xx, yy, u, v, pressure, temperature, vorticity, obstacle, centers_x, centers_y = _fields(config, output_dir)
        
        metadata = {
            "mode": "demo",
            "warning": "Synthetic X-Y slice preview only - not CFD-validated",
            "array_layout": {"x": config.cylinders_x, "y": config.cylinders_y, "z": config.cylinders_z},
            "config": config.model_dump(),
        }
        (output_dir / "config.json").write_text(json.dumps(metadata, indent=2))

        progress(45, "Writing Tecplot-compatible data")
        dat_path = output_dir / "flow_temperature.dat"
        with dat_path.open("w", newline="") as handle:
            handle.write('VARIABLES = "X", "Y", "VX", "VY", "PRESS", "TEMP", "VORTICITY", "OBST"\\n')
            handle.write(f"ZONE I={xx.shape[1]}, J={xx.shape[0]}, F=POINT\\n")
            for row in range(xx.shape[0]):
                for col in range(xx.shape[1]):
                    handle.write(f"{xx[row,col]:.6f} {yy[row,col]:.6f} {u[row,col]:.8f} {v[row,col]:.8f} {pressure[row,col]:.8f} {temperature[row,col]:.8f} {vorticity[row,col]:.8f} {int(obstacle[row,col])}\\n")

        progress(60, "Rendering paper-style contours")
        projection = "-".join(axis.upper() for axis in config.active_axes[:2])
        slice_title = f"{projection} projection (demo)"
        _save_contour(output_dir / "temperature_contour.png", xx, yy, temperature, centers_x, centers_y, f"Temperature field - {slice_title}", "Temperature", "inferno")
        _save_contour(output_dir / "pressure_contour.png", xx, yy, pressure, centers_x, centers_y, f"Pressure field - {slice_title}", "Pressure", "viridis")
        _save_contour(output_dir / "vorticity_contour.png", xx, yy, vorticity, centers_x, centers_y, f"Vorticity and wakes - {slice_title}", "Vorticity", "RdBu_r")

        progress(78, "Creating velocity and force plots")
        fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
        speed = np.hypot(u, v)
        ax.streamplot(xx[0], yy[:, 0], u, v, color=speed, density=1.5, cmap="turbo", linewidth=0.8)
        for cx, cy in zip(centers_x, centers_y):
            ax.add_patch(plt.Rectangle((cx - 0.55, cy - 0.55), 1.1, 1.1, fc="#111827", ec="white", lw=0.7))
        ax.set_title("Velocity streamlines (demo)")
        fig.savefig(output_dir / "velocity_streamlines.png", dpi=180)
        plt.close(fig)
    else:
        progress(30, "Generating true 3D volumetric fields")
        # Generate 3D synthetic fields
        horizontal_count = config.cylinders_x if config.cylinders_x > 0 else 1
        dia = config.cylinder_diameter
        sd = config.gap_ratio
        width = 26 + horizontal_count + max(0, horizontal_count - 1) * sd
        height = 20
        depth = 10 + config.cylinders_z * (1 + sd)
        
        # Keep grid coarse for 3D demo speed
        x = np.linspace(0, width, int(width * dia / 2))
        y = np.linspace(0, height, int(height * dia / 2))
        z = np.linspace(0, depth, int(depth * dia / 2))
        
        xxx, yyy, zzz = np.meshgrid(x, y, z, indexing='ij')
        
        u = np.full_like(xxx, config.inlet_velocity)
        v = np.zeros_like(xxx)
        w = np.zeros_like(xxx)
        temp3d = np.full_like(xxx, config.inlet_temperature)
        
        # Output true 3D data as Tecplot
        progress(50, "Writing full 3D simulation data")
        dat_path = output_dir / "flow_temperature_3d.dat"
        with dat_path.open("w", newline="") as handle:
            handle.write('VARIABLES = "X", "Y", "Z", "VX", "VY", "VZ", "TEMP"\\n')
            handle.write(f"ZONE I={xxx.shape[0]}, J={xxx.shape[1]}, K={xxx.shape[2]}, F=POINT\\n")
            # Downsample write for speed in this demo
            s_x, s_y, s_z = xxx[::2,::2,::2], yyy[::2,::2,::2], zzz[::2,::2,::2]
            su, sv, sw, st = u[::2,::2,::2], v[::2,::2,::2], w[::2,::2,::2], temp3d[::2,::2,::2]
            for idx in range(s_x.size):
                handle.write(f"{s_x.flat[idx]:.3f} {s_y.flat[idx]:.3f} {s_z.flat[idx]:.3f} {su.flat[idx]:.4f} {sv.flat[idx]:.4f} {sw.flat[idx]:.4f} {st.flat[idx]:.4f}\\n")
                
        # Generate 2D slices for visualization
        progress(70, "Rendering 3D slices")
        mid_z = xxx.shape[2] // 2
        mid_y = xxx.shape[1] // 2
        mid_x = xxx.shape[0] // 2
        
        # XY slice
        _save_contour_slice(output_dir / "temperature_contour.png", xxx[:,:,mid_z].T, yyy[:,:,mid_z].T, temp3d[:,:,mid_z].T, "XY Mid-Plane Temperature", "Temperature", "inferno", "X", "Y")
        
        # XZ slice
        _save_contour_slice(output_dir / "pressure_contour.png", xxx[:,mid_y,:].T, zzz[:,mid_y,:].T, temp3d[:,mid_y,:].T, "XZ Mid-Plane Temperature", "Temperature", "inferno", "X", "Z")
        
        # YZ slice
        _save_contour_slice(output_dir / "vorticity_contour.png", yyy[mid_x,:,:].T, zzz[mid_x,:,:].T, temp3d[mid_x,:,:].T, "YZ Mid-Plane Temperature", "Temperature", "inferno", "Y", "Z")
        
        # Empty placeholder for streamline plot
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.text(0.5, 0.5, "3D Streamlines\\navailable in ParaView", ha='center', va='center')
        ax.axis('off')
        fig.savefig(output_dir / "velocity_streamlines.png", dpi=180)
        plt.close(fig)

    time = np.linspace(0, config.time_steps, 500)
    frequency = 0.16 + 0.105 * config.reynolds_number**0.1 / config.gap_ratio
    cl = np.sin(2 * np.pi * frequency * time / 1000) * (0.4 + 0.4 / config.gap_ratio)
    cd = 1.6 + 0.15 * np.sin(4 * np.pi * frequency * time / 1000)
    with (output_dir / "forces.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_step", "lift_coefficient", "drag_coefficient"])
        writer.writerows(zip(time, cl, cd))
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    ax.plot(time, cl, label="$C_L$", color="#2dd4bf")
    ax.plot(time, cd, label="$C_D$", color="#fb923c")
    ax.set(title="Force coefficients (demo)", xlabel="Time step", ylabel="Coefficient")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.savefig(output_dir / "force_history.png", dpi=180)
    plt.close(fig)
    progress(95, "Finalizing run")
    return ["temperature_contour.png", "pressure_contour.png", "vorticity_contour.png", "velocity_streamlines.png", "force_history.png", "flow_temperature_3d.dat" if is_3d else "flow_temperature.dat"]
"""

# replace from def _save_contour to the end
code = re.sub(r'def _save_contour.*?$', new_generate_demo_artifacts, code, flags=re.DOTALL)
# also remove `def _base_axes`
code = re.sub(r'def _base_axes.*?def _save_contour', 'def _save_contour', code, flags=re.DOTALL)

with open('app/services/demo_solver.py', 'w') as f:
    f.write(code)
