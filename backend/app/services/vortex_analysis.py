import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.ndimage import maximum_filter, minimum_filter
from app.services.dat_parser import parse_dat_file

def analyze_vortices(temp_id: str):
    temp_dir = Path(f"runs/temp_{temp_id}")
    dat_files = list(temp_dir.glob("*.dat"))
    if not dat_files:
        raise FileNotFoundError("No .dat file found in temp directory")
        
    dat_file = dat_files[0]
    parsed = parse_dat_file(dat_file)
    variables = [v.upper() for v in parsed["variables"]]
    
    # Check if VX and VY exist
    try:
        vx_idx = variables.index("VX") if "VX" in variables else variables.index("U")
        vy_idx = variables.index("VY") if "VY" in variables else variables.index("V")
    except ValueError:
        raise ValueError("Velocity variables (VX/VY or U/V) not found in data")

    x_idx = variables.index("X")
    y_idx = variables.index("Y")

    results = []
    trajectories = [] # list of lists for plotting
    
    for zone_idx, zone in enumerate(parsed["zones"]):
        data = zone["data"]
        i_dim = zone["i"]
        j_dim = zone["j"]
        
        x = data[:, x_idx].reshape(j_dim, i_dim)
        y = data[:, y_idx].reshape(j_dim, i_dim)
        u = data[:, vx_idx].reshape(j_dim, i_dim)
        v = data[:, vy_idx].reshape(j_dim, i_dim)
        
        dx = (np.max(x) - np.min(x)) / max(1, i_dim - 1)
        dy = (np.max(y) - np.min(y)) / max(1, j_dim - 1)
        
        du_dy, du_dx = np.gradient(u, dy, dx)
        dv_dy, dv_dx = np.gradient(v, dy, dx)
        
        vorticity = dv_dx - du_dy
        # 2D Q-criterion
        q_crit = du_dx * dv_dy - du_dy * dv_dx
        
        q_threshold = 0.01 * np.max(q_crit) if np.max(q_crit) > 0 else 0
        
        # Find local maxima (CCW) and minima (CW) of vorticity
        local_max = (maximum_filter(vorticity, size=5) == vorticity) & (vorticity > 0) & (q_crit > q_threshold)
        local_min = (minimum_filter(vorticity, size=5) == vorticity) & (vorticity < 0) & (q_crit > q_threshold)
        
        # Get coordinates and strength
        ccw_y, ccw_x = np.where(local_max)
        cw_y, cw_x = np.where(local_min)
        
        # Track up to 3 strongest of each to avoid clutter
        ccw_vorts = []
        for yi, xi in zip(ccw_y, ccw_x):
            ccw_vorts.append((x[yi, xi], y[yi, xi], vorticity[yi, xi]))
        ccw_vorts = sorted(ccw_vorts, key=lambda v: v[2], reverse=True)[:3]
            
        cw_vorts = []
        for yi, xi in zip(cw_y, cw_x):
            cw_vorts.append((x[yi, xi], y[yi, xi], vorticity[yi, xi]))
        cw_vorts = sorted(cw_vorts, key=lambda v: v[2])[:3]
        
        time_val = zone["time"]
        for vx, vy, vstrength in ccw_vorts:
            results.append({"zone_idx": zone_idx, "time": time_val, "type": "CCW", "x": vx, "y": vy, "strength": vstrength})
        for vx, vy, vstrength in cw_vorts:
            results.append({"zone_idx": zone_idx, "time": time_val, "type": "CW", "x": vx, "y": vy, "strength": vstrength})
            
        trajectories.append({
            "ccw": ccw_vorts,
            "cw": cw_vorts,
            "vorticity": vorticity,
            "x": x,
            "y": y
        })

    # Export CSV
    csv_path = temp_dir / "vortex_analysis.csv"
    with open(csv_path, "w", newline="") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            
    # Plot Strength vs Time
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    times = sorted(list(set(r["zone_idx"] for r in results)))
    
    # A bit naive: just plot max and min strength per time step
    max_strengths = []
    min_strengths = []
    for t_idx in times:
        t_res = [r for r in results if r["zone_idx"] == t_idx]
        ccws = [r["strength"] for r in t_res if r["type"] == "CCW"]
        cws = [r["strength"] for r in t_res if r["type"] == "CW"]
        max_strengths.append(max(ccws) if ccws else 0)
        min_strengths.append(min(cws) if cws else 0)
        
    ax.plot(times, max_strengths, color="#ef4444", marker="o", label="Max CCW Strength")
    ax.plot(times, min_strengths, color="#3b82f6", marker="o", label="Max CW Strength")
    ax.set_xlabel("Time Step / Zone")
    ax.set_ylabel("Peak Vorticity")
    ax.set_title("Vortex Strength vs Time")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.savefig(temp_dir / "vortex_strength.png", dpi=150)
    plt.close(fig)
    
    # Plot contour and overlaid centers on last zone
    last_traj = trajectories[-1]
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    vmax = np.max(np.abs(last_traj["vorticity"])) or 1.0
    image = ax.contourf(last_traj["x"], last_traj["y"], last_traj["vorticity"], levels=30, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    
    for vx, vy, _ in last_traj["ccw"]:
        ax.plot(vx, vy, 'rx', markersize=10, markeredgewidth=2)
    for vx, vy, _ in last_traj["cw"]:
        ax.plot(vx, vy, 'bx', markersize=10, markeredgewidth=2)
        
    ax.set_aspect("equal")
    ax.set_title("Vortex Centers (Q-criterion + Vorticity Extrema)")
    fig.colorbar(image, ax=ax)
    fig.savefig(temp_dir / "vortex_centers.png", dpi=150)
    plt.close(fig)

    return {
        "csv_url": f"/api/analysis/{temp_id}/vortex_analysis.csv",
        "strength_plot": f"/api/analysis/{temp_id}/vortex_strength.png",
        "centers_plot": f"/api/analysis/{temp_id}/vortex_centers.png"
    }
