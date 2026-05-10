import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Hourglass, Sparkles, Upload, Search, Trash2 } from "lucide-react";

const COUNTRIES = [
  { code: "MR", label: "Mauritanie", labelAr: "موريتانيا" },
  { code: "TN", label: "Tunisie", labelAr: "تونس" },
  { code: "MA", label: "Maroc", labelAr: "المغرب" },
  { code: "DZ", label: "Algérie", labelAr: "الجزائر" },
  { code: "LY", label: "Libye", labelAr: "ليبيا" },
  { code: "FR", label: "France", labelAr: "فرنسا" },
];

const ARABIC_COUNTRIES = ["MR", "TN", "MA", "DZ", "LY"];

export default function Generator() {
  const { t, i18n } = useTranslation();
  const isAr = i18n.resolvedLanguage === "ar";
  const [country, setCountry] = useState("FR");
  const [institutions, setInstitutions] = useState([]);
  const [institutionId, setInstitutionId] = useState("");
  const [meta, setMeta] = useState({ cycles: [], durations: [] });
  const [topic, setTopic] = useState("");
  const [cycle, setCycle] = useState("");
  const [duration, setDuration] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [sources, setSources] = useState("");
  const [language, setLanguage] = useState("fr");
  const [uploadedSources, setUploadedSources] = useState([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState([]);
  const [jurisQuery, setJurisQuery] = useState("");
  const [jurisResults, setJurisResults] = useState([]);
  const [selectedJurisIds, setSelectedJurisIds] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  useEffect(() => { api.get("/meta/options").then((r) => setMeta(r.data)); }, []);
  useEffect(() => { refreshSources(); }, []);

  useEffect(() => {
    api.get(`/institutions?country_code=${country}`).then((r) => {
      setInstitutions(r.data);
      if (r.data.length) setInstitutionId(r.data[0].id);
    });
  }, [country]);

  const refreshSources = () => api.get("/sources").then((r) => setUploadedSources(r.data));

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { toast.error(t("generator.uploadHint")); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/sources/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`Source +${data.extracted_chars.toLocaleString()} ${isAr ? "حرف" : "car."}`);
      await refreshSources();
      setSelectedSourceIds((ids) => [...ids, data.id]);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t("auth.errorGeneric"));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const removeSource = async (id) => {
    await api.delete(`/sources/${id}`);
    setSelectedSourceIds((ids) => ids.filter((x) => x !== id));
    refreshSources();
  };

  const searchJuris = async () => {
    try {
      const { data } = await api.get("/jurisprudences", {
        params: { q: jurisQuery, country: COUNTRIES.find((c) => c.code === country)?.label, limit: 10 },
      });
      setJurisResults(data);
      if (!data.length) toast.info(isAr ? "لا توجد نتائج." : "Aucune jurisprudence trouvée.");
    } catch { toast.error(t("auth.errorGeneric")); }
  };

  const toggleJuris = (id) =>
    setSelectedJurisIds((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  const canSubmit = useMemo(
    () => topic.length >= 4 && institutionId && cycle && duration,
    [topic, institutionId, cycle, duration]
  );

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    // Snapshot de la liste de générations existantes — permet de détecter
    // un livrable créé côté backend même si la connexion HTTP est coupée
    // par le proxy avant que la réponse n'arrive (Claude prend 60-120s).
    let existingIds = [];
    try {
      const { data: existing } = await api.get("/generations");
      existingIds = existing.map((g) => g.id);
    } catch { /* non bloquant */ }

    try {
      const { data } = await api.post("/generations", {
        topic, institution_id: institutionId, cycle, duration, year, sources,
        source_ids: selectedSourceIds.length ? selectedSourceIds : null,
        jurisprudence_ids: selectedJurisIds.length ? selectedJurisIds : null,
        language,
      }, { timeout: 180000 });
      toast.success(t("generator.successToast"));
      nav(`/preview/${data.id}`);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      // Considère comme "connexion interrompue" :
      // - pas de response (axios cancel/timeout/CORS)
      // - response 502/503/504 (proxy K8s coupe à 60s ou amont mort)
      // - response sans detail JSON exploitable
      const isInterrupted = !err?.response
        || [502, 503, 504].includes(status)
        || typeof detail !== "string";

      if (isInterrupted) {
        // Le proxy K8s a coupé la connexion HTTP (>60s). Le backend a peut-être
        // quand même terminé la génération — on tente de la récupérer.
        try {
          await new Promise((r) => setTimeout(r, 3000));
          const { data: latest } = await api.get("/generations");
          const fresh = latest.find((g) => !existingIds.includes(g.id));
          if (fresh) {
            toast.success(isAr ? "تم استرجاع المادة." : "Livrable récupéré.");
            nav(`/preview/${fresh.id}`);
            return;
          }
        } catch { /* on retombe sur l'erreur réseau */ }
        toast.error(
          isAr
            ? "انقطع الاتصال (الخادم بطيء جدا أو خدمة Claude مزدحمة). جرب مجددا خلال دقيقة. إذا تكرّر، تأكد من رصيد Universal Key."
            : "Connexion interrompue ou service IA saturé (>60s). Réessayez dans 1 minute. Si cela persiste, vérifiez le solde Universal Key (Profile → Add Balance) — Claude consomme parfois un crédit même en cas d'erreur 502.",
          { duration: 15000 },
        );
        return;
      }

      const msg = detail || t("auth.errorGeneric");
      if (status === 402) toast.error(msg, { duration: 12000 });
      else if (status === 502) toast.error(msg, { duration: 12000 });
      else toast.error(msg, { duration: 8000 });
    } finally { setLoading(false); }
  };

  const arabicAvailable = ARABIC_COUNTRIES.includes(country);

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <div className="grid lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2">
          <span className="vf-tag">{t("generator.title")}</span>
          <h1 className="vf-serif text-4xl sm:text-5xl mt-4 text-slate-50">
            {t("generator.subtitle")}
          </h1>

          <form onSubmit={submit} className="mt-10 vf-card p-8 space-y-6" data-testid="generator-form">
            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.topicLabel")}</label>
              <input
                data-testid="gen-topic" value={topic} onChange={(e) => setTopic(e.target.value)}
                required minLength={4}
                placeholder={t("generator.topicPlaceholder")}
                className="vf-input w-full mt-2 px-3 py-3"
              />
            </div>
            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.countryLabel")}</label>
                <select data-testid="gen-country" value={country} onChange={(e) => setCountry(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3">
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>{isAr ? c.labelAr : c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.institutionLabel")}</label>
                <select data-testid="gen-institution" value={institutionId}
                  onChange={(e) => setInstitutionId(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3">
                  {institutions.map((i) => (
                    <option key={i.id} value={i.id}>{i.name} — {i.city}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.cycleLabel")}</label>
                <select data-testid="gen-cycle" value={cycle} onChange={(e) => setCycle(e.target.value)} required
                  className="vf-input w-full mt-2 px-3 py-3">
                  <option value="">— —</option>
                  {meta.cycles?.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.durationLabel")}</label>
                <select data-testid="gen-duration" value={duration} onChange={(e) => setDuration(e.target.value)} required
                  className="vf-input w-full mt-2 px-3 py-3">
                  <option value="">— —</option>
                  {meta.durations?.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.yearLabel")}</label>
                <input data-testid="gen-year" type="number" value={year} min={2024} max={2100}
                  onChange={(e) => setYear(parseInt(e.target.value || "0"))}
                  className="vf-input w-full mt-2 px-3 py-3" />
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.languageLabel")}</label>
                <select data-testid="gen-language" value={language} onChange={(e) => setLanguage(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3">
                  <option value="fr">Français</option>
                  <option value="ar" disabled={!arabicAvailable}>
                    {arabicAvailable
                      ? "العربية"
                      : "العربية — MENA"}
                  </option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">{t("generator.sourcesLabel")}</label>
              <textarea data-testid="gen-sources" value={sources} onChange={(e) => setSources(e.target.value)} rows={3}
                placeholder={t("generator.sourcesPlaceholder")}
                className="vf-input w-full mt-2 px-3 py-3 resize-y" />
            </div>

            <div className="border border-[#1E293B] p-5 bg-[#0F1730]">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-xs vf-mono tracking-[0.2em] text-[#D4AF37]/80">{t("generator.uploadLabel")}</div>
                  <p className="text-xs text-slate-500 mt-1">{t("generator.uploadHint")}</p>
                </div>
                <label className="vf-btn-ghost cursor-pointer flex items-center gap-2 text-xs" data-testid="upload-source-btn">
                  <Upload className="w-4 h-4" />
                  {uploading ? "…" : t("common.submit")}
                  <input type="file" accept=".pdf,.docx,.txt" hidden onChange={handleUpload} disabled={uploading} />
                </label>
              </div>
              {uploadedSources.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {uploadedSources.map((s) => (
                    <li key={s.id} className="flex items-center gap-3 text-sm border border-[#1E293B] px-3 py-2">
                      <input type="checkbox" data-testid={`source-cb-${s.id}`}
                        checked={selectedSourceIds.includes(s.id)}
                        onChange={() => setSelectedSourceIds((ids) =>
                          ids.includes(s.id) ? ids.filter((x) => x !== s.id) : [...ids, s.id])}
                        className="accent-[#D4AF37]" />
                      <span className="flex-1 truncate text-slate-200">{s.original_filename}</span>
                      <span className="text-xs text-slate-500">{Math.round(s.size/1024)} Ko</span>
                      <button type="button" onClick={() => removeSource(s.id)}
                        className="text-red-400 hover:text-red-300" data-testid={`source-del-${s.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="border border-[#1E293B] p-5 bg-[#0F1730]">
              <div className="text-xs vf-mono tracking-[0.2em] text-[#D4AF37]/80">{t("nav.analyse")} · RAG</div>
              <div className="flex gap-2 mt-3">
                <input value={jurisQuery} onChange={(e) => setJurisQuery(e.target.value)}
                  placeholder={t("common.search") + "…"}
                  className="vf-input flex-1 px-3 py-2" data-testid="juris-q" />
                <button type="button" onClick={searchJuris} className="vf-btn-ghost flex items-center gap-2" data-testid="juris-search">
                  <Search className="w-4 h-4" /> {t("common.search")}
                </button>
              </div>
              {jurisResults.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {jurisResults.map((j) => (
                    <li key={j.id} className="flex items-start gap-3 border border-[#1E293B] px-3 py-2 text-sm">
                      <input type="checkbox" data-testid={`juris-cb-${j.id}`}
                        checked={selectedJurisIds.includes(j.id)}
                        onChange={() => toggleJuris(j.id)} className="mt-1 accent-[#D4AF37]" />
                      <div className="flex-1">
                        <div className="text-slate-100">{j.title}</div>
                        <div className="text-xs text-slate-500">
                          {j.country}{j.reference ? ` · ${j.reference}` : ""}
                          {j.tags?.length ? ` · ${j.tags.join(", ")}` : ""}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <button type="submit" disabled={!canSubmit || loading} data-testid="gen-submit"
              className="vf-btn-primary w-full inline-flex items-center justify-center gap-3 py-3">
              {loading ? (
                <><Hourglass className="w-4 h-4 vf-spin" /> {t("generator.generating")}</>
              ) : (
                <><Sparkles className="w-4 h-4" /> {t("generator.submit")}</>
              )}
            </button>
            {loading && (
              <p className="text-xs text-slate-400 text-center">
                {t("generator.generating")} — 30-90s.
              </p>
            )}
          </form>
        </div>

        <aside className="space-y-5">
          <div className="vf-frame bg-[#0F1730]/60">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">VITA-FORM</div>
            <ul className="text-sm text-slate-300 mt-4 space-y-2">
              <li>• {t("landing.feat1Body")}</li>
            </ul>
          </div>
          <div className="vf-card p-6">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">{t("preview.unlockTitle")}</div>
            <p className="text-sm text-slate-300 mt-3 leading-relaxed">
              <strong className="text-[#D4AF37]">14,90 €</strong> · PDF / Word / Slides
            </p>
            <p className="text-xs text-slate-500 mt-3 italic">
              PayPal · {t("preview.tabWire")}
            </p>
          </div>
          {language === "ar" && (
            <div className="vf-card p-5 border-[#D4AF37]/40">
              <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-[#D4AF37]/80">اللغة</div>
              <p className="text-slate-200 mt-2 text-sm" dir="rtl">
                سيُحرَّر هذا الملف بالعربية الفصحى مع الحفاظ على الإحالات القانونية الفرنسية الأصلية.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
