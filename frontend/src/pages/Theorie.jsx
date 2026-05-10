import { Hourglass, Scale, ShieldAlert, Coins, GraduationCap, Heart } from "lucide-react";
import { Link } from "react-router-dom";

export default function Theorie() {
  return (
    <div className="max-w-6xl mx-auto px-6 md:px-12 py-16">
      <span className="vf-tag" data-testid="theorie-tag">Doctrine</span>
      <h1 className="vf-serif text-4xl sm:text-5xl lg:text-6xl mt-5 text-slate-50">
        La Théorie Vitaliste<br/><span className="italic text-[#D4AF37]">des Finances Publiques</span>
      </h1>
      <p className="text-slate-300 mt-6 max-w-3xl leading-relaxed text-lg">
        Élaborée par le Professeur Ahmed ELY Mustapha (Docteur d'État en Droit public et Finances publiques),
        cette théorie opère une rupture épistémologique avec les paradigmes juridique et économique classiques :
        elle refuse de réduire les deniers de l'État à des agrégats comptables et restitue à chaque euro,
        chaque dirham, chaque dinar sa nature profonde de <strong className="text-[#F3E5AB]">temps de vie humaine confisqué</strong>.
      </p>

      <div className="grid lg:grid-cols-3 gap-6 mt-14">
        <div className="vf-card p-8 lg:col-span-2">
          <Hourglass className="w-7 h-7 text-[#D4AF37]" />
          <div className="vf-serif text-2xl mt-5 text-slate-50">Le postulat fondateur</div>
          <blockquote className="border-l-2 border-[#D4AF37] pl-5 mt-5 text-slate-200 italic leading-relaxed">
            « Les finances publiques sont la somme de tranches de vies humaines traduites en unités monétaires,
            prélevées sur la liberté des personnes à travers leur force de travail confisquée par un prélèvement
            obligatoire pour financer la collectivité nationale. »
          </blockquote>
          <p className="text-slate-400 text-sm mt-5">
            Chaque dépense mal engagée est une vie gaspillée. Chaque acte de corruption est, au sens le plus
            rigoureux du terme, un vol d'âmes.
          </p>
        </div>

        <div className="vf-card p-8 bg-gradient-to-br from-[#1B2542] to-[#0F1730]">
          <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">FORMULE CARDINALE</div>
          <div className="vf-serif text-3xl mt-5 text-slate-50 leading-snug">
            Valeur-Vie<br/>
            <span className="text-[#D4AF37] vf-mono text-base block mt-3">=</span>
            Valeur Monétaire<br/>
            <span className="text-[#D4AF37] vf-mono text-base block mt-1">÷</span>
            Salaire Journalier
          </div>
          <Link to="/analyse" className="vf-btn-primary mt-7 inline-block" data-testid="theorie-cta-calc">
            Lancer un calcul
          </Link>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6 mt-10">
        {[
          { i: ShieldAlert, t: "Corruption = Vol d'âmes", d: "Détourner des fonds publics, c'est voler la vie d'autrui : pas un crime financier mais un crime contre la personne." },
          { i: Heart, t: "Dépense = Restitution", d: "L'État doit rendre la vie prélevée via la santé, l'éducation, la sécurité. Tout autre usage est confiscation." },
          { i: Coins, t: "Dette = Hypothèque vitale", d: "L'endettement public confisque le temps de vie des générations qui ne sont pas encore nées." },
          { i: Scale, t: "Reddition de comptes vitaliste", d: "Le citoyen peut exiger de savoir comment sa vie confisquée est utilisée. C'est un droit nouveau." },
          { i: GraduationCap, t: "Niveau doctoral", d: "VITA-FORM produit des contenus calibrés ENA/ENFIP/INSP, écrits dans la rigueur juridique française." },
          { i: Hourglass, t: "Filiation philosophique", d: "Bachelard, Rawls, Sartre, Einstein. L'avoir et l'être ne sont rien devant le devenir." },
        ].map((p, i) => (
          <div key={p.t} className="vf-card p-7" data-testid={`theorie-pillar-${i}`}>
            <p.i className="w-6 h-6 text-[#D4AF37]" />
            <div className="vf-serif text-xl mt-4 text-slate-50">{p.t}</div>
            <div className="text-sm text-slate-400 mt-3 leading-relaxed">{p.d}</div>
          </div>
        ))}
      </div>

      <div className="mt-16 vf-frame bg-[#0F1730]/60 grid lg:grid-cols-2 gap-10 items-center">
        <img
          src="https://customer-assets.emergentagent.com/job_4b295bcf-9dab-41b7-9ef2-697a4cc68804/artifacts/bkrdomo4_affiche-fr.png"
          alt="Affiche Théorie Vitaliste"
          className="w-full border border-[#D4AF37]/20"
          data-testid="theorie-affiche-img"
        />
        <div>
          <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">SYNTHÈSE VISUELLE</div>
          <h2 className="vf-serif text-3xl mt-4 text-slate-50">Indicateurs de Performance Vitaliste</h2>
          <p className="text-slate-300 mt-5 leading-relaxed">
            Pour chaque domaine de l'action publique (Santé, Éducation, Sécurité), VITA-FORM compare la
            <strong className="text-[#F3E5AB]"> Valeur-Vie engagée</strong> (jours prélevés sur les contribuables) à la
            <strong className="text-[#F3E5AB]"> Valeur-Vie restituée</strong> (années gagnées, capabilités développées,
            libertés protégées). C'est la nouvelle grammaire de la redevabilité publique.
          </p>
          <Link to="/generator" className="vf-btn-primary mt-7 inline-block" data-testid="theorie-cta-generator">
            Générer un cours vitaliste
          </Link>
        </div>
      </div>
    </div>
  );
}
