"use client";

import React from 'react';
import { 
  AlertTriangle, 
  MessageSquare, 
  Hash, 
  ChevronDown,
  Flag
} from 'lucide-react';

export default function SystemFeedbackPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl">
      {/* Header Section */}
      <div className="space-y-1">
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Dispute Analysis Result
        </h2>
        <p className="text-sm text-gray-500 font-medium">
          Flag incorrect AI matches for manual verification
        </p>
      </div>

      {/* Form Container */}
      <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-10 shadow-2xl">
        <div className="flex items-center gap-2 mb-8 border-b border-gray-800/50 pb-6">
            <MessageSquare className="size-4 text-amber-600" />
            <h3 className="text-white font-bold text-xs uppercase tracking-[0.2em]">Correction Details</h3>
        </div>

        <form className="space-y-8">
          {/* Related Analysis ID Dropdown */}
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 flex items-center gap-2 ml-1">
              <Hash className="size-3 text-amber-600" /> Related Analysis ID
            </label>
            <div className="relative group">
              <select 
                defaultValue="" 
                className="w-full bg-black/40 border border-gray-800 rounded-xl px-5 py-4 text-sm text-gray-300 appearance-none outline-none focus:border-amber-600/50 transition-all cursor-pointer group-hover:bg-black/60"
              >
                <option value="" disabled>Select a recent analysis...</option>
                <option value="AN-9021">AN-9021 (Fingerprint Match)</option>
                <option value="AN-8842">AN-8842 (Toolmark Comparison)</option>
                <option value="AN-7730">AN-7730 (Pattern Recognition)</option>
              </select>
              <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 size-4 text-gray-500 pointer-events-none group-hover:text-amber-500 transition-colors" />
            </div>
          </div>

          {/* Reason for Flagging Dropdown */}
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 flex items-center gap-2 ml-1">
              <AlertTriangle className="size-3 text-amber-600" /> Reason for Flagging
            </label>
            <div className="relative group">
              <select 
                defaultValue="" 
                className="w-full bg-black/40 border border-gray-800 rounded-xl px-5 py-4 text-sm text-gray-300 appearance-none outline-none focus:border-amber-600/50 transition-all cursor-pointer group-hover:bg-black/60"
              >
                <option value="" disabled>Select Reason</option>
                <option value="false-positive">False Positive Match</option>
                <option value="low-confidence">Low Confidence Score</option>
                <option value="artifact-error">Image Artifact Interference</option>
                <option value="misclassification">Category Misclassification</option>
              </select>
              <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 size-4 text-gray-500 pointer-events-none group-hover:text-amber-500 transition-colors" />
            </div>
          </div>

          {/* Investigator Comment Textarea */}
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-widest text-gray-400 ml-1">
              Investigator Comment
            </label>
            <textarea 
              placeholder="Describe why the AI result is being questioned..."
              rows={5}
              className="w-full bg-black/40 border border-gray-800 rounded-2xl px-5 py-4 text-sm text-gray-300 outline-none focus:border-amber-600/50 transition-all resize-none placeholder:text-gray-700 hover:bg-black/60"
            />
          </div>

          {/* Submit Button */}
          <div className="pt-4">
            <button 
              type="button"
              className="w-full bg-[#cc1d1d] hover:bg-red-700 text-white font-bold py-5 rounded-xl flex items-center justify-center gap-3 transition-all active:scale-[0.98] shadow-lg shadow-red-900/20 uppercase text-[11px] tracking-[0.25em]"
            >
              <Flag className="size-4" /> Flag for Manual Review
            </button>
          </div>
        </form>
      </div>

      {/* Footer Note */}
      <div className="flex items-center justify-center gap-2 opacity-40">
        <div className="h-px w-8 bg-gray-600"></div>
        <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">
          SECURE DISPUTE TERMINAL
        </p>
        <div className="h-px w-8 bg-gray-600"></div>
      </div>
    </div>
  );
}