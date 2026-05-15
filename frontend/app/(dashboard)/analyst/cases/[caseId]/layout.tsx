"use client";

import React, { use } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Upload, 
  Fingerprint, 
  History, 
  FileText, 
  LayoutGrid,
  ArrowRightLeft,
  CheckCircle2
} from 'lucide-react';

export default function CaseLayout({ 
  children, 
  params: paramsPromise 
}: { 
  children: React.ReactNode, 
  params: Promise<{ caseId: string }> 
}) {
  // 1. Unwrap the params promise using React.use() for Client Components
  const params = use(paramsPromise);
  const pathname = usePathname();

  // 2. Define tabs with the specific icons from your Figma
  const tabs = [
    { label: "Overview", path: "", icon: LayoutGrid }, // Empty path is the main [caseId] page
    { label: "Upload Evidence", path: "/upload", icon: Upload },
    { label: "result", path: "/analysis", icon: Fingerprint },
    { label: "Cross-Case", path: "/compare", icon: ArrowRightLeft },
    { label: "Reports", path: "/reports", icon: FileText },
    { label: "History", path: "/history", icon: History },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      
      {/* 3. The Navigation Tab Bar (The "Pill" style from your design) */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 bg-black/40 border border-gray-800/60 rounded-2xl w-fit backdrop-blur-md">
        {tabs.map((tab) => {
          const fullPath = `/analyst/cases/${params.caseId}${tab.path}`;
          // Check if active: exact match for overview, startsWith for others
          const isActive = tab.path === "" 
            ? pathname === fullPath 
            : pathname.startsWith(fullPath);

          return (
            <Link 
              key={tab.path}
              href={fullPath}
              className={`flex items-center gap-2.5 px-5 py-2.5 rounded-xl text-[10px] font-bold uppercase tracking-[0.15em] transition-all duration-300 ${
                isActive 
                  ? "bg-amber-600 text-black shadow-lg shadow-amber-900/20" 
                  : "text-gray-500 hover:text-white hover:bg-white/5"
              }`}
            >
              <tab.icon className={`size-3.5 ${isActive ? "text-black" : "text-amber-600/60"}`} />
              {tab.label}
            </Link>
          );
        })}
      </div>

      {/* 4. Page Content Area */}
      <div className="relative">
        {/* Subtle background glow to separate content from sidebar */}
        <div className="absolute -top-20 -left-20 size-64 bg-amber-600/5 blur-[100px] pointer-events-none" />
        
        <div className="relative z-10">
          {children}
        </div>
      </div>
    </div>
  );
}