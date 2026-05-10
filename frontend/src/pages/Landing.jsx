import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Hourglass, Scale, BookOpenCheck, Sparkles, FileText, Calculator, Building2 } from "lucide-react";

export default function Landing() {
  const { t } = useTranslation();
  return (
    <div>
      {/* Hero */}
      <section className="vf-hero relative">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-28 lg:py-40 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 vf-fade-up">
            <span className="vf-tag" data-testid="hero-tag">{t("landing.tag")}</span>
            <h1 className="vf-serif text-4xl sm:text-5xl lg:text-6xl tracking-tight text-slate-50 mt-6 leading-[1.05]">
              {t("landing.title")}
            </h1>
            <p className="text-base sm:text-lg text-slate-300 mt-6 max-w-2xl leading-relaxed">
              {t("landing.subtitle")}
            </p>
            <div className="flex flex-wrap gap-4 mt-9">
              <Link to="/generator" className="vf-btn-primary inline-flex items-center gap-2" data-testid="hero-cta-generate">
                {t("landing.ctaStart")} <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/theorie" className="vf-btn-ghost inline-flex items-center gap-2" data-testid="hero-cta-theory">
                {t("landing.ctaTheory")}
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5 vf-fade-up vf-delay-200">
            <div className="vf-frame bg-[#0F1730]/80 backdrop-blur">
              <div className="flex items-start gap-4">
                <Hourglass className="w-10 h-10 text-[#D4AF37] mt-1" />
                <div>
                  <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">FORMULA · VITALIS</div>
                  <div className="vf-serif text-2xl mt-3 text-slate-100">
                    Valeur-Vie = <span className="text-[#D4AF37]">Valeur Monétaire</span> ÷ Salaire Journalier
                  </div>
                  <p className="text-slate-300 mt-4 italic">
                    {t("footer.quote")}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-8 text-center">
                {[
                  { l: "23+", s: t("landing.stat1") },
                  { l: "5+1", s: t("landing.stat2") },
                  { l: "8+", s: t("landing.stat3") },
                ].map((m) => (
                  <div key={m.l} className="border border-[#D4AF37]/20 p-3">
                    <div className="vf-serif text-2xl text-[#D4AF37]">{m.l}</div>
                    <div className="text-[0.7rem] text-slate-400 mt-1">{m.s}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Modules */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 py-20">
        <div className="grid md:grid-cols-3 gap-6 mt-4">
          {[
            { icon: FileText, t: t("landing.feat1Title"), d: t("landing.feat1Body"), to: "/generator" },
            { icon: Calculator, t: t("landing.feat2Title"), d: t("landing.feat2Body"), to: "/analyse" },
            { icon: BookOpenCheck, t: t("landing.feat3Title"), d: t("landing.feat3Body"), to: "/library" },
          ].map((m) => (
            <Link to={m.to} key={m.t} className="vf-card p-8 group" data-testid={`module-${m.to.replace("/", "")}`}>
              <m.icon className="w-8 h-8 text-[#D4AF37]" />
              <div className="vf-serif text-2xl mt-5 text-slate-50">{m.t}</div>
              <div className="text-sm text-slate-400 mt-3 leading-relaxed">{m.d}</div>
              <div className="mt-6 text-[#D4AF37] inline-flex items-center gap-2 text-sm group-hover:gap-3 transition-all">
                <ArrowRight className="w-4 h-4" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Showcase: book + infographic */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 py-12">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <span className="vf-tag">{t("nav.auteur")}</span>
            <h2 className="vf-serif text-3xl sm:text-4xl mt-5 text-slate-50">
              Finances Publiques — <span className="italic text-[#D4AF37]">Une Nouvelle Théorie</span>
            </h2>
            <p className="text-slate-300 mt-5 leading-relaxed">
              {t("landing.subtitle")}
            </p>
            <div className="flex flex-wrap gap-4 mt-8">
              <Link to="/auteur" className="vf-btn-primary" data-testid="showcase-auteur-btn">{t("nav.auteur")}</Link>
              <Link to="/theorie" className="vf-btn-ghost" data-testid="showcase-theorie-btn">{t("nav.theorie")}</Link>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-5">
            <img
              src="https://customer-assets.emergentagent.com/job_4b295bcf-9dab-41b7-9ef2-697a4cc68804/artifacts/42tc58ej_RECTO%20HAUTE%20RESOLUTION.png"
              alt="Finances Publiques - Une Nouvelle Théorie"
              className="w-full border border-[#D4AF37]/30 shadow-2xl shadow-[#D4AF37]/10"
              data-testid="book-cover-img"
            />
            <img
              src="https://customer-assets.emergentagent.com/job_4b295bcf-9dab-41b7-9ef2-697a4cc68804/artifacts/bkrdomo4_affiche-fr.png"
              alt="VITA-FORM Infographic"
              className="w-full border border-[#D4AF37]/30 shadow-2xl shadow-[#D4AF37]/10"
              data-testid="infographic-img"
            />
          </div>
        </div>
      </section>

      {/* Pillars */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 py-20">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mt-2">
          {[
            { icon: Scale, t: "Conversio Vitalis", d: "Valeur-Vie = Valeur Monétaire ÷ Salaire Journalier." },
            { icon: BookOpenCheck, t: "Reddition", d: t("landing.feat2Body") },
            { icon: Sparkles, t: "Restitutio", d: t("landing.feat3Body") },
            { icon: Building2, t: "Hypothèque", d: t("landing.feat1Body") },
          ].map((p, i) => (
            <div key={p.t} className={`vf-card p-7 vf-fade-up vf-delay-${(i+1)*100}`} data-testid={`pillar-${i}`}>
              <p.icon className="w-7 h-7 text-[#D4AF37]" />
              <div className="vf-serif text-xl mt-5 text-slate-50">{p.t}</div>
              <div className="text-sm text-slate-400 mt-3 leading-relaxed">{p.d}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
