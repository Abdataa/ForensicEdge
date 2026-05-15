"use client";

import { useState } from "react";
import { Save, X, Shield, Globe, HardDrive, Cpu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function SystemSettings() {
  const [is2FAEnabled, setIs2FAEnabled] = useState(true);
  const [isAnalysisEnabled, setIsAnalysisEnabled] = useState(true);

  return (
    <div className="max-w-5xl space-y-8 animate-in fade-in duration-500 pb-20">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">System Settings</h1>
        <p className="text-gray-400 mt-1">Configure system-wide preferences and policies</p>
      </div>

      {/* General Settings Section */}
      <section className="bg-[#1a1614] border border-gray-800 rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-gray-800 flex items-center gap-2">
          <Globe className="size-4 text-[#a37c53]" />
          <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider">General Settings</h2>
        </div>
        <div className="p-8 space-y-6">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-400">System Name</label>
            <Input 
              defaultValue="ForensicEdge" 
              className="bg-black/40 border-gray-800 text-white h-12 focus:ring-[#a37c53]"
            />
            <p className="text-[10px] text-gray-500 italic">Displayed in the sidebar and login page</p>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-400">Timezone</label>
            <Select defaultValue="eat">
              <SelectTrigger className="bg-black/40 border-gray-800 text-white h-12">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent className="bg-[#1a1614] border-gray-800 text-white">
                <SelectItem value="eat">East Africa Time (GMT+3)</SelectItem>
                <SelectItem value="utc">UTC / GMT</SelectItem>
                <SelectItem value="est">Eastern Standard Time</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-[10px] text-gray-500 italic">All timestamps will be displayed in this timezone</p>
          </div>
        </div>
      </section>

      {/* Security Settings Section */}
      <section className="bg-[#1a1614] border border-gray-800 rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-gray-800 flex items-center gap-2">
          <Shield className="size-4 text-[#a37c53]" />
          <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider">Security Settings</h2>
        </div>
        <div className="p-8 space-y-8">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-400">Password Policy</label>
            <Input 
              defaultValue="ForensicEdge" 
              className="bg-black/40 border-gray-800 text-white h-12" 
            />
          </div>
          
          <div className="flex items-center justify-between p-4 bg-black/20 rounded-xl border border-gray-800/50">
            <div>
              <p className="text-sm font-medium text-gray-200">Enable Two-Factor Authentication (2FA)</p>
              <p className="text-xs text-gray-500 mt-1">Require 2FA for all user accounts</p>
            </div>
            <Switch 
              checked={is2FAEnabled} 
              onCheckedChange={setIs2FAEnabled}
              className="data-[state=checked]:bg-[#a37c53]"
            />
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-400">Session Timeout (minutes)</label>
            <Select defaultValue="30">
              <SelectTrigger className="bg-black/40 border-gray-800 text-white h-12">
                <SelectValue placeholder="Select timeout" />
              </SelectTrigger>
              <SelectContent className="bg-[#1a1614] border-gray-800 text-white">
                <SelectItem value="15">15 minutes</SelectItem>
                <SelectItem value="30">30 minutes</SelectItem>
                <SelectItem value="60">60 minutes</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </section>

      {/* File Upload Settings */}
      <section className="bg-[#1a1614] border border-gray-800 rounded-2xl overflow-hidden">
        <div className="p-6 border-b border-gray-800 flex items-center gap-2">
          <HardDrive className="size-4 text-[#a37c53]" />
          <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider">File Upload Settings</h2>
        </div>
        <div className="p-8 space-y-6">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-400">Maximum File Size (MB)</label>
            <Input 
              type="number" 
              defaultValue="500" 
              className="bg-black/40 border-gray-800 text-white h-12"
            />
            <p className="text-[10px] text-gray-500 italic">Maximum size for evidence file uploads</p>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-gray-400">Allowed File Formats</label>
            <div className="flex flex-wrap gap-2 mt-2">
              {[".mp4", ".zip", ".pdf", ".png", ".jpg"].map((ext) => (
                <span key={ext} className="bg-[#a37c53]/10 text-[#a37c53] border border-[#a37c53]/30 px-3 py-1 rounded text-[10px] font-bold">
                  {ext}
                </span>
              ))}
            </div>
            <p className="text-[10px] text-gray-500 italic mt-2">Click to add or remove file formats</p>
          </div>
        </div>
      </section>

      {/* System Controls Toggle */}
      <section className="bg-[#1a1614] border border-gray-800 rounded-2xl p-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-amber-500/10 rounded-xl">
              <Cpu className="size-5 text-[#a37c53]" />
            </div>
            <div>
              <p className="text-sm font-bold text-gray-200">Enable Analysis Module</p>
              <p className="text-xs text-gray-500 mt-1">Allow AI-powered evidence analysis</p>
            </div>
          </div>
          <Switch 
            checked={isAnalysisEnabled} 
            onCheckedChange={setIsAnalysisEnabled}
            className="data-[state=checked]:bg-[#a37c53]"
          />
        </div>
      </section>

      {/* Action Buttons */}
      <div className="flex justify-end gap-4">
        <Button variant="ghost" className="text-gray-400 hover:text-white hover:bg-white/5 px-8">
          Cancel
        </Button>
        <Button className="bg-[#a37c53] hover:bg-[#8e6b47] text-[#1a1614] font-bold px-10 h-11 rounded-lg transition-transform active:scale-95">
          Save Setting
        </Button>
      </div>
    </div>
  );
}