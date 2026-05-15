"use client";

import React, { useRef, useState } from 'react';
import { 
  User, 
  Mail, 
  Phone, 
  Building2, 
  Camera,
  Save,
  RotateCcw
} from 'lucide-react';

export default function ProfilePage() {
  // 1. Reference for the hidden file input
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  // 2. Function to trigger the file browser
  const handlePhotoClick = () => {
    fileInputRef.current?.click();
  };

  // 3. Handle the file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header Section */}
      <div className="space-y-1">
        <h2 className="text-2xl font-bold text-white tracking-tight">Profile</h2>
        <p className="text-sm text-gray-500 font-medium">
          Manage your account information
        </p>
      </div>

      {/* Hidden File Input */}
      <input 
        type="file" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
        className="hidden" 
        accept="image/*"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Avatar & Role Card */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-8 flex flex-col items-center text-center shadow-xl">
            <div className="relative group mb-6">
              {/* Display preview if available, otherwise show the 'P' placeholder */}
              <div 
                onClick={handlePhotoClick}
                className="size-32 bg-[#b8860b] rounded-full flex items-center justify-center text-black text-5xl font-black shadow-lg shadow-amber-900/20 overflow-hidden cursor-pointer"
              >
                {previewImage ? (
                  <img src={previewImage} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  "P"
                )}
              </div>
              
              {/* Camera Icon Button */}
              <button 
                onClick={handlePhotoClick}
                className="absolute bottom-0 right-0 bg-black border border-gray-800 p-2 rounded-full text-amber-500 hover:text-amber-400 transition-colors shadow-lg active:scale-90"
              >
                <Camera className="size-4" />
              </button>
            </div>
            
            <div className="space-y-1 mb-6">
              <h3 className="text-xl font-bold text-white uppercase tracking-tight">Profile</h3>
              <p className="text-sm text-gray-500 font-medium lowercase">name@forensicedge.com</p>
            </div>

            <div className="inline-block px-4 py-1.5 bg-amber-600/10 border border-amber-600/20 rounded-lg text-amber-500 text-[10px] font-black uppercase tracking-widest mb-8">
              Analyst
            </div>

            {/* Change Photo Button */}
            <button 
              onClick={handlePhotoClick}
              className="w-full bg-[#b8860b]/10 border border-[#b8860b]/30 text-[#b8860b] hover:bg-[#b8860b]/20 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all active:scale-95"
            >
              Change Photo
            </button>
          </div>
        </div>

        {/* Right Column: Personal Information Form */}
        <div className="lg:col-span-2">
          <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-10 shadow-xl">
            <div className="flex items-center gap-2 mb-10 border-b border-gray-800/50 pb-6">
              <User className="size-4 text-amber-600" />
              <h3 className="text-white font-bold text-xs uppercase tracking-[0.2em]">Personal Information</h3>
            </div>

            <form className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">First Name</label>
                <input 
                  type="text" 
                  placeholder="First Name" 
                  className="w-full bg-black/40 border border-gray-800 rounded-xl px-5 py-3.5 text-sm text-gray-300 outline-none focus:border-amber-600/50 transition-all"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">Last Name</label>
                <input 
                  type="text" 
                  placeholder="Last Name" 
                  className="w-full bg-black/40 border border-gray-800 rounded-xl px-5 py-3.5 text-sm text-gray-300 outline-none focus:border-amber-600/50 transition-all"
                />
              </div>

              <div className="md:col-span-2 space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">Email</label>
                <input 
                  type="email" 
                  placeholder="Enter your email" 
                  className="w-full bg-black/40 border border-gray-800 rounded-xl px-5 py-3.5 text-sm text-gray-300 outline-none focus:border-amber-600/50 transition-all"
                />
              </div>

              <div className="md:col-span-2 space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">Phone</label>
                <input 
                  type="tel" 
                  placeholder="Enter your phone" 
                  className="w-full bg-black/40 border border-gray-800 rounded-xl px-5 py-3.5 text-sm text-gray-300 outline-none focus:border-amber-600/50 transition-all"
                />
              </div>

              <div className="md:col-span-2 space-y-2">
                <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">Department</label>
                <div className="w-full bg-black/20 border border-amber-900/20 rounded-xl px-5 py-3.5 text-sm text-[#b8860b] font-bold">
                  Forensic Analysis
                </div>
              </div>

              <div className="md:col-span-2 flex items-center gap-4 pt-6">
                <button 
                  type="button"
                  className="bg-[#b8860b] hover:bg-amber-600 text-black px-8 py-3 rounded-xl text-xs font-black uppercase tracking-widest flex items-center gap-2 shadow-lg shadow-amber-900/20 transition-all active:scale-95"
                >
                  <Save className="size-4" /> Save Change
                </button>
                <button 
                  type="button"
                  className="bg-gray-800/50 hover:bg-gray-800 text-gray-400 px-8 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all active:scale-95 border border-gray-700"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>

      </div>
    </div>
  );
}