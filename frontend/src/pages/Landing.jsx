import { Link } from "react-router-dom";
import { ArrowRight, Hourglass, Scale, BookOpenCheck, Sparkles, FileText, Calculator, Building2 } from "lucide-react";

export default function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className="vf-hero relative">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-28 lg:py-40 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 vf-fade-up">
            <span className="vf-tag" data-testid="hero-tag">Plateforme Pédagogique Vitaliste</span>
            <h1 className="vf-serif text-4xl sm:text-5xl lg:text-6xl tracking-tight text-slate-50 mt-6 leading-[1.05]">
              L'argent public est<br/>
              <span className="text-[#D4AF37] italic">du temps de vie.</span>
            </h1>
            <p className="text-base sm:text-lg text-slate-300 mt-6 max-w-2xl leading-relaxed">
              VITA-FORM forme les fonctionnaires, magistrats et apprenants des grandes écoles
              d'administration publique (ENA, ENFIP, INSP) à la Théorie Vitaliste des Finances
              Publiques du Pr. Ahmed ELY Mustapha — un changement de paradigme qui regarde les
              budgets, les lois de finances et les dettes avec les yeux de ceux qui les financent : leurs vies.
            </p>
            <div className="flex flex-wrap gap-4 mt-9">
              <Link to="/generator" className="vf-btn-primary inline-flex items-center gap-2" data-testid="hero-cta-generate">
                Générer un parcours <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/theorie" className="vf-btn-ghost inline-flex items-center gap-2" data-testid="hero-cta-theory">
                Découvrir la théorie
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5 vf-fade-up vf-delay-200">
            <div className="vf-frame bg-[#0F1730]/80 backdrop-blur">
              <div className="flex items-start gap-4">
                <Hourglass className="w-10 h-10 text-[#D4AF37] mt-1" />
                <div>
                  <div className="vf-mono text-[0.7rem] tracking-[0.3em] text-[#D4AF37]/80">FORMULE DE CONVERSION VITALE</div>
                  <div className="vf-serif text-2xl mt-3 text-slate-100">
                    Valeur-Vie = <span className="text-[#D4AF37]">Valeur Monétaire</span> ÷ Salaire Journalier
                  </div>
                  <p className="text-slate-300 mt-4 italic">
                    « On ne manipule pas des chiffres, mais des âmes. »
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-8 text-center">
                {[
                  { l: "12+", s: "années cédées sur 40 ans" },
                  { l: "365", s: "jours-vie de chaque budget" },
                  { l: "∞", s: "générations endettées" },
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

      {/* Pillars */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <span className="vf-tag">Quatre piliers doctrinaux</span>
          <h2 className="vf-serif text-3xl sm:text-4xl lg:text-5xl mt-5 text-slate-50">
            Une rupture épistémologique avec la doctrine classique
          </h2>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mt-14">
          {[
            { icon: Scale, t: "Conversion Vitale", d: "Chaque unité monétaire publique = fraction du temps de vie d'un contribuable." },
            { icon: BookOpenCheck, t: "Reddition Vitaliste", d: "Le citoyen exige de savoir comment sa vie confisquée est utilisée." },
            { icon: Sparkles, t: "Restitution", d: "L'État rend la vie prélevée via santé, éducation, sécurité." },
            { icon: Building2, t: "Hypothèque Future", d: "La dette publique confisque le temps de vie des générations à naître." },
          ].map((p, i) => (
            <div key={p.t} className={`vf-card p-7 vf-fade-up vf-delay-${(i+1)*100}`} data-testid={`pillar-${i}`}>
              <p.icon className="w-7 h-7 text-[#D4AF37]" />
              <div className="vf-serif text-xl mt-5 text-slate-50">{p.t}</div>
              <div className="text-sm text-slate-400 mt-3 leading-relaxed">{p.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Showcase: book + infographic */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 py-12">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <span className="vf-tag">Ouvrage fondateur</span>
            <h2 className="vf-serif text-3xl sm:text-4xl mt-5 text-slate-50">
              Finances Publiques — <span className="italic text-[#D4AF37]">Une Nouvelle Théorie</span>
            </h2>
            <p className="text-slate-300 mt-5 leading-relaxed">
              <em>Entre l'être et l'avoir : les finances publiques à l'aune de la vie humaine.</em>
              Cet ouvrage du Pr. Ahmed ELY Mustapha refonde la discipline des finances publiques
              en intégrant Bachelard, Rawls, Sartre et la relativité einsteinienne pour faire émerger
              une éthique de la vie collective. VITA-FORM en est l'extension pédagogique opérationnelle.
            </p>
            <div className="flex flex-wrap gap-4 mt-8">
              <Link to="/auteur" className="vf-btn-primary" data-testid="showcase-auteur-btn">L'auteur</Link>
              <Link to="/theorie" className="vf-btn-ghost" data-testid="showcase-theorie-btn">La théorie en détail</Link>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-5">
            <img
              src="https://customer-assets.emergentagent.com/job_4b295bcf-9dab-41b7-9ef2-697a4cc68804/artifacts/42tc58ej_RECTO%20HAUTE%20RESOLUTION.png"
              alt="Couverture du livre Finances Publiques - Une Nouvelle Théorie"
              className="w-full border border-[#D4AF37]/30 shadow-2xl shadow-[#D4AF37]/10"
              data-testid="book-cover-img"
            />
            <img
              src="https://customer-assets.emergentagent.com/job_4b295bcf-9dab-41b7-9ef2-697a4cc68804/artifacts/bkrdomo4_affiche-fr.png"
              alt="Infographie Théorie Vitaliste"
              className="w-full border border-[#D4AF37]/30 shadow-2xl shadow-[#D4AF37]/10"
              data-testid="infographic-img"
            />
          </div>
        </div>
      </section>

      {/* Modules */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 py-20">
        <div className="text-center">
          <span className="vf-tag">Trois moteurs</span>
          <h2 className="vf-serif text-3xl sm:text-4xl lg:text-5xl mt-5 text-slate-50">
            De la doctrine au livrable académique
          </h2>
        </div>
        <div className="grid md:grid-cols-3 gap-6 mt-12">
          {[
            { icon: FileText, t: "Génération de cours", d: "Cours, TD, études de cas pour ENA/ENFIP de Mauritanie, Tunisie, Maroc, Algérie, Libye et France.", to: "/generator" },
            { icon: Calculator, t: "Analyse vitaliste pratique", d: "Soumettez budget, convention, dette : obtenez le temps de vie confisqué chiffré.", to: "/analyse" },
            { icon: BookOpenCheck, t: "Bibliothèque personnelle", d: "Aperçus watermarqués, paywall hermétique, exports PDF/Word/Slides académiques.", to: "/library" },
          ].map((m) => (
            <Link to={m.to} key={m.t} className="vf-card p-8 group" data-testid={`module-${m.t.toLowerCase().split(" ")[0]}`}>
              <m.icon className="w-8 h-8 text-[#D4AF37]" />
              <div className="vf-serif text-2xl mt-5 text-slate-50">{m.t}</div>
              <div className="text-sm text-slate-400 mt-3 leading-relaxed">{m.d}</div>
              <div className="mt-6 text-[#D4AF37] inline-flex items-center gap-2 text-sm group-hover:gap-3 transition-all">
                Accéder <ArrowRight className="w-4 h-4" />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
