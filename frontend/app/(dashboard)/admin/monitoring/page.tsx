"use client";

import { useState, useEffect } from "react";
import { 
  Activity, 
  Cpu, 
  Database, 
  HardDrive, 
  Zap, 
  CheckCircle2, 
  AlertCircle,
  Clock,
  ChevronDown
} from "lucide-react";
import { Button } from "@/components/ui/button";

const SYSTEM_STATUS = [
  { name: "Backend Server", status: "Online", color: "text-green-500", icon: <CheckCircle2 className="size-4" /> },
  { name: "Database", status: "Connected", color: "text-green-500", icon: <CheckCircle2 className="size-4" /> },
  { name: "AI Model", status: "Active", color: "text-green-500", icon: <CheckCircle2 className="size-4" /> },
  { name: "Cache Service", status: "Degraded", color: "text-orange-500", icon: <AlertCircle className="size-4" /> },
];

export default function SystemMonitoring() {
  const [cpuUsage, setCpuUsage] = useState(42);

  useEffect(() => {
    const interval = setInterval(() => {
      setCpuUsage(prev => Math.max(30, Math.min(prev + (Math.random() * 10 - 5), 85)));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">System Monitoring</h1>
        <p className="text-gray-400 mt-1">Real-time system performance and health metrics</p>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "CPU Usage", val: `${cpuUsage.toFixed(1)}%`, icon: <Cpu />, color: "text-amber-500" },
          { label: "Memory Usage", val: "64%", icon: <Activity />, color: "text-blue-500" },
          { label: "Storage Usage", val: "82%", icon: <HardDrive />, color: "text-purple-500" },
          { label: "API Response", val: "124ms", icon: <Zap />, color: "text-green-500" },
        ].map((stat, i) => (
          <div key={i} className="bg-[#1a1614] border border-gray-800 p-6 rounded-2xl flex flex-col items-center gap-3">
            <div className={`${stat.color} bg-white/5 p-3 rounded-xl`}>{stat.icon}</div>
            <p className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">{stat.label}</p>
            <p className="text-2xl font-bold text-white">{stat.val}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* CPU Trend - Fixed height class here */}
        <div className="lg:col-span-2 bg-[#1a1614] border border-gray-800 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-6">CPU Usage Trend (24h)</h3>
          <div className="h-[200px] flex items-end gap-2 px-2">
            {[40, 60, 45, 90, 70, 30, 55, 80, 40, 60].map((h, i) => (
              <div 
                key={i} 
                className="flex-1 bg-[#a37c53]/20 border-t-2 border-[#a37c53] rounded-t-sm transition-all duration-500 hover:bg-[#a37c53]/40 cursor-help"
                style={{ height: `${h}%` }}
              />
            ))}
          </div>
          <div className="flex justify-between mt-4 text-[10px] font-mono text-gray-600">
            <span>00:00</span><span>04:00</span><span>08:00</span><span>12:00</span><span>16:00</span>
          </div>
        </div>

        {/* System Status List */}
        <div className="bg-[#1a1614] border border-gray-800 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-6">System Status</h3>
          <div className="space-y-4">
            {SYSTEM_STATUS.map((sys, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-black/20 border border-gray-800/50">
                <div className="flex items-center gap-3">
                  <span className={sys.color}>{sys.icon}</span>
                  <span className="text-sm text-gray-300">{sys.name}</span>
                </div>
                <span className={`text-[10px] font-bold uppercase ${sys.color}`}>{sys.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AI Model Information Box */}
      <div className="bg-[#0c0a09] border border-[#a37c53]/30 rounded-2xl p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-[#a37c53]/5 blur-[100px]" />
        <h3 className="text-white font-bold mb-6 flex items-center gap-2">
          AI Model Information
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { label: "Model Version", val: "v2.4.1", color: "text-[#a37c53]" },
            { label: "Accuracy", val: "94.7%", color: "text-green-500" },
            { label: "Last Updated", val: "Apr 30", color: "text-gray-400" },
            { label: "Training Data", val: "2.4M samples", color: "text-gray-400" },
          ].map((item, i) => (
            <div key={i} className="space-y-1">
              <p className="text-[10px] uppercase text-gray-500 font-bold">{item.label}</p>
              <p className={`text-lg font-bold ${item.color}`}>{item.val}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 p-4 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center gap-3">
          <CheckCircle2 className="text-green-500 size-5" />
          <p className="text-xs text-green-200/80">
            Model is performing optimally. All metrics are within acceptable ranges.
          </p>
        </div>
      </div>

      {/* Recent System Events */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Recent System Events</h3>
        {[
          { msg: "Automated database backup completed successfully", time: "2026-04-30 13:42:19", icon: <CheckCircle2 className="size-4 text-green-500" /> },
          { msg: "AI model updated to version 2.4.1", time: "2026-04-30 13:13:27", icon: <Zap className="size-4 text-amber-500" /> },
        ].map((event, i) => (
          <div key={i} className="bg-[#1a1614] border border-gray-800 p-4 rounded-xl flex items-center gap-4">
            {event.icon}
            <div className="flex-1">
              <p className="text-sm text-gray-200">{event.msg}</p>
              <p className="text-[10px] text-gray-600 mt-1 flex items-center gap-1 font-mono">
                <Clock className="size-3" /> {event.time}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}