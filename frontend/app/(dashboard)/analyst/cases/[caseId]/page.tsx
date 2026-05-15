import React from 'react';
import { 
  User, 
  Calendar,
  FileSearch,
  ShieldCheck,
  Briefcase
} from 'lucide-react';
import { notFound } from 'next/navigation';

export default async function CaseOverviewPage({ 
  params 
}: { 
  params: Promise<{ caseId: string }> 
}) {
  // 1. Await the params (Required for Next.js 14/15)
  const { caseId } = await params;

  // 2. Data source (Matches your main list)
  const allCases = [
    { 
      id: "CR-2026-001", 
      title: "Store Break-in - Electronics Shop", 
      description: "Fingerprint analysis from commercial break-in. Multiple surfaces swept for latent prints including the main register and back exit.",
      status: "In Progress", 
      priority: "High",
      investigator: "Meti Jemal",
      date: "28/04/2026"
    },
    { 
      id: "CR-2026-002", 
      title: "Armed Robbery - Downtown Bank", 
      description: "Fingerprint and toolmark analysis from bank robbery scene. High-priority case involving federal coordination.",
      status: "Open", 
      priority: "High",
      investigator: "Abebe Kebede",
      date: "30/04/2026"
    },
    { 
      id: "CR-2026-003", 
      title: "Home Invasion - Maple Avenue", 
      description: "Comprehensive evidence analysis for home invasion case involving forced entry and DNA retrieval.",
      status: "Closed", 
      priority: "Medium",
      investigator: "Meron Tilahun",
      date: "03/05/2026"
    }
  ];

  // 3. Find case (Case-insensitive check to prevent 404s)
  const caseData = allCases.find(c => c.id.toLowerCase() === caseId.toLowerCase());

  // 4. Fallback: If ID is not in list, show a generic version instead of 404ing
  const displayData = caseData || {
    id: caseId.toUpperCase(),
    title: "Unknown Case File",
    description: "The details for this specific case are currently being indexed or are unavailable in the mock database.",
    status: "In Review",
    priority: "Low",
    investigator: "System Assigned",
    date: "Pending"
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Case Header Card - Matching Figma image_086fdb.png style */}
      <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-10 shadow-2xl">
        <div className="flex flex-col md:flex-row justify-between items-start gap-6 mb-8">
          <div className="space-y-2">
             <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-600/10 rounded-lg">
                    <Briefcase className="size-5 text-amber-500" />
                </div>
                <p className="font-mono text-amber-500 text-sm tracking-[0.3em] uppercase">{displayData.id}</p>
             </div>
            <h1 className="text-4xl font-bold text-white tracking-tight">{displayData.title}</h1>
          </div>
          
          <div className="flex gap-3">
             <span className="px-4 py-1.5 bg-[#b8c51a]/10 text-[#b8c51a] text-[11px] font-bold uppercase tracking-widest rounded-full border border-[#b8c51a]/20">
               {displayData.status}
             </span>
             <span className={`px-4 py-1.5 text-[11px] font-bold uppercase tracking-widest rounded-full border ${
               displayData.priority === 'High' 
               ? 'bg-red-500/10 text-red-500 border-red-500/20' 
               : 'bg-gray-500/10 text-gray-500 border-gray-500/20'
             }`}>
               {displayData.priority} Priority
             </span>
          </div>
        </div>

        {/* Triple Info Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-8 border-t border-gray-800/50">
          <div className="flex items-center gap-4">
            <div className="size-10 rounded-full bg-gray-900 border border-gray-800 flex items-center justify-center">
                <User className="size-5 text-gray-400" />
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase font-black tracking-tighter">Primary Investigator</p>
              <p className="text-base text-gray-200 font-semibold">{displayData.investigator}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="size-10 rounded-full bg-gray-900 border border-gray-800 flex items-center justify-center">
                <Calendar className="size-5 text-gray-400" />
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase font-black tracking-tighter">Case Registered</p>
              <p className="text-base text-gray-200 font-semibold">{displayData.date}</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="size-10 rounded-full bg-gray-900 border border-gray-800 flex items-center justify-center">
                <ShieldCheck className="size-5 text-gray-400" />
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase font-black tracking-tighter">Encryption</p>
              <p className="text-base text-green-500 font-semibold uppercase text-[12px]">AES-256 Active</p>
            </div>
          </div>
        </div>
      </div>

      {/* Description Box */}
      <div className="bg-black/40 border border-gray-800/60 rounded-2xl p-8 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-4">
            <FileSearch className="size-4 text-amber-600" />
            <h3 className="text-white font-bold text-xs uppercase tracking-[0.2em]">Investigation Brief</h3>
        </div>
        <p className="text-gray-400 text-base leading-relaxed font-medium">
          {displayData.description}
        </p>
      </div>
    </div>
  );
}