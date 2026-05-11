import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import Header from "../components/Header";
import { fmtUSD } from "../lib/format";
import { Trophy, ArrowRight, Sparkle, Lightning } from "@phosphor-icons/react";

export default function Leaderboard() {
  const [data, setData] = useState(null);
  const [period, setPeriod] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get(`/leaderboard?limit=10&period=${period}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div>
      <Header />
      <main className="max-w-[1280px] mx-auto px-6 lg:px-10 py-10">
        <div className="mb-10 flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Trophy size={18} weight="fill" color="#FFD600" />
              <span className="overline">Leaderboard</span>
            </div>
            <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tighter mb-2">
              Top deals right now.
            </h1>
            <p className="text-ink-secondary max-w-2xl">
              Ranked by discount-to-adjudged-value, weighted by AI investment grade. Refreshed every time you load.
            </p>
          </div>
          <div className="flex gap-2" data-testid="leaderboard-period-toggle">
            {[
              { v: "all", l: "All" },
              { v: "week", l: "This week" },
            ].map((opt) => (
              <button
                key={opt.v}
                onClick={() => setPeriod(opt.v)}
                className={
                  "px-4 py-2 text-sm font-medium transition-colors " +
                  (period === opt.v ? "bg-inverse text-white" : "btn-outline")
                }
                data-testid={`period-${opt.v}`}
              >
                {opt.l}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="py-20 text-center">
            <div className="ai-loader max-w-xs mx-auto" />
            <p className="text-sm text-ink-secondary mt-4">Computing rankings…</p>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="swiss-card p-12 text-center">
            <h3 className="font-display text-2xl font-semibold tracking-tight mb-2">No eligible properties.</h3>
            <p className="text-sm text-ink-secondary">
              Leaderboard requires both an adjudged value and a minimum bid. Try scraping more counties or running CAD enrichment.
            </p>
          </div>
        ) : (
          <div className="swiss-card-strong overflow-hidden">
            <div className="bg-inverse text-white px-6 py-3 flex items-center justify-between">
              <span className="overline" style={{ color: "rgba(255,255,255,0.6)" }}>
                Top {data.items.length} · {data.total_eligible} eligible
              </span>
              <span className="font-mono text-xs text-white/60">
                {new Date(data.generated_at).toLocaleString()}
              </span>
            </div>
            <div className="divide-y divide-default">
              {data.items.map((it, idx) => (
                <Link
                  to={`/property/${it.id}`}
                  key={it.id}
                  className="grid grid-cols-12 gap-4 items-center px-6 py-5 hover:bg-subtle transition-colors fade-up"
                  style={{ animationDelay: `${idx * 30}ms` }}
                  data-testid={`leaderboard-row-${idx}`}
                >
                  <div className="col-span-1 font-display text-3xl font-semibold tracking-tighter text-ink-tertiary">
                    {String(idx + 1).padStart(2, "0")}
                  </div>
                  <div className="col-span-12 md:col-span-4">
                    <div className="font-display text-base font-semibold tracking-tight">
                      {it.address}
                    </div>
                    <div className="text-xs text-ink-secondary mt-0.5">
                      {it.city} · {it.county}
                    </div>
                    <div className="flex gap-1 mt-1.5">
                      <span className="badge badge-muted">{it.property_type}</span>
                      {it.ai_grade && (
                        <span className={"badge score-" + it.ai_grade}>GRADE {it.ai_grade}</span>
                      )}
                    </div>
                  </div>
                  <div className="col-span-6 md:col-span-2">
                    <div className="overline">Min Bid</div>
                    <div className="font-mono text-base font-semibold">{fmtUSD(it.minimum_bid)}</div>
                  </div>
                  <div className="col-span-6 md:col-span-2">
                    <div className="overline">Adj. Value</div>
                    <div className="font-mono text-base font-semibold">{fmtUSD(it.adjudged_value)}</div>
                  </div>
                  <div className="col-span-12 md:col-span-2">
                    <div className="overline">Discount</div>
                    <div className="font-mono text-xl font-bold text-[#00C853] flex items-baseline gap-1">
                      {it.discount_pct}%
                      <span className="text-xs text-ink-secondary font-normal">
                        ({fmtUSD(it.discount_amount)})
                      </span>
                    </div>
                  </div>
                  <div className="hidden md:flex col-span-1 justify-end items-center gap-1.5">
                    <Lightning size={14} weight="fill" color="#002FA7" />
                    <span className="font-mono text-sm font-bold text-brand">{it.deal_score}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {data && data.items.length > 0 && (
          <div className="mt-10 swiss-card p-7 flex items-start gap-4 bg-ai border-l-2 border-brand">
            <Sparkle size={18} weight="fill" color="#002FA7" className="mt-1 shrink-0" />
            <div>
              <div className="overline mb-1">How this ranks</div>
              <p className="text-sm text-ink-secondary">
                <span className="font-mono">deal_score = (discount %) × (1 + AI score / 100)</span>.
                Ungraded properties default to score 0, so running AI insights on a candidate boosts its rank up to 2× when graded A.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
