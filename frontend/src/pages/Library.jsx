import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "@/lib/api";
import { Lock, CheckCircle2, ArrowRight } from "lucide-react";

export default function Library() {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.get("/generations").then((r) => setItems(r.data)).finally(() => setLoading(false)); }, []);

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <span className="vf-tag">{t("library.title")}</span>
      <h1 className="vf-serif text-4xl sm:text-5xl mt-4 text-slate-50">{t("library.title")}</h1>
      <p className="text-slate-400 mt-3 max-w-2xl">
        {t("library.subtitle")}
      </p>

      {loading ? (
        <div className="mt-10 text-slate-400">{t("common.loading")}</div>
      ) : items.length === 0 ? (
        <div className="mt-10 vf-card p-10 text-center">
          <p className="text-slate-300">{t("library.empty")}</p>
          <Link to="/generator" className="vf-btn-primary mt-6 inline-block" data-testid="library-empty-cta">
            {t("landing.ctaStart")}
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-5 mt-10">
          {items.map((it) => (
            <Link key={it.id} to={`/preview/${it.id}`} className="vf-card p-6 group" data-testid={`lib-item-${it.id}`}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className="vf-tag !text-[0.55rem]">
                    {it.kind === "vitalist_analysis" ? t("nav.analyse") : t("nav.generator")}
                  </span>
                  {it.language === "ar" && (
                    <span className="vf-tag !text-[0.55rem] !ml-2 !border-[#D4AF37]/60 !text-[#D4AF37]">AR</span>
                  )}
                  <div className="vf-serif text-xl mt-3 text-slate-50">{it.topic}</div>
                  <div className="text-xs text-slate-400 mt-2">
                    {it.institution_name} · {it.cycle} · {it.duration}
                  </div>
                </div>
                {it.unlocked ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                ) : (
                  <Lock className="w-5 h-5 text-[#D4AF37] shrink-0" />
                )}
              </div>
              <div className="mt-5 text-[#D4AF37] inline-flex items-center gap-2 text-sm group-hover:gap-3 transition-all">
                <ArrowRight className="w-4 h-4" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
