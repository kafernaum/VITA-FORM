import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { CheckCircle2, AlertTriangle, Hourglass, ArrowRight } from "lucide-react";

const POLL_INTERVAL_MS = 2500;
const MAX_ATTEMPTS = 16;

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const txnId = params.get("txn_id") || params.get("session_id");
  const [status, setStatus] = useState("polling");
  const [generationId, setGenerationId] = useState(null);
  const attemptsRef = useRef(0);
  const nav = useNavigate();

  useEffect(() => {
    if (!txnId) { setStatus("error"); return; }
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      attemptsRef.current += 1;
      try {
        const { data } = await api.get(`/payments/checkout/status/${txnId}`);
        setGenerationId(data.generation_id);
        if (data.payment_status === "paid") { setStatus("paid"); return; }
        if (data.status === "rejected") { setStatus("expired"); return; }
      } catch {
        if (attemptsRef.current >= MAX_ATTEMPTS) { setStatus("error"); return; }
      }
      if (attemptsRef.current >= MAX_ATTEMPTS) { setStatus("error"); return; }
      setTimeout(poll, POLL_INTERVAL_MS);
    };
    poll();
    return () => { cancelled = true; };
  }, [txnId]);

  return (
    <div className="max-w-2xl mx-auto px-6 md:px-12 py-24">
      <div className="vf-card p-10 text-center" data-testid="payment-success-card">
        {status === "polling" && (
          <>
            <Hourglass className="w-12 h-12 text-[#D4AF37] vf-spin mx-auto" />
            <h1 className="vf-serif text-3xl mt-6 text-slate-50">Vérification du paiement…</h1>
            <p className="text-slate-400 mt-3">
              PayPal nous transmet le statut de votre transaction. Quelques secondes seulement.
            </p>
          </>
        )}
        {status === "paid" && (
          <>
            <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
            <h1 className="vf-serif text-3xl mt-6 text-slate-50">Paiement confirmé</h1>
            <p className="text-slate-300 mt-3">
              Votre livrable est désormais accessible en téléchargement (PDF, Word, Slides).
            </p>
            {generationId && (
              <button
                onClick={() => nav(`/preview/${generationId}`)}
                data-testid="goto-deliverable-btn"
                className="vf-btn-primary mt-8 inline-flex items-center gap-2"
              >
                Accéder au livrable <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </>
        )}
        {status === "expired" && (
          <>
            <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto" />
            <h1 className="vf-serif text-3xl mt-6 text-slate-50">Session expirée</h1>
            <p className="text-slate-400 mt-3">
              La session de paiement Stripe a expiré. Relancez l'opération depuis le livrable.
            </p>
            <Link to="/library" className="vf-btn-ghost mt-8 inline-block" data-testid="back-to-library">
              Retour à la bibliothèque
            </Link>
          </>
        )}
        {status === "error" && (
          <>
            <AlertTriangle className="w-12 h-12 text-red-400 mx-auto" />
            <h1 className="vf-serif text-3xl mt-6 text-slate-50">Statut indéterminé</h1>
            <p className="text-slate-400 mt-3">
              Impossible de récupérer le statut. Si vous avez payé, le webhook Stripe finalisera
              automatiquement le déblocage. Réessayez la page du livrable dans quelques minutes.
            </p>
            <Link to="/library" className="vf-btn-ghost mt-8 inline-block" data-testid="back-to-library-error">
              Retour à la bibliothèque
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
