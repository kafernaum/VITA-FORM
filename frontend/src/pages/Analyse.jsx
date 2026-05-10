import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Calculator, Hourglass } from "lucide-react";

const DOC_TYPES = ["Budget", "Convention de prêt", "Bilan", "Loi de finances", "Marché public", "Dette publique", "Autre"];

export default function Analyse() {
  const [salaries, setSalaries] = useState({});
  const [country, setCountry] = useState("FR");
  const [docType, setDocType] = useState("Budget");
  const [title, setTitle] = useState("");
  const [docText, setDocText] = useState("");
  const [amount, setAmount] = useState("");
  const [customSalary, setCustomSalary] = useState("");
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/meta/options").then((r) => setSalaries(r.data.daily_salaries || {}));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/vitalist/analyze", {
        document_type: docType,
        document_text: docText,
        monetary_amount: parseFloat(amount),
        country_code: country,
        daily_salary: customSalary ? parseFloat(customSalary) : null,
        title: title || `Analyse ${docType}`,
      });
      toast.success("Analyse vitaliste produite.");
      nav(`/preview/${data.id}`);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erreur d'analyse.";
      toast.error(msg);
    } finally { setLoading(false); }
  };

  const currentSalary = salaries[country];

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
      <div className="grid lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2">
          <span className="vf-tag">Module Analyse Vitaliste</span>
          <h1 className="vf-serif text-4xl sm:text-5xl mt-4 text-slate-50">
            Calculateur de <span className="italic text-[#D4AF37]">temps de vie confisqué</span>
          </h1>
          <p className="text-slate-300 mt-4 max-w-2xl leading-relaxed">
            Soumettez un document financier réel (budget, convention, dette). VITA-FORM applique la
            formule <span className="vf-mono text-[#F3E5AB]">Valeur-Vie = Montant ÷ Salaire Journalier</span>
            puis confie l'analyse doctrinale à Claude Sonnet 4.5.
          </p>

          <form onSubmit={submit} className="mt-10 vf-card p-8 space-y-5" data-testid="analyse-form">
            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">TYPE DE DOCUMENT</label>
                <select
                  data-testid="ana-doctype"
                  value={docType} onChange={(e) => setDocType(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3"
                >
                  {DOC_TYPES.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">PAYS DE RÉFÉRENCE</label>
                <select
                  data-testid="ana-country"
                  value={country} onChange={(e) => setCountry(e.target.value)}
                  className="vf-input w-full mt-2 px-3 py-3"
                >
                  {Object.entries(salaries).map(([k, v]) => (
                    <option key={k} value={k}>{v.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">INTITULÉ (FACULTATIF)</label>
              <input
                data-testid="ana-title" value={title} onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex. Convention de prêt FMI 2024 — Mauritanie"
                className="vf-input w-full mt-2 px-3 py-3"
              />
            </div>

            <div className="grid sm:grid-cols-2 gap-5">
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">MONTANT EN JEU</label>
                <input
                  data-testid="ana-amount" type="number" step="0.01" min="0" required
                  value={amount} onChange={(e) => setAmount(e.target.value)}
                  placeholder="1000000"
                  className="vf-input w-full mt-2 px-3 py-3"
                />
                {currentSalary && (
                  <div className="text-xs text-slate-500 mt-2">Devise : {currentSalary.currency}</div>
                )}
              </div>
              <div>
                <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">
                  SALAIRE JOURNALIER {currentSalary && `(défaut: ${currentSalary.value} ${currentSalary.currency})`}
                </label>
                <input
                  data-testid="ana-salary" type="number" step="0.01" min="0"
                  value={customSalary} onChange={(e) => setCustomSalary(e.target.value)}
                  placeholder={currentSalary ? `${currentSalary.value}` : "Salaire journalier moyen"}
                  className="vf-input w-full mt-2 px-3 py-3"
                />
              </div>
            </div>

            <div>
              <label className="text-xs vf-mono tracking-[0.2em] text-slate-400">CONTENU DU DOCUMENT</label>
              <textarea
                data-testid="ana-doctext" value={docText} onChange={(e) => setDocText(e.target.value)}
                required minLength={20} rows={9}
                placeholder="Collez ici le texte du budget, de la convention, de l'arrêté de dette..."
                className="vf-input w-full mt-2 px-3 py-3 resize-y vf-mono text-sm"
              />
            </div>

            <button
              type="submit" disabled={loading}
              data-testid="ana-submit"
              className="vf-btn-primary w-full inline-flex items-center justify-center gap-3 py-3"
            >
              {loading ? <><Hourglass className="w-4 h-4 vf-spin" /> Conversion vitaliste…</>
                       : <><Calculator className="w-4 h-4" /> Lancer l'analyse vitaliste</>}
            </button>
          </form>
        </div>

        <aside className="space-y-5">
          <div className="vf-frame bg-[#0F1730]/60">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">FORMULE APPLIQUÉE</div>
            <div className="vf-serif text-2xl mt-4 text-slate-100 leading-snug">
              <span className="text-[#D4AF37]">Valeur-Vie</span> =<br/>Montant ÷ Salaire Journalier
            </div>
            <p className="text-sm text-slate-400 mt-4 leading-relaxed">
              L'unité de résultat est le <strong className="text-[#F3E5AB]">jour-vie humain</strong>, ensuite
              converti en mois et années.
            </p>
          </div>
          <div className="vf-card p-6">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">RAPPORT PRODUIT</div>
            <ul className="text-sm text-slate-300 mt-3 space-y-2">
              <li>• Synthèse classique</li>
              <li>• Re-lecture vitaliste argumentée</li>
              <li>• Tableau chiffré jours/mois/années-vie</li>
              <li>• Indicateurs de Performance Vitaliste</li>
              <li>• Verdict doctrinal</li>
              <li>• Recommandations de réécriture</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
