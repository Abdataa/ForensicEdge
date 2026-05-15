"use client";

import { useState } from "react";
import { 
  Search, 
  Plus, 
  Filter, 
  Eye, 
  Edit3, 
  Trash2, 
  MoreHorizontal,
  Calendar,
  User as UserIcon
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Data from image_efb019.png
const INITIAL_CASES = [
  {
    id: "CR-2026-001",
    title: "Store Break in - Electronics Shop",
    status: "In Progress",
    priority: "High",
    investigator: "Meron Tilahun",
    created: "28/04/2026",
  },
  {
    id: "CR-2026-002",
    title: "Armed Robbery - Downtown Bank",
    status: "Open",
    priority: "Low",
    investigator: "Meti Jemal",
    created: "30/04/2026",
  },
  {
    id: "CR-2026-003",
    title: "Home Invasion - Maple Avenue",
    status: "Closed",
    priority: "Medium",
    investigator: "Emma Wilson",
    created: "22/04/2026",
  },
  {
    id: "CR-2026-004",
    title: "Burglary Investigation - Street",
    status: "In Progress",
    priority: "Low",
    investigator: "Sarah Chen",
    created: "29/04/2026",
  },
];

export default function CaseManagement() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "high": return "bg-red-950/40 text-red-500 border-red-900/50";
      case "medium": return "bg-amber-950/40 text-amber-500 border-amber-900/50";
      default: return "bg-gray-800/40 text-gray-400 border-gray-700";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "in progress": return "bg-lime-500 text-black font-bold";
      case "open": return "bg-blue-600 text-white";
      case "closed": return "bg-green-700 text-white";
      default: return "bg-gray-600";
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header section with Create Button */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Case Management</h1>
          <p className="text-gray-400 mt-1">
            Manage and track <span className="text-amber-500/80">forensic investigations</span>
          </p>
        </div>
        <Button className="bg-amber-600 hover:bg-amber-700 text-white gap-2 px-6 shadow-lg shadow-amber-900/20">
          <Plus className="size-4" /> Create Case
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap gap-4 items-center bg-[#1a1614]/50 p-4 rounded-xl border border-gray-800">
        <div className="relative flex-1 min-w-[300px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-500" />
          <Input 
            placeholder="Search by Case name, ID or investigator..." 
            className="pl-10 bg-gray-950 border-gray-800 focus:ring-amber-600"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <Select onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px] bg-gray-950 border-gray-800">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent className="bg-gray-950 border-gray-800 text-white">
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="in progress">In Progress</SelectItem>
            <SelectItem value="closed">Closed</SelectItem>
          </SelectContent>
        </Select>

        <Select>
          <SelectTrigger className="w-[180px] bg-gray-950 border-gray-800">
            <SelectValue placeholder="All Priorities" />
          </SelectTrigger>
          <SelectContent className="bg-gray-950 border-gray-800 text-white">
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Case Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {INITIAL_CASES.map((item) => (
          <div 
            key={item.id} 
            className="bg-[#1a1614] border border-gray-800 rounded-2xl p-6 hover:border-gray-600 transition-all group relative overflow-hidden"
          >
            {/* Subtle Gradient Background */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-600/5 blur-3xl pointer-events-none" />
            
            <div className="flex justify-between items-start mb-6">
              <div className="space-y-1">
                <h3 className="font-bold text-lg group-hover:text-amber-500 transition-colors">{item.title}</h3>
                <p className="text-xs font-mono text-gray-500 tracking-wider">{item.id}</p>
              </div>
              <div className="flex gap-2">
                <Badge className={`${getStatusColor(item.status)} border-none text-[10px] uppercase px-2 py-0.5`}>
                  {item.status}
                </Badge>
                <Badge variant="outline" className={`${getPriorityColor(item.priority)} text-[10px] uppercase`}>
                  {item.priority}
                </Badge>
              </div>
            </div>

            <div className="space-y-3 mb-8">
              <div className="flex items-center gap-3 text-gray-400">
                <UserIcon className="size-4" />
                <span className="text-sm font-medium text-gray-300">Investigator: {item.investigator}</span>
              </div>
              <div className="flex items-center gap-3 text-gray-400">
                <Calendar className="size-4" />
                <span className="text-sm">Created: {item.created}</span>
              </div>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-gray-800/50">
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" className="size-8 text-gray-400 hover:text-white hover:bg-gray-800">
                  <Eye className="size-4" />
                </Button>
                <Button variant="ghost" size="icon" className="size-8 text-gray-400 hover:text-amber-500 hover:bg-gray-800">
                  <Edit3 className="size-4" />
                </Button>
                <Button variant="ghost" size="icon" className="size-8 text-gray-400 hover:text-red-500 hover:bg-gray-800">
                  <Trash2 className="size-4" />
                </Button>
              </div>
              <Button variant="ghost" size="icon" className="size-8 text-gray-500">
                <MoreHorizontal className="size-4" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Summary Stats matching the design */}
      <div className="grid grid-cols-3 gap-4 pt-8">
        {[
          { label: "Total Case", val: 20, color: "text-amber-500" },
          { label: "Active Case", val: 15, color: "text-green-500" },
          { label: "Closed", val: 5, color: "text-blue-500" },
        ].map((stat, i) => (
          <div key={i} className="bg-gray-950/30 border border-gray-800/50 p-4 rounded-xl text-center">
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.val}</p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-gray-600 font-bold mt-1">{stat.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}