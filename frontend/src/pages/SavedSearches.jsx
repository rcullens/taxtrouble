import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import Header from "../components/Header";
import { fmtUSD } from "../lib/format";
import { Trash, ArrowRight, FloppyDisk } from "@phosphor-icons/react";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";

export default function SavedSearches() {
  const { user, loading } = useAuth();
  const nav = useNavigate();
  const [items, setItems] = useState([]);
  const [loadingItems, setLoadingItems] = useState(true);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      nav("/login", { state: { from: "/saved" } });
      return;
    }
    api
      .get("/saved-searches")
      .then((r) => setItems(r.data.items || []))
      .finally(() => setLoadingItems(false));
  }, [user, loading, nav]);

  const remove = async (id) => {
    if (!window.confirm("Delete this saved search?")) return;
    await api.delete(`/saved-searches/${id}`);
    setItems((cur) => cur.filter((x) => x.id !== id));
    toast.success("Deleted");
  };

  const run = (filters) => {
    sessionStorage.setItem("tx_filters", JSON.stringify(filters));
    nav("/dashboard");
  };

  return (
    <div>
      <Header />
      <main className="max-w-[1200px] mx-auto px-6 lg:px-10 py-10">
        <span className="overline">Saved</span>
        <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tighter mt-2 mb-2">
          Your searches.
        </h1>
        <p className="text-ink-secondary mb-10">
          Re-run a saved filter combination with one click.
        </p>

        {loadingItems ? (
          <div className="ai-loader" />
        ) : items.length === 0 ? (
          <div className="swiss-card p-12 text-center" data-testid="saved-empty">
            <FloppyDisk size={32} className="mx-auto mb-3 text-ink-tertiary" />
            <h3 className="font-display text-2xl font-semibold tracking-tight mb-2">No saved searches yet.</h3>
            <p className="text-sm text-ink-secondary mb-6">
              Save filter combinations from the dashboard for quick re-runs.
            </p>
            <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2">
              Go to dashboard <ArrowRight size={14} weight="bold" />
            </Link>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {items.map((s) => (
              <div key={s.id} className="swiss-card p-5 fade-up" data-testid={`saved-${s.id}`}>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <h3 className="font-display text-lg font-semibold tracking-tight">{s.name}</h3>
                  <button
                    onClick={() => remove(s.id)}
                    className="text-ink-tertiary hover:text-danger transition-colors"
                    data-testid={`saved-delete-${s.id}`}
                  >
                    <Trash size={16} />
                  </button>
                </div>
                <div className="flex flex-wrap gap-1.5 mb-4 min-h-[24px]">
                  {(s.filters?.counties || []).map((c) => (
                    <span key={c} className="badge badge-muted">{c}</span>
                  ))}
                  {s.filters?.property_type && (
                    <span className="badge badge-muted">{s.filters.property_type}</span>
                  )}
                  {s.filters?.zip_code && (
                    <span className="badge badge-muted">ZIP {s.filters.zip_code}</span>
                  )}
                  {(s.filters?.min_amount || s.filters?.max_amount) && (
                    <span className="badge badge-muted">
                      {fmtUSD(s.filters.min_amount || 0)} – {fmtUSD(s.filters.max_amount || 999999)}
                    </span>
                  )}
                  {s.filters?.has_hoa_lien && <span className="badge badge-danger">HOA</span>}
                </div>
                <button
                  onClick={() => run(s.filters)}
                  className="btn-outline w-full inline-flex items-center justify-center gap-2 text-sm"
                  data-testid={`saved-run-${s.id}`}
                >
                  Run search <ArrowRight size={14} weight="bold" />
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
