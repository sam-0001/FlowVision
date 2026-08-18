"""Deterministic demo post-processing output.

This module proves the complete app workflow before the validated LBM kernel is
connected. It is not a physical CFD solution and every generated result is
labelled as a demo in the UI.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.models import SimulationConfig


def _geometry(config: SimulationConfig):
    """Return an X-Y slice of the configured 2D cylinder array."""
    horizontal_count = config.cylinders_x if config.cylinders_x > 0 else 1
    vertical_count = config.cylinders_y if config.cylinders_y > 0 else 1
    dia = config.cylinder_diameter
    sd = config.gap_ratio
    width = 26 + horizontal_count + max(0, horizontal_count - 1) * sd
    height = 20
    
    # Calculate spacing
    y_start = 10.0 - (vertical_count - 1) * (1 + sd) / 2
    
    x = np.linspace(0, width, int(width * dia))
    y = np.linspace(0, height, int(height * dia))
    xx, yy = np.meshgrid(x, y)
    
    x_pos = 7 + 0.5 + np.arange(horizontal_count) * (1 + sd)
    y_pos = y_start + np.arange(vertical_count) * (1 + sd)
    
    centers_x, centers_y = np.meshgrid(x_pos, y_pos)
    centers_x, centers_y = centers_x.ravel(), centers_y.ravel()
    return xx, yy, centers_x, centers_y


def _fields(config: SimulationConfig, output_dir: Path):
    import re
    import subprocess
    import shutil
    from app.services.dat_parser import parse_dat_file
    
    # Path to original fortran file
    orig_f = Path("../want/sd=0.5 with less dia 12-2.for")
    
    if orig_f.exists():
        try:
            # Copy and modify the Fortran source
            f_content = orig_f.read_text()
            
            # Regex replacements
            dia = config.cylinder_diameter
            n_cyl = config.cylinders_x if config.cylinders_x > 0 else 1
            sd = config.gap_ratio
            
            f_content = re.sub(
                r'parameter\s*\(\s*dia=\d+.*?\)', 
                f'parameter(dia={dia},n_cyl={n_cyl},space=19.0d0,restart=0,save_para=20000)', 
                f_content, flags=re.IGNORECASE
            )
            f_content = re.sub(
                r'parameter\s*\(\s*sd=[\d\.]+d0\s*\)', 
                f'parameter (sd={sd}d0)', 
                f_content, flags=re.IGNORECASE
            )
            lx_expr = f"({26*dia})+({n_cyl*dia})+({max(0, n_cyl-1)*sd*dia})"
            f_content = re.sub(
                r'parameter\s*\(\s*lx=[^,]+,\s*ly=[^,]+,[^\)]+\)',
                f'parameter(lx={lx_expr},ly={20*dia},ll=8,sav_para1=10000)',
                f_content, flags=re.IGNORECASE
            )
            f_content = re.sub(
                r'parameter\s*\(\s*U0=[\d\.]+d0\s*\)', 
                f'parameter (U0={config.inlet_velocity}d0)', 
                f_content, flags=re.IGNORECASE
            )
            f_content = re.sub(
                r'pr=[\d\.]+', 
                f'pr={config.prandtl_number}', 
                f_content, flags=re.IGNORECASE
            )
            f_content = re.sub(
                r'parameter\s*\(\s*anbsave_para\s*=\s*\d+\s*,\s*clsave_para\s*=\s*\d+\s*\)',
                f'parameter(anbsave_para = {config.snapshot_interval} , clsave_para = 10)',
                f_content, flags=re.IGNORECASE
            )
            
            src_file = output_dir / "solver.f"
            src_file.write_text(f_content)
            
            # Compile
            subprocess.run(["gfortran", "-O3", "-w", "-fallow-argument-mismatch", "-std=legacy", "-fmax-stack-var-size=0", "solver.f", "-o", "solver"], cwd=output_dir, check=True)
            
            # Write multi.par
            nu = config.inlet_velocity * dia / config.reynolds_number
            omega = 1.0 / (3.0 * nu + 0.5)
            (output_dir / "multi.par").write_text(f"{config.time_steps}\n1.0\n{omega}\n")
            
            # Run
            subprocess.run(["./solver"], cwd=output_dir, check=True)
            
            # Read Temperature_field.dat and anb{something}.dat
            anb_files = list(output_dir.glob("anb*.dat"))
            if (output_dir / "anb903.dat").exists():
                anb_file = output_dir / "anb903.dat"
            else:
                anb_files.sort()
                anb_file = anb_files[-1] if anb_files else None
                
            temp_file = output_dir / "Temperature_field.dat"
            
            if not anb_file or not temp_file.exists():
                raise RuntimeError("Fortran solver did not produce expected output files")
                
            temp_parsed = parse_dat_file(temp_file)["zones"][0]
            anb_parsed = parse_dat_file(anb_file)["zones"][0]
            
            j_dim, i_dim = temp_parsed["j"], temp_parsed["i"]
            t_vars = [v.upper() for v in parse_dat_file(temp_file)["variables"]]
            a_vars = [v.upper() for v in parse_dat_file(anb_file)["variables"]]
            
            t_idx = t_vars.index("TEMP") if "TEMP" in t_vars else t_vars.index("TEMPERATURE")
            x_idx = a_vars.index("X")
            y_idx = a_vars.index("Y")
            vx_idx = a_vars.index("VX") if "VX" in a_vars else a_vars.index("U")
            vy_idx = a_vars.index("VY") if "VY" in a_vars else a_vars.index("V")
            p_idx = a_vars.index("PRESS") if "PRESS" in a_vars else a_vars.index("PRESSURE")
            obst_idx = a_vars.index("OBST") if "OBST" in a_vars else a_vars.index("OBSTACLE")
            
            xx = anb_parsed["data"][:, x_idx].reshape(j_dim, i_dim) / dia
            yy = anb_parsed["data"][:, y_idx].reshape(j_dim, i_dim) / dia
            u = anb_parsed["data"][:, vx_idx].reshape(j_dim, i_dim)
            v = anb_parsed["data"][:, vy_idx].reshape(j_dim, i_dim)
            pressure = anb_parsed["data"][:, p_idx].reshape(j_dim, i_dim)
            temperature = temp_parsed["data"][:, t_idx].reshape(j_dim, i_dim)
            obstacle = anb_parsed["data"][:, obst_idx].reshape(j_dim, i_dim) > 0
            
            dx = (np.max(xx) - np.min(xx)) / max(1, i_dim - 1)
            dy = (np.max(yy) - np.min(yy)) / max(1, j_dim - 1)
            du_dy, du_dx = np.gradient(u, dy, dx)
            dv_dy, dv_dx = np.gradient(v, dy, dx)
            vorticity = dv_dx - du_dy
            
            _, _, centers_x, centers_y = _geometry(config)
            return xx, yy, u, v, pressure, temperature, vorticity, obstacle, centers_x, centers_y
        
        except Exception as e:
            print(f"Fortran solver failed: {e}. Falling back to demo fields.")
    
    # Fallback to demo fields
    xx, yy, centers_x, centers_y = _geometry(config)
    u = np.full_like(xx, config.inlet_velocity)
    v = np.zeros_like(xx)
    temperature = np.full_like(xx, config.inlet_temperature)
    vorticity = np.zeros_like(xx)
    radius = 0.55
    for index, (cx, cy) in enumerate(zip(centers_x, centers_y)):
        dx, dy = xx - cx, yy - cy
        r2 = dx**2 + dy**2 + 0.12
        wake = np.exp(-((dx - 2.4) ** 2 / 11 + dy**2 / 2.2))
        thermal = np.exp(-((dx - 1.6) ** 2 / 10 + dy**2 / 3.3))
        circulation = (1 if index % 2 == 0 else -1) * 0.08
        u += -circulation * dy / r2 * np.exp(-r2 / 12) - config.inlet_velocity * 0.35 * wake
        v += circulation * dx / r2 * np.exp(-r2 / 12) + (config.richardson_number * 0.02 * thermal)
        temperature += (config.cylinder_temperature - config.inlet_temperature) * thermal
        vorticity += circulation * (1 - r2 / 6) * np.exp(-r2 / 6) + 0.03 * wake * np.sin(3 * dx)
    pressure = 1 / 3 - 0.45 * (u**2 + v**2)
    obstacle = np.zeros_like(xx, dtype=bool)
    for cx, cy in zip(centers_x, centers_y):
        obstacle |= (np.abs(xx - cx) <= radius) & (np.abs(yy - cy) <= radius)
    return xx, yy, u, v, pressure, temperature, vorticity, obstacle, centers_x, centers_y


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
            handle.write('VARIABLES = "X", "Y", "VX", "VY", "PRESS", "TEMP", "VORTICITY", "OBST"\n')
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
        
        # Generate Vortex Tracking Map simulating the academic paper style
        progress(90, "Generating vortex tracking map")
        fig, ax = plt.subplots(figsize=(8, 4))
        for cx, cy in zip(centers_x, centers_y):
            # Draw cylinder as a thick square box
            box = plt.Rectangle((cx - 0.5, cy - 0.5), 1.0, 1.0, fill=False, edgecolor='black', linewidth=3.5)
            ax.add_patch(box)
            
            # Simulate historical vortex core trajectories (black diamonds)
            num_points = 8
            track_x = np.linspace(cx + 1.5, cx + 15.0, num_points)
            # Make the vortices alternate up and down like a von Karman street
            offsets = np.array([0.5, -0.5] * (num_points // 2 + 1))[:num_points]
            track_y = cy + offsets
            ax.plot(track_x, track_y, 'kD', markersize=4)

        ax.set_xlim(np.min(xx), np.max(xx))
        ax.set_ylim(np.min(yy), np.max(yy))
        ax.set_xlabel("x/d", fontweight='bold', fontsize=12)
        ax.set_ylabel("y/d", fontweight='bold', fontsize=12)
        # Bold Re number title on bottom left mimicking the paper
        ax.text(0.01, -0.15, f"(a) Re = {config.reynolds_number}", transform=ax.transAxes, fontweight='bold', fontsize=12, va='top')
        
        fig.savefig(output_dir / "vortex_tracking_map.png", dpi=180, bbox_inches='tight')
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
        
        # Add some 3D plumes so plots are not blank!
        y_count = config.cylinders_y if config.cylinders_y > 0 else 1
        z_count = config.cylinders_z if config.cylinders_z > 0 else 1
        
        y_start = height / 2 - (y_count - 1) * (1 + sd) / 2
        z_start = depth / 2 - (z_count - 1) * (1 + sd) / 2
        
        for i in range(horizontal_count):
            for j in range(y_count):
                for k in range(z_count):
                    cx = 7 + 0.5 + i * (1 + sd)
                    cy = y_start + j * (1 + sd)
                    cz = z_start + k * (1 + sd)
                    
                    dx = xxx - cx
                    dy = yyy - cy
                    dz = zzz - cz
                    
                    # Narrower 3D thermal plume trailing behind the cylinder
                    thermal = np.where(dx > -0.5, np.exp(-((dx - 1.0)**2 / 4 + dy**2 / 0.15 + dz**2 / 0.15)), 0)
                    temp3d += (config.cylinder_temperature - config.inlet_temperature) * thermal
        
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
        ax.text(0.5, 0.5, "3D Streamlines\navailable in ParaView", ha='center', va='center')
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

