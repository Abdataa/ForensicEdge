"use client";

import React from 'react';
import { 
  FileText, 
  Download, 
  Eye, 
  Plus, 
  FileCheck2,
  MoreVertical
} from 'lucide-react';

export default function ReportsPage() {
  // Mock data matching the table in image_07831b.png
  const reports = [
    { 
      id: "RPT 01", 
      caseId: "case 01", 
      title: "Fingerprint Analysis", 
      type: "Fingerprint", 
      date: "April 1", 
      size: "2.5 MB", 
      status: "Final" 
    },
    { 
      id: "RPT 02", 
      caseId: "case 02", 
      title: "Toolmark Analysis", 
      type: "Toolmark", 
      date: "Mar 11", 
      size: "4.5 MB", 
      status: "Final" 
    },
    { 
      id: "RPT 03", 
      caseId: "case 03", 
      title: "Fingerprint Analysis", 
      type: "Fingerprint", 
      date: "Mar 4", 
      size: "6.3 MB", 
      status: "Default" 
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-xl font-bold text-white tracking-tight">
            Generate and manage forensic analysis reports
          </h2>
          <p className="text-sm text-gray-500">
            View, download, or create new comprehensive case documentations.
          </p>
        </div>
        
        <button className="bg-[#b8860b] hover:bg-amber-600 text-black px-6 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] transition-all flex items-center gap-2 shadow-lg shadow-amber-900/20">
          Generate New Report
        </button>
      </div>

      {/* Reports Table Container */}
      <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] overflow-hidden">
        <div className="p-8">
          <div className="flex items-center gap-2 mb-6">
            <FileText className="size-4 text-amber-600" />
            <h3 className="text-white font-bold text-xs uppercase tracking-[0.2em]">Generated Reports</h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-separate border-spacing-y-3">
              <thead>
                <tr className="text-[10px] uppercase tracking-widest text-gray-500 font-black">
                  <th className="px-4 py-2">Report ID</th>
                  <th className="px-4 py-2">CASE ID</th>
                  <th className="px-4 py-2">Title</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Date</th>
                  <th className="px-4 py-2">Size</th>
                  <th className="px-4 py-2 text-center">Status</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.id} className="group bg-black/40 hover:bg-black/60 transition-colors border border-gray-800">
                    <td className="px-4 py-4 first:rounded-l-xl border-y border-l border-gray-800/50">
                      <span className="text-xs font-mono text-amber-500/80">{report.id}</span>
                    </td>
                    <td className="px-4 py-4 border-y border-gray-800/50">
                      <span className="text-xs text-gray-400 font-medium uppercase tracking-tighter">{report.caseId}</span>
                    </td>
                    <td className="px-4 py-4 border-y border-gray-800/50">
                      <span className="text-sm text-gray-200 font-bold">{report.title}</span>
                    </td>
                    <td className="px-4 py-4 border-y border-gray-800/50">
                      <span className="text-xs text-gray-500 uppercase font-bold">{report.type}</span>
                    </td>
                    <td className="px-4 py-4 border-y border-gray-800/50">
                      <span className="text-xs text-gray-400">{report.date}</span>
                    </td>
                    <td className="px-4 py-4 border-y border-gray-800/50">
                      <span className="text-xs text-gray-500">{report.size}</span>
                    </td>
                    <td className="px-4 py-4 border-y border-gray-800/50 text-center">
                      <span className={`text-[9px] font-black uppercase px-3 py-1 rounded-md ${
                        report.status === 'Final' 
                        ? 'bg-green-500/10 text-green-500 border border-green-500/20' 
                        : 'bg-[#b8860b]/10 text-[#b8860b] border border-[#b8860b]/20'
                      }`}>
                        {report.status}
                      </span>
                    </td>
                    <td className="px-4 py-4 last:rounded-r-xl border-y border-r border-gray-800/50 text-right">
                      <div className="flex justify-end gap-3">
                        <button title="View Report" className="p-1.5 text-gray-400 hover:text-white transition-colors">
                          <Eye className="size-4" />
                        </button>
                        <button title="Download PDF" className="p-1.5 text-gray-400 hover:text-amber-500 transition-colors">
                          <Download className="size-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}