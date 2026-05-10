import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Hourglass, Sparkles, Upload, X, Search, Trash2 } from "lucide-react";

const COUNTRIES = [
  { code: "MR", label: "Mauritanie" },
  { code: "TN", label: "Tunisie" },
  { code: "MA", label: "Maroc" },
  { code: "DZ", label: "Algérie" },
  { code: "LY", label: "Libye" },
  { code: "FR", label: "France" },
];

const ARABIC_COUNTRIES = ["MR", "TN", "MA", "DZ", "LY"];

export default function Generator() {
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
    if (file.size > 10 * 1024 * 1024) { toast.error("Fichier > 10 Mo"); return; }
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/sources/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`Source ajoutée (${data.extracted_chars.toLocaleString()} car. extraits)`);
      await refreshSources();
      setSelectedSourceIds((ids) => [...ids, data.id]);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Échec upload");
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
      if (!data.length) toast.info("Aucune jurisprudence trouvée pour cette requête.");
    } catch { toast.error("Recherche impossible"); }
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
    try {
      const { data } = await api.post("/generations", {
        topic, institution_id: institutionId, cycle, duration, year, sources,
        source_ids: selectedSourceIds.length ? selectedSourceIds : null,
        jurisprudence_ids: selectedJurisIds.length ? selectedJurisIds : null,
        language,
      });
      toast.success("Parcours généré.");
      nav(`/preview/${data.id}`);
    } catch (err) {
      const status = err?.response?.status;
      const msg = err?.response?.data?.detail || "Erreur de génération.";
      if (status === 402) toast.error(msg, { duration: 8000 });
      else toast.error(msg);
    } finally { setLoading(false); }
  };

  const arabicAvailable = ARABIC_COUNTRIES.includes(country);

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <div className="grid lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2">
          <span className="vf-tag">Moteur de génération</span>
          <h1 className="vf-serif text-4xl sm:text-5xl mt-4 text-slate-50">
            Composez votre <span className="italic text-[#D4AF37]">parcours vitaliste</span>
          </h1>
          <p className="text-slate-300 mt-4 max-w-2xl leading-relaxed">
            Téléversez vos PDF/DOCX, sélectionnez des jurisprudences indexées, choisissez la langue.
            VITA-FORM passe l'ensemble au crible doctrinal.
          </p>

          <form onSubmit={submit} className="mt-10 vf-card p-8 space-y-6" data-testid="generator-form">
            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">THÈME / SUJET</label>
              <input
                data-testid="gen-topic" value={topic} onChange={(e) => setTopic(e.target.value)}
                required minLength={4}
                placeholder="Ex. La dette publique mauritanienne sous l'angle vitaliste"
                className="vf-input w-full mt-2 px-3 py-3"
              />
            </div>
            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">PAYS</label>
                <select data-testid="gen-country" value={country} onChange={(e) => setCountry(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3">
                  {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">INSTITUTION</label>
                <select data-testid="gen-institution" value={institutionId}
                  onChange={(e) => setInstitutionId(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3">
                  {institutions.map((i) => (
                    <option key={i.id} value={i.id}>{i.name} — {i.city}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">CYCLE</label>
                <select data-testid="gen-cycle" value={cycle} onChange={(e) => setCycle(e.target.value)} required
                  className="vf-input w-full mt-2 px-3 py-3">
                  <option value="">— Choisir —</option>
                  {meta.cycles?.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">DURÉE</label>
                <select data-testid="gen-duration" value={duration} onChange={(e) => setDuration(e.target.value)} required
                  className="vf-input w-full mt-2 px-3 py-3">
                  <option value="">— Choisir —</option>
                  {meta.durations?.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">ANNÉE ACADÉMIQUE</label>
                <input data-testid="gen-year" type="number" value={year} min={2024} max={2100}
                  onChange={(e) => setYear(parseInt(e.target.value || "0"))}
                  className="vf-input w-full mt-2 px-3 py-3" />
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">LANGUE DE RÉDACTION</label>
                <select data-testid="gen-language" value={language} onChange={(e) => setLanguage(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3">
                  <option value="fr">Français</option>
                  <option value="ar" disabled={!arabicAvailable}>
                    {arabicAvailable
                      ? "العربية (arabe)"
                      : "العربية (arabe) — pays MENA uniquement"}
                  </option>
                </select>
              </div>
            </div>

            {/* Sources libres */}
            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">SOURCES LIBRES (TEXTE COLLÉ)</label>
              <textarea data-testid="gen-sources" value={sources} onChange={(e) => setSources(e.target.value)} rows={3}
                placeholder="Collez ici lois, articles, conventions..."
                className="vf-input w-full mt-2 px-3 py-3 resize-y" />
            </div>

            {/* Upload PDF/DOCX */}
            <div className="border border-[#1E293B] p-5 bg-[#0F1730]">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-xs vf-mono tracking-[0.2em] text-[#D4AF37]/80">SOURCES TÉLÉVERSÉES</div>
                  <p className="text-xs text-slate-500 mt-1">PDF, DOCX, TXT — 10 Mo max. Texte extrait automatiquement.</p>
                </div>
                <label className="vf-btn-ghost cursor-pointer flex items-center gap-2 text-xs" data-testid="upload-source-btn">
                  <Upload className="w-4 h-4" />
                  {uploading ? "Envoi…" : "Téléverser"}
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

            {/* Jurisprudence search */}
            <div className="border border-[#1E293B] p-5 bg-[#0F1730]">
              <div className="text-xs vf-mono tracking-[0.2em] text-[#D4AF37]/80">JURISPRUDENCE / CORPUS JURIDIQUE</div>
              <p className="text-xs text-slate-500 mt-1">Recherche full-text dans le corpus VITA-FORM (admin).</p>
              <div className="flex gap-2 mt-3">
                <input value={jurisQuery} onChange={(e) => setJurisQuery(e.target.value)}
                  placeholder="Ex. dette souveraine, marchés publics, LOLF…"
                  className="vf-input flex-1 px-3 py-2" data-testid="juris-q" />
                <button type="button" onClick={searchJuris} className="vf-btn-ghost flex items-center gap-2" data-testid="juris-search">
                  <Search className="w-4 h-4" /> Chercher
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
                <><Hourglass className="w-4 h-4 vf-spin" /> Génération vitaliste en cours…</>
              ) : (
                <><Sparkles className="w-4 h-4" /> Générer le parcours</>
              )}
            </button>
            {loading && (
              <p className="text-xs text-slate-400 text-center">
                Compilation doctrinale puis rédaction académique — 30 à 90 secondes.
              </p>
            )}
          </form>
        </div>

        <aside className="space-y-5">
          <div className="vf-frame bg-[#0F1730]/60">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">LIVRABLES INCLUS</div>
            <ul className="text-sm text-slate-300 mt-4 space-y-2">
              <li>• Plan général + volumes horaires</li>
              <li>• Cadrage doctrinal vitaliste</li>
              <li>• Cours académique principal</li>
              <li>• TD corrigé + Étude de cas</li>
              <li>• Scénario de simulation</li>
              <li>• Quiz d'évaluation type ENA</li>
              <li>• Bibliographie 10+ références</li>
              <li>• Réécriture vitaliste finale</li>
            </ul>
          </div>
          <div className="vf-card p-6">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">PAYWALL</div>
            <p className="text-sm text-slate-300 mt-3 leading-relaxed">
              Aperçu watermarqué gratuit. Téléchargement <strong>PDF / Word / Slides</strong> à <strong className="text-[#D4AF37]">14,90 €</strong>.
            </p>
            <p className="text-xs text-slate-500 mt-3 italic">
              Carte Stripe test : 4242 4242 4242 4242 + date future + CVC.
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
