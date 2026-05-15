"use client";

import React from 'react';
import { 
  BarChart3, 
  Calendar, 
  Upload, 
  PlayCircle,
  CheckCircle2,
  Clock
} from 'lucide-react';

export default function ModelVersions() {
  const modelVersions = [
    {
      id: 1,
      name: "Fingerprint CNN",
      version: "v2.3",
      type: "CNN",
      status: "deployed",
      trainedDate: "2026-04-01",
      metrics: [
        { label: "Accuracy", value: "94.2%", icon: BarChart3 },
        { label: "Precision", value: "92.8%", icon: BarChart3 },
        { label: "Recall", value: "91.5%", icon: BarChart3 },
        { label: "F1 Score", value: "92.1%", icon: BarChart3 },
      ]
    },
    {
      id: 2,
      name: "Toolmark Siamese",
      version: "v1.8",
      type: "Siamese",
      status: "ready",
      trainedDate: "2026-04-01",
      metrics: [
        { label: "Accuracy", value: "88.1%", icon: BarChart3 },
        { label: "Precision", value: "87.5%", icon: BarChart3 },
        { label: "Recall", value: "86.2%", icon: BarChart3 },
        { label: "F1 Score", value: "86.8%", icon: BarChart3 },
      ]
    }
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-3xl font-bold text-white tracking-tight">Model Versions</h1>
        <p className="text-sm text-gray-500 font-medium">
          Browse and deploy trained <span className="text-[#b8860b]">model versions</span>
        </p>
      </div>

      {/* Grid Layout for Model Cards */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {modelVersions.map((model) => (
          <div 
            key={model.id} 
            className="bg-[#1e1b16] border border-gray-800/50 rounded-[2.5rem] p-8 shadow-2xl flex flex-col justify-between"
          >
            {/* Card Top: Title and Status Badge */}
            <div className="flex justify-between items-start mb-8">
              <div>
                <h3 className="text-xl font-bold text-white tracking-tight">{model.name}</h3>
                <p className="text-[10px] text-gray-500 uppercase tracking-widest font-black mt-1">
                  {model.version} • {model.type}
                </p>
              </div>
              
              <div className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest flex items-center gap-2 border
                ${model.status === 'deployed' 
                  ? 'bg-green-900/20 border-green-800/50 text-green-500' 
                  : 'bg-amber-900/20 border-amber-800/50 text-[#b8860b]'
                }`}
              >
                <div className={`size-1.5 rounded-full ${model.status === 'deployed' ? 'bg-green-500' : 'bg-[#b8860b]'}`} />
                {model.status}
              </div>
            </div>

            {/* Metrics Grid (4 items) */}
            <div className="grid grid-cols-2 gap-4 mb-8">
              {model.metrics.map((metric, i) => (
                <div 
                  key={i} 
                  className="bg-black/40 border border-gray-800/50 rounded-3xl p-6 flex items-center gap-4 group hover:border-amber-900/30 transition-all"
                >
                  <metric.icon className="size-4 text-amber-700/50 group-hover:text-amber-600 transition-colors" />
                  <div>
                    <p className="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-0.5">
                      {metric.label}
                    </p>
                    <p className="text-sm font-bold text-white">{metric.value}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Card Footer: Date and Action */}
            <div className="pt-6 border-t border-gray-800/50 flex justify-between items-center">
              <div className="flex items-center gap-2 text-gray-500">
                <Calendar className="size-3.5" />
                <span className="text-[10px] font-bold uppercase tracking-widest">Trained {model.trainedDate}</span>
              </div>
              
              <div className="flex items-center gap-3">
                <button className="p-2.5 bg-black rounded-xl border border-gray-800 text-gray-500 hover:text-white transition-all">
                  <Upload className="size-4" />
                </button>
                
                {model.status === 'ready' && (
                  <button className="bg-[#b8860b] hover:bg-amber-600 text-black px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-2 shadow-lg active:scale-95">
                    <PlayCircle className="size-4" />
                    Deploy
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}