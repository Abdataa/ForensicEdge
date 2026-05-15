"use client";

import React, { useState } from 'react';
import { Upload, X, FileIcon, Image as ImageIcon } from 'lucide-react';

export default function UploadEvidencePage() {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-bold text-white tracking-tight">
          Upload forensic evidence files for analysis
        </h2>
        <p className="text-sm text-gray-500">
          Supported formats: PNG, JPG, PDF (Up to 50MB)
        </p>
      </div>

      {/* Main Upload Container - Matches the large brown/dark box in Figma */}
      <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-12">
        <div 
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          className={`
            relative border-2 border-dashed rounded-[1.5rem] p-20
            flex flex-col items-center justify-center gap-6 transition-all
            ${isDragging 
              ? "border-amber-500 bg-amber-500/5" 
              : "border-gray-800 hover:border-amber-900/50 hover:bg-white/5"}
          `}
        >
          <input 
            type="file" 
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
            multiple
          />
          
          <div className="bg-amber-600/10 p-4 rounded-full">
            <Upload className="size-8 text-amber-500" />
          </div>

          <div className="text-center space-y-2">
            <p className="text-lg font-bold text-gray-200">
              Click to upload or drag and drop
            </p>
            <p className="text-xs text-gray-500 font-medium uppercase tracking-widest">
              PNG, JPG, PDF up to 50MB
            </p>
          </div>
        </div>

        {/* Action Buttons - Matching the brown/gold and beige style at the bottom */}
        <div className="flex items-center justify-center gap-4 mt-12">
          <button className="bg-[#b8860b] hover:bg-amber-600 text-black px-10 py-3 rounded-xl text-xs font-black uppercase tracking-[0.2em] transition-all flex items-center gap-2 shadow-lg shadow-amber-900/20">
            <Upload className="size-4" /> Upload Evidence
          </button>
          
          <button className="bg-[#d4c3a3] hover:bg-[#c4b393] text-black px-10 py-3 rounded-xl text-xs font-black uppercase tracking-[0.2em] transition-all">
            Cancel
          </button>
        </div>
      </div>

      {/* Optional: File Queue Preview Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* You can map uploaded files here later */}
      </div>
    </div>
  );
}