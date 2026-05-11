import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { fmtUSD } from "../lib/format";
import { ChartLineUp, ArrowRight, Spinner } from "@phosphor-icons/react";

export default function ComparablesPanel({ propertyId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get(`/properties/${propertyId}/comparables?limit=5`)
      .then((r) => !cancelled && setData(r.data))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [propertyId]);

  if (loading) {
    return (
      <div className="swiss-card p-7">
        <div className="ai-loader" />
        <p className="text-sm text-ink-secondary mt-3">Loading comparables…</p>
      </div>
    );
  }
  if (!data || !data.comparables.length) return null;

  return (
    <div className="swiss-card-strong overflow-hidden" data-testid="comparables-panel">
      <div className="bg-subtle border-b border-default px-7 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <ChartLineUp size={20} weight="duotone" />
          <div>
            <div className="overline">Comparable Properties</div>
            <div className="text-sm font-semibold mt-0.5">
              {data.comparables.length} comps · scope: {data.scope}
              {data.area_avg_price_per_sqft && (
                <span className="text-ink-secondary ml-2 font-mono text-xs">
                  · area avg ${data.area_avg_price_per_sqft}/sqft
                </span>
              )}
            </div>
          </div>
        </div>
        {data.target?.price_per_sqft && (
          <div className="text-right">
            <div className="overline">This property</div>
            <div className="font-mono text-base font-semibold">
              ${data.target.price_per_sqft}<span className="text-ink-tertiary text-sm">/sqft</span>
            </div>
          </div>
        )}
      </div>
      <div className="p-7">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left">
                {["Property", "Type", "Sqft", "Min Bid", "Adj. Value", "$/sqft", "Δ vs target"].map((h) => (
                  <th key={h} className="overline pb-3 font-bold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.comparables.map((c) => {
                const delta = c.delta_pct_vs_target;
                return (
                  <tr key={c.id} className="border-t border-default swiss-row">
                    <td className="py-3 pr-4">
                      <Link to={`/property/${c.id}`} className="font-medium text-ink hover:text-brand">
                        {c.address}
                      </Link>
                      <div className="text-xs text-ink-secondary mt-0.5">
                        {c.city}, {c.zip_code}
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <span className="badge badge-muted">{c.property_type}</span>
                    </td>
                    <td className="py-3 pr-4 font-mono">{c.sqft ? c.sqft.toLocaleString() : "—"}</td>
                    <td className="py-3 pr-4 font-mono">{fmtUSD(c.minimum_bid)}</td>
                    <td className="py-3 pr-4 font-mono">{fmtUSD(c.adjudged_value)}</td>
                    <td className="py-3 pr-4 font-mono">{c.price_per_sqft ? `$${c.price_per_sqft}` : "—"}</td>
                    <td className="py-3 pr-4 font-mono">
                      {delta == null ? (
                        <span className="text-ink-tertiary">—</span>
                      ) : delta > 0 ? (
                        <span className="text-danger">+{delta}%</span>
                      ) : (
                        <span className="text-[#00C853]">{delta}%</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
