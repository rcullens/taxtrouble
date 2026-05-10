import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import Header from "../components/Header";
import { fmtUSD, fmtUSDPrecise, propertyTypeLabel, taxStatusLabel, fmtNum } from "../lib/format";
import {
  ArrowLeft, Sparkle, MapPin, Buildings, Warning, FileText, CheckCircle, XCircle, LinkSimple, Spinner, House, Stack,
} from "@phosphor-icons/react";
import { toast } from "sonner";

export default function PropertyDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [prop, setProp] = useState(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [cadBusy, setCadBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get(`/properties/${id}`)
      .then((r) => !cancelled && setProp(r.data))
      .catch(() => !cancelled && setError("Property not found"));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const runAI = async () => {
    setAiBusy(true);
    try {
      const { data } = await api.post(`/properties/${id}/ai-insights`);
      setProp(data);
      toast.success("AI analysis complete");
    } catch (err) {
      toast.error("AI failed: " + (err.response?.data?.detail || "try again"));
    } finally {
      setAiBusy(false);
    }
  };

  const runCAD = async () => {
    setCadBusy(true);
    try {
      const { data } = await api.post(`/properties/${id}/cad-enrich`);
      setProp(data);
      toast.success("CAD enrichment complete");
    } catch (err) {
      toast.error("CAD enrichment failed: " + (err.response?.data?.detail || "try again"));
    } finally {
      setCadBusy(false);
    }
  };

  if (error) {
    return (
      <div>
        <Header />
        <main className="max-w-3xl mx-auto px-6 py-20 text-center">
          <h2 className="font-display text-3xl font-semibold">Property not found.</h2>
          <button onClick={() => nav("/dashboard")} className="btn-primary mt-6">
            Back to dashboard
          </button>
        </main>
      </div>
    );
  }

  if (!prop) {
    return (
      <div>
        <Header />
        <main className="max-w-3xl mx-auto px-6 py-20">
          <div className="ai-loader" />
          <p className="text-sm text-ink-secondary mt-3 text-center">Loading property…</p>
        </main>
      </div>
    );
  }

  const grade = prop.ai_grade;
  const score = prop.ai_score;

  return (
    <div>
      <Header />
      <main className="max-w-[1440px] mx-auto px-6 lg:px-10 py-8" data-testid="property-detail">
        <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-ink-secondary hover:text-ink mb-6">
          <ArrowLeft size={14} /> Back to dashboard
        </Link>

        <div className="grid lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            {/* Header card */}
            <div className="swiss-card-strong p-7 fade-up">
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <span className="badge badge-brand">{prop.county}</span>
                <span className="badge badge-muted">{propertyTypeLabel(prop.property_type)}</span>
                {prop.has_back_taxes && (
                  <span className="badge badge-warning">
                    <Warning size={10} weight="fill" /> BACK TAXES
                  </span>
                )}
                {prop.has_hoa_lien && (
                  <span className="badge badge-danger">
                    <Buildings size={10} weight="fill" /> HOA LIEN
                  </span>
                )}
                <span className="badge badge-muted">{taxStatusLabel(prop.tax_status)}</span>
              </div>
              <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tighter leading-[1] text-ink">
                {prop.address}
              </h1>
              <div className="flex items-center gap-1.5 text-base text-ink-secondary mt-3">
                <MapPin size={14} />
                <span>
                  {prop.city}, TX {prop.zip_code || ""}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-default border border-default mt-6">
                {[
                  { label: "Tax Owed", val: fmtUSD(prop.tax_owed), danger: true },
                  { label: "Min Bid", val: fmtUSD(prop.minimum_bid) },
                  { label: "Adj. Value", val: fmtUSD(prop.adjudged_value) },
                  { label: "HOA Lien", val: prop.has_hoa_lien ? fmtUSD(prop.hoa_lien_amount) : "—" },
                ].map((m) => (
                  <div key={m.label} className="bg-white p-4">
                    <div className="overline mb-1.5">{m.label}</div>
                    <div className={"font-mono text-lg font-semibold " + (m.danger ? "text-danger" : "text-ink")}>
                      {m.val}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Insights */}
            <div className="swiss-card-strong overflow-hidden">
              <div className="bg-ai border-b-2 border-brand px-7 py-4 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Sparkle size={20} weight="fill" color="#002FA7" />
                  <div>
                    <div className="overline" style={{ color: "var(--ai-text)" }}>
                      AI Investment Analysis
                    </div>
                    <div className="text-sm font-semibold mt-0.5 text-ink">Claude Sonnet 4.5</div>
                  </div>
                </div>
                {!score && (
                  <button
                    onClick={runAI}
                    disabled={aiBusy}
                    className="btn-primary inline-flex items-center gap-2 text-sm"
                    data-testid="generate-ai-btn"
                  >
                    {aiBusy ? <Spinner size={14} className="animate-spin" /> : <Sparkle size={14} weight="fill" />}
                    {aiBusy ? "Analyzing..." : "Generate Insights"}
                  </button>
                )}
              </div>
              <div className="p-7">
                {aiBusy && (
                  <div>
                    <div className="ai-loader mb-4" />
                    <p className="text-sm text-ink-secondary">
                      Claude is analyzing market context, discount, lien risk, and redemption exposure...
                    </p>
                  </div>
                )}
                {!score && !aiBusy && (
                  <p className="text-sm text-ink-secondary">
                    Click <span className="font-medium">Generate Insights</span> to get an AI-powered
                    investment score, summary, pros, and cons for this property.
                  </p>
                )}
                {score != null && (
                  <div className="space-y-6">
                    <div className="flex items-center gap-6">
                      <div className={"flex flex-col items-center justify-center w-24 h-24 score-" + grade}>
                        <span className="text-[10px] font-bold tracking-widest">GRADE</span>
                        <span className="font-display text-5xl font-bold leading-none">{grade}</span>
                      </div>
                      <div className="flex-1">
                        <div className="overline">Investment Score</div>
                        <div className="font-display text-5xl font-semibold tracking-tighter">
                          {score}
                          <span className="text-ink-tertiary text-2xl">/100</span>
                        </div>
                        <p className="text-sm text-ink-secondary mt-2 max-w-md leading-relaxed">
                          {prop.ai_summary}
                        </p>
                      </div>
                    </div>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <div className="overline mb-3 flex items-center gap-1.5">
                          <CheckCircle size={12} weight="fill" color="#00C853" /> Strengths
                        </div>
                        <ul className="space-y-2">
                          {(prop.ai_pros || []).map((p, i) => (
                            <li key={i} className="text-sm flex gap-2">
                              <span className="text-[#00C853] font-bold mt-0.5">+</span>
                              <span>{p}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <div className="overline mb-3 flex items-center gap-1.5">
                          <XCircle size={12} weight="fill" color="#FF3333" /> Red Flags
                        </div>
                        <ul className="space-y-2">
                          {(prop.ai_cons || []).map((c, i) => (
                            <li key={i} className="text-sm flex gap-2">
                              <span className="text-danger font-bold mt-0.5">−</span>
                              <span>{c}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* CAD Data */}
            <div className="swiss-card-strong overflow-hidden">
              <div className="bg-inverse text-white px-7 py-4 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Stack size={20} weight="duotone" color="#FFFFFF" />
                  <div>
                    <div className="overline" style={{ color: "rgba(255,255,255,0.6)" }}>
                      County Appraisal District
                    </div>
                    <div className="text-sm font-semibold mt-0.5">
                      {prop.cad_data_source || prop.county + " CAD"}
                    </div>
                  </div>
                </div>
                <button
                  onClick={runCAD}
                  disabled={cadBusy}
                  className="btn-primary inline-flex items-center gap-2 text-sm bg-white text-ink hover:bg-[#F4F4F5]"
                  data-testid="cad-enrich-btn"
                >
                  {cadBusy ? <Spinner size={14} className="animate-spin" /> : <House size={14} weight="fill" />}
                  {cadBusy ? "Fetching..." : "Pull Live CAD"}
                </button>
              </div>
              <div className="p-7">
                {cadBusy && (
                  <>
                    <div className="ai-loader mb-3" />
                    <p className="text-sm text-ink-secondary">
                      Hitting {prop.county.replace(" County", "")} CAD eSearch via headless browser. May take 10-15 seconds.
                    </p>
                  </>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-default border border-default">
                  {[
                    { label: "Appraised Value", val: fmtUSD(prop.appraised_value) },
                    { label: "Land Value", val: fmtUSD(prop.land_value) },
                    { label: "Improvement Value", val: fmtUSD(prop.improvement_value) },
                    { label: "Year Built", val: prop.year_built || "—" },
                    { label: "Living Sqft", val: prop.sqft ? fmtNum(prop.sqft) : "—" },
                    { label: "Deed Reference", val: prop.deed_reference || "—" },
                  ].map((m) => (
                    <div key={m.label} className="bg-white p-4">
                      <div className="overline mb-1.5">{m.label}</div>
                      <div className="font-mono text-base font-semibold text-ink">{m.val}</div>
                    </div>
                  ))}
                </div>

                {prop.exemptions && prop.exemptions.length > 0 && (
                  <div className="mt-5">
                    <div className="overline mb-2">Exemptions on file</div>
                    <div className="flex flex-wrap gap-1.5">
                      {prop.exemptions.map((e) => (
                        <span key={e} className="badge badge-success">{e}</span>
                      ))}
                    </div>
                  </div>
                )}

                {(prop.cad_search_url || prop.cad_property_url) && (
                  <div className="mt-5 pt-5 border-t border-default flex flex-col sm:flex-row gap-3 text-sm">
                    {prop.cad_property_url ? (
                      <a
                        href={prop.cad_property_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-outline inline-flex items-center gap-1.5 text-xs"
                        data-testid="cad-property-link"
                      >
                        <LinkSimple size={12} /> Open exact CAD record
                      </a>
                    ) : null}
                    {prop.cad_search_url && (
                      <a
                        href={prop.cad_search_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-outline inline-flex items-center gap-1.5 text-xs"
                        data-testid="cad-search-link"
                      >
                        <LinkSimple size={12} /> Search on {prop.county.replace(" County", "")} CAD
                      </a>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Legal */}
            <div className="swiss-card p-7">
              <div className="overline mb-3 flex items-center gap-1.5">
                <FileText size={12} /> Legal Description
              </div>
              <p className="text-sm leading-relaxed text-ink-secondary font-mono">
                {prop.legal_description || "—"}
              </p>
            </div>
          </div>

          {/* Sidebar */}
          <aside className="lg:col-span-4 space-y-6">
            <div className="swiss-card p-5">
              <div className="overline mb-4">Parcel Information</div>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Parcel ID</dt>
                  <dd className="font-mono font-semibold text-right">{prop.parcel_id}</dd>
                </div>
                {prop.case_number && (
                  <div className="flex justify-between gap-3">
                    <dt className="text-ink-secondary">Case #</dt>
                    <dd className="font-mono text-right">{prop.case_number}</dd>
                  </div>
                )}
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Owner</dt>
                  <dd className="font-medium text-right">{prop.owner}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Acres</dt>
                  <dd className="font-mono text-right">{prop.acres ? fmtNum(prop.acres) : "—"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Year Built</dt>
                  <dd className="font-mono text-right">{prop.year_built || "—"}</dd>
                </div>
              </dl>
            </div>

            <div className="swiss-card p-5">
              <div className="overline mb-4">Sale Information</div>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Sale Date</dt>
                  <dd className="font-medium text-right">{prop.sale_date || "TBD"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Location</dt>
                  <dd className="font-medium text-right">{prop.sale_location || "—"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Tax Owed</dt>
                  <dd className="font-mono font-semibold text-danger text-right">
                    {fmtUSDPrecise(prop.tax_owed)}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-ink-secondary">Min Bid</dt>
                  <dd className="font-mono font-semibold text-right">{fmtUSDPrecise(prop.minimum_bid)}</dd>
                </div>
              </dl>
            </div>

            {(prop.source_url || prop.source_doc) && (
              <div className="swiss-card p-5">
                <div className="overline mb-4">Public Records</div>
                <div className="space-y-2 text-sm">
                  {prop.source_url && (
                    <a
                      href={prop.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 text-brand hover:underline break-all"
                    >
                      <LinkSimple size={12} /> County Tax Office
                    </a>
                  )}
                  {prop.source_doc && (
                    <a
                      href={prop.source_doc}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 text-brand hover:underline break-all"
                    >
                      <FileText size={12} /> Official Notice / Auction
                    </a>
                  )}
                </div>
              </div>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}
