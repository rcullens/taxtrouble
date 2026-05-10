import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import Header from "../components/Header";
import FilterPanel from "../components/FilterPanel";
import PropertyCard from "../components/PropertyCard";
import { fmtUSD } from "../lib/format";
import { useAuth } from "../lib/auth";
import {
  MagnifyingGlass, Sparkle, FileCsv, FloppyDisk, ArrowRight, Spinner,
} from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Dashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [filters, setFilters] = useState({});
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [sort, setSort] = useState("tax_owed_desc");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [nlQuery, setNlQuery] = useState("");
  const [nlBusy, setNlBusy] = useState(false);
  const [nlInterpretation, setNlInterpretation] = useState("");
  const [counties, setCounties] = useState([]);

  const runSearch = useCallback(async (currFilters, p = 1, s = sort) => {
    setLoading(true);
    try {
      const { data } = await api.post(
        `/properties/search?page=${p}&page_size=${pageSize}&sort=${s}`,
        currFilters || {}
      );
      setResults(data.results);
      setTotal(data.total);
      setPage(p);
    } catch (err) {
      toast.error("Search failed");
    } finally {
      setLoading(false);
    }
  }, [pageSize, sort]);

  useEffect(() => {
    runSearch(filters, 1, sort);
  }, [filters, sort, runSearch]);

  useEffect(() => {
    api.get("/stats/dashboard").then((r) => setStats(r.data)).catch(() => {});
    api.get("/counties").then((r) => setCounties(r.data.available || [])).catch(() => {});
  }, []);

  const runNL = async () => {
    if (!nlQuery.trim()) return;
    setNlBusy(true);
    try {
      const { data } = await api.post("/search/nl-parse", { query: nlQuery });
      setNlInterpretation(data.interpreted);
      setFilters(data.filters);
      toast.success("Query interpreted with AI");
    } catch (err) {
      toast.error("AI parsing failed - " + (err.response?.data?.detail || "try again"));
    } finally {
      setNlBusy(false);
    }
  };

  const exportCsv = async () => {
    try {
      const res = await api.post("/properties/export", filters, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `tx_properties_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast.success("Export downloaded");
    } catch {
      toast.error("Export failed");
    }
  };

  const saveSearch = async () => {
    if (!user) {
      toast.error("Sign in to save searches");
      nav("/login", { state: { from: "/dashboard" } });
      return;
    }
    const name = window.prompt("Name this search:", "My search");
    if (!name) return;
    try {
      await api.post("/saved-searches", { name, filters });
      toast.success("Search saved");
    } catch {
      toast.error("Could not save");
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <Header />
      <main className="max-w-[1440px] mx-auto px-6 lg:px-10 py-10">
        {/* Hero NL Search */}
        <div className="mb-10 fade-up">
          <span className="overline">Dashboard</span>
          <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tighter mt-2 mb-2">
            Property control room.
          </h1>
          <p className="text-ink-secondary mb-8 max-w-2xl">
            Search 36+ real distressed Texas properties. Use natural language or sharpen with filters.
          </p>

          <div className="swiss-card-strong p-2 flex items-center gap-2">
            <div className="px-3">
              <Sparkle size={20} weight="fill" color="#002FA7" />
            </div>
            <input
              type="text"
              value={nlQuery}
              onChange={(e) => setNlQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runNL()}
              placeholder="Try: 'Waco residentials under $10k with HOA liens' or 'land in Hill County'"
              className="flex-1 px-2 py-3 text-base font-medium border-0 outline-none bg-transparent"
              data-testid="nl-search-input"
            />
            <button
              onClick={runNL}
              disabled={nlBusy}
              className="btn-primary inline-flex items-center gap-2 shrink-0"
              data-testid="nl-search-btn"
            >
              {nlBusy ? <Spinner size={16} className="animate-spin" /> : <MagnifyingGlass size={16} weight="bold" />}
              <span className="hidden sm:inline">{nlBusy ? "Thinking..." : "AI Search"}</span>
            </button>
          </div>
          {nlBusy && <div className="ai-loader mt-2" data-testid="ai-loader" />}
          {nlInterpretation && (
            <div className="mt-3 bg-ai border-l-2 border-brand px-4 py-2 text-sm flex gap-2">
              <Sparkle size={14} weight="fill" className="mt-0.5 shrink-0" color="#002FA7" />
              <span className="text-ink-secondary">
                <span className="overline mr-2">Interpreted</span>
                {nlInterpretation}
              </span>
            </div>
          )}
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
            {[
              { label: "Properties indexed", val: stats.total_properties, mono: false },
              { label: "Total tax owed", val: fmtUSD(stats.total_value_at_risk), mono: true },
              { label: "Counties covered", val: stats.counties_covered },
              { label: "New this week", val: stats.new_this_week },
            ].map((s, i) => (
              <div
                key={s.label}
                className="swiss-card p-5 fade-up"
                style={{ animationDelay: `${i * 50}ms` }}
                data-testid={`stat-${i}`}
              >
                <div className="overline mb-2">{s.label}</div>
                <div className={"metric-big " + (s.mono ? "font-mono" : "")}>{s.val}</div>
              </div>
            ))}
          </div>
        )}

        {/* Main grid */}
        <div className="grid lg:grid-cols-12 gap-6">
          <aside className="lg:col-span-3">
            <FilterPanel
              value={filters}
              onChange={setFilters}
              allCounties={counties}
              onSave={saveSearch}
            />
          </aside>

          <section className="lg:col-span-9 space-y-4">
            {/* Toolbar */}
            <div className="swiss-card p-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="overline">Results</div>
                <div className="text-sm font-medium mt-0.5">
                  {loading ? "Loading…" : `${total.toLocaleString()} properties`}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value)}
                  className="swiss-input text-sm"
                  data-testid="sort-select"
                >
                  <option value="tax_owed_desc">Highest tax owed</option>
                  <option value="tax_owed_asc">Lowest tax owed</option>
                  <option value="newest">Most recently scraped</option>
                  <option value="ai_score">Best AI score</option>
                </select>
                <button onClick={exportCsv} className="btn-outline inline-flex items-center gap-1.5 text-sm" data-testid="export-btn">
                  <FileCsv size={14} /> Export CSV
                </button>
                <button onClick={saveSearch} className="btn-outline inline-flex items-center gap-1.5 text-sm" data-testid="save-search-btn">
                  <FloppyDisk size={14} /> Save
                </button>
              </div>
            </div>

            {/* Results grid */}
            {loading ? (
              <div className="py-20 text-center">
                <div className="ai-loader max-w-xs mx-auto" />
                <p className="text-sm text-ink-secondary mt-4">Querying properties...</p>
              </div>
            ) : results.length === 0 ? (
              <div className="swiss-card p-12 text-center">
                <h3 className="font-display text-2xl font-semibold tracking-tight mb-2">No properties match.</h3>
                <p className="text-sm text-ink-secondary mb-6">Try clearing filters or scraping a new county.</p>
                <button onClick={() => nav("/scrape")} className="btn-primary inline-flex items-center gap-2">
                  Scrape a county <ArrowRight size={14} weight="bold" />
                </button>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {results.map((p) => (
                  <PropertyCard key={p.id} property={p} />
                ))}
              </div>
            )}

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <button
                  onClick={() => runSearch(filters, page - 1, sort)}
                  disabled={page <= 1}
                  className="btn-outline disabled:opacity-40 disabled:cursor-not-allowed"
                  data-testid="pagination-prev"
                >
                  ← Previous
                </button>
                <span className="text-sm font-mono text-ink-secondary">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => runSearch(filters, page + 1, sort)}
                  disabled={page >= totalPages}
                  className="btn-outline disabled:opacity-40 disabled:cursor-not-allowed"
                  data-testid="pagination-next"
                >
                  Next →
                </button>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
