"use client";

import React from 'react';
import { 
  Shield, 
  Search, 
  BarChart4, 
  FileText, 
  ArrowRight,
  Database,
  Cpu,
  Fingerprint
} from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="bg-[#0a0a0a] text-white selection:bg-[#b8860b] selection:text-black">
      {/* 1. HERO SECTION */}
      <section className="relative min-height-[90vh] flex flex-col items-center justify-center text-center px-6 overflow-hidden">
        {/* Background Overlay (matches your design with bullet casings) */}
        <div className="absolute inset-0 opacity-40 grayscale pointer-events-none">
           <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0a]/20 via-[#0a0a0a]/80 to-[#0a0a0a]" />
           <img 
            src="/hero-background.jpg" // Placeholder for your bullet/forensic background
            className="w-full h-full object-cover"
            alt="Forensic Background"
           />
        </div>

        <nav className="absolute top-0 w-full py-8 flex justify-center gap-12 text-[10px] font-black uppercase tracking-[0.3em] text-gray-400">
          <a href="#features" className="hover:text-[#b8860b] transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-[#b8860b] transition-colors">How It Works</a>
          <a href="#about" className="hover:text-[#b8860b] transition-colors">About</a>
          <button className="bg-[#b8860b] text-black px-6 py-2 rounded-lg -mt-2">Login</button>
        </nav>

        <div className="relative z-10 max-w-4xl space-y-6">
          <h1 className="text-5xl md:text-7xl font-light tracking-tight italic">
            AI-Optimized <span className="text-[#b8860b] font-bold not-italic">Fingerprint</span> <br />
            and <span className="text-[#b8860b] font-bold not-italic">Tool-Mark</span> Analysis
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto font-medium leading-relaxed">
            Revolutionize forensic evidence analysis with advanced neural networks. 
            <span className="text-[#b8860b]"> ForensicEdge</span> helps investigators analyze fingerprints 
            and tool marks using intelligent image processing and deep learning technology.
          </p>
          <button className="mt-8 bg-[#b8860b] hover:bg-amber-600 text-black px-10 py-4 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-2xl shadow-amber-900/20">
            Get Started
          </button>
        </div>
      </section>

      {/* 2. ADVANCED FEATURES SECTION (Gritty Grid) */}
      <section id="features" className="py-24 px-6 bg-[#0a0a0a] relative">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold mb-4">Advanced Features for <span className="text-[#b8860b]">Modern Forensics</span></h2>
            <p className="text-gray-500 font-bold uppercase tracking-widest text-[10px]">Cutting-edge AI technology designed to assist forensic analysts</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FeatureCard 
              title="Automated Feature Extraction"
              description="Advanced computer vision automatically detects fingerprint minutiae, ridge patterns, and tool-mark characteristics."
              icon={<Fingerprint className="size-6" />}
            />
            <FeatureCard 
              title="Smart Forensic Reports"
              description="Generate structured analysis reports with visual comparisons and similarity scores, helping investigators document findings."
              icon={<FileText className="size-6" />}
              highlight
            />
            <FeatureCard 
              title="Secure Evidence Chain"
              description="Evidence files and analysis results are securely stored and organized, allowing investigators to maintain reliable records."
              icon={<Shield className="size-6" />}
              highlight
            />
            <FeatureCard 
              title="AI-Powered Evidence Matching"
              description="Deep learning models compare forensic samples and identify similarities to find potential matches quickly."
              icon={<Cpu className="size-6" />}
            />
          </div>
        </div>
      </section>

      {/* 3. HOW IT WORKS SECTION (Numbered Steps) */}
      <section id="how-it-works" className="py-24 px-6 bg-black">
        <div className="max-w-6xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-12">How <span className="text-[#b8860b]">ForensicEdge</span> Works</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <Step number="1" title="Evidence Upload" description="Upload fingerprint or tool-mark images through the platform." />
            <Step number="2" title="AI Feature Analysis" description="AI models analyze images, extracting key forensic features." active />
            <Step number="3" title="Evidence Comparison" description="Siamese networks compare samples and calculate similarity scores." />
            <Step number="4" title="Report Generation" description="System generates structured reports for investigators." />
          </div>
        </div>
      </section>
    </div>
  );
}

// Sub-components to keep code clean
function FeatureCard({ title, description, icon, highlight = false }) {
  return (
    <div className={`p-10 rounded-[2.5rem] border transition-all duration-500 group ${
      highlight ? 'bg-[#b8860b] text-black border-transparent' : 'bg-[#1e1b16] border-gray-800/50 text-white'
    }`}>
      <div className={`mb-6 ${highlight ? 'text-black' : 'text-[#b8860b]'}`}>
        {icon}
      </div>
      <h3 className="text-xl font-bold mb-4">{title}</h3>
      <p className={`text-sm leading-relaxed ${highlight ? 'text-black/70' : 'text-gray-500'}`}>
        {description}
      </p>
    </div>
  );
}

function Step({ number, title, description, active = false }) {
  return (
    <div className="space-y-6 group">
      <div className={`size-16 mx-auto rounded-2xl flex items-center justify-center text-2xl font-black transition-all ${
        active ? 'bg-[#b8860b] text-black shadow-xl shadow-amber-900/40' : 'bg-[#1e1b16] text-[#b8860b] border border-gray-800'
      }`}>
        {number}
      </div>
      <h4 className="font-bold text-lg">{title}</h4>
      <p className="text-gray-500 text-xs leading-relaxed px-4">{description}</p>
    </div>
  );
}