"use client";

import React from 'react';
import { 
  Database, 
  Zap, 
  CheckCircle, 
  Activity,
  ArrowUpRight,
  TrendingUp,
  Clock,
  MoreVertical
} from 'lucide-react';

export default function AIEngineerDashboard() {
  const stats = [
    { label: "Active Datasets", value: "12", icon: Database },
    { label: "Models Trained", value: "48", icon: Zap },
    { label: "Avg. Accuracy", value: "94.2%", icon: CheckCircle },
    { label: "Active Training", value: "2", icon: Activity },
  ];

  const recentActivity = [
    { 
      title: "Model deployed", 
      subtitle: "Fingerprint CNN v2.3", 
      time: "2 hours ago",
      type: "deployment" 
    },
    { 
      title: "Training completed", 
      subtitle: "Toolmark Siamese v1.8", 
      time: "8 hours ago",
      type: "training" 
    },
    { 
      title: "Dataset uploaded", 
      subtitle: "Fingerprint Set B-402", 
      time: "1 days ago",
      type: "upload" 
    },
    { 
      title: "Training started", 
      subtitle: "Hybrid CNN v2.1", 
      time: "1 days ago",
      type: "training" 
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Header Section */}
      <div className="flex justify-between items-end">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-white tracking-tight">DashBoard</h1>
          <p className="text-sm text-gray-500 font-medium">
            Monitor your <span className="text-[#b8860b]">forensic AI system</span> performance
          </p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-black border border-gray-800 rounded-xl text-[10px] font-black uppercase tracking-widest text-gray-400 hover:text-white transition-all">
            System Logs
          </button>
          <button className="px-4 py-2 bg-[#b8860b] text-black rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-amber-500 transition-all font-bold">
            Model Ops
          </button>
        </div>
      </div>

      {/* 4-Column Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <div 
            key={i} 
            className="bg-[#1e1b16] border border-gray-800/50 p-7 rounded-[2rem] flex flex-col items-center justify-center gap-4 text-center group hover:border-amber-900/40 transition-all shadow-xl"
          >
            <div className="p-3 bg-black/40 rounded-2xl group-hover:scale-110 transition-transform">
              <stat.icon className="size-5 text-amber-600" />
            </div>
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black">{stat.label}</p>
              <h3 className="text-3xl font-bold text-white tracking-tight">{stat.value}</h3>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid: Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Chart 1: Model Accuracy Trend */}
        <div className="bg-[#1e1b16] border border-gray-800/50 p-8 rounded-[2.5rem] space-y-8 shadow-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TrendingUp className="size-4 text-amber-600" />
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-400">Model Accuracy Trend</h3>
            </div>
            <MoreVertical className="size-4 text-gray-700 cursor-pointer" />
          </div>

          <div className="relative h-64 w-full bg-black/20 rounded-3xl p-6 border border-gray-800/30">
            {/* SVG Line Chart */}
            <svg className="w-full h-full overflow-visible" viewBox="0 0 400 200" preserveAspectRatio="none">
              <defs>
                <linearGradient id="lineGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#b8860b" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="#b8860b" stopOpacity="0" />
                </linearGradient>
              </defs>
              {/* The Trend Line */}
              <path 
                d="M 0 180 Q 50 170 100 140 T 200 100 T 300 60 T 400 20" 
                fill="none" 
                stroke="#b8860b" 
                strokeWidth="3"
                strokeLinecap="round"
                className="drop-shadow-[0_0_10px_rgba(184,134,11,0.6)]"
              />
              {/* Data Points */}
              <circle cx="100" cy="140" r="4" fill="#b8860b" />
              <circle cx="300" cy="60" r="4" fill="#b8860b" />
              <circle cx="400" cy="20" r="4" fill="#b8860b" />
            </svg>
            
            {/* Labels */}
            <div className="absolute bottom-4 left-6 right-6 flex justify-between text-[9px] font-black text-gray-600 uppercase tracking-widest">
              <span>Mar 28</span>
              <span>Mar 30</span>
              <span>April 2</span>
            </div>
          </div>
        </div>

        {/* Chart 2: Training Progress */}
        <div className="bg-[#1e1b16] border border-gray-800/50 p-8 rounded-[2.5rem] space-y-8 shadow-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="size-4 text-amber-600" />
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-gray-400">Training Progress</h3>
            </div>
            <div className="px-3 py-1 bg-amber-600/10 border border-amber-600/20 rounded-full text-[9px] font-black text-amber-500 uppercase">Live</div>
          </div>

          <div className="relative h-64 w-full bg-black/20 rounded-3xl p-6 border border-gray-800/30">
            {/* SVG Progress Line */}
            <svg className="w-full h-full overflow-visible" viewBox="0 0 400 200" preserveAspectRatio="none">
              <path 
                d="M 0 200 L 400 20" 
                fill="none" 
                stroke="#b8860b" 
                strokeWidth="2"
                strokeDasharray="8 4"
                className="opacity-30"
              />
              <path 
                d="M 0 200 L 280 74" 
                fill="none" 
                stroke="#b8860b" 
                strokeWidth="4"
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center">
              <p className="text-4xl font-black text-white">70%</p>
              <p className="text-[10px] font-black text-amber-600 uppercase tracking-widest">In Progress</p>
            </div>
          </div>
        </div>

      </div>

      {/* Recent Activity Table */}
      <div className="bg-[#1e1b16] border border-gray-800/50 p-10 rounded-[3rem] shadow-2xl">
        <div className="flex justify-between items-center mb-10">
          <h3 className="text-xs font-black uppercase tracking-[0.3em] text-gray-500">System Activity Logs</h3>
          <button className="text-[10px] font-black uppercase text-amber-600 hover:text-amber-500 transition-colors">View All Logs</button>
        </div>
        
        <div className="space-y-4">
          {recentActivity.map((item, i) => (
            <div 
              key={i} 
              className="flex items-center justify-between p-5 hover:bg-black/40 border border-transparent hover:border-gray-800/50 rounded-[2rem] transition-all group"
            >
              <div className="flex items-center gap-6">
                <div className="size-12 rounded-2xl bg-black border border-gray-800 flex items-center justify-center group-hover:border-amber-900/50 transition-colors">
                  <div className={`size-2.5 rounded-full ${item.type === 'deployment' ? 'bg-green-500' : 'bg-amber-600'} animate-pulse`} />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold text-gray-100 group-hover:text-white transition-colors">{item.title}</p>
                  <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">{item.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <span className="text-[10px] font-black text-gray-600 uppercase tracking-tighter">{item.time}</span>
                <div className="p-2 bg-gray-900/50 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity">
                   <ArrowUpRight className="size-4 text-amber-600" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}