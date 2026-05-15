"use client";

import { useState } from "react";
import { Search, Download, Filter, Info, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const LOGS_DATA = [
  { id: 1, time: "2026-04-30 16:45:23", user: "Admin user", action: "Viewed case", module: "case", status: "Success", detail: "Accessed case details page" },
  { id: 2, time: "2026-04-30 16:45:23", user: "Meron Tilahun", action: "Uploaded evidence", module: "Analysis", status: "Warning", detail: "Analysis another case" },
  { id: 3, time: "2026-04-30 16:45:23", user: "Meti Jemal", action: "Completed analysis", module: "Evidence", status: "Error", detail: "Pattern matching analysis failed due to model version mismatch" },
  { id: 4, time: "2026-04-30 13:13:27", user: "Michael Ross", action: "Uploaded evidence", module: "System", status: "Success", detail: "Uploaded evidence - File size exceeds recommended limit" },
  { id: 5, time: "2026-04-30 16:45:23", user: "Meron Tilahun", action: "Uploaded evidence", module: "Analysis", status: "Active", detail: "Flagged for manual review" },
];

export default function ActivityLogs() {
  const [logs, setLogs] = useState(LOGS_DATA);

  const handleAction = (id: number, action: string) => {
    console.log(`Action: ${action} on log ${id}`);
    // Add interaction: filter out or update status
    if (action === "Ignore") {
      setLogs(logs.filter(log => log.id !== id));
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header with the Bright Amber Button */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Activity Logs</h1>
          <p className="text-gray-400 mt-1">Complete audit trail of system activity</p>
        </div>
        <Button 
          className="bg-[#FFB800] hover:bg-[#E6A600] text-black font-bold px-6 h-11 rounded-lg transition-transform active:scale-95"
          onClick={() => alert("Exporting Logs...")}
        >
          Export Logs
        </Button>
      </div>

      {/* Filter Row with Blue Glow Focus */}
      <div className="flex justify-end gap-4 items-center">
        <span className="text-gray-500 text-sm">Filter</span>
        <div className="flex gap-2">
          <button className="bg-[#1a1c2e] border border-[#0095FF] text-[#0095FF] px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
            All Modules <ChevronDown className="size-4" />
          </button>
          <button className="bg-[#111e1f] border border-[#00F0FF] text-[#00F0FF] px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
            All Status <ChevronDown className="size-4" />
          </button>
        </div>
      </div>

      {/* The Logs Table */}
      <div className="bg-[#121212] border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-gray-800 text-[#FFB800] font-semibold text-sm">
              <th className="px-6 py-5">Time stamp</th>
              <th className="px-6 py-5">User</th>
              <th className="px-6 py-5">Action</th>
              <th className="px-6 py-5">Module</th>
              <th className="px-6 py-5">Status</th>
              <th className="px-6 py-5">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/50">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-white/[0.03] group transition-colors">
                <td className="px-6 py-4 text-[13px] text-gray-400 font-mono">{log.time}</td>
                <td className="px-6 py-4 text-sm text-gray-200">{log.user}</td>
                <td className="px-6 py-4 text-sm text-gray-300">{log.action}</td>
                <td className="px-6 py-4">
                  <span className={`text-[10px] uppercase font-bold px-3 py-1 rounded-full ${getModuleStyle(log.module)}`}>
                    {log.module}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className={`text-[10px] px-3 py-1 rounded-full font-bold shadow-sm ${getStatusStyle(log.status)}`}>
                    {log.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex justify-between items-center gap-4">
                    <span className="text-sm text-gray-400 truncate max-w-[200px] italic">{log.detail}</span>
                    
                    {/* Interactive Buttons from Design */}
                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      {log.status === "Active" ? (
                        <>
                          <Button 
                            size="sm" 
                            className="bg-[#0095FF] hover:bg-[#007acc] text-white h-8 text-[11px] px-4 font-bold"
                            onClick={() => handleAction(log.id, "Investigate")}
                          >
                            Investigate
                          </Button>
                          <Button 
                            size="sm" 
                            className="bg-[#FF4D4D] hover:bg-[#D43F3F] text-white h-8 text-[11px] px-4 font-bold"
                            onClick={() => handleAction(log.id, "Ignore")}
                          >
                            Ignore
                          </Button>
                        </>
                      ) : (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="border-[#FFB800] text-[#FFB800] hover:bg-[#FFB800]/10 h-8 text-[11px] px-4 font-bold"
                          onClick={() => handleAction(log.id, "View Detail")}
                        >
                          Detail
                        </Button>
                      )}
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function getModuleStyle(module: string) {
  switch (module.toLowerCase()) {
    case 'case': return "bg-blue-600/20 text-blue-400 border border-blue-500/30";
    case 'analysis': return "bg-cyan-600/20 text-cyan-400 border border-cyan-500/30";
    case 'evidence': return "bg-purple-600/20 text-purple-400 border border-purple-500/30";
    default: return "bg-red-600/20 text-red-400 border border-red-500/30";
  }
}

function getStatusStyle(status: string) {
  switch (status) {
    case "Success": return "bg-[#00FF85]/20 text-[#00FF85] shadow-[#00FF85]/10";
    case "Warning": return "bg-[#FF9900]/20 text-[#FF9900]";
    case "Error": return "bg-[#FF4D4D]/20 text-[#FF4D4D]";
    case "Active": return "bg-[#00FF85]/20 text-[#00FF85] border border-[#00FF85]/40 shadow-[0_0_8px_rgba(0,255,133,0.3)]";
    default: return "bg-gray-800 text-gray-400";
  }
}

function ChevronDown({ className }: { className?: string }) {
  return <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>;
}