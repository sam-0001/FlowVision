import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

def parse_dat_file(filepath: Path):
    variables = []
    zones = []
    current_zone = None

    with open(filepath, "r") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("VARIABLES"):
            vars_str = line.split("=", 1)[1]
            variables = [v.strip().strip('"').strip("'") for v in vars_str.split(",")]
        elif line.upper().startswith("ZONE"):
            if current_zone is not None:
                zones.append(current_zone)
            
            i_match = re.search(r"I\s*=\s*(\d+)", line, re.IGNORECASE)
            j_match = re.search(r"J\s*=\s*(\d+)", line, re.IGNORECASE)
            t_match = re.search(r"T\s*=\s*\"([^\"]+)\"", line, re.IGNORECASE)
            time_val = t_match.group(1) if t_match else f"Zone {len(zones) + 1}"
            
            current_zone = {
                "i": int(i_match.group(1)) if i_match else None,
                "j": int(j_match.group(1)) if j_match else None,
                "time": time_val,
                "data": []
            }
        else:
            if current_zone is not None:
                try:
                    row = [float(val) for val in line.split()]
                    if len(row) > 0:
                        current_zone["data"].append(row)
                except ValueError:
                    pass

    if current_zone is not None:
        zones.append(current_zone)

    if not variables:
        raise ValueError("No VARIABLES line found in .dat file")
    
    parsed_zones = []
    expected_length = len(variables)
    
    for z_idx, z in enumerate(zones):
        if z["i"] is None or z["j"] is None:
            print(f"Warning: Zone {z_idx} missing I or J dimensions")
            continue
            
        clean_data = [row for row in z["data"] if len(row) == expected_length]
        if not clean_data:
            print(f"Warning: Zone {z_idx} has no valid data")
            continue
            
        data_arr = np.array(clean_data)
        if len(data_arr) != z["i"] * z["j"]:
            print(f"Warning: Zone {z_idx} expected {z['i'] * z['j']} points, got {len(data_arr)}")
            
        parsed_zones.append({
            "i": z["i"],
            "j": z["j"],
            "time": z["time"],
            "data": data_arr
        })

    if not parsed_zones:
        raise ValueError("No valid zones found in file")
        
    return {
        "variables": variables,
        "zones": parsed_zones
    }

def generate_preview(parsed_data: dict, output_path: Path):
    variables = [v.upper() for v in parsed_data["variables"]]
    
    # Just preview the first zone
    zone = parsed_data["zones"][0]
    i_dim = zone["i"]
    j_dim = zone["j"]
    data = zone["data"]

    # We need to reshape the data. F=POINT implies outer loop is J, inner loop is I
    # Some files might have different ordering, but typically it's (J, I)
    
    # Find spatial coordinates
    try:
        x_idx = variables.index("X")
        y_idx = variables.index("Y")
        # Ensure correct shape based on number of points available
        actual_points = len(data)
        if actual_points == i_dim * j_dim:
            xx = data[:, x_idx].reshape(j_dim, i_dim)
            yy = data[:, y_idx].reshape(j_dim, i_dim)
        else:
            # Fallback if points don't match exact dimensions (e.g., malformed lines)
            raise ValueError(f"Cannot reshape: got {actual_points} points, expected {i_dim * j_dim}")
    except ValueError:
        raise ValueError("X or Y coordinates not found in variables")

    # Find a field to plot (TEMP, then VX/VY, then PRESS, etc.)
    plot_var_idx = None
    plot_var_name = ""
    for target in ["TEMP", "TEMPERATURE", "VX", "VY", "U", "V", "PRESS", "PRESSURE"]:
        if target in variables:
            plot_var_idx = variables.index(target)
            plot_var_name = target
            break

    if plot_var_idx is None:
        # Just pick the first non-X/Y variable
        for idx, var in enumerate(variables):
            if var not in ["X", "Y", "OBST", "OBSTACLE"]:
                plot_var_idx = idx
                plot_var_name = var
                break

    if plot_var_idx is None:
        raise ValueError("No suitable field found to plot")

    field = data[:, plot_var_idx].reshape(j_dim, i_dim)

    # Plot
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    image = ax.contourf(xx, yy, field, levels=30, cmap="viridis")
    
    # Overlay obstacles if present
    obst_idx = None
    for target in ["OBST", "OBSTACLE"]:
        if target in variables:
            obst_idx = variables.index(target)
            break
            
    if obst_idx is not None:
        obst = data[:, obst_idx].reshape(j_dim, i_dim)
        # Assuming obst > 0 means obstacle
        ax.contourf(xx, yy, obst, levels=[0.5, 1.5], colors=['black'], alpha=0.5)

    ax.set_aspect("equal")
    ax.set_title(f"Preview: {plot_var_name} ({zone['time']})")
    fig.colorbar(image, ax=ax)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return plot_var_name
