import { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Config = {
  cylinders_x: number; cylinders_y: number; cylinders_z: number; total_cylinders?: number; cylinder_diameter: number; gap_ratio: number; reynolds_number: number;
  prandtl_number: number; richardson_number: number; inlet_temperature: number; cylinder_temperature: number; inlet_velocity: number;
  time_steps: number; snapshot_interval: number; include_temperature: boolean; include_pressure: boolean;
};
type Run = { id: string; status: "queued" | "running" | "completed" | "failed"; progress: number; config: Config; created_at: string; message?: string; artifact_names: string[] };

const initialConfig: Config = {
  cylinders_x: 3, cylinders_y: 4, cylinders_z: 0, cylinder_diameter: 12, gap_ratio: 0.5, reynolds_number: 100,
  prandtl_number: 0.71, richardson_number: 0.0, inlet_temperature: 0, cylinder_temperature: 1, inlet_velocity: 0.05,
  time_steps: 10000, snapshot_interval: 500, include_temperature: true, include_pressure: true,
};
const plotNames: Record<string, string> = {
  "temperature_contour.png": "Temperature field", "pressure_contour.png": "Pressure field",
  "vorticity_contour.png": "Vorticity and wake", "velocity_streamlines.png": "Velocity streamlines",
  "vortex_tracking_map.png": "Vortex Tracking Map", "force_history.png": "Lift and drag history",
};

function App() {
  const [config, setConfig] = useState<Config>(initialConfig);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [mode, setMode] = useState<"simulate" | "analyze">("simulate");
  const [analysisFile, setAnalysisFile] = useState<File | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [thermalResult, setThermalResult] = useState<any>(null);
  const [runningThermalAnalysis, setRunningThermalAnalysis] = useState(false);
  const [thermalError, setThermalError] = useState("");
  const [vortexResult, setVortexResult] = useState<any>(null);
  const [runningVortexAnalysis, setRunningVortexAnalysis] = useState(false);
  const [vortexError, setVortexError] = useState("");

  const derived = useMemo(() => ({
    viscosity: config.inlet_velocity * config.cylinder_diameter / config.reynolds_number,
    thermalDiffusivity: config.inlet_velocity * config.cylinder_diameter / config.reynolds_number / config.prandtl_number,
    totalCylinders: Math.max(config.cylinders_x, 1) * Math.max(config.cylinders_y, 1) * Math.max(config.cylinders_z, 1),
    latticeWidth: Math.round((10 + Math.max(config.cylinders_x, config.cylinders_y, config.cylinders_z, 1) * (1 + config.gap_ratio) + 10) * config.cylinder_diameter),
  }), [config]);

  useEffect(() => { void refreshRuns(); }, []);
  useEffect(() => {
    if (!activeRun || ["completed", "failed"].includes(activeRun.status)) return;
    const id = window.setInterval(async () => {
      const response = await fetch(`/api/runs/${activeRun.id}`);
      if (response.ok) setActiveRun(await response.json());
      void refreshRuns();
    }, 1100);
    return () => window.clearInterval(id);
  }, [activeRun?.id, activeRun?.status]);

  async function refreshRuns() {
    try { const response = await fetch("/api/runs"); if (response.ok) setRuns(await response.json()); } catch { /* API may be offline initially */ }
  }
  function setNumber(key: keyof Config, value: string) { setConfig(previous => ({ ...previous, [key]: Number(value) })); }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try {
      const response = await fetch("/api/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) });
      if (!response.ok) { const detail = await response.json(); throw new Error(detail.detail?.[0]?.msg || "Could not start the simulation"); }
      const created = await response.json();
      const detail = await fetch(`/api/runs/${created.id}`); const run = await detail.json();
      setActiveRun(run); void refreshRuns();
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Unable to contact backend"); }
    finally { setSubmitting(false); }
  }

  async function handleFileUpload(e: FormEvent) {
    e.preventDefault();
    if (!analysisFile) return;
    setAnalyzing(true); setAnalysisError(""); setAnalysisResult(null);
    try {
      const formData = new FormData();
      formData.append("file", analysisFile);
      const res = await fetch("/api/analysis/preview", { method: "POST", body: formData });
      if (!res.ok) {
        const detail = await res.json();
        throw new Error(detail.detail || "Could not analyze file");
      }
      setAnalysisResult(await res.json());
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "Error uploading file");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleThermalAnalysis() {
    if (!analysisResult?.id) return;
    setRunningThermalAnalysis(true); setThermalError(""); setThermalResult(null);
    try {
      const res = await fetch(`/api/analysis/${analysisResult.id}/thermal`, { method: "POST" });
      if (!res.ok) {
        const detail = await res.json();
        throw new Error(detail.detail || "Could not run thermal analysis");
      }
      setThermalResult(await res.json());
    } catch (err) {
      setThermalError(err instanceof Error ? err.message : "Error running analysis");
    } finally {
      setRunningThermalAnalysis(false);
    }
  }

  async function handleVortexAnalysis() {
    if (!analysisResult?.id) return;
    setRunningVortexAnalysis(true); setVortexError(""); setVortexResult(null);
    try {
      const res = await fetch(`/api/analysis/${analysisResult.id}/vortex`, { method: "POST" });
      if (!res.ok) {
        const detail = await res.json();
        throw new Error(detail.detail || "Could not run vortex analysis");
      }
      setVortexResult(await res.json());
    } catch (err) {
      setVortexError(err instanceof Error ? err.message : "Error running analysis");
    } finally {
      setRunningVortexAnalysis(false);
    }
  }

  return <main>
    <header className="topbar"><div className="brand"><span className="mark">◒</span><div><strong>FlowVision</strong><small>CFD experiment studio</small></div></div><div className="status"><span></span> API-connected workflow</div></header>
    <section className="hero"><div><p className="eyebrow">THERMAL FLOW • CYLINDER ARRAYS</p><h1>From parameters to<br/><em>publishable flow visuals.</em></h1><p className="intro">Configure the experiment, run the solver, and get organized field data plus paper-style temperature, pressure, vortex, and force figures.</p></div><aside><p>Current workflow</p><b>2D LBM + thermal transport</b><span>Validated solver connection is the next integration step.</span></aside></section>
    <div className="layout">
      <div>
        <div className="tabs">
          <button type="button" className={mode === "simulate" ? "active" : ""} onClick={() => setMode("simulate")}>Simulate</button>
          <button type="button" className={mode === "analyze" ? "active" : ""} onClick={() => setMode("analyze")}>Analyze Existing .dat</button>
        </div>
        {mode === "simulate" ? (
          <form className="panel config" onSubmit={submit}>
            <div className="panel-heading"><div><p className="eyebrow">01 / CONFIGURE</p><h2>Simulation inputs</h2></div><button type="button" className="link-button" onClick={() => setConfig(initialConfig)}>Reset defaults</button></div>
            <fieldset><legend>3D cylinder array</legend><p className="array-note">Use 0 to disable an axis. X = 3, Y = 0, Z = 0 creates a 1D row of 3; X = 3, Y = 4, Z = 0 creates a 2D 3×4 plane; X = 3, Y = 4, Z = 3 creates 36 cylinders.</p><div className="fields three"><NumberField label="X-axis cylinders" value={config.cylinders_x} min={0} max={20} onChange={v => setNumber("cylinders_x", v)} /><NumberField label="Y-axis cylinders" value={config.cylinders_y} min={0} max={20} onChange={v => setNumber("cylinders_y", v)} /><NumberField label="Z-axis cylinders" value={config.cylinders_z} min={0} max={20} onChange={v => setNumber("cylinders_z", v)} /><NumberField label="Diameter (nodes)" value={config.cylinder_diameter} min={8} onChange={v => setNumber("cylinder_diameter", v)} /><NumberField label="Gap ratio, s/d" value={config.gap_ratio} step={0.1} min={0.1} onChange={v => setNumber("gap_ratio", v)} /></div></fieldset>
            <fieldset><legend>Fluid and thermal state</legend><div className="fields three"><NumberField label="Reynolds number" value={config.reynolds_number} min={2} onChange={v => setNumber("reynolds_number", v)} /><NumberField label="Prandtl number" value={config.prandtl_number} step={0.01} min={0.01} onChange={v => setNumber("prandtl_number", v)} /><NumberField label="Richardson number" value={config.richardson_number} step={0.01} min={0} onChange={v => setNumber("richardson_number", v)} /><NumberField label="Inlet velocity" value={config.inlet_velocity} step={0.01} min={0.001} onChange={v => setNumber("inlet_velocity", v)} /><NumberField label="Inlet temperature" value={config.inlet_temperature} step={0.1} onChange={v => setNumber("inlet_temperature", v)} /><NumberField label="Cylinder temperature" value={config.cylinder_temperature} step={0.1} onChange={v => setNumber("cylinder_temperature", v)} /></div></fieldset>
            <fieldset><legend>Run and output</legend><div className="fields two"><NumberField label="Time steps" value={config.time_steps} min={100} step={100} onChange={v => setNumber("time_steps", v)} /><NumberField label="Snapshot every (steps)" value={config.snapshot_interval} min={10} step={10} onChange={v => setNumber("snapshot_interval", v)} /></div><div className="checks"><Check label="Temperature field" checked={config.include_temperature} onChange={v => setConfig(p => ({...p, include_temperature: v}))}/><Check label="Pressure field" checked={config.include_pressure} onChange={v => setConfig(p => ({...p, include_pressure: v}))}/></div></fieldset>
            <div className="derived"><div><span>Total cylinders</span><b>{derived.totalCylinders}</b></div><div><span>Derived viscosity</span><b>{derived.viscosity.toExponential(3)}</b></div><div><span>Thermal diffusivity</span><b>{derived.thermalDiffusivity.toExponential(3)}</b></div><div><span>Estimated X grid width</span><b>{derived.latticeWidth} nodes</b></div></div>
            {error && <p className="error">{error}</p>}<button className="run-button" disabled={submitting || activeRun?.status === "running"}>{submitting ? "Starting…" : "Generate simulation output"}<span>→</span></button>
          </form>
        ) : (
          <form className="panel config" onSubmit={handleFileUpload}>
            <div className="panel-heading"><div><p className="eyebrow">01 / UPLOAD</p><h2>Analyze Existing Data</h2></div></div>
            <fieldset><legend>Data source</legend>
              <input type="file" accept=".dat" onChange={e => setAnalysisFile(e.target.files?.[0] || null)} style={{width: "100%", padding: "10px", marginTop: "10px", fontFamily: "inherit"}}/>
            </fieldset>
            {analysisError && <p className="error">{analysisError}</p>}
            <button type="submit" className="run-button" style={{marginTop: "20px"}} disabled={analyzing || !analysisFile}>{analyzing ? "Analyzing…" : "Upload and Preview"}<span>→</span></button>
            {analysisResult && (
              <>
                <div className="derived" style={{ marginTop: 20 }}>
                  <div><span>Grid (I × J)</span><b>{analysisResult.i} × {analysisResult.j}</b></div>
                  <div><span>Variables</span><b>{analysisResult.variables.length}</b></div>
                  <div style={{gridColumn: "1 / -1", background: "transparent", padding: 0}}>
                    <p style={{fontSize: 10, color: "var(--muted)", margin: "0 0 5px"}}>Variables: {analysisResult.variables.join(", ")}</p>
                  </div>
                </div>
                {(analysisResult.variables.includes("TEMP") || analysisResult.variables.includes("TEMPERATURE") || analysisResult.variables.includes("temp") || analysisResult.variables.includes("temperature")) ? (
                  <div style={{marginTop: "20px"}}>
                    <div className="panel-heading" style={{marginBottom: "10px"}}><div><p className="eyebrow">02 / ANALYSIS</p><h2>Thermal Blobs</h2></div></div>
                    {thermalError && <p className="error">{thermalError}</p>}
                    <button type="button" className="run-button" style={{background: "var(--accent)"}} disabled={runningThermalAnalysis} onClick={handleThermalAnalysis}>{runningThermalAnalysis ? "Running..." : "Analyze Thermal Blobs"}<span>→</span></button>
                  </div>
                ) : null}
                {(analysisResult.variables.includes("VX") || analysisResult.variables.includes("U")) && (analysisResult.variables.includes("VY") || analysisResult.variables.includes("V")) ? (
                  <div style={{marginTop: "10px"}}>
                    <div className="panel-heading" style={{marginBottom: "10px"}}><div><p className="eyebrow">03 / ANALYSIS</p><h2>Vortex Tracking</h2></div></div>
                    {vortexError && <p className="error">{vortexError}</p>}
                    <button type="button" className="run-button" style={{background: "#3b82f6"}} disabled={runningVortexAnalysis} onClick={handleVortexAnalysis}>{runningVortexAnalysis ? "Running..." : "Analyze Vortices"}<span>→</span></button>
                  </div>
                ) : null}
              </>
            )}
          </form>
        )}
      </div>
      <section className="right-column">
        {mode === "simulate" ? (
          <>
            <article className="panel run-panel"><div className="panel-heading"><div><p className="eyebrow">02 / RUN STATUS</p><h2>{activeRun ? `Run ${activeRun.id}` : "Ready to run"}</h2></div><span className={`badge ${activeRun?.status || "idle"}`}>{activeRun?.status || "idle"}</span></div>{activeRun ? <><div className="progress"><i style={{width: `${activeRun.progress}%`}}/></div><div className="progress-copy"><span>{activeRun.message}</span><b>{activeRun.progress}%</b></div><p className="fine-print">Demo mode renders an X-Y slice of the requested X × Y × Z array. Connect the optimized 3D solver before using results for publication.</p></> : <p className="empty">Choose inputs and create a run. Each simulation has its own folder, data exports, and generated figures.</p>}</article>
            <article className="panel results"><div className="panel-heading"><div><p className="eyebrow">03 / RESULTS</p><h2>Visual output</h2></div>{activeRun?.status === "completed" && <><button type="button" className="link-button" onClick={() => {
              const filename = activeRun.config.cylinders_z > 0 ? "flow_temperature_3d.dat" : "flow_temperature.dat";
              fetch(`/api/runs/${activeRun.id}/analyze`, { method: "POST" })
                .then(r => r.json())
                .then(data => { setAnalysisResult(data); setMode("analyze"); })
                .catch(e => alert("Analysis error: " + e));
            }} style={{marginRight: "15px"}}>Analyze Run</button><a className="download" href={`/api/runs/${activeRun.id}/artifacts/${activeRun.config.cylinders_z > 0 ? "flow_temperature_3d.dat" : "flow_temperature.dat"}`}>Download .dat</a></>}</div>{activeRun?.status === "completed" ? <div className="gallery">{activeRun.artifact_names.filter(name => name.endsWith(".png")).map(name => <figure key={name}><img src={`/api/runs/${activeRun.id}/artifacts/${name}`} alt={plotNames[name] || name}/><figcaption>{plotNames[name] || name}<a href={`/api/runs/${activeRun.id}/artifacts/${name}`} target="_blank">Open</a></figcaption></figure>)}</div> : <div className="visual-placeholder"><div className="contour"></div><p>Temperature, pressure, vorticity, streamlines, and force figures will appear here.</p></div>}</article>
            {runs.length > 0 && <article className="recent"><p className="eyebrow">RECENT RUNS</p>{runs.slice(0, 3).map(run => <button type="button" key={run.id} onClick={() => setActiveRun(run)}><span className={`dot ${run.status}`}/><b>{run.id}</b><span>{run.config.cylinders_x}×{run.config.cylinders_y}×{run.config.cylinders_z} · Re {run.config.reynolds_number}</span><em>{run.status}</em></button>)}</article>}
          </>
        ) : (
          analysisResult ? (
            <div style={{display: "grid", gap: "22px"}}>
              <article className="panel results">
                <div className="panel-heading">
                  <div><p className="eyebrow">PREVIEW</p><h2>{analysisResult.plotted_variable} field</h2></div>
                </div>
                <div className="gallery" style={{ gridTemplateColumns: "1fr" }}>
                  <figure style={{aspectRatio: "auto"}}>
                    <img src={analysisResult.preview_url} alt="Preview" style={{aspectRatio: "auto", height: "auto"}} />
                    <figcaption>Extracted variable field contour <a href={analysisResult.preview_url} target="_blank">Open Full</a></figcaption>
                  </figure>
                </div>
              </article>
              {thermalResult && (
                <article className="panel results">
                  <div className="panel-heading">
                    <div><p className="eyebrow">THERMAL ANALYSIS</p><h2>Blob tracking results</h2></div>
                    <a className="download" href={thermalResult.csv_url}>Download CSV</a>
                  </div>
                  <div className="gallery">
                    <figure style={{aspectRatio: "auto"}}>
                      <img src={thermalResult.centroid_plot} alt="Centroid tracking" style={{aspectRatio: "auto", height: "auto"}} />
                      <figcaption>Thermal blob centroid tracking <a href={thermalResult.centroid_plot} target="_blank">Open</a></figcaption>
                    </figure>
                    <figure style={{aspectRatio: "auto"}}>
                      <img src={thermalResult.strength_plot} alt="Blob strength vs time" style={{aspectRatio: "auto", height: "auto"}} />
                      <figcaption>Integrated strength over time <a href={thermalResult.strength_plot} target="_blank">Open</a></figcaption>
                    </figure>
                  </div>
                </article>
              )}
              {vortexResult && (
                <article className="panel results">
                  <div className="panel-heading">
                    <div><p className="eyebrow">VORTEX ANALYSIS</p><h2>Vortex tracking results</h2></div>
                    <a className="download" href={vortexResult.csv_url}>Download CSV</a>
                  </div>
                  <div className="gallery">
                    <figure style={{aspectRatio: "auto"}}>
                      <img src={vortexResult.centers_plot} alt="Vortex centers" style={{aspectRatio: "auto", height: "auto"}} />
                      <figcaption>Vortex centers overlay <a href={vortexResult.centers_plot} target="_blank">Open</a></figcaption>
                    </figure>
                    <figure style={{aspectRatio: "auto"}}>
                      <img src={vortexResult.strength_plot} alt="Vortex strength vs time" style={{aspectRatio: "auto", height: "auto"}} />
                      <figcaption>Peak vorticity vs time <a href={vortexResult.strength_plot} target="_blank">Open</a></figcaption>
                    </figure>
                  </div>
                </article>
              )}
            </div>
          ) : (
            <article className="panel results">
              <div className="panel-heading">
                <div><p className="eyebrow">02 / PREVIEW</p><h2>Awaiting data</h2></div>
              </div>
              <div className="visual-placeholder"><p>Upload a .dat file to see a preview of the grid and fields.</p></div>
            </article>
          )
        )}
      </section>
    </div>
  </main>;
}
function NumberField({ label, value, onChange, ...props }: { label: string; value: number; onChange: (value: string) => void; min?: number; max?: number; step?: number }) { return <label className="field"><span>{label}</span><input type="number" value={value} onChange={e => onChange(e.target.value)} {...props}/></label>; }
function Check({ label, checked, onChange }: {label: string; checked: boolean; onChange: (value: boolean) => void}) { return <label className="check"><input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)}/><span>{label}</span></label>; }
createRoot(document.getElementById("root")!).render(<App />);
