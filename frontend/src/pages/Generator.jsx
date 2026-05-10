import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Hourglass, Sparkles } from "lucide-react";

const COUNTRIES = [
  { code: "MR", label: "Mauritanie" },
  { code: "TN", label: "Tunisie" },
  { code: "MA", label: "Maroc" },
  { code: "DZ", label: "Algérie" },
  { code: "LY", label: "Libye" },
  { code: "FR", label: "France" },
];

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
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  useEffect(() => { api.get("/meta/options").then((r) => setMeta(r.data)); }, []);

  useEffect(() => {
    api.get(`/institutions?country_code=${country}`).then((r) => {
      setInstitutions(r.data);
      if (r.data.length) setInstitutionId(r.data[0].id);
    });
  }, [country]);

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
      });
      toast.success("Parcours généré.");
      nav(`/preview/${data.id}`);
    } catch (err) {
      const status = err?.response?.status;
      const msg = err?.response?.data?.detail || "Erreur de génération.";
      if (status === 402) toast.error(msg, { duration: 8000 });
      else toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <div className="grid lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2">
          <span className="vf-tag">Moteur de génération</span>
          <h1 className="vf-serif text-4xl sm:text-5xl mt-4 text-slate-50">
            Composez votre <span className="italic text-[#D4AF37]">parcours vitaliste</span>
          </h1>
          <p className="text-slate-300 mt-4 max-w-2xl leading-relaxed">
            VITA-FORM appelle Claude Sonnet 4.5 sous prompt système doctrinal vitaliste. La génération
            est gratuite ; seul le téléchargement déclenche le paywall.
          </p>

          <form onSubmit={submit} className="mt-10 vf-card p-8 space-y-6" data-testid="generator-form">
            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">THÈME / SUJET</label>
              <input
                data-testid="gen-topic"
                value={topic} onChange={(e) => setTopic(e.target.value)} required minLength={4}
                placeholder="Ex. La dette publique mauritanienne sous l'angle vitaliste"
                className="vf-input w-full mt-2 px-3 py-3"
              />
            </div>
            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">PAYS</label>
                <select
                  data-testid="gen-country"
                  value={country} onChange={(e) => setCountry(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3"
                >
                  {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">INSTITUTION</label>
                <select
                  data-testid="gen-institution"
                  value={institutionId} onChange={(e) => setInstitutionId(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3"
                >
                  {institutions.map((i) => (
                    <option key={i.id} value={i.id}>{i.name} — {i.city}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">CYCLE</label>
                <select
                  data-testid="gen-cycle"
                  value={cycle} onChange={(e) => setCycle(e.target.value)} required
                  className="vf-input w-full mt-2 px-3 py-3"
                >
                  <option value="">— Choisir —</option>
                  {meta.cycles?.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">DURÉE</label>
                <select
                  data-testid="gen-duration"
                  value={duration} onChange={(e) => setDuration(e.target.value)} required
                  className="vf-input w-full mt-2 px-3 py-3"
                >
                  <option value="">— Choisir —</option>
                  {meta.durations?.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">ANNÉE ACADÉMIQUE</label>
                <input
                  data-testid="gen-year"
                  type="number" value={year} min={2024} max={2100}
                  onChange={(e) => setYear(parseInt(e.target.value || "0"))}
                  className="vf-input w-full mt-2 px-3 py-3"
                />
              </div>
            </div>
            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">SOURCES À INTÉGRER (OPTIONNEL)</label>
              <textarea
                data-testid="gen-sources"
                value={sources} onChange={(e) => setSources(e.target.value)} rows={4}
                placeholder="Collez ici lois, articles, conventions à utiliser comme corpus de base."
                className="vf-input w-full mt-2 px-3 py-3 resize-y"
              />
            </div>
            <button
              type="submit" disabled={!canSubmit || loading}
              data-testid="gen-submit"
              className="vf-btn-primary w-full inline-flex items-center justify-center gap-3 py-3"
            >
              {loading ? (
                <><Hourglass className="w-4 h-4 vf-spin" /> Génération vitaliste en cours…</>
              ) : (
                <><Sparkles className="w-4 h-4" /> Générer le parcours</>
              )}
            </button>
            {loading && (
              <p className="text-xs text-slate-400 text-center">Premier passage doctrinal puis rédaction académique — comptez 30 à 90 secondes.</p>
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
              <li>• TD corrigé + Étude de cas réelle</li>
              <li>• Scénario de simulation</li>
              <li>• Quiz d'évaluation type ENA</li>
              <li>• Bibliographie 10+ références</li>
              <li>• Réécriture vitaliste finale</li>
            </ul>
          </div>
          <div className="vf-card p-6">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">PAYWALL</div>
            <p className="text-sm text-slate-300 mt-3 leading-relaxed">
              Aperçu watermarqué gratuit. Téléchargement <strong>PDF / Word / Slides</strong> à <strong className="text-[#D4AF37]">14,90 €</strong> par livrable.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
