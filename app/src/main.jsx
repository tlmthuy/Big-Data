import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const models = [
  { id: "Popularity", available: true },
  { id: "GRU", available: false },
  { id: "XLNet", available: false },
];

function App() {
  const [demo, setDemo] = useState(null);
  const [model, setModel] = useState("Popularity");
  const [sessionId, setSessionId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/demo-data.json")
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => {
        setDemo(data);
        setSessionId(data.sessions[0]?.user_session ?? "");
      })
      .catch((cause) => setError(cause.message));
  }, []);

  const selectedModel = models.find((item) => item.id === model);
  const session = useMemo(
    () => demo?.sessions.find((item) => item.user_session === sessionId),
    [demo, sessionId],
  );
  const targetRank = session?.top20.findIndex((id) => String(id) === String(session.target));

  if (error) return <main className="shell"><p className="error">Unable to load demo data: {error}</p></main>;
  if (!demo) return <main className="shell"><p className="loading">Loading demo…</p></main>;

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">TV4 / Session recommender</p>
          <h1>Next-item recommendation</h1>
        </div>
        <span className="badge">Toy data · K=20</span>
      </header>

      <section className="controls" aria-label="Demo controls">
        <label>Model
          <select value={model} onChange={(event) => setModel(event.target.value)}>
            {models.map((item) => (
              <option key={item.id} value={item.id}>{item.id}{item.available ? "" : " — no output"}</option>
            ))}
          </select>
        </label>
        <label>Session
          <select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
            {demo.sessions.map((item) => (
              <option key={item.user_session} value={item.user_session}>{item.user_session}</option>
            ))}
          </select>
        </label>
        <label>Subset<input value={demo.subset} readOnly /></label>
        <label>Split<input value={demo.split} readOnly /></label>
      </section>

      {!selectedModel.available ? (
        <section className="unavailable" role="status">
          <strong>{model} prediction output is not available.</strong>
          <p>The selection is preserved, but no synthetic ranking is shown.</p>
        </section>
      ) : (
        <>
          <section className="grid">
            <article className="panel history-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">Input</p><h2>Session history</h2></div>
                <span>{session.prefix.length} items</span>
              </div>
              <p className="definition">Prefix after splitting out the target</p>
              <div className="history" aria-label="Session history">
                {session.prefix.map((id, index) => (
                  <React.Fragment key={`${id}-${index}`}>
                    {index > 0 && <span className="arrow" aria-hidden="true">→</span>}
                    <span className="product-chip">{String(id)}</span>
                  </React.Fragment>
                ))}
              </div>
            </article>
            <article className="panel actual-panel">
              <p className="eyebrow">Ground truth</p>
              <h2>Actual next item</h2>
              <div className="actual-id">{String(session.target)}</div>
              <p className={targetRank >= 0 ? "match" : "miss"}>
                {targetRank >= 0 ? `Hit · rank ${targetRank + 1} of 20` : "Miss · outside Top-20"}
              </p>
            </article>
          </section>

          <section className="panel recommendations">
            <div className="panel-heading">
              <div><p className="eyebrow">Output</p><h2>Top-20 recommendations</h2></div>
              <span>{model}</span>
            </div>
            <div className="ranking">
              {session.top20.map((id, index) => {
                const isTarget = String(id) === String(session.target);
                return (
                  <div className={isTarget ? "rank-row hit" : "rank-row"} key={`${id}-${index}`}>
                    <span className="rank">{index + 1}</span>
                    <span className="rank-id">{String(id)}</span>
                    {isTarget && <span className="hit-label">Actual next item</span>}
                  </div>
                );
              })}
            </div>
          </section>

          <footer>
            <span>Subset: <strong>{demo.subset}</strong></span>
            <span>Split: <strong>{demo.split}</strong></span>
            <span>Catalog: <strong>{demo.catalog.length} items</strong></span>
          </footer>
        </>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
