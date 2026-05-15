"use client";

import React, { useState, useRef } from 'react';
import { 
  Database, 
  Search, 
  Eye, 
  Trash2, 
  ChevronDown,
  FileUp,
  CheckCircle2,
  Loader2,
  X
} from 'lucide-react';

export default function DatasetManagement() {
  // 1. References and States
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [datasetName, setDatasetName] = useState("");
  const [dataType, setDataType] = useState("Fingerprint");
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const [datasets, setDatasets] = useState([
    { name: "Fingerprint Set A-301", type: "Fingerprint", samples: "125", size: "1 GB", date: "April 1" },
    { name: "Toolmark Collection B", type: "Toolmark", samples: "230", size: "1.2 GB", date: "Mar 11" },
    { name: "Fingerprint Set B-402", type: "Fingerprint", samples: "400", size: "400 MG", date: "Mar 20" },
    { name: "Toolmark Collection D", type: "Toolmark", samples: "280", size: "1.1 GB", date: "Mar 30" },
  ]);

  // 2. Logic Handlers
  const filteredDatasets = datasets.filter(ds => 
    ds.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ds.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleFileButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(e.target.files);
    }
  };

  const handleUpload = () => {
    if (!datasetName) return alert("Please enter a dataset name");
    if (!selectedFiles) return alert("Please select files first");
    
    setIsUploading(true);
    
    // Simulate Forensic Data Processing
    setTimeout(() => {
      const newEntry = {
        name: datasetName,
        type: dataType,
        samples: selectedFiles.length.toString(),
        size: `${(Math.random() * 2).toFixed(1)} GB`, // Random size for simulation
        date: "May 15"
      };
      
      setDatasets([newEntry, ...datasets]);
      setIsUploading(false);
      setShowSuccess(true);
      
      // Reset Form
      setDatasetName("");
      setSelectedFiles(null);
      if (fileInputRef.current) fileInputRef.current.value = "";

      setTimeout(() => setShowSuccess(false), 3000);
    }, 2000);
  };

  const removeSelectedFiles = () => {
    setSelectedFiles(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700 relative">
      
      {/* Success Notification */}
      {showSuccess && (
        <div className="fixed top-10 right-10 z-50 bg-[#b8860b] text-black px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 animate-in slide-in-from-right-10">
          <CheckCircle2 className="size-5" />
          <span className="font-black text-xs uppercase tracking-widest">Dataset Processed and Archived</span>
        </div>
      )}

      <div className="space-y-1">
        <h1 className="text-3xl font-bold text-white tracking-tight">Dataset Management</h1>
        <p className="text-sm text-gray-500 font-medium">
          Upload and <span className="text-[#b8860b]">manage</span> training datasets
        </p>
      </div>

      {/* Hidden File Input */}
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
        className="hidden" 
        multiple 
      />

      {/* Upload Section */}
      <div className="bg-[#1e1b16] border border-gray-800/50 rounded-[2.5rem] p-10 shadow-2xl">
        <h3 className="text-sm font-bold text-white mb-8">Upload New Dataset</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-end">
          {/* Dataset Name */}
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Dataset Name</label>
            <input 
              type="text" 
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g Fingerprint Set E-503"
              className="w-full bg-black/40 border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 focus:outline-none focus:border-amber-900/50 transition-colors"
            />
          </div>

          {/* Data Type */}
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Data Type</label>
            <div className="relative">
              <select 
                value={dataType}
                onChange={(e) => setDataType(e.target.value)}
                className="w-full bg-black border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 appearance-none focus:outline-none focus:border-amber-900/50 cursor-pointer"
              >
                <option value="Fingerprint" className="bg-[#1e1b16]">Fingerprint</option>
                <option value="Toolmark" className="bg-[#1e1b16]">Toolmark</option>
              </select>
              <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 size-4 text-gray-600 pointer-events-none" />
            </div>
          </div>

          {/* File Upload Button */}
          <div className="space-y-3">
            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">File Source</label>
            <div className="relative">
              <button 
                onClick={handleFileButtonClick}
                className={`w-full h-[54px] rounded-2xl px-6 border border-dashed transition-all flex items-center justify-center gap-3 text-sm
                  ${selectedFiles 
                    ? 'border-amber-600 bg-amber-600/5 text-amber-500' 
                    : 'border-gray-800 bg-black/40 text-gray-500 hover:text-gray-300 hover:border-amber-900/50'
                  }`}
              >
                <FileUp className={`size-4 ${selectedFiles ? 'text-amber-500' : ''}`} />
                <span className="truncate">
                  {selectedFiles ? `${selectedFiles.length} files selected` : 'Choose Files'}
                </span>
              </button>
              
              {selectedFiles && (
                <button 
                  onClick={removeSelectedFiles}
                  className="absolute -top-2 -right-2 bg-red-900 text-white p-1 rounded-full hover:bg-red-700 transition-colors"
                >
                  <X className="size-3" />
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="mt-8">
          <button 
            onClick={handleUpload}
            disabled={isUploading || !selectedFiles}
            className="bg-[#b8860b] hover:bg-amber-600 disabled:opacity-30 disabled:cursor-not-allowed text-black px-10 py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-lg flex items-center gap-3"
          >
            {isUploading && <Loader2 className="size-4 animate-spin" />}
            {isUploading ? "Processing Dataset..." : "Upload Dataset"}
          </button>
        </div>
      </div>

      {/* Dataset Table Section */}
      <div className="bg-[#1e1b16] border border-gray-800/50 rounded-[2.5rem] shadow-2xl overflow-hidden">
        <div className="p-8 border-b border-gray-800/50 flex items-center bg-black/20">
          <div className="relative w-full max-w-md flex items-center gap-4">
            <Search className="size-4 text-amber-900" />
            <input 
              type="text" 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name or type..."
              className="w-full bg-transparent border-none text-sm text-gray-300 placeholder:text-amber-900/50 focus:ring-0"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-[#b8860b] text-black">
              <tr className="text-[10px] font-black uppercase tracking-[0.2em]">
                <th className="px-8 py-5">Dataset Name</th>
                <th className="px-8 py-5">Type</th>
                <th className="px-8 py-5">Samples</th>
                <th className="px-8 py-5">Size</th>
                <th className="px-8 py-5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50 text-gray-300">
              {filteredDatasets.map((dataset, idx) => (
                <tr key={idx} className="hover:bg-black/40 transition-colors group">
                  <td className="px-8 py-6 text-sm font-medium">{dataset.name}</td>
                  <td className="px-8 py-6">
                    <span className="px-3 py-1 bg-black rounded-lg text-[10px] text-gray-500 font-bold uppercase tracking-widest border border-gray-800">
                      {dataset.type}
                    </span>
                  </td>
                  <td className="px-8 py-6 text-xs font-mono text-amber-700">{dataset.samples}</td>
                  <td className="px-8 py-6 text-xs font-mono">{dataset.size}</td>
                  <td className="px-8 py-6">
                    <div className="flex items-center justify-center gap-4">
                      <button className="p-2.5 bg-black rounded-xl border border-gray-800 text-amber-600 hover:border-amber-600 transition-all active:scale-90">
                        <Eye className="size-4" />
                      </button>
                      <button 
                        onClick={() => setDatasets(datasets.filter((_, i) => i !== idx))}
                        className="p-2.5 bg-black rounded-xl border border-gray-800 text-red-900 hover:border-red-600 transition-all active:scale-90"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {filteredDatasets.length === 0 && (
            <div className="py-20 text-center space-y-2">
              <Database className="size-10 text-gray-800 mx-auto opacity-20" />
              <p className="text-gray-600 font-bold uppercase tracking-widest text-xs">No forensic datasets found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}