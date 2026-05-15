"use client";

import React, { useState } from 'react';
import { 
  Bell, 
  ShieldCheck, 
  Database, 
  Save,
  CheckSquare,
  Square,
  Lock,
  HardDrive
} from 'lucide-react';

export default function SettingsPage() {
  // State for toggles
  const [notifications, setNotifications] = useState({
    email: true,
    highPriority: true,
    analysis: false
  });

  const [autoLogout, setAutoLogout] = useState(true);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header Section */}
      <div className="space-y-1">
        <h2 className="text-2xl font-bold text-white tracking-tight">Settings</h2>
        <p className="text-sm text-gray-500 font-medium">
          Configure your application preferences
        </p>
      </div>

      <div className="max-w-4xl space-y-6">
        
        {/* Notifications Section */}
        <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-8 shadow-xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-amber-600/10 rounded-lg">
              <Bell className="size-5 text-amber-600" />
            </div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest">Notifications</h3>
          </div>

          <div className="space-y-6">
            {[
              { id: 'email', label: 'Email notifications for case updates' },
              { id: 'highPriority', label: 'Alert on high-priority cases' },
              { id: 'analysis', label: 'Analysis completion notifications' }
            ].map((item) => (
              <div 
                key={item.id}
                onClick={() => setNotifications(prev => ({ ...prev, [item.id]: !prev[item.id as keyof typeof notifications] }))}
                className="flex items-center justify-between group cursor-pointer"
              >
                <span className="text-sm text-gray-400 group-hover:text-gray-200 transition-colors">{item.label}</span>
                <div className="text-[#b8860b]">
                  {notifications[item.id as keyof typeof notifications] ? (
                    <CheckSquare className="size-6 fill-[#b8860b] text-black" />
                  ) : (
                    <Square className="size-6 text-gray-700" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Security Section */}
        <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-8 shadow-xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-amber-600/10 rounded-lg">
              <ShieldCheck className="size-5 text-amber-600" />
            </div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest">Security</h3>
          </div>

          <div className="space-y-6">
            <button className="w-full flex items-center justify-between p-4 bg-black/40 border border-gray-800 rounded-xl hover:border-amber-900/40 transition-all group">
              <span className="text-sm text-gray-400 group-hover:text-gray-200">Change Password</span>
              <Lock className="size-4 text-gray-600" />
            </button>

            <button className="w-full flex items-center justify-between p-4 bg-black/40 border border-gray-800 rounded-xl hover:border-amber-900/40 transition-all group">
              <span className="text-sm text-gray-400 group-hover:text-gray-200">Enable Two-Factor Authentication</span>
              <div className="px-3 py-1 bg-gray-800 rounded text-[10px] text-gray-500 font-bold uppercase">Disabled</div>
            </button>

            <div 
              onClick={() => setAutoLogout(!autoLogout)}
              className="flex items-center justify-between group cursor-pointer pt-2"
            >
              <span className="text-sm text-gray-400 group-hover:text-gray-200">Auto-logout after inactivity</span>
              <div className="text-[#b8860b]">
                {autoLogout ? (
                  <CheckSquare className="size-6 fill-[#b8860b] text-black" />
                ) : (
                  <Square className="size-6 text-gray-700" />
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Data & Storage Section */}
        <div className="bg-[#1a1610] border border-gray-800 rounded-[2rem] p-8 shadow-xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-amber-600/10 rounded-lg">
              <Database className="size-5 text-amber-600" />
            </div>
            <h3 className="text-white font-bold text-sm uppercase tracking-widest">Data & Storage</h3>
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <div className="flex justify-between items-end">
                <div className="space-y-1">
                  <p className="text-xs font-bold text-gray-200">Storage Used</p>
                  <p className="text-[10px] text-gray-500">24.5 GB of 100 GB</p>
                </div>
                <span className="text-xs font-bold text-amber-600">24%</span>
              </div>
              
              {/* Progress Bar */}
              <div className="h-2 w-full bg-black rounded-full overflow-hidden border border-gray-800">
                <div 
                  className="h-full bg-gradient-to-r from-amber-900 to-[#b8860b] rounded-full transition-all duration-1000" 
                  style={{ width: '24.5%' }}
                />
              </div>
            </div>

            <button className="w-full bg-black border border-gray-800 text-gray-300 hover:text-white hover:bg-gray-900 py-3.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all">
              Manage Storage
            </button>
          </div>
        </div>

        {/* Global Save Button */}
        <div className="pt-4 flex justify-end">
          <button className="bg-[#b8860b] hover:bg-amber-600 text-black px-10 py-4 rounded-2xl text-xs font-black uppercase tracking-widest flex items-center gap-2 shadow-xl shadow-amber-900/20 transition-all active:scale-95">
            <Save className="size-4" /> Save Preferences
          </button>
        </div>

      </div>
    </div>
  );
}