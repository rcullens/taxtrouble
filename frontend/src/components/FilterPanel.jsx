import { useState, useEffect } from "react";

const COUNTIES = ["McLennan County", "Hill County", "Bosque County"];
const PROP_TYPES = [
  { v: "", l: "Any type" },
  { v: "residential", l: "Residential" },
  { v: "commercial", l: "Commercial" },
  { v: "land", l: "Land" },
  { v: "manufactured_home", l: "Manufactured Home" },
  { v: "mixed_use", l: "Mixed Use" },
];
const STATUSES = [
  { v: "", l: "Any status" },
  { v: "delinquent", l: "Delinquent" },
  { v: "in_foreclosure", l: "In Foreclosure" },
  { v: "scheduled_for_sale", l: "Scheduled For Sale" },
  { v: "struck_off", l: "Struck Off" },
];

export default function FilterPanel({ value, onChange, allCounties, onSave }) {
  const [local, setLocal] = useState(value || {});
  useEffect(() => setLocal(value || {}), [value]);

  const update = (patch) => {
    const next = { ...local, ...patch };
    setLocal(next);
    onChange(next);
  };

  const reset = () => {
    setLocal({});
    onChange({});
  };

  const countiesList = allCounties && allCounties.length ? allCounties : COUNTIES;

  return (
    <div className="swiss-card p-5 sticky top-20" data-testid="filter-panel">
      <div className="flex items-center justify-between mb-5">
        <h3 className="overline">Filters</h3>
        <button
          onClick={reset}
          className="text-xs font-medium text-ink-secondary hover:text-ink transition-colors"
          data-testid="filter-reset-btn"
        >
          Clear all
        </button>
      </div>

      <div className="space-y-5">
        <div>
          <label className="overline block mb-2">Counties</label>
          <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
            {countiesList.map((c) => {
              const checked = (local.counties || []).includes(c);
              return (
                <label
                  key={c}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:bg-subtle px-2 py-1.5 -mx-2 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      const cur = local.counties || [];
                      update({
                        counties: checked ? cur.filter((x) => x !== c) : [...cur, c],
                      });
                    }}
                    className="w-3.5 h-3.5 accent-[#002FA7]"
                    data-testid={`filter-county-${c.replace(/\s+/g, "-").toLowerCase()}`}
                  />
                  <span>{c}</span>
                </label>
              );
            })}
          </div>
        </div>

        <div>
          <label className="overline block mb-2">Property Type</label>
          <select
            value={local.property_type || ""}
            onChange={(e) => update({ property_type: e.target.value || undefined })}
            className="swiss-input"
            data-testid="filter-property-type"
          >
            {PROP_TYPES.map((t) => (
              <option key={t.v} value={t.v}>
                {t.l}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="overline block mb-2">Tax Status</label>
          <select
            value={local.tax_status || ""}
            onChange={(e) => update({ tax_status: e.target.value || undefined })}
            className="swiss-input"
            data-testid="filter-tax-status"
          >
            {STATUSES.map((s) => (
              <option key={s.v} value={s.v}>
                {s.l}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="overline block mb-2">Tax Owed (USD)</label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="Min"
              value={local.min_amount ?? ""}
              onChange={(e) =>
                update({ min_amount: e.target.value ? Number(e.target.value) : undefined })
              }
              className="swiss-input font-mono"
              data-testid="filter-min-amount"
            />
            <input
              type="number"
              placeholder="Max"
              value={local.max_amount ?? ""}
              onChange={(e) =>
                update({ max_amount: e.target.value ? Number(e.target.value) : undefined })
              }
              className="swiss-input font-mono"
              data-testid="filter-max-amount"
            />
          </div>
        </div>

        <div>
          <label className="overline block mb-2">ZIP Code</label>
          <input
            type="text"
            value={local.zip_code || ""}
            onChange={(e) => update({ zip_code: e.target.value || undefined })}
            placeholder="76704"
            className="swiss-input font-mono"
            data-testid="filter-zip"
          />
        </div>

        <div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={local.has_hoa_lien === true}
              onChange={(e) =>
                update({ has_hoa_lien: e.target.checked ? true : undefined })
              }
              className="w-3.5 h-3.5 accent-[#002FA7]"
              data-testid="filter-hoa-lien"
            />
            <span>Has HOA Lien</span>
          </label>
        </div>

        {onSave && (
          <button
            onClick={onSave}
            className="btn-outline w-full text-sm"
            data-testid="filter-save-btn"
          >
            Save this search
          </button>
        )}
      </div>
    </div>
  );
}
