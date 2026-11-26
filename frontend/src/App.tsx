import { useEffect, useRef, useState } from "react";
import {
  Activity, ChevronLeft, ChevronRight, Gauge, Hash, Layers3, Pause,
  Play, RefreshCcw, RotateCcw, Timer, Trophy,
} from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { compareSimulation, runSimulation, type HashTable, type HeapNode, type Snapshot, type SimulationResult, type Workload } from "./api";

const colors: Record<Workload, string> = { random: "#8b7cf6", looping: "#58a6ff", zipfian: "#4ecb8d" };

function HashVisualizer({ state, snapshot }: { state: HashTable; snapshot?: Snapshot }) {
  const [page, setPage] = useState(0);
  const pageSize = 96;
  const focus = snapshot?.bucket;
  const pages = Math.ceil(state.bucket_count / pageSize);
  const current = focus !== undefined && state.bucket_count > pageSize
    ? Math.floor(focus / pageSize)
    : page;
  const start = current * pageSize;
  const visible = state.buckets.slice(start, start + pageSize);
  return (
    <section className="panel hash-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">DSA 01</span><h2>Custom Hash Table</h2></div>
        <div className="hash-meta"><span>{state.unique_items} keys</span><span>{state.bucket_count} buckets</span></div>
      </div>
      <div className="bucket-toolbar">
        <span>FNV-1a / separate chaining</span>
        <div>
          <button className="icon-button" onClick={() => setPage(Math.max(0, current - 1))} disabled={current === 0}><ChevronLeft size={15} /></button>
          <span>{current + 1} / {pages}</span>
          <button className="icon-button" onClick={() => setPage(Math.min(pages - 1, current + 1))} disabled={current >= pages - 1}><ChevronRight size={15} /></button>
        </div>
      </div>
      <div className="buckets-grid">
        {visible.map((bucket) => (
          <div key={bucket.index} className={`bucket ${bucket.index === focus ? "focus" : ""} ${bucket.items.length ? "occupied" : ""}`}>
            <div className="bucket-index">#{bucket.index}</div>
            {bucket.items.length === 0 ? <div className="empty">empty</div> : bucket.items.map((item) => (
              <div key={item.item} className={`bucket-item ${snapshot?.incoming === item.item ? "accessed" : ""}`}>
                <b>{item.item}</b>
                <span>f={item.frequency} · t={item.last_accessed}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="stat-strip">
        <span>Avg chain <b>{state.stats.avg_chain.toFixed(2)}</b></span>
        <span>Max chain <b>{state.stats.max_chain}</b></span>
        <span>Empty <b>{state.stats.empty_buckets}</b></span>
      </div>
    </section>
  );
}

function HeapVisualizer({ nodes, root, updated }: { nodes: HeapNode[]; root: string | null; updated?: string }) {
  const depth = nodes.length ? Math.floor(Math.log2(nodes.length)) : 0;
  const levels = Array.from({ length: depth + 1 }, (_, d) =>
    nodes.slice((1 << d) - 1, (1 << (d + 1)) - 1),
  );
  return (
    <section className="panel heap-panel">
      <div className="panel-heading">
        <div><span className="eyebrow">DSA 02</span><h2>Max Heap</h2></div>
        <div className="heap-root">ROOT · <b>{root || "empty"}</b></div>
      </div>
      <div className="heap-tree">
        {levels.map((level, levelIndex) => (
          <div className="heap-level" key={levelIndex}>
            {level.map((node) => (
              <div key={node.index} className={`heap-node ${node.is_root ? "root" : ""} ${node.is_updated || updated === node.item ? "updated" : ""}`}>
                <span className="node-index">{node.index}</span>
                <b>{node.item}</b>
                <small>freq {node.frequency} · ts {node.last_accessed}</small>
              </div>
            ))}
          </div>
        ))}
      </div>
      {nodes.length === 0 && <div className="empty-state">No heap nodes yet</div>}
    </section>
  );
}

function App() {
  const [workload, setWorkload] = useState<Workload>("random");
  const [size, setSize] = useState(10000);
  const [seed, setSeed] = useState(42);
  const [topK, setTopK] = useState(5);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [comparison, setComparison] = useState<Record<Workload, SimulationResult> | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(500);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const timer = useRef<number>();

  const run = async () => {
    setLoading(true); setError(""); setPlaying(false);
    try {
      const [single, multi] = await Promise.all([
        runSimulation({ workload, size, seed, top_k: topK, snapshot_limit: 80 }),
        compareSimulation({ size, seed, top_k: topK }),
      ]);
      setResult(single); setComparison(multi); setStepIndex(0);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not connect to the API");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!playing || !result) return;
    timer.current = window.setTimeout(() => {
      if (stepIndex < result.snapshots.length - 1) setStepIndex((value) => value + 1);
      else setPlaying(false);
    }, speed);
    return () => window.clearTimeout(timer.current);
  }, [playing, stepIndex, speed, result]);

  const snapshot = result?.snapshots[stepIndex];
  const currentHash = snapshot?.hash_table || result?.hash_table;
  const currentHeap = snapshot?.heap || result?.heap;
  const accuracyData = comparison ? (Object.keys(comparison) as Workload[]).map((name) => ({
    workload: name[0].toUpperCase() + name.slice(1),
    accuracy: comparison[name].accuracy,
  })) : [];
  const runtimeData = comparison ? (Object.keys(comparison) as Workload[]).map((name) => ({
    workload: name[0].toUpperCase() + name.slice(1),
    runtime: comparison[name].latency_ms,
  })) : [];

  return (
    <main>
      <header>
        <div className="brand">
          <div className="logo"><Layers3 size={20} /></div>
          <div><h1>Predictive Cache &amp; Memory Access Simulator</h1><p>Frequency/recency analysis with Hash Tables and Heaps</p></div>
        </div>
        <div className="header-actions">
          <div className="status"><span className={loading ? "pulse" : ""}></span>{loading ? "Running" : result ? "Complete" : "Ready"}</div>
          <button className="secondary" onClick={() => { setResult(null); setComparison(null); setStepIndex(0); setPlaying(false); }}><RotateCcw size={16} />Reset</button>
          <button className="primary" onClick={run} disabled={loading}><Activity size={16} />{loading ? "Running..." : "Run Simulation"}</button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="dashboard-grid">
        <aside className="controls panel">
          <div className="panel-heading"><div><span className="eyebrow">CONFIGURATION</span><h2>Simulation controls</h2></div></div>
          <label>Workload
            <select value={workload} onChange={(event) => setWorkload(event.target.value as Workload)}>
              <option value="random">Random</option><option value="looping">Looping</option><option value="zipfian">Zipfian</option>
            </select>
          </label>
          <label>Input size
            <select value={size} onChange={(event) => setSize(Number(event.target.value))}>
              <option value={1000}>1,000 accesses</option><option value={10000}>10,000 accesses</option><option value={50000}>50,000 accesses</option>
            </select>
          </label>
          <label>Top-K items
            <input type="number" min={1} max={20} value={topK} onChange={(event) => setTopK(Math.max(1, Math.min(20, Number(event.target.value))))} />
          </label>
          <label>Seed
            <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </label>
          <button className="primary full" onClick={run} disabled={loading}><Play size={16} />Run selected workload</button>
        </aside>

        <section className="kpi-grid">
          {[
            ["Total Accesses", result?.input_accesses.toLocaleString() || "—", <Hash size={16}/>],
            ["Prediction Hits", result?.hits.toLocaleString() || "—", <Trophy size={16}/>],
            ["Prediction Misses", result?.misses.toLocaleString() || "—", <Activity size={16}/>],
            ["Prediction Accuracy", result ? `${result.accuracy.toFixed(2)}%` : "—", <Gauge size={16}/>],
            ["Execution Time", result ? `${result.latency_ms.toFixed(2)} ms` : "—", <Timer size={16}/>],
          ].map(([label, value, icon]) => (
            <article className="kpi" key={String(label)}><div>{icon}<span>{label}</span></div><strong>{value}</strong></article>
          ))}
        </section>

        <section className="panel chart-panel accuracy-chart">
          <div className="panel-heading"><div><span className="eyebrow">COMPARISON</span><h2>Prediction accuracy</h2></div></div>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={accuracyData}>
              <CartesianGrid stroke="#252a36" vertical={false} />
              <XAxis dataKey="workload" tick={{ fill: "#9aa3b5", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#9aa3b5", fontSize: 12 }} unit="%" axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#1a1d25" }} contentStyle={{ background: "#151820", border: "1px solid #303644" }} />
              <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>{accuracyData.map((item) => <Cell key={item.workload} fill={colors[item.workload.toLowerCase() as Workload]} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="panel chart-panel runtime-chart">
          <div className="panel-heading"><div><span className="eyebrow">PERFORMANCE</span><h2>Runtime comparison</h2></div></div>
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={runtimeData}>
              <CartesianGrid stroke="#252a36" vertical={false} />
              <XAxis dataKey="workload" tick={{ fill: "#9aa3b5", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#9aa3b5", fontSize: 12 }} unit=" ms" axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#151820", border: "1px solid #303644" }} />
              <Line type="monotone" dataKey="runtime" stroke="#8b7cf6" strokeWidth={2} dot={{ r: 4, fill: "#8b7cf6" }} />
            </LineChart>
          </ResponsiveContainer>
        </section>

        <section className="panel step-panel">
          <div className="panel-heading">
            <div><span className="eyebrow">TRACE</span><h2>Step-by-step prediction</h2></div>
            {snapshot && <div className={`result-badge ${snapshot.correct ? "correct" : "incorrect"}`}>{snapshot.correct ? "Correct" : "Incorrect"}</div>}
          </div>
          {snapshot ? (
            <>
              <div className="trace-flow">
                <div><span>Incoming access</span><b>{snapshot.incoming}</b></div>
                <div><span>Hash bucket</span><b>#{snapshot.bucket}</b></div>
                <div><span>Predicted</span><b>{snapshot.predicted || "warm-up"}</b></div>
                <div><span>Actual</span><b>{snapshot.actual}</b></div>
              </div>
              <div className="trace-details">
                <span>Lookup: <b>{snapshot.lookup}</b></span>
                <span>Frequency: <b>{snapshot.updated_frequency ?? "—"}</b></span>
                <span>Timestamp: <b>{snapshot.updated_timestamp ?? "—"}</b></span>
                <span>Collision: <b>{snapshot.collision ? "yes" : "no"}</b></span>
              </div>
            </>
          ) : <div className="empty-state">Run a simulation to inspect access steps</div>}
          <div className="playback">
            <button className="icon-button" onClick={() => setStepIndex((value) => Math.max(0, value - 1))} disabled={!snapshot}><ChevronLeft size={16} /></button>
            <button className="play-button" onClick={() => setPlaying((value) => !value)} disabled={!result?.snapshots.length}>{playing ? <Pause size={16}/> : <Play size={16}/>}</button>
            <button className="icon-button" onClick={() => setStepIndex((value) => Math.min((result?.snapshots.length || 1) - 1, value + 1))} disabled={!snapshot}><ChevronRight size={16} /></button>
            <input type="range" min={0} max={Math.max(0, (result?.snapshots.length || 1) - 1)} value={stepIndex} onChange={(event) => setStepIndex(Number(event.target.value))} />
            <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}><option value={1000}>1x</option><option value={500}>2x</option><option value={150}>4x</option></select>
          </div>
        </section>

        {currentHash && <HashVisualizer state={currentHash} snapshot={snapshot} />}
        {currentHeap && <HeapVisualizer nodes={currentHeap.nodes} root={currentHeap.root} updated={snapshot?.incoming} />}

        <section className="panel topk-panel">
          <div className="panel-heading"><div><span className="eyebrow">RANKING</span><h2>Top-K frequently accessed</h2></div></div>
          <table>
            <thead><tr><th>Rank</th><th>Item / page</th><th>Frequency</th><th>Last access</th></tr></thead>
            <tbody>
              {result?.top_k.map((item) => <tr key={item.item}><td>{item.rank}</td><td>{item.item}</td><td>{item.frequency}</td><td>{item.last_accessed}</td></tr>) ||
                <tr><td colSpan={4}>No simulation result</td></tr>}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}

export default App;
