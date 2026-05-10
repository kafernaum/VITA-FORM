import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, API } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";
import { toast } from "sonner";
import { Lock, Download, FileText, FileType2, Presentation, CheckCircle2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

export default function Preview() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [paying, setPaying] = useState(false);
  const [method, setMethod] = useState("card");

  const load = () => {
    api.get(`/generations/${id}`).then((r) => setDoc(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, [id]);

  const download = async (fmt) => {
    if (!doc?.unlocked) { setPaywallOpen(true); return; }
    try {
      const token = localStorage.getItem("vf_token");
      const res = await fetch(`${API}/generations/${id}/download/${fmt}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Téléchargement refusé");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vitaform-${id.slice(0,8)}.${fmt === "slides" ? "html" : fmt}`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error("Échec du téléchargement.");
    }
  };

  const checkout = async () => {
    setPaying(true);
    try {
      await api.post("/payments/mock-checkout", { generation_id: id, method });
      toast.success("Paiement enregistré. Livrable débloqué.");
      setPaywallOpen(false);
      load();
    } catch (e) {
      toast.error("Paiement échoué.");
    } finally { setPaying(false); }
  };

  if (loading) return <div className="max-w-5xl mx-auto px-6 py-20 text-slate-400">Chargement…</div>;
  if (!doc) return <div className="max-w-5xl mx-auto px-6 py-20 text-slate-400">Livrable introuvable.</div>;

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-12">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <span className="vf-tag" data-testid="preview-kind">
            {doc.kind === "vitalist_analysis" ? "Analyse vitaliste" : "Parcours académique"}
          </span>
          <h1 className="vf-serif text-3xl sm:text-4xl mt-4 text-slate-50">{doc.topic}</h1>
          <div className="text-sm text-slate-400 mt-2">
            {doc.institution_name} · {doc.cycle} · {doc.duration}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {doc.unlocked ? (
            <span className="text-sm text-emerald-300 flex items-center gap-2" data-testid="unlocked-badge">
              <CheckCircle2 className="w-4 h-4" /> Livrable débloqué
            </span>
          ) : (
            <span className="text-sm text-[#D4AF37] flex items-center gap-2" data-testid="locked-badge">
              <Lock className="w-4 h-4" /> Aperçu watermarqué
            </span>
          )}
        </div>
      </div>

      {doc.metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
          {[
            { l: "Montant", v: `${doc.metrics.monetary_amount.toLocaleString("fr-FR")} ${doc.metrics.currency}` },
            { l: "Jours-vie", v: doc.metrics.life_days.toLocaleString("fr-FR") },
            { l: "Mois-vie", v: doc.metrics.life_months.toLocaleString("fr-FR") },
            { l: "Années-vie", v: doc.metrics.life_years.toLocaleString("fr-FR") },
          ].map((m) => (
            <div key={m.l} className="vf-card p-5" data-testid={`metric-${m.l.toLowerCase()}`}>
              <div className="vf-mono text-[0.65rem] tracking-[0.25em] text-[#D4AF37]/80">{m.l.toUpperCase()}</div>
              <div className="vf-serif text-2xl mt-2 text-[#F3E5AB]">{m.v}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-10 grid lg:grid-cols-4 gap-8">
        <article className={`lg:col-span-3 vf-card p-8 ${doc.unlocked ? "" : "vf-watermark"}`}>
          <div
            className="vf-prose relative z-0"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(doc.content) }}
            data-testid="preview-content"
          />
        </article>

        <aside className="space-y-4">
          <div className="vf-frame bg-[#0F1730]/60">
            <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">EXPORTS ACADÉMIQUES</div>
            <div className="space-y-3 mt-5">
              {[
                { fmt: "pdf", icon: FileText, label: "Télécharger PDF" },
                { fmt: "docx", icon: FileType2, label: "Télécharger Word (.docx)" },
                { fmt: "slides", icon: Presentation, label: "Télécharger Slides (HTML)" },
              ].map((b) => (
                <button
                  key={b.fmt} onClick={() => download(b.fmt)}
                  data-testid={`download-${b.fmt}`}
                  className="vf-btn-ghost w-full flex items-center justify-between"
                >
                  <span className="flex items-center gap-2"><b.icon className="w-4 h-4" /> {b.label}</span>
                  {!doc.unlocked && <Lock className="w-3.5 h-3.5" />}
                  {doc.unlocked && <Download className="w-3.5 h-3.5" />}
                </button>
              ))}
            </div>
            {!doc.unlocked && (
              <button
                onClick={() => setPaywallOpen(true)}
                data-testid="open-paywall-btn"
                className="vf-btn-primary w-full mt-6"
              >
                Débloquer · {doc.paywall_price_eur?.toFixed(2)} €
              </button>
            )}
          </div>
        </aside>
      </div>

      <Dialog open={paywallOpen} onOpenChange={setPaywallOpen}>
        <DialogContent className="bg-[#131B33] border border-[#D4AF37]/40 text-slate-100 max-w-md">
          <DialogHeader>
            <DialogTitle className="vf-serif text-2xl text-slate-50">Accès au livrable complet</DialogTitle>
            <DialogDescription className="text-slate-400">
              Le téléchargement PDF / Word / Slides est protégé. Mode démonstration : paiement simulé pour le MVP.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-3">
            <div className="text-sm text-slate-300">Montant : <span className="text-[#D4AF37] vf-mono">{doc.paywall_price_eur?.toFixed(2)} €</span></div>
            <div className="grid grid-cols-2 gap-2">
              {["card", "paypal"].map((m) => (
                <button
                  key={m} onClick={() => setMethod(m)}
                  data-testid={`paywall-${m}`}
                  className={`py-3 border text-sm ${method === m ? "border-[#D4AF37] text-[#D4AF37]" : "border-[#1E293B] text-slate-400"}`}
                >
                  {m === "card" ? "Carte de crédit" : "PayPal"}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-500 italic">
              Production : passerelle PayPal vers <code>ely.mustapha@yahoo.ca</code> (Merchant ID XGYL8NPMKHDUY) ou Stripe Card.
            </p>
          </div>
          <DialogFooter>
            <button onClick={() => setPaywallOpen(false)} className="vf-btn-ghost" data-testid="paywall-cancel">Annuler</button>
            <button onClick={checkout} disabled={paying} className="vf-btn-primary" data-testid="paywall-confirm">
              {paying ? "Traitement…" : "Confirmer le paiement"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
