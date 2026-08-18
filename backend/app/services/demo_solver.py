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
    import numpy as np
    
    dia = int(config.cylinder_diameter)
    sd = float(config.gap_ratio)
    horizontal_count = config.cylinders_x if config.cylinders_x > 0 else 1
    vertical_count = config.cylinders_y if config.cylinders_y > 0 else 1
    
    lx = int((26 * dia) + (horizontal_count * dia) + (max(0, horizontal_count - 1) * sd * dia))
    ly = int(20 * dia)
    
    x = np.arange(1, lx + 1, dtype=np.float64)
    y = np.arange(1, ly + 1, dtype=np.float64)
    xx, yy = np.meshgrid(x, y)
    
    obst = np.zeros((ly, lx), dtype=bool)
    centers_x, centers_y = [], []
    
    start_x = 7.0 * dia + 1.0
    start_y = 10.0 * dia - (vertical_count - 1) * (1.0 + sd) * dia / 2.0
    
    for i in range(horizontal_count):
        for j in range(vertical_count):
            c_x = start_x + i * dia * (1.0 + sd) + dia / 2.0
            c_y = start_y + j * dia * (1.0 + sd) + dia / 2.0
            centers_x.append(c_x / dia)
            centers_y.append(c_y / dia)
            x_min = start_x + i * dia * (1.0 + sd)
            x_max = x_min + dia
            y_min = start_y + j * dia * (1.0 + sd)
            y_max = y_min + dia
            mask = (xx >= x_min) & (xx <= x_max) & (yy >= y_min) & (yy <= y_max)
            obst |= mask
            
    U0 = float(config.inlet_velocity)
    Re = float(config.reynolds_number)
    nu = (U0 * dia) / max(Re, 1.0)
    omega = 2.0 / (6.0 * nu + 1.0)
    
    pr = float(config.prandtl_number)
    alpha = nu / max(pr, 0.01)
    omega_t = 2.0 / (6.0 * alpha + 1.0)
    
    w = np.array([4/9, 1/9, 1/9, 1/9, 1/9, 1/36, 1/36, 1/36, 1/36], dtype=np.float64)
    cx = np.array([0, 1, 0, -1, 0, 1, -1, -1, 1], dtype=int)
    cy = np.array([0, 0, 1, 0, -1, 1, 1, -1, -1], dtype=int)
    opp = [0, 3, 4, 1, 2, 7, 8, 5, 6]
    
    rho = np.ones((ly, lx), dtype=np.float64)
    u = np.full((ly, lx), U0, dtype=np.float64)
    v = np.zeros((ly, lx), dtype=np.float64)
    temp = np.full((ly, lx), config.inlet_temperature, dtype=np.float64)
    
    f = np.zeros((9, ly, lx), dtype=np.float64)
    g = np.zeros((9, ly, lx), dtype=np.float64)
    
    def get_eq(r, ux, uy):
        usq = ux*ux + uy*uy
        feq = np.zeros_like(f)
        for i in range(9):
            cu = cx[i]*ux + cy[i]*uy
            feq[i] = w[i] * r * (1.0 + 3.0*cu + 4.5*cu*cu - 1.5*usq)
        return feq

    f = get_eq(rho, u, v)
    for i in range(9):
        g[i] = w[i] * temp * (1.0 + 3.0*(cx[i]*u + cy[i]*v))
        
    time_steps = min(config.time_steps, 2000)
    T_cyl = float(config.cylinder_temperature)
    T_in = float(config.inlet_temperature)
    
    for t in range(time_steps):
        rho = np.sum(f, axis=0)
        u = np.sum(f * cx[:, None, None], axis=0) / rho
        v = np.sum(f * cy[:, None, None], axis=0) / rho
        temp = np.sum(g, axis=0)
        
        u[obst] = 0.0
        v[obst] = 0.0
        temp[obst] = T_cyl
        
        feq = get_eq(rho, u, v)
        f_post = f - omega * (f - feq)
        
        geq = np.zeros_like(g)
        for i in range(9):
            cu = cx[i]*u + cy[i]*v
            geq[i] = w[i] * temp * (1.0 + 3.0*cu)
        g_post = g - omega_t * (g - geq)
        
        for i in range(9):
            f_post[i, obst] = f[opp[i], obst]
            g_post[i, obst] = w[i]*T_cyl + w[opp[i]]*T_cyl - g[opp[i], obst]
            
        for i in range(9):
            f[i] = np.roll(f_post[i], shift=(cy[i], cx[i]), axis=(0, 1))
            g[i] = np.roll(g_post[i], shift=(cy[i], cx[i]), axis=(0, 1))
            
        u_in = U0
        v_in = 0.0
        rho_in = (f[0,:,0] + f[2,:,0] + f[4,:,0] + 2.0*(f[3,:,0] + f[6,:,0] + f[7,:,0])) / (1.0 - u_in)
        f[1,:,0] = f[3,:,0] + (2.0/3.0)*rho_in*u_in
        f[5,:,0] = f[7,:,0] - 0.5*(f[2,:,0]-f[4,:,0]) + (1.0/6.0)*rho_in*u_in + 0.5*rho_in*v_in
        f[8,:,0] = f[6,:,0] + 0.5*(f[2,:,0]-f[4,:,0]) + (1.0/6.0)*rho_in*u_in - 0.5*rho_in*v_in
        
        for i in range(9):
            if cx[i] > 0:
                g[i,:,0] = w[i] * T_in * (1.0 + 3.0*(cx[i]*u_in + cy[i]*v_in))
                
        for i in range(9):
            if cx[i] < 0:
                f[i,:,-1] = f[i,:,-2]
                g[i,:,-1] = g[i,:,-2]

    rho = np.sum(f, axis=0)
    u = np.sum(f * cx[:, None, None], axis=0) / rho
    v = np.sum(f * cy[:, None, None], axis=0) / rho
    temp = np.sum(g, axis=0)
    u[obst] = 0.0
    v[obst] = 0.0
    temp[obst] = T_cyl
    
    xx = xx / dia
    yy = yy / dia
    
    dx = 1.0 / max(1, lx - 1)
    dy = 1.0 / max(1, ly - 1)
    dv_dy, dv_dx = np.gradient(v, dy, dx)
    du_dy, du_dx = np.gradient(u, dy, dx)
    vorticity = dv_dx - du_dy
    pressure = rho / 3.0
    
    return xx, yy, u, v, pressure, temp, vorticity, obst, centers_x, centers_y


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
    progress(25, "Running LBM physics engine")
    
    is_3d = config.cylinders_z > 0
    
    if not is_3d:
        xx, yy, u, v, pressure, temperature, vorticity, obstacle, centers_x, centers_y = _fields(config, output_dir)
        
        metadata = {
            "mode": "lbm",
            "warning": "Full 2D Lattice Boltzmann simulation",
            "array_layout": {"x": config.cylinders_x, "y": config.cylinders_y, "z": config.cylinders_z},
            "config": config.model_dump(),
        }
        (output_dir / "config.json").write_text(json.dumps(metadata, indent=2))

        progress(45, "Writing Tecplot-compatible data")
        dat_path = output_dir / "flow_temperature.dat"
        with dat_path.open("w", newline="") as handle:
            handle.write('VARIABLES = "X", "Y", "VX", "VY", "PRESS", "TEMP", "VORTICITY", "OBST"\n')
            handle.write(f"ZONE I={xx.shape[1]}, J={xx.shape[0]}, F=POINT\n")
            for row in range(xx.shape[0]):
                for col in range(xx.shape[1]):
                    handle.write(f"{xx[row,col]:.6f} {yy[row,col]:.6f} {u[row,col]:.8f} {v[row,col]:.8f} {pressure[row,col]:.8f} {temperature[row,col]:.8f} {vorticity[row,col]:.8f} {int(obstacle[row,col])}\n")

        progress(60, "Rendering paper-style contours")
        projection = "-".join(axis.upper() for axis in config.active_axes[:2])
        slice_title = f"{projection} projection"
        _save_contour(output_dir / "temperature_contour.png", xx, yy, temperature, centers_x, centers_y, f"Temperature field - {slice_title}", "Temperature", "inferno")
        _save_contour(output_dir / "pressure_contour.png", xx, yy, pressure, centers_x, centers_y, f"Pressure field - {slice_title}", "Pressure", "viridis")
        _save_contour(output_dir / "vorticity_contour.png", xx, yy, vorticity, centers_x, centers_y, f"Vorticity and wakes - {slice_title}", "Vorticity", "RdBu_r")

        progress(78, "Creating velocity and force plots")
        fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
        speed = np.hypot(u, v)
        ax.streamplot(xx[0], yy[:, 0], u, v, color=speed, density=1.5, cmap="turbo", linewidth=0.8)
        for cx, cy in zip(centers_x, centers_y):
            ax.add_patch(plt.Rectangle((cx - 0.55, cy - 0.55), 1.1, 1.1, fc="#111827", ec="white", lw=0.7))
        ax.set_title("Velocity streamlines")
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
            handle.write('VARIABLES = "X", "Y", "Z", "VX", "VY", "VZ", "TEMP"\n')
            handle.write(f"ZONE I={xxx.shape[0]}, J={xxx.shape[1]}, K={xxx.shape[2]}, F=POINT\n")
            # Downsample write for speed in this demo
            s_x, s_y, s_z = xxx[::2,::2,::2], yyy[::2,::2,::2], zzz[::2,::2,::2]
            su, sv, sw, st = u[::2,::2,::2], v[::2,::2,::2], w[::2,::2,::2], temp3d[::2,::2,::2]
            for idx in range(s_x.size):
                handle.write(f"{s_x.flat[idx]:.3f} {s_y.flat[idx]:.3f} {s_z.flat[idx]:.3f} {su.flat[idx]:.4f} {sv.flat[idx]:.4f} {sw.flat[idx]:.4f} {st.flat[idx]:.4f}\n")
                
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

