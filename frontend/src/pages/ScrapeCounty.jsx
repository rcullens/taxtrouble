import { useEffect, useState } from "react";
import api from "../lib/api";
import Header from "../components/Header";
import { CheckCircle, Spinner, Warning, ArrowRight, MapPin, ArrowsClockwise } from "@phosphor-icons/react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

export default function ScrapeCounty() {
  const nav = useNavigate();
  const [counties, setCounties] = useState({ presupported: [], available: [] });
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);
  const [lastResults, setLastResults] = useState(null);
  const [jobs, setJobs] = useState([]);

  useEffect(() => {
    api.get("/counties").then((r) => setCounties(r.data)).catch(() => {});
    api.get("/scrape/jobs?limit=5").then((r) => setJobs(r.data.items || [])).catch(() => {});
  }, []);

  const toggle = (c) =>
    setSelected((cur) => (cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c]));

  const run = async () => {
    if (selected.length === 0) {
      toast.error("Pick at least one county");
      return;
    }
    setBusy(true);
    setLastResults(null);
    try {
      const { data } = await api.post("/scrape", { counties: selected });
      setLastResults(data.results || []);
      const ok = (data.results || []).filter((r) => r.status === "success").length;
      toast.success(`Scrape complete — ${ok}/${selected.length} counties succeeded`);
      api.get("/scrape/jobs?limit=5").then((r) => setJobs(r.data.items || []));
    } catch (err) {
      toast.error("Scrape failed");
    } finally {
      setBusy(false);
    }
  };

  const presupportedNames = new Set((counties.presupported || []).map((c) => c.name));
  const otherCounties = (counties.available || []).filter((c) => !presupportedNames.has(c));

  return (
    <div>
      <Header />
      <main className="max-w-[1440px] mx-auto px-6 lg:px-10 py-10">
        <span className="overline">On-demand scraping</span>
        <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tighter mt-2 mb-2">
          Scrape any Texas county.
        </h1>
        <p className="text-ink-secondary max-w-2xl mb-10">
          Trigger a fresh scrape against public records. Pre-supported counties ship with verified data; other counties run through a generic scraper against MVBA Law & county tax-office sites.
        </p>

        <div className="grid lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            {/* Pre-supported */}
            <div className="swiss-card-strong p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="badge badge-brand">VERIFIED</span>
                <h2 className="font-display text-xl font-semibold tracking-tight">
                  Pre-supported counties (real data)
                </h2>
              </div>
              <div className="space-y-2">
                {(counties.presupported || []).map((c) => {
                  const checked = selected.includes(c.name);
                  return (
                    <label
                      key={c.name}
                      className={
                        "flex items-start gap-3 p-4 cursor-pointer transition-colors swiss-card " +
                        (checked ? "border-strong bg-subtle" : "hover:bg-subtle")
                      }
                      data-testid={`county-presupported-${c.name.replace(/\s+/g, "-").toLowerCase()}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(c.name)}
                        className="mt-1 w-4 h-4 accent-[#002FA7]"
                      />
                      <div className="flex-1">
                        <div className="font-display font-semibold text-base">{c.name}</div>
                        <div className="flex items-center gap-1 text-xs text-ink-secondary mt-0.5">
                          <MapPin size={11} />
                          <span>{c.sale_location}</span>
                        </div>
                        {c.source_doc && (
                          <a
                            href={c.source_doc}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-xs text-brand hover:underline mt-1 inline-block break-all"
                          >
                            {c.source_doc}
                          </a>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Other counties */}
            <div className="swiss-card p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="badge badge-muted">EXPERIMENTAL</span>
                <h2 className="font-display text-xl font-semibold tracking-tight">
                  Other Texas counties (generic scraper)
                </h2>
              </div>
              <p className="text-sm text-ink-secondary mb-4">
                These counties go through our generic scraper which attempts to parse MVBA Law tax sale PDFs and county tax-office pages. Results vary by county.
              </p>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-96 overflow-y-auto pr-1">
                {otherCounties.map((c) => {
                  const checked = selected.includes(c);
                  return (
                    <label
                      key={c}
                      className={
                        "flex items-center gap-2 text-sm p-2.5 cursor-pointer transition-colors swiss-card " +
                        (checked ? "border-strong bg-subtle" : "hover:bg-subtle")
                      }
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(c)}
                        className="w-3.5 h-3.5 accent-[#002FA7]"
                      />
                      <span>{c}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Results */}
            {lastResults && (
              <div className="swiss-card-strong p-6">
                <h3 className="font-display text-lg font-semibold tracking-tight mb-4">Last run</h3>
                <div className="space-y-2">
                  {lastResults.map((r) => (
                    <div
                      key={r.county}
                      className={
                        "p-4 border-l-4 flex items-start justify-between gap-4 " +
                        (r.status === "success"
                          ? "border-[#00C853] bg-[#F0FDF4]"
                          : r.status === "error"
                          ? "border-danger bg-[#FFF1F1]"
                          : "border-warning bg-[#FFFBEB]")
                      }
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          {r.status === "success" ? (
                            <CheckCircle size={16} weight="fill" color="#00C853" />
                          ) : r.status === "error" ? (
                            <Warning size={16} weight="fill" color="#FF3333" />
                          ) : (
                            <Warning size={16} weight="fill" color="#FFD600" />
                          )}
                          <span className="font-semibold">{r.county}</span>
                        </div>
                        <div className="text-xs text-ink-secondary mt-1 font-mono">
                          {r.properties_found} found · {r.properties_inserted} new · {r.properties_updated} updated · {r.duration_seconds?.toFixed(2)}s
                        </div>
                        {r.message && <div className="text-xs text-ink-secondary mt-1">{r.message}</div>}
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => nav("/dashboard")}
                  className="btn-primary mt-5 inline-flex items-center gap-2"
                >
                  View results in dashboard <ArrowRight size={14} weight="bold" />
                </button>
              </div>
            )}
          </div>

          {/* Run panel */}
          <aside className="lg:col-span-4">
            <div className="swiss-card-strong p-6 sticky top-20">
              <div className="overline mb-2">Run Scraper</div>
              <div className="font-display text-3xl font-semibold tracking-tight mb-1">
                {selected.length} <span className="text-ink-tertiary text-xl">selected</span>
              </div>
              <div className="text-xs text-ink-secondary mb-5">
                {selected.length === 0
                  ? "Pick one or more counties to begin."
                  : selected.join(", ")}
              </div>

              <button
                onClick={run}
                disabled={busy || selected.length === 0}
                className="btn-primary w-full flex items-center justify-center gap-2"
                data-testid="run-scrape-btn"
              >
                {busy ? (
                  <>
                    <Spinner size={16} className="animate-spin" /> Scraping...
                  </>
                ) : (
                  <>
                    <ArrowsClockwise size={16} weight="bold" /> Start Scrape
                  </>
                )}
              </button>
              {busy && <div className="ai-loader mt-4" />}

              {jobs.length > 0 && (
                <div className="mt-6 pt-5 border-t border-default">
                  <div className="overline mb-3">Recent jobs</div>
                  <ul className="space-y-2 text-xs">
                    {jobs.slice(0, 5).map((j) => (
                      <li key={j.id} className="flex items-center justify-between gap-2">
                        <span className="font-mono text-ink-secondary truncate">
                          {(j.counties || []).join(", ")}
                        </span>
                        <span
                          className={
                            "badge " +
                            (j.status === "completed" ? "badge-success" : "badge-muted")
                          }
                        >
                          {j.status}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
