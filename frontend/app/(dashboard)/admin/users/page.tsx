"use client";

import { useState } from "react";
import { Search, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const USERS_DATA = [
  { name: "Meron Tilahun", email: "merontilahun@gmail.com", role: "Analyst", status: "Pending", date: "April 1" },
  { name: "Meti Jemal", email: "metijemal@gmail.com", role: "AI Engineer", status: "Pending", date: "Mar 11" },
  { name: "Abdi Dawid", email: "abdidawid@gmail.com", role: "Analyst", status: "Active", date: "Mar 20" },
  { name: "Abdellah Omar", email: "abdellahmar@gmail.com", role: "AI Engineer", status: "Active", date: "Mar 30" },
  { name: "Abebe Kumbi", email: "abebekumbi@gmail.com", role: "Analyst", status: "Disabled", date: "Mar 31" },
  { name: "Nancy Jemal", email: "nancyjemal@gmail.com", role: "AI Engineer", status: "Rejected", date: "Mar 31" },
];

export default function UserManagement() {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">User Management</h1>
        <p className="text-gray-400 mt-1">Manage users and permissions</p>
      </div>

      <div className="flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 min-w-[300px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-500" />
          <Input 
            placeholder="search cases" 
            className="pl-10 bg-[#120f0e] border-none text-gray-300 h-12 rounded-lg"
          />
        </div>
        
        <Select>
          <SelectTrigger className="w-[180px] bg-[#a37c53] border-none text-[#1a1614] font-bold h-12 rounded-lg">
            <SelectValue placeholder="All Roles" />
          </SelectTrigger>
          <SelectContent className="bg-[#1a1614] border-gray-800 text-white">
            <SelectItem value="all">All Roles</SelectItem>
            <SelectItem value="analyst">Analyst</SelectItem>
            <SelectItem value="engineer">AI Engineer</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="bg-[#1a1614] border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="text-[#a37c53] font-bold text-[13px]">
              <th className="px-6 py-5">Name</th>
              <th className="px-6 py-5">Email</th>
              <th className="px-6 py-5 text-center">Role</th>
              <th className="px-6 py-5 text-center">Status</th>
              <th className="px-6 py-5">Date</th>
              <th className="px-6 py-5 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/30 text-gray-300">
            {USERS_DATA.map((user, i) => (
              <tr key={i} className="hover:bg-white/[0.02]">
                <td className="px-6 py-4 text-sm">{user.name}</td>
                <td className="px-6 py-4 text-sm underline decoration-gray-700 underline-offset-4">{user.email}</td>
                <td className="px-6 py-4 text-center">
                  <span className="text-[10px] bg-gray-800/50 px-2 py-1 rounded border border-gray-700 text-gray-400">
                    {user.role}
                  </span>
                </td>
                <td className="px-6 py-4 text-center">
                  <span className={`text-[10px] px-2 py-1 rounded font-bold ${getStatusStyle(user.status)}`}>
                    {user.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-400">{user.date}</td>
                <td className="px-6 py-4">
                  <div className="flex justify-center gap-2">
                    {renderActions(user.status)}
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

// Logic to match the color coded statuses in image_92fe30.png
function getStatusStyle(status: string) {
  switch (status) {
    case "Pending": return "bg-amber-900/20 text-amber-500";
    case "Active": return "bg-green-900/20 text-green-500";
    case "Disabled": return "bg-gray-800 text-gray-400";
    case "Rejected": return "bg-red-900/20 text-red-500";
    default: return "";
  }
}

// Logic to match the dynamic action buttons
function renderActions(status: string) {
  if (status === "Pending") {
    return (
      <>
        <Button size="sm" className="bg-green-600 hover:bg-green-700 h-7 text-[10px] px-3">Approve</Button>
        <Button size="sm" className="bg-red-600 hover:bg-red-700 h-7 text-[10px] px-3">Reject</Button>
      </>
    );
  }
  if (status === "Active") {
    return (
      <>
        <Button variant="outline" size="sm" className="border-gray-700 h-7 text-[10px] px-3">Disable</Button>
        <Button variant="outline" size="sm" className="border-gray-700 h-7 text-[10px] px-3">Edit</Button>
      </>
    );
  }
  if (status === "Disabled") {
    return (
      <>
        <Button size="sm" className="bg-green-600/20 text-green-500 hover:bg-green-600/30 h-7 text-[10px] px-3">Reactivate</Button>
        <Button variant="outline" size="sm" className="border-gray-700 h-7 text-[10px] px-3">Edit</Button>
      </>
    );
  }
  return <span className="text-[10px] text-gray-600 italic">No actions</span>;
}