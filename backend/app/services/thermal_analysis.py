import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from app.services.dat_parser import parse_dat_file

def analyze_thermal_blobs(temp_id: str, threshold_ratio: float = 0.1):
    temp_dir = Path(f"runs/temp_{temp_id}")
    dat_files = list(temp_dir.glob("*.dat"))
    if not dat_files:
        raise FileNotFoundError("No .dat file found in temp directory")
        
    dat_file = dat_files[0]
    parsed = parse_dat_file(dat_file)
    variables = [v.upper() for v in parsed["variables"]]
    
    # Check if TEMP or TEMPERATURE exists
    temp_idx = None
    for target in ["TEMP", "TEMPERATURE"]:
        if target in variables:
            temp_idx = variables.index(target)
            break
            
    if temp_idx is None:
        raise ValueError("Temperature variable not found in data")

    x_idx = variables.index("X")
    y_idx = variables.index("Y")

    results = []
    
    for zone_idx, zone in enumerate(parsed["zones"]):
        data = zone["data"]
        i_dim = zone["i"]
        j_dim = zone["j"]
        
        x = data[:, x_idx]
        y = data[:, y_idx]
        t = data[:, temp_idx]
        
        # Calculate ambient/reference temperature
        t_ref = np.min(t)
        t_excess = t - t_ref
        
        max_excess = np.max(t_excess)
        threshold = threshold_ratio * max_excess
        
        blob_mask = t_excess > threshold
        blob_points = np.sum(blob_mask)
        
        if blob_points > 0:
            # Assuming uniform grid for area calculation
            # Calculate dx, dy approximately
            dx = (np.max(x) - np.min(x)) / max(1, i_dim - 1)
            dy = (np.max(y) - np.min(y)) / max(1, j_dim - 1)
            cell_area = dx * dy
            blob_area = blob_points * cell_area
            
            integrated_excess = np.sum(t_excess[blob_mask]) * cell_area
            
            # Weighted centroid
            cx = np.sum(x[blob_mask] * t_excess[blob_mask]) / np.sum(t_excess[blob_mask])
            cy = np.sum(y[blob_mask] * t_excess[blob_mask]) / np.sum(t_excess[blob_mask])
        else:
            blob_area = 0.0
            integrated_excess = 0.0
            cx, cy = 0.0, 0.0
            
        results.append({
            "zone_idx": zone_idx,
            "time": zone["time"],
            "t_ref": t_ref,
            "max_excess": max_excess,
            "blob_area": blob_area,
            "integrated_excess": integrated_excess,
            "cx": cx,
            "cy": cy
        })

    # Export to CSV
    csv_path = temp_dir / "thermal_analysis.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
        
    # Plot strength-vs-time
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    times = [r["zone_idx"] for r in results] # Fallback to index if time is string
    try:
        # Try to parse time as float if possible
        times = [float(r["time"].replace("Zone", "").strip()) for r in results]
    except ValueError:
        pass
        
    strengths = [r["integrated_excess"] for r in results]
    ax.plot(times, strengths, marker="o", color="#fb923c", label="Integrated Temp Excess")
    ax.set_xlabel("Time Step / Zone")
    ax.set_ylabel("Thermal Strength")
    ax.set_title("Thermal Blob Strength over Time")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.savefig(temp_dir / "thermal_strength.png", dpi=150)
    plt.close(fig)

    # Plot centroid overlay on last zone
    last_zone = parsed["zones"][-1]
    data = last_zone["data"]
    i_dim = last_zone["i"]
    j_dim = last_zone["j"]
    xx = data[:, x_idx].reshape(j_dim, i_dim)
    yy = data[:, y_idx].reshape(j_dim, i_dim)
    field = data[:, temp_idx].reshape(j_dim, i_dim)
    
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    image = ax.contourf(xx, yy, field, levels=30, cmap="inferno")
    
    last_res = results[-1]
    if last_res["blob_area"] > 0:
        ax.plot(last_res["cx"], last_res["cy"], 'wx', markersize=12, markeredgewidth=2, label="Blob Centroid")
        ax.legend()
        
    ax.set_aspect("equal")
    ax.set_title(f"Thermal Blob Tracking (Zone: {last_zone['time']})")
    fig.colorbar(image, ax=ax)
    fig.savefig(temp_dir / "thermal_centroid.png", dpi=150)
    plt.close(fig)

    return {
        "csv_url": f"/api/analysis/{temp_id}/thermal_analysis.csv",
        "strength_plot": f"/api/analysis/{temp_id}/thermal_strength.png",
        "centroid_plot": f"/api/analysis/{temp_id}/thermal_centroid.png",
        "summary": results[-1]
    }
