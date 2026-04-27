"use client";
import React, { useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Monitor, Palette, Rocket, Send, ArrowUpRight, Check, MessageCircle, ArrowDown, Mail } from "lucide-react";
import Header from "@/components/Header";
import DynamicBackground from "@/components/DynamicBackground";
import ServiceCard from "@/components/ServiceCard";

gsap.registerPlugin(ScrollTrigger);

const Home = () => {
  useEffect(() => {
    // Tracciamento IP (Visita passiva)
    fetch("/api/track", { method: "POST" }).catch(() => {});

    // Reveal Animations
    const revealElements = document.querySelectorAll(".reveal-up");
    revealElements.forEach((el) => {
      gsap.fromTo(el, 
        { opacity: 0, y: 40, autoAlpha: 0 },
        {
          scrollTrigger: {
            trigger: el,
            start: "top 90%",
            toggleActions: "play none none none",
          },
          opacity: 1,
          y: 0,
          autoAlpha: 1,
          duration: 1,
          ease: "power3.out",
        }
      );
    });

    // Refresh ScrollTrigger after a short delay to ensure correct positioning
    setTimeout(() => {
      ScrollTrigger.refresh();
    }, 500);

    // Parallax for Glass Cards
    gsap.utils.toArray(".glass-card img").forEach((img: any) => {
      gsap.to(img, {
        scrollTrigger: {
          trigger: img,
          start: "top bottom",
          end: "bottom top",
          scrub: true,
        },
        scale: 1.15,
        y: 20,
        ease: "none"
      });
    });

    // Mouse Move Parallax for Hero Images with performance optimization
    let mmContext = gsap.context(() => {
      const handleHeroMouseMove = (e: MouseEvent) => {
        const xPos = (e.clientX / window.innerWidth - 0.5);
        const yPos = (e.clientY / window.innerHeight - 0.5);
        
        gsap.to("#hero-img-1", { 
          x: xPos * 40, 
          y: yPos * 40, 
          rotation: 3 + xPos * 2,
          duration: 2, 
          ease: "power2.out" 
        });
        gsap.to("#hero-img-2", { 
          x: -xPos * 30, 
          y: -yPos * 30, 
          rotation: -6 - xPos * 3,
          duration: 2, 
          ease: "power2.out" 
        });
      };
      window.addEventListener("mousemove", handleHeroMouseMove);
      
      // Cleanup for context
      return () => window.removeEventListener("mousemove", handleHeroMouseMove);
    });

    // Tilt Effect
    const tiltElements = document.querySelectorAll(".glass-card");
    tiltElements.forEach((card) => {
      const handleCardMouseMove = (e: any) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        gsap.to(card, {
          rotateX: (y - centerY) / 20,
          rotateY: (centerX - x) / 20,
          duration: 0.5,
          ease: "power3.out",
        });
      };
      const handleCardMouseLeave = () => {
        gsap.to(card, { rotateX: 0, rotateY: 0, duration: 0.5 });
      };
      card.addEventListener("mousemove", handleCardMouseMove);
      card.addEventListener("mouseleave", handleCardMouseLeave);
    });

    // Hero Title Stagger Animation
    const titleWords = document.querySelectorAll(".hero-title-word");
    gsap.fromTo(titleWords, 
      { opacity: 0, y: 100, filter: "blur(20px)" },
      { 
        opacity: 1, 
        y: 0, 
        filter: "blur(0px)",
        duration: 1.8, 
        stagger: 0.12, 
        ease: "expo.out",
        delay: 0.8
      }
    );

    // Hero Subtitle Stagger Animation
    const subtitleWords = document.querySelectorAll(".hero-subtitle-word");
    gsap.fromTo(subtitleWords, 
      { opacity: 0, x: -30, filter: "blur(5px)" },
      { 
        opacity: 1, 
        x: 0, 
        filter: "blur(0px)",
        duration: 1.2, 
        stagger: 0.03, 
        ease: "power3.out",
        delay: 1.4
      }
    );

    // Tech Stack Parallax
    gsap.utils.toArray(".tech-icon").forEach((icon: any, i) => {
      gsap.to(icon, {
        y: -10,
        repeat: -1,
        yoyo: true,
        duration: 2 + (i * 0.2),
        ease: "sine.inOut"
      });
    });

    return () => {
      mmContext.revert();
      ScrollTrigger.getAll().forEach(t => t.kill());
    };
  }, []);

  const [formSubmitted, setFormSubmitted] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    const form = e.currentTarget;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });
      
      if (response.ok) {
        setFormSubmitted(true);
        form.reset();
        setTimeout(() => setFormSubmitted(false), 5000); // Reset feedback after 5s
      } else {
        const errorData = await response.json();
        alert(`Errore: ${errorData.error || "Riprova più tardi."}`);
      }
    } catch (error) {
      alert("Errore di connessione. Controlla la tua rete.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="relative z-10">
      <DynamicBackground />
      <Header />

      {/* Hero Section */}
      <section className="min-h-screen flex flex-col justify-center relative px-8 md:px-20 pt-20 overflow-hidden" aria-label="Introduzione">
        {/* Subtle Gradient Overlay for depth */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/5 to-white/20 pointer-events-none" />
        
        <div className="max-w-7xl mx-auto w-full relative z-10">
          <div className="reveal-up mb-10">
            <span className="inline-block py-2 px-4 bg-brand/10 text-brand rounded-full text-[10px] font-extrabold tracking-[0.3em] uppercase border border-brand/20">
              Web Creator Freelance | Siti Semplici & Avanzati
            </span>
          </div>

          <h1 className="section-title font-display font-extrabold tracking-tight mb-12 reveal-up">
            <span className="hero-title-word block">IL TUO</span>
            <span className="hero-title-word block italic font-serif text-brand filter brightness-110">SITO</span>
            <span className="hero-title-word block">Senza <span className="text-dark">Limiti.</span></span>
          </h1>

          <div className="grid md:grid-cols-12 gap-10 items-end reveal-up" style={{ transitionDelay: "0.2s" }}>
            <div className="md:col-span-7">
              <p className="text-2xl md:text-3xl text-dark/80 font-light leading-snug max-w-2xl drop-shadow-[0_1px_5px_rgba(255,255,255,0.8)] flex flex-wrap gap-x-2">
                {"Dalla landing page veloce all'app web complessa, trasformo il tuo business in un'esperienza digitale unica. ALLA POTENZA.".split(" ").map((word, i) => (
                  <span key={i} className="hero-subtitle-word inline-block">{word}</span>
                ))}
              </p>
            </div>
            <div className="md:col-span-5 flex md:justify-end">
              <button 
                className="flex items-center gap-4 group cursor-pointer" 
                onClick={() => document.querySelector('#servizi')?.scrollIntoView({ behavior: 'smooth' })}
                aria-label="Scopri i miei servizi"
              >
                <div className="w-16 h-16 rounded-full border-2 border-brand flex items-center justify-center group-hover:bg-brand transition-all duration-500">
                  <ArrowDown className="text-brand group-hover:text-white transition-colors" />
                </div>
                <span className="text-sm font-bold tracking-widest uppercase opacity-40 group-hover:opacity-100">Scopri i Servizi</span>
              </button>
            </div>
          </div>
        </div>

        {/* Floating Motion Elements */}
        <div className="absolute top-[15%] right-[5%] w-80 h-[500px] floating-img rotate-3 hidden lg:block pointer-events-none" id="hero-img-1">
          <img src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop" alt="Abstract 3D Motion Design" className="w-full h-full object-cover rounded-3xl" loading="eager" />
        </div>
        <div className="absolute bottom-[10%] left-[-5%] w-72 h-96 floating-img -rotate-6 hidden lg:block opacity-80 pointer-events-none" id="hero-img-2">
          <img src="https://images.unsplash.com/photo-1633167606207-d840b5070fc2?q=80&w=2564&auto=format&fit=crop" alt="Digital Flow Visualization" className="w-full h-full object-cover rounded-3xl" loading="eager" />
        </div>
      </section>

      {/* Marquee Section */}
      <div className="py-12 border-y border-dark/5 bg-white/40 backdrop-blur-md overflow-hidden whitespace-nowrap">
        <div className="inline-block animate-marquee">
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-brand">Sviluppo Web</span>
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-dark/80 italic font-serif">Design Moderno</span>
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-accent">Soluzioni Custom</span>
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-brand-light italic font-serif">E-commerce</span>
        </div>
        <div className="inline-block animate-marquee">
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-brand">Sviluppo Web</span>
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-dark/80 italic font-serif">Design Moderno</span>
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-accent">Soluzioni Custom</span>
          <span className="text-6xl font-display font-extrabold uppercase px-10 tracking-tighter text-brand-light italic font-serif">E-commerce</span>
        </div>
      </div>

      {/* Chi Sono Section */}
      <section id="chi-sono" className="py-40 px-8 md:px-20 relative overflow-hidden" aria-label="Chi Sono">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-20 items-center">
            <div className="reveal-up">
              <span className="text-brand font-bold uppercase tracking-[0.3em] text-[10px] mb-6 block">Dietro il Codice</span>
              <h2 className="text-6xl md:text-8xl font-display font-extrabold tracking-tighter mb-10 leading-none">
                SONO UN <br /> <span className="text-brand italic font-serif">Creatore Digitale.</span>
              </h2>
              <p className="text-xl md:text-2xl text-dark/60 font-light leading-relaxed mb-8">
                Mi chiamo Andrea e aiuto aziende e professionisti a trasformare le loro idee in realtà digitali concrete. La mia missione è semplice: **costruire il futuro del web, un pixel alla volta**, rendendo la tecnologia accessibile e performante per ogni tipo di business.
              </p>
              <p className="text-lg text-dark/40 leading-relaxed mb-10">
                Non mi considero solo un programmatore, ma un partner strategico. Credo fermamente che un sito web non debba solo essere "bello", ma debba fungere da motore di crescita. Per questo motivo, ogni mia creazione è il risultato di un equilibrio maniacale tra **design d&apos;avanguardia** e **ingegneria del software solida**.
              </p>
              <div className="grid grid-cols-2 gap-8 mb-12">
                <div className="space-y-4">
                  <h4 className="font-bold uppercase tracking-widest text-[10px] text-brand">La mia Filosofia</h4>
                  <p className="text-sm text-dark/50 leading-relaxed">Punto sulla trasparenza e sulla qualità estrema. Se un progetto non aggiunge valore reale al tuo business, non è un progetto finito.</p>
                </div>
                <div className="space-y-4">
                  <h4 className="font-bold uppercase tracking-widest text-[10px] text-brand">Il mio Obiettivo</h4>
                  <p className="text-sm text-dark/50 leading-relaxed">Rendere il web un posto più veloce, sicuro e intuitivo, portando la tecnologia dei colossi del tech alla portata di tutti.</p>
                </div>
              </div>
              <div className="flex gap-10 border-t border-dark/5 pt-10">
                <div>
                  <p className="text-4xl font-display font-bold text-brand tracking-tighter">50+</p>
                  <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Progetti Lanciati</p>
                </div>
                <div>
                  <p className="text-4xl font-display font-bold text-brand tracking-tighter">5 anni</p>
                  <p className="text-[10px] font-extrabold uppercase tracking-widest opacity-30">Esperienza Web</p>
                </div>
              </div>
            </div>
            <div className="relative reveal-up" style={{ transitionDelay: "0.2s" }}>
              <div className="aspect-[3/4] md:aspect-[4/6] bg-brand/10 rounded-[3rem] shadow-2xl overflow-hidden p-3 border border-white/20 -mt-20 md:-mt-32 flex items-center justify-center">
                <div className="text-center p-12">
                   <div className="w-24 h-24 bg-brand/20 rounded-full flex items-center justify-center mx-auto mb-8 animate-pulse">
                      <Monitor className="text-brand w-12 h-12" />
                   </div>
                   <h3 className="text-2xl font-display font-bold text-brand mb-4 uppercase tracking-tighter">Innovazione Digitale</h3>
                   <p className="text-sm text-dark/40 font-medium leading-relaxed">Trasformiamo concetti astratti in infrastrutture software solide e scalabili.</p>
                </div>
              </div>
              {/* Floating Badge */}
              <div className="absolute -bottom-6 -left-6 bg-dark text-white p-8 rounded-3xl shadow-2xl rotate-3">
                <p className="text-[10px] font-bold uppercase tracking-widest opacity-50 mb-2">Disponibile per</p>
                <p className="text-xl font-display font-bold tracking-tight text-brand">Nuovi Progetti</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Servizi Section */}
      <section id="servizi" className="py-40 px-8 md:px-20 relative z-10">
        <div className="max-w-7xl mx-auto">
          {/* Main Service Title Block */}
          <div className="py-12 md:py-20 mb-32 reveal-up text-center relative overflow-hidden group">
            <h2 className="text-5xl md:text-8xl font-display font-extrabold tracking-tighter mb-8 leading-none relative z-10">
              IL TUO SITO <br /> <span className="text-brand italic font-serif">Senza Limiti.</span>
            </h2>
            <p className="text-xl md:text-2xl text-dark/60 font-light max-w-2xl mx-auto relative z-10">
              Dalla <span className="text-dark font-semibold">landing page veloce</span> all&apos;app web complessa, trasformo il tuo business in un&apos;esperienza digitale unica. <span className="text-brand font-bold uppercase tracking-widest text-[10px] block mt-6">Verso la Potenza</span>
            </p>
          </div>

          <div className="mb-24 reveal-up">
            <h2 className="section-title font-display font-extrabold tracking-tighter">SERVIZI<span className="text-brand">.</span></h2>
            <p className="text-xl text-dark/40 max-w-xl mt-6">Soluzioni digitali su misura, dalla landing page elegante all&apos;applicazione web complessa.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-12">
            <ServiceCard 
              icon={<Monitor className="text-brand w-8 h-8" />}
              title="Siti Web Semplici"
              description="Per chi cerca una presenza online chiara e immediata. Landing page e siti vetrina costruiti per caricarsi in meno di 1 secondo, ottimizzati per la conversione e pronti per il mobile."
              tags={["Static Generation (SSG)", "SEO Semantica", "Performance Core Web Vitals"]}
              color="brand"
            />
            <ServiceCard 
              icon={<Rocket className="text-accent w-8 h-8" />}
              title="Sviluppo Avanzato"
              description="Applicazioni web complesse e scalabili. Utilizzo Next.js e React per creare dashboard, e-commerce e sistemi gestionali che gestiscono grandi carichi di dati con facilità."
              tags={["Server Side Rendering (SSR)", "API Integration", "Database Management"]}
              color="accent"
            />
            <ServiceCard 
              icon={<Palette className="text-dark w-8 h-8" />}
              title="Design & UX"
              description="Non mi occupo solo di codice. Progetto interfacce basate sulla psicologia del comportamento per garantire che ogni utente trovi esattamente ciò che cerca, senza frizioni."
              tags={["User Psychology", "Interactive Prototyping", "Design Systems"]}
              color="dark"
            />
          </div>

          {/* Tech Stack Sub-section */}
          <div className="mt-32 reveal-up">
            <p className="text-[10px] font-bold uppercase tracking-[0.3em] opacity-30 mb-10 text-center">Tecnologie che utilizzo</p>
            <div className="flex flex-wrap justify-center gap-8 md:gap-16 opacity-40 grayscale hover:grayscale-0 transition-all duration-500">
                <span className="tech-icon text-2xl font-bold tracking-tighter hover:text-brand cursor-default transition-colors">Next.js 14</span>
                <span className="tech-icon text-2xl font-bold tracking-tighter hover:text-brand cursor-default transition-colors" style={{ transitionDelay: "0.1s" }}>React</span>
                <span className="tech-icon text-2xl font-bold tracking-tighter hover:text-brand cursor-default transition-colors" style={{ transitionDelay: "0.2s" }}>TypeScript</span>
                <span className="tech-icon text-2xl font-bold tracking-tighter hover:text-brand cursor-default transition-colors" style={{ transitionDelay: "0.3s" }}>Tailwind CSS</span>
                <span className="tech-icon text-2xl font-bold tracking-tighter hover:text-brand cursor-default transition-colors" style={{ transitionDelay: "0.4s" }}>GSAP</span>
                <span className="tech-icon text-2xl font-bold tracking-tighter hover:text-brand cursor-default transition-colors" style={{ transitionDelay: "0.5s" }}>Framer Motion</span>
                <span className="tech-icon text-2xl font-bold tracking-tighter hover:text-brand cursor-default transition-colors" style={{ transitionDelay: "0.6s" }}>Node.js</span>
              </div>
          </div>
        </div>
      </section>

      {/* Metodo Section */}
      <section id="metodo" className="py-40 px-8 md:px-20 relative bg-dark text-white overflow-hidden rounded-[4rem] mx-4 my-20">
        <div className="max-w-7xl mx-auto">
          <div className="reveal-up mb-24 text-center">
            <h2 className="section-title font-display font-extrabold tracking-tighter">IL MIO <br /><span className="text-brand italic font-serif">Metodo.</span></h2>
            <p className="text-xl text-white/40 max-w-xl mx-auto mt-6">Dall&apos;idea al lancio: ecco come trasformo la tua visione in realtà.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-12 relative">
            {/* Step 1 */}
            <div className="reveal-up space-y-6 relative z-10">
              <div className="text-7xl font-display font-black text-white/5 absolute -top-10 -left-4">01</div>
              <h3 className="text-2xl font-bold text-brand">Visione</h3>
              <p className="text-white/50 leading-relaxed">Analizzo l&apos;anima del tuo brand per estrarne la traiettoria di crescita. Ogni progetto inizia con una strategia, non con un pixel.</p>
            </div>
            {/* Step 2 */}
            <div className="reveal-up space-y-6 relative z-10" style={{ transitionDelay: "0.1s" }}>
              <div className="text-7xl font-display font-black text-white/5 absolute -top-10 -left-4">02</div>
              <h3 className="text-2xl font-bold text-brand">Distillazione</h3>
              <p className="text-white/50 leading-relaxed">Semplifico la complessità. Creo interfacce che sono estensioni naturali dell&apos;intento dell&apos;utente, riducendo ogni frizione.</p>
            </div>
            {/* Step 3 */}
            <div className="reveal-up space-y-6 relative z-10" style={{ transitionDelay: "0.2s" }}>
              <div className="text-7xl font-display font-black text-white/5 absolute -top-10 -left-4">03</div>
              <h3 className="text-2xl font-bold text-brand">Esplosione</h3>
              <p className="text-white/50 leading-relaxed">Il lancio è solo l&apos;inizio. Ottimizzo le performance per una velocità che non si vede, si sente.</p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-40 px-8 md:px-20">
        <div className="max-w-4xl mx-auto">
          <div className="reveal-up mb-20 text-center">
            <h2 className="text-5xl font-display font-extrabold tracking-tighter mb-6">DOMANDE <span className="text-brand italic font-serif">Frequenti.</span></h2>
          </div>
          <div className="space-y-6">
            <FaqItem 
              question="Quanto tempo ci vuole per un sito?" 
              answer="Dipende dalla complessità. Un sito vetrina semplice può essere pronto in 1-2 settimane, mentre una web app avanzata può richiedere 4-8 settimane."
            />
            <FaqItem 
              question="Il sito sarà ottimizzato per Google?" 
              answer="Assolutamente sì. Utilizzo Next.js che garantisce performance SEO di altissimo livello e una velocità di caricamento imbattibile."
            />
            <FaqItem 
              question="Posso aggiornare i contenuti da solo?" 
              answer="Certamente. Integro CMS (Content Management Systems) intuitivi che ti permettono di modificare testi e immagini in totale autonomia."
            />
          </div>
        </div>
      </section>

      {/* Contatti Section */}
      <section id="contatti" className="py-40 px-8 relative z-20">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-20 items-start">
            <div className="opacity-100 transition-all duration-1000">
              <h2 className="section-title font-display font-extrabold tracking-tighter leading-[0.8] mb-12">
                VUOI UN <br /> <span className="text-brand italic font-serif">Sito Web?</span>
              </h2>
              <p className="text-2xl text-dark/50 font-light leading-snug mb-16 max-w-lg">
                Che tu abbia bisogno di una pagina semplice o di un portale avanzato, sono qui per aiutarti a realizzarlo. Contattami per una consulenza gratuita.
              </p>
              
              <div className="space-y-10">
                <div className="flex items-center gap-6 group cursor-pointer" onClick={() => window.location.href='mailto:sapienzaandrea557@gmail.com'}>
                  <div className="w-14 h-14 rounded-2xl bg-white flex items-center justify-center shadow-lg group-hover:bg-brand group-hover:text-white transition-all duration-500">
                    <Mail className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-[10px] font-extrabold uppercase tracking-[0.3em] opacity-30 mb-1">Email Diretta</p>
                    <p className="text-xl font-bold">sapienzaandrea557@gmail.com</p>
                  </div>
                </div>
                
                <div className="flex items-center gap-6 group cursor-pointer" onClick={() => window.open('https://wa.me/393517473557', '_blank')}>
                  <div className="w-14 h-14 rounded-2xl bg-white flex items-center justify-center shadow-lg group-hover:bg-[#25D366] group-hover:text-white transition-all duration-500">
                    <svg viewBox="0 0 24 24" className="w-6 h-6 fill-current" xmlns="http://www.w3.org/2000/svg">
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                    </svg>
                  </div>
                  <div>
                    <p className="text-[10px] font-extrabold uppercase tracking-[0.3em] opacity-30 mb-1">WhatsApp Rapido</p>
                    <p className="text-xl font-bold">+39 351 747 3557</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-card p-10 md:p-16 opacity-100 transition-all duration-1000 delay-200">
              {!formSubmitted ? (
                <form onSubmit={handleSubmit} className="space-y-8">
                  <div className="grid md:grid-cols-2 gap-8">
                    <div className="space-y-2">
                      <label htmlFor="contact-name" className="text-[10px] font-extrabold uppercase tracking-[0.3em] opacity-30 ml-2">Nome</label>
                      <input id="contact-name" type="text" name="name" required placeholder="Il tuo nome" className="w-full bg-white/50 border border-white/80 rounded-2xl px-6 py-4 outline-none focus:border-brand transition-all font-semibold disabled:opacity-50" disabled={isSubmitting} />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="contact-email" className="text-[10px] font-extrabold uppercase tracking-[0.3em] opacity-30 ml-2">Email</label>
                      <input id="contact-email" type="email" name="email" required placeholder="la-tua@email.it" className="w-full bg-white/50 border border-white/80 rounded-2xl px-6 py-4 outline-none focus:border-brand transition-all font-semibold disabled:opacity-50" disabled={isSubmitting} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="contact-project" className="text-[10px] font-extrabold uppercase tracking-[0.3em] opacity-30 ml-2">Il Tuo Progetto</label>
                    <textarea id="contact-project" name="project" rows={4} required placeholder="Raccontami la tua visione..." className="w-full bg-white/50 border border-white/80 rounded-2xl px-6 py-4 outline-none focus:border-brand transition-all font-semibold resize-none disabled:opacity-50" disabled={isSubmitting}></textarea>
                  </div>
                  <button 
                    type="submit" 
                    className={`group w-full bg-dark text-white rounded-full py-6 font-extrabold uppercase tracking-widest text-xs flex items-center justify-center gap-4 transition-all shadow-xl ${isSubmitting ? 'opacity-70 cursor-wait' : 'hover:bg-brand hover:shadow-brand/20 active:scale-95'}`}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'INVIO IN CORSO...' : 'INVIA PROPOSTA'} 
                    {!isSubmitting && <Send className="w-6 h-6 group-hover:translate-x-2 group-hover:-translate-y-2 transition-transform" />}
                  </button>
                </form>
              ) : (
                <div className="text-center py-20 space-y-6">
                  <div className="w-24 h-24 bg-brand/10 text-brand rounded-full flex items-center justify-center mx-auto mb-10 animate-bounce">
                    <Check className="w-12 h-12" />
                  </div>
                  <h3 className="text-4xl font-display font-extrabold tracking-tighter">Messaggio Inviato!</h3>
                  <p className="text-dark/40 max-w-xs mx-auto">Ti contatterò via email entro 24 ore.</p>
                  <button onClick={() => setFormSubmitted(false)} className="text-brand font-bold uppercase tracking-widest text-xs mt-10 hover:underline">Invia un altro messaggio</button>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-24 text-center border-t border-dark/5 bg-white/40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-8 flex flex-col items-center">
          <div className="mb-12">
            <span className="text-2xl font-display font-extrabold tracking-tighter group cursor-pointer">
              <span className="group-hover:text-brand transition-colors duration-300">STUDIO</span>
              <span className="text-brand group-hover:text-dark transition-colors duration-300">.</span>
              <span className="font-serif italic font-normal text-dark/80 group-hover:text-brand transition-colors duration-300">
                CREATIVE
              </span>
            </span>
          </div>
          <p className="text-sm font-bold uppercase tracking-[0.4em] opacity-30 mb-8">
            © 2026 Creative Engineering Studio - Milano, IT
          </p>
          <div className="text-[14vw] font-display font-black text-dark/[0.03] select-none tracking-tighter uppercase leading-none w-full">
            Digital Craft
          </div>
        </div>
      </footer>

      {/* WhatsApp Fixed */}
      <a href="https://wa.me/393517473557" target="_blank" className="whatsapp-fixed group" aria-label="Chat su WhatsApp">
        <svg viewBox="0 0 24 24" className="w-8 h-8 fill-current" xmlns="http://www.w3.org/2000/svg">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
        </svg>
        <span className="absolute right-20 bg-white text-dark px-4 py-2 rounded-xl text-xs font-bold shadow-xl opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap border border-dark/5">
          Hai una domanda? <span className="text-brand">Chatta ora</span>
        </span>
      </a>

      {/* Back to Top */}
      <button 
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        className="fixed bottom-10 left-10 w-12 h-12 bg-white/80 backdrop-blur-md border border-dark/5 rounded-full flex items-center justify-center shadow-lg hover:bg-brand hover:text-white transition-all z-[50] group"
        aria-label="Torna su"
      >
        <ArrowDown className="rotate-180 group-hover:-translate-y-1 transition-transform" size={20} />
      </button>
    </main>
  );
};

const FaqItem = ({ question, answer }: { question: string; answer: string }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  return (
    <div className="glass-card p-8 cursor-pointer group" onClick={() => setIsOpen(!isOpen)}>
      <div className="flex justify-between items-center">
        <h4 className="text-lg font-bold">{question}</h4>
        <div className={`w-8 h-8 rounded-full border border-dark/10 flex items-center justify-center transition-transform ${isOpen ? "rotate-45" : ""}`}>
          <ArrowUpRight className="w-4 h-4" />
        </div>
      </div>
      <div className={`overflow-hidden transition-all duration-500 ${isOpen ? "max-h-40 mt-6" : "max-h-0"}`}>
        <p className="text-dark/40 leading-relaxed">{answer}</p>
      </div>
    </div>
  );
};

export default Home;
