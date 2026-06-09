import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import {
  fetchLatestScreening,
  runScreening,
  type Candidate,
  type ScreeningResponse
} from "../api/client";
import { CandidateDetail } from "../components/CandidateDetail";
import { CandidateTable } from "../components/CandidateTable";

export function Dashboard() {
  const [result, setResult] = useState<ScreeningResponse | null>(null);
  const [selected, setSelected] = useState<Candidate | undefined>();
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadLatest() {
      setInitialLoading(true);
      setError(null);
      try {
        const latest = await fetchLatestScreening();
        setResult(latest);
        setSelected(latest.candidates[0]);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Failed to load latest screening");
      } finally {
        setInitialLoading(false);
      }
    }

    void loadLatest();
  }, []);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const next = await runScreening(10);
      setResult(next);
      setSelected(next.candidates[0]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Screening failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <div>
          <h1>Investment Opportunity Dashboard</h1>
          <p>Local-first screening with a self-hosted LLM research layer.</p>
        </div>
        <button onClick={handleRun} disabled={loading} title="Run screening">
          <RefreshCw size={18} />
          {loading ? "Running" : "Run"}
        </button>
      </header>

      {error && <div className="notice error">{error}</div>}
      {result?.warnings.length ? <div className="notice">{result.warnings.join(" | ")}</div> : null}

      <section className="layout">
        <div className="panel">
          <div className="panel-head">
            <h2>Today&apos;s Candidates</h2>
            <span>{initialLoading ? "loading" : result?.run_id ?? "not run"}</span>
          </div>
          <CandidateTable
            candidates={result?.candidates ?? []}
            selectedSymbol={selected?.symbol}
            onSelect={setSelected}
          />
        </div>
        <CandidateDetail candidate={selected} />
      </section>
    </main>
  );
}
