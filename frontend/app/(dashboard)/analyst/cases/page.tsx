"use client";

import React, { useState } from 'react';
import { Search, Plus, ChevronRight, X, Briefcase } from 'lucide-react';
import Link from 'next/link';

export default function CasesListPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  
  // State for Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedPriority, setSelectedPriority] = useState("all");

  const cases = [
    { 
      id: "CR-2026-001", 
      title: "Store Break-in - Electronics Shop", 
      description: "Fingerprint analysis from commercial break-in",
      status: "In Progress", 
      priority: "High",
      date: "28/04/2026"
    },
    { 
      id: "CR-2026-002", 
      title: "Armed Robbery - Downtown Bank", 
      description: "Fingerprint and toolmark analysis from bank robbery scene",
      status: "Open", 
      priority: "Low",
      date: "30/04/2026"
    },
    { 
      id: "CR-2026-003", 
      title: "Home Invasion - Maple Avenue", 
      description: "Comprehensive evidence analysis for home invasion case",
      status: "Closed", 
      priority: "Medium",
      date: "03/05/2026"
    },
    { 
      id: "CR-2026-004", 
      title: "Burglary Investigation - Street", 
      description: "Fingerprint and toolmark analysis from bank robbery scene",
      status: "In Progress", 
      priority: "Low",
      date: "30/04/2026"
    }
  ];

  // Logic to filter cases based on the 3 inputs
  const filteredCases = cases.filter((c) => {
    const matchesSearch = c.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                         c.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = selectedStatus === "all" || c.status === selectedStatus;
    const matchesPriority = selectedPriority === "all" || c.priority === selectedPriority;
    
    return matchesSearch && matchesStatus && matchesPriority;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "In Progress": return "bg-[#b8c51a]/20 text-[#b8c51a]";
      case "Open": return "bg-blue-500/20 text-blue-400";
      case "Closed": return "bg-green-500/20 text-green-400";
      default: return "bg-gray-500/20 text-gray-400";
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto relative">
      {/* Header Section */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold text-white tracking-tight">Case Management</h1>
        <p className="text-sm text-gray-500">
          Manage and track <span className="text-amber-600">forensic investigations</span>
        </p>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-1 gap-3 max-w-3xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-amber-600/70" />
            <input 
              placeholder="Search by Case name or ID..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-[#1a1610] border border-gray-800 rounded-lg text-sm text-white placeholder:text-gray-600 outline-none focus:border-amber-600/50 transition-all"
            />
          </div>
          
          <select 
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-[#1a1610] border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-400 outline-none cursor-pointer hover:border-gray-700 transition-colors"
          >
            <option value="all">All Statuses</option>
            <option value="Open">Open</option>
            <option value="In Progress">In Progress</option>
            <option value="Closed">Closed</option>
          </select>

          <select 
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
            className="bg-[#1a1610] border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-400 outline-none cursor-pointer hover:border-gray-700 transition-colors"
          >
            <option value="all">All Priorities</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
        
        <button 
          onClick={() => setIsCreateModalOpen(true)}
          className="bg-[#b8860b] hover:bg-amber-600 text-black px-5 py-2.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all uppercase tracking-wider"
        >
          <Plus className="size-4" /> Create Case
        </button>
      </div>

      {/* Case Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredCases.length > 0 ? (
          filteredCases.map((c) => (
            <div key={c.id} className="bg-black border border-gray-800/60 rounded-[32px] p-8 flex flex-col gap-4 relative overflow-hidden group hover:border-amber-900/40 transition-all">
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <h3 className="text-xl font-bold text-white leading-tight">{c.title}</h3>
                  <p className="font-mono text-xs text-amber-500 tracking-widest">{c.id}</p>
                </div>
                <div className="flex gap-2">
                  <span className={`text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full ${getStatusColor(c.status)}`}>
                    {c.status}
                  </span>
                  {c.priority === "High" && (
                    <span className="text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full bg-red-600/20 text-red-500 border border-red-500/20">
                      {c.priority}
                    </span>
                  )}
                </div>
              </div>
              
              <p className="text-sm text-gray-400 font-medium leading-relaxed max-w-[80%]">
                {c.description}
              </p>
              
              <div className="pt-4 border-t border-gray-800/40 flex items-center justify-between">
                <p className="text-[11px] text-gray-500 font-bold uppercase tracking-tighter">
                  Created: <span className="text-gray-400">{c.date}</span>
                </p>
                <Link 
                  href={`/analyst/cases/${c.id}`} 
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#1a1610] text-[#b8860b] text-xs font-bold border border-amber-900/20 hover:bg-amber-900/10 transition-all"
                >
                  View Details <ChevronRight className="size-4" />
                </Link>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full py-20 text-center border-2 border-dashed border-gray-900 rounded-[32px]">
            <p className="text-gray-600 font-medium italic">No investigations match your current filters.</p>
          </div>
        )}
      </div>

      {/* --- CREATE CASE MODAL --- */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div 
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={() => setIsCreateModalOpen(false)}
          />
          
          <div className="relative w-full max-w-lg bg-[#b8860b] rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-8 space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-2xl font-black text-black uppercase tracking-tight">Case Management</h2>
                  <p className="text-sm text-black/70 font-medium">Enter the details for your new forensic investigation case</p>
                </div>
                <button 
                  onClick={() => setIsCreateModalOpen(false)}
                  className="p-1 hover:bg-black/10 rounded-full transition-colors"
                >
                  <X className="size-6 text-black" />
                </button>
              </div>

              <form className="space-y-5">
                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.15em] text-black/80">
                    Case Name
                  </label>
                  <input 
                    type="text"
                    placeholder="eg. Store Break-in - Electronics Shop"
                    className="w-full bg-black/20 border border-black/10 rounded-xl px-4 py-3 text-sm text-black placeholder:text-black/40 outline-none focus:bg-black/30 transition-all"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.15em] text-black/80">
                    Description
                  </label>
                  <textarea 
                    placeholder="Provide detail about the case..."
                    rows={4}
                    className="w-full bg-black/20 border border-black/10 rounded-xl px-4 py-3 text-sm text-black placeholder:text-black/40 outline-none focus:bg-black/30 transition-all resize-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-black uppercase tracking-[0.15em] text-black/80">
                    Evidence Type
                  </label>
                  <div className="relative">
                    <select 
                      defaultValue=""
                      className="w-full bg-black/20 border border-black/10 rounded-xl px-4 py-3 text-sm text-black outline-none appearance-none cursor-pointer"
                    >
                      <option value="" disabled>Select type</option>
                      <option value="fingerprint">Fingerprint Analysis</option>
                      <option value="toolmark">Toolmark Analysis</option>
                      <option value="dna">DNA Profiling</option>
                    </select>
                    <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 size-4 text-black rotate-90 pointer-events-none" />
                  </div>
                </div>

                <div className="flex gap-3 pt-4">
                  <button 
                    type="submit"
                    className="flex-1 bg-black text-[#b8860b] py-3.5 rounded-xl font-black text-xs uppercase tracking-widest hover:bg-black/90 transition-all"
                  >
                    Create Case
                  </button>
                  <button 
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="flex-1 bg-black/10 text-black py-3.5 rounded-xl font-black text-xs uppercase tracking-widest hover:bg-black/20 transition-all border border-black/10"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}