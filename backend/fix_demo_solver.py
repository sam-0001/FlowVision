import re

with open('app/services/demo_solver.py', 'r') as f:
    code = f.read()

# I will replace the entire _fields function with a try-except
new_fields = """
def _fields(config: SimulationConfig, output_dir: Path):
    import re
    import subprocess
    import shutil
    from app.services.dat_parser import parse_dat_file
    
    # Path to original fortran file
    orig_f = Path("../want/sd=0.5 with less dia 12-2.for")
    fortran_success = False
    
    if orig_f.exists():
        try:
            # Copy and modify the Fortran source
            f_content = orig_f.read_text()
            dia = config.cylinder_diameter
            n_cyl = config.cylinders_x if config.cylinders_x > 0 else 1
            sd = config.gap_ratio
            
            f_content = re.sub(r'parameter\s*\(\s*dia=\d+.*?\)', f'parameter(dia={dia},n_cyl={n_cyl},space=19.0d0,restart=0,save_para=20000)', f_content, flags=re.IGNORECASE)
            f_content = re.sub(r'parameter\s*\(\s*sd=[\d\.]+d0\s*\)', f'parameter (sd={sd}d0)', f_content, flags=re.IGNORECASE)
            lx_expr = f"({26*dia})+({n_cyl*dia})+({max(0, n_cyl-1)*sd*dia})"
            f_content = re.sub(r'parameter\s*\(\s*lx=[^,]+,\s*ly=[^,]+,[^\)]+\)', f'parameter(lx={lx_expr},ly={20*dia},ll=8,sav_para1=10000)', f_content, flags=re.IGNORECASE)
            f_content = re.sub(r'parameter\s*\(\s*U0=[\d\.]+d0\s*\)', f'parameter (U0={config.inlet_velocity}d0)', f_content, flags=re.IGNORECASE)
            f_content = re.sub(r'pr=[\d\.]+', f'pr={config.prandtl_number}', f_content, flags=re.IGNORECASE)
            f_content = re.sub(r'parameter\s*\(\s*anbsave_para\s*=\s*\d+\s*,\s*clsave_para\s*=\s*\d+\s*\)', f'parameter(anbsave_para = {config.snapshot_interval} , clsave_para = 10)', f_content, flags=re.IGNORECASE)
            
            src_file = output_dir / "solver.f"
            src_file.write_text(f_content)
            
            subprocess.run(["gfortran", "-O3", "-w", "-fallow-argument-mismatch", "-std=legacy", "-fmax-stack-var-size=0", "solver.f", "-o", "solver"], cwd=output_dir, check=True)
            
            nu = config.inlet_velocity * dia / config.reynolds_number
            omega = 1.0 / (3.0 * nu + 0.5)
            (output_dir / "multi.par").write_text(f"{config.time_steps}\\n1.0\\n{omega}\\n")
            
            subprocess.run(["./solver"], cwd=output_dir, check=True)
            
            anb_files = list(output_dir.glob("anb*.dat"))
            if (output_dir / "anb903.dat").exists():
                anb_file = output_dir / "anb903.dat"
            else:
                anb_files.sort()
                anb_file = anb_files[-1] if anb_files else None
            temp_file = output_dir / "Temperature_field.dat"
            
            if anb_file and temp_file.exists():
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
            print(f"Fortran solver failed: {e}. Falling back to demo synthetic fields.")

    # Fallback synthetic logic
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
        v += circulation * dx / r2 * np.exp(-r2 / 12)
        temperature += (config.cylinder_temperature - config.inlet_temperature) * thermal
        vorticity += circulation * (1 - r2 / 6) * np.exp(-r2 / 6) + 0.03 * wake * np.sin(3 * dx)
    pressure = 1 / 3 - 0.45 * (u**2 + v**2)
    obstacle = np.zeros_like(xx, dtype=bool)
    for cx, cy in zip(centers_x, centers_y):
        obstacle |= (np.abs(xx - cx) <= radius) & (np.abs(yy - cy) <= radius)
    return xx, yy, u, v, pressure, temperature, vorticity, obstacle, centers_x, centers_y
"""

code = re.sub(r'def _fields\(config: SimulationConfig, output_dir: Path\):.*?return xx, yy, u, v, pressure, temperature, vorticity, obstacle, centers_x, centers_y', new_fields, code, flags=re.DOTALL)

with open('app/services/demo_solver.py', 'w') as f:
    f.write(code)
