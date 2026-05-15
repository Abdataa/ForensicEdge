import React from 'react';
import { 
  Activity, 
  Upload, 
  Search, 
  FileText, 
  Shield, 
  Database, 
  ArrowRight 
} from 'lucide-react';
import Link from 'next/link';

export default function AnalystDashboard() {
  // Mock data based on your Figma "Recent Investigations" table
  const investigations = [
    { id: "CASE 01", evidence: "Fingerprint.png", status: "Analysed", analyst: "Admin", date: "April 1", statusColor: "text-green-500 bg-green-500/10" },
    { id: "CASE 02", evidence: "Toolmark.png", status: "Pending", analyst: "Ms. Meti", date: "Mar 11", statusColor: "text-amber-500 bg-amber-500/10" },
    { id: "CASE 03", evidence: "Fingerprint.png", status: "Analysed", analyst: "Ms. Meron", date: "Mar 20", statusColor: "text-green-500 bg-green-500/10" },
    { id: "CASE 04", evidence: "Toolmark.png", status: "Analysed", analyst: "Admin", date: "Mar 30", statusColor: "text-green-500 bg-green-500/10" },
    { id: "CASE 05", evidence: "Fingerprint.png", status: "Processing", analyst: "Admin", date: "April 5", statusColor: "text-purple-500 bg-purple-500/10" },
  ];

  return (
    <div className="flex flex-col space-y-8 p-2">
      {/* Header Section */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Forensic DashBoard</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Access Level:</span>
            <span className="text-[10px] uppercase tracking-widest text-amber-500 font-bold italic">Analyst</span>
          </div>
        </div>
      </div>

      {/* Case Overview Grid - Based on Figma Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "Activity Cases", count: "12", icon: Activity },
          { label: "Evidence Upload", count: "45", icon: Upload },
          { label: "Analysis Done", count: "30", icon: Search },
          { label: "Report Generated", count: "24", icon: FileText },
        ].map((item) => (
          <div key={item.label} className="bg-[#1a1610] border border-gray-800 p-5 rounded-xl hover:border-amber-600/40 transition-colors cursor-default">
            <p className="text-xs font-semibold text-gray-400 mb-3">{item.label}</p>
            <div className="flex justify-between items-end">
               <span className="text-2xl font-bold text-white">{item.count}</span>
               <item.icon className="size-5 text-amber-600/50" />
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions Section */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">Quick Actions</h3>
        <div className="flex flex-wrap gap-4">
          <Link href="/analyst/cases" className="px-6 py-2 bg-amber-600 text-black text-xs font-bold rounded-lg hover:bg-amber-500 transition-colors flex items-center gap-2">
            Upload Evidence
          </Link>
          <button className="px-6 py-2 bg-[#2a241a] text-amber-500 text-xs font-bold rounded-lg border border-amber-900/30 hover:bg-[#362e21] transition-colors">
            Start Analysis
          </button>
          <button className="px-6 py-2 bg-[#2a241a] text-amber-500 text-xs font-bold rounded-lg border border-amber-900/30 hover:bg-[#362e21] transition-colors">
            Generate Report
          </button>
        </div>
      </div>

      {/* Recent Investigations Table */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">Recent Investigations</h3>
        <div className="bg-[#0d0d0d] border border-gray-800 rounded-2xl overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#1a1a1a] text-gray-400 font-medium">
              <tr>
                <th className="px-6 py-4">Case ID</th>
                <th className="px-6 py-4">Evidence</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Analyst</th>
                <th className="px-6 py-4 text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {investigations.map((investigation) => (
                <tr key={investigation.id} className="hover:bg-white/5 transition-colors group">
                  <td className="px-6 py-4 font-mono text-gray-300">{investigation.id}</td>
                  <td className="px-6 py-4 text-gray-400">{investigation.evidence}</td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-tighter ${investigation.statusColor}`}>
                      {investigation.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-400">{investigation.analyst}</td>
                  <td className="px-6 py-4 text-right text-gray-500 font-mono">{investigation.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* System Status Footer - Matches Figma */}
      <div className="flex justify-center gap-12 pt-4 border-t border-gray-900">
        <div className="flex items-center gap-2">
          <div className="size-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">AI Engine: <span className="text-green-500">Running</span></span>
        </div>
        <div className="flex items-center gap-2">
          <div className="size-2 bg-green-500 rounded-full" />
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Database: <span className="text-green-500">Connected</span></span>
        </div>
      </div>
    </div>
  );
}