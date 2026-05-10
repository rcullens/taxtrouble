import { Link } from "react-router-dom";
import { ArrowRight, Sparkle, Database, MagnifyingGlass, FileCsv, Buildings } from "@phosphor-icons/react";
import Header from "../components/Header";

export default function Landing() {
  return (
    <div>
      <Header />
      <main>
        {/* Hero */}
        <section className="relative grid-bg border-b border-default">
          <div className="max-w-[1440px] mx-auto px-6 lg:px-10 py-20 lg:py-28">
            <div className="grid lg:grid-cols-12 gap-12 items-start">
              <div className="lg:col-span-7 fade-up">
                <div className="inline-flex items-center gap-2 px-3 py-1.5 swiss-card-strong mb-8">
                  <span className="w-1.5 h-1.5 bg-danger animate-pulse" />
                  <span className="overline">LIVE · 36 Distressed Properties Indexed</span>
                </div>
                <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-semibold tracking-tighter leading-[0.95] text-ink mb-6">
                  Find Texas properties
                  <br />
                  before <span className="text-brand">the auction</span>.
                </h1>
                <p className="text-lg text-ink-secondary max-w-xl leading-relaxed mb-8">
                  Real-time intelligence on tax-delinquent and HOA-lien properties across Texas. Pre-scraped real data from McLennan, Hill, and Bosque counties — plus on-demand scraping for any county you need.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Link to="/register" className="btn-primary inline-flex items-center gap-2" data-testid="landing-cta-primary">
                    Start free <ArrowRight size={16} weight="bold" />
                  </Link>
                  <Link to="/dashboard" className="btn-outline inline-flex items-center gap-2" data-testid="landing-cta-secondary">
                    Browse properties
                  </Link>
                </div>
              </div>

              <div className="lg:col-span-5 fade-up" style={{ animationDelay: "120ms" }}>
                <div className="swiss-card-strong overflow-hidden">
                  <div className="bg-inverse text-white px-5 py-3 flex items-center justify-between">
                    <span className="overline" style={{ color: "rgba(255,255,255,0.6)" }}>
                      Live Index
                    </span>
                    <span className="font-mono text-xs">tx.lien.intel</span>
                  </div>
                  <div className="p-5 space-y-4 bg-subtle">
                    {[
                      { county: "McLennan", count: 15, val: "$182,420", grade: "B" },
                      { county: "Hill", count: 12, val: "$70,827", grade: "A" },
                      { county: "Bosque", count: 9, val: "$82,262", grade: "B" },
                    ].map((r) => (
                      <div key={r.county} className="flex items-center justify-between bg-white border border-default p-3">
                        <div>
                          <div className="overline">{r.county} County</div>
                          <div className="font-display text-lg font-semibold mt-0.5">{r.count} properties</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-sm text-ink-secondary">{r.val}</div>
                          <div className={"badge mt-1 score-" + r.grade}>GRADE {r.grade}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="border-b border-default">
          <div className="max-w-[1440px] mx-auto px-6 lg:px-10 py-20">
            <div className="grid lg:grid-cols-12 gap-10">
              <div className="lg:col-span-4">
                <span className="overline">Capabilities</span>
                <h2 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight mt-3">
                  Built for serious tax-sale investors.
                </h2>
              </div>
              <div className="lg:col-span-8 grid sm:grid-cols-2 gap-px bg-default border border-default">
                {[
                  {
                    icon: <Database size={22} weight="duotone" />,
                    title: "Real public records",
                    desc: "Live scrape of county tax offices, MVBA, GovEase, and trustee notices — not invented data.",
                  },
                  {
                    icon: <Sparkle size={22} weight="duotone" />,
                    title: "AI investment scoring",
                    desc: "Claude-powered analysis grades each property A-F with discount, pros, cons and red flags.",
                  },
                  {
                    icon: <MagnifyingGlass size={22} weight="duotone" />,
                    title: "Natural-language search",
                    desc: '"Show me Waco residentials under $10k with no HOA lien" — translated into filters automatically.',
                  },
                  {
                    icon: <FileCsv size={22} weight="duotone" />,
                    title: "Export everything",
                    desc: "One-click CSV export of filtered results — addresses, parcel IDs, amounts, AI scores.",
                  },
                ].map((f) => (
                  <div key={f.title} className="bg-white p-7">
                    <div className="text-brand mb-4">{f.icon}</div>
                    <h3 className="font-display text-lg font-semibold tracking-tight mb-2">{f.title}</h3>
                    <p className="text-sm text-ink-secondary leading-relaxed">{f.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="bg-inverse text-white">
          <div className="max-w-[1440px] mx-auto px-6 lg:px-10 py-20 grid lg:grid-cols-2 gap-10 items-end">
            <div>
              <span className="overline" style={{ color: "rgba(255,255,255,0.6)" }}>
                Get started
              </span>
              <h2 className="font-display text-4xl sm:text-5xl font-semibold tracking-tighter mt-3">
                The next tax sale is closer than you think.
              </h2>
            </div>
            <div className="flex lg:justify-end gap-3">
              <Link to="/register" className="btn-primary inline-flex items-center gap-2 bg-white text-ink hover:bg-[#F4F4F5]">
                Create an account <ArrowRight size={16} weight="bold" />
              </Link>
              <Link to="/dashboard" className="btn-outline border-white text-white hover:bg-white/10">
                Explore data
              </Link>
            </div>
          </div>
        </section>

        <footer className="border-t border-default">
          <div className="max-w-[1440px] mx-auto px-6 lg:px-10 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-sm text-ink-secondary">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 bg-inverse flex items-center justify-center">
                <Buildings size={14} color="#FFFFFF" weight="fill" />
              </div>
              <span className="font-display font-semibold tracking-tight text-ink">LIEN/TX</span>
            </div>
            <span className="text-xs">
              Data sourced from official Texas county public records. For informational use only.
            </span>
          </div>
        </footer>
      </main>
    </div>
  );
}
