import { Link } from "react-router-dom";
import { fmtUSD, propertyTypeLabel, taxStatusLabel } from "../lib/format";
import { MapPin, Warning, Sparkle, Buildings } from "@phosphor-icons/react";

export default function PropertyCard({ property }) {
  const p = property;
  const score = p.ai_score;
  const grade = p.ai_grade;
  return (
    <Link
      to={`/property/${p.id}`}
      className="swiss-card p-5 flex flex-col gap-4 hover:border-strong transition-colors fade-up"
      data-testid={`property-card-${p.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="overline">{p.county}</span>
            <span className="text-ink-tertiary text-[10px]">/</span>
            <span className="overline">{propertyTypeLabel(p.property_type)}</span>
          </div>
          <h3 className="font-display text-lg font-semibold tracking-tight text-ink leading-tight">
            {p.address}
          </h3>
          <div className="flex items-center gap-1 text-sm text-ink-secondary mt-0.5">
            <MapPin size={12} />
            <span>
              {p.city}, TX {p.zip_code || ""}
            </span>
          </div>
        </div>
        {score != null && (
          <div
            className={"flex flex-col items-center justify-center px-2.5 py-1.5 score-" + (grade || "C")}
            data-testid={`ai-score-${p.id}`}
          >
            <span className="text-[9px] font-bold tracking-widest leading-none">SCORE</span>
            <span className="font-display text-2xl font-bold leading-none mt-1">{score}</span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {p.has_back_taxes && (
          <span className="badge badge-warning">
            <Warning size={10} weight="fill" /> BACK TAXES
          </span>
        )}
        {p.has_hoa_lien && (
          <span className="badge badge-danger">
            <Buildings size={10} weight="fill" /> HOA LIEN
          </span>
        )}
        <span className="badge badge-muted">{taxStatusLabel(p.tax_status)}</span>
      </div>

      <div className="grid grid-cols-3 gap-4 pt-3 border-t border-default">
        <div>
          <div className="overline mb-1">Tax Owed</div>
          <div className="font-mono text-base font-semibold text-danger">{fmtUSD(p.tax_owed)}</div>
        </div>
        <div>
          <div className="overline mb-1">Min Bid</div>
          <div className="font-mono text-base font-semibold text-ink">{fmtUSD(p.minimum_bid)}</div>
        </div>
        <div>
          <div className="overline mb-1">Adj. Value</div>
          <div className="font-mono text-base font-semibold text-ink">{fmtUSD(p.adjudged_value)}</div>
        </div>
      </div>

      {p.ai_summary && (
        <div className="bg-ai border-l-2 border-brand px-3 py-2 flex gap-2">
          <Sparkle size={14} weight="fill" className="mt-0.5 shrink-0" color="#002FA7" />
          <p className="text-xs leading-relaxed text-ink-secondary line-clamp-2">{p.ai_summary}</p>
        </div>
      )}
    </Link>
  );
}
