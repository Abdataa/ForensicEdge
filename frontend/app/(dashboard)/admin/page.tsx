"use client";

import { useState } from "react";
import { 
  Users, UserPlus, Briefcase, Activity, CheckCircle2, XCircle, AlertCircle 
} from "lucide-react";
import { 
  PieChart, Pie, Cell, ResponsiveContainer, 
  BarChart, Bar, XAxis, Tooltip 
} from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// Data matching the design content
const INITIAL_APPROVALS = [
  { id: 1, name: "Alex Johnson", email: "alex.j@forensics.gov", role: "Analyst" },
  { id: 2, name: "Maria Garcia", email: "maria.g@forensics.gov", role: "AI Engineer" },
  { id: 3, name: "Robert Chen", email: "robert.c@forensics.gov", role: "Analyst" },
];

const RECENT_ACTIVITY = [
  { id: 1, user: "Meron Tilahun", action: "Uploaded fingerprint evidence", time: "2 minutes ago", status: "success" },
  { id: 2, user: "Meti Jemal", action: "Completed similarity analysis", time: "9 minutes ago", status: "success" },
  { id: 3, user: "Emma Wilson", action: "Failed upload - file too large", time: "32 minutes ago", status: "error" },
  { id: 4, user: "David Kim", action: "Generated comparison report", time: "44 minutes ago", status: "success" },
];

export default function AdminDashboard() {
  const [approvals, setApprovals] = useState(INITIAL_APPROVALS);

  const handleAction = (id: number, action: 'approve' | 'reject') => {
    // Functional logic: Remove from list upon action
    setApprovals(prev => prev.filter(item => item.id !== id));
    console.log(`${action === 'approve' ? 'Approved' : 'Rejected'} user ${id}`);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <section>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-gray-400 mt-1">System overview and analytics</p>
      </section>

      {/* Content Top: Stats with live counts */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <StatCard label="Total Users" value="1,284" icon={Users} />
        <StatCard label="Pending Approvals" value={approvals.length.toString()} icon={UserPlus} />
        <StatCard label="Total Cases" value="458" icon={Briefcase} />
        <StatCard label="Active Cases" value="89" icon={Activity} />
        <StatCard label="System Health" value="Online" icon={CheckCircle2} color="text-green-500" />
      </div>

      {/* Content Middle: Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-[#1a1614] border border-gray-800 p-6 rounded-2xl">
          <h3 className="font-semibold mb-6">Case Status Distribution</h3>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={[
                    { name: "Closed", value: 31, color: "#65a30d" },
                    { name: "Open", value: 21, color: "#0ea5e9" },
                    { name: "In progress", value: 48, color: "#eab308" },
                  ]}
                  innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value"
                >
                  <Cell fill="#65a30d" /><Cell fill="#0ea5e9" /><Cell fill="#eab308" />
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-[#1a1614] border border-gray-800 p-6 rounded-2xl">
          <h3 className="font-semibold mb-6">User Activity Trends</h3>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                { d: "Mar 28", v: 40 }, { d: "Mar 29", v: 80 }, { d: "Mar 30", v: 45 },
                { d: "Apr 1", v: 70 }, { d: "Apr 2", v: 30 }
              ]}>
                <XAxis dataKey="d" axisLine={false} tickLine={false} tick={{fill: '#6b7280'}} />
                <Bar dataKey="v" fill="#a8a29e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Content Bottom: Functional Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Activity Content */}
        <div className="space-y-4">
          <h3 className="font-semibold">Recent Activity</h3>
          <div className="space-y-3">
            {RECENT_ACTIVITY.map((act) => (
              <div key={act.id} className="bg-[#1a1614] p-4 rounded-xl border border-gray-800 flex justify-between items-start">
                <div className="flex gap-3">
                  {act.status === 'error' ? 
                    <AlertCircle className="size-4 text-red-500 mt-1" /> : 
                    <CheckCircle2 className="size-4 text-green-500 mt-1" />
                  }
                  <div>
                    <p className="font-medium text-sm">{act.user}</p>
                    <p className={`text-xs ${act.status === 'error' ? 'text-red-400' : 'text-gray-500'}`}>
                      {act.action}
                    </p>
                  </div>
                </div>
                <span className="text-[10px] text-gray-600 whitespace-nowrap">{act.time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pending Approvals Content */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Pending User Approvals</h3>
            <Badge className="bg-amber-600/10 text-amber-500">{approvals.length} Pending</Badge>
          </div>
          <div className="space-y-3">
            {approvals.map((user) => (
              <div key={user.id} className="bg-[#1a1614] p-4 rounded-xl border border-gray-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="size-10 rounded-full bg-amber-900/20 flex items-center justify-center text-amber-500 font-bold text-xs">
                    {user.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <p className="text-sm font-medium">{user.name}</p>
                    <p className="text-[10px] text-gray-500">{user.email}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button onClick={() => handleAction(user.id, 'approve')} size="sm" className="bg-green-600 hover:bg-green-700 h-8">Approve</Button>
                  <Button onClick={() => handleAction(user.id, 'reject')} size="sm" variant="destructive" className="h-8">Reject</Button>
                </div>
              </div>
            ))}
            {approvals.length === 0 && (
              <div className="text-center py-8 border-2 border-dashed border-gray-800 rounded-xl text-gray-500">
                No pending approvals
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color }: any) {
  return (
    <div className="bg-[#1a1614] border border-gray-800 p-4 rounded-xl flex items-center gap-4">
      <div className="size-10 rounded-lg bg-gray-900 flex items-center justify-center border border-gray-800">
        <Icon className="size-5 text-gray-400" />
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">{label}</p>
        <p className={`text-xl font-bold ${color || "text-white"}`}>{value}</p>
      </div>
    </div>
  );
}