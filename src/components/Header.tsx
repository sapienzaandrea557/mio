"use client";
import React, { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";

const Header = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Home", href: "#" },
    { name: "Chi Sono", href: "#chi-sono" },
    { name: "Servizi", href: "#servizi" },
    { name: "Metodo", href: "#metodo" },
    { name: "Contatti", href: "#contatti" },
  ];

  return (
    <header
      className={`fixed top-0 left-0 w-full z-50 transition-all duration-500 px-8 md:px-16 flex justify-between items-center ${
        isScrolled ? "py-4 bg-white/60 backdrop-blur-2xl shadow-sm" : "py-8"
      }`}
      id="main-header"
    >
      <a href="#" className="text-2xl font-display font-extrabold tracking-tighter group flex items-center" aria-label="Home">
        <span className="group-hover:text-brand transition-colors duration-300">STUDIO</span>
        <span className="text-brand group-hover:text-dark transition-colors duration-300">.</span>
        <span className="font-serif italic font-normal text-dark/80 group-hover:text-brand transition-colors duration-300">
          CREATIVE
        </span>
      </a>

      {/* Desktop Navigation */}
      <nav className="hidden md:flex items-center gap-12 bg-white/40 backdrop-blur-xl px-10 py-4 rounded-full border border-white/50 shadow-sm" aria-label="Menu principale">
        {navLinks.map((link) => (
          <a key={link.name} href={link.href} className="text-xs font-bold uppercase tracking-widest hover:text-brand transition-colors">
            {link.name}
          </a>
        ))}
      </nav>

      <div className="flex items-center gap-6">
        <a
          href="#contatti"
          className="hidden sm:block bg-dark text-white px-8 py-3 rounded-full text-xs font-bold hover:bg-brand transition-all shadow-xl hover:shadow-brand/20 active:scale-95"
        >
          START PROJECT
        </a>
        
        {/* Mobile Menu Toggle */}
        <button 
          className="md:hidden p-2 text-dark hover:text-brand transition-colors"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label={isMobileMenuOpen ? "Chiudi menu" : "Apri menu"}
        >
          {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Navigation Overlay */}
      <div className={`fixed inset-0 bg-white/95 backdrop-blur-xl z-[60] flex flex-col items-center justify-center transition-transform duration-500 md:hidden ${isMobileMenuOpen ? "translate-x-0" : "translate-x-full"}`}>
        <button 
          className="absolute top-8 right-8 p-2 text-dark"
          onClick={() => setIsMobileMenuOpen(false)}
        >
          <X size={32} />
        </button>
        <nav className="flex flex-col items-center gap-8">
          {navLinks.map((link) => (
            <a 
              key={link.name} 
              href={link.href} 
              className="text-3xl font-display font-extrabold tracking-tighter hover:text-brand transition-colors"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {link.name}
            </a>
          ))}
          <a
            href="#contatti"
            className="mt-8 bg-brand text-white px-12 py-4 rounded-full text-sm font-bold shadow-2xl"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            START PROJECT
          </a>
        </nav>
      </div>
    </header>
  );
};

export default Header;
