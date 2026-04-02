"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Folder,
  Upload,
  Activity,
  FileText,
  Plus,
  Play,
  CheckCircle2,
  Clock,
  Database,
  Cpu,
  Calendar,
  ShieldAlert,
  Users,
  LogOut,
} from "lucide-react";

import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";

import { Badge } from "../../components/ui/badge";

const stats = [
  {
    label: "Active Cases",
    value: "12",
    icon: Folder,
    color: "text-amber-500",
    bgColor: "bg-amber-950",
  },
  {
    label: "Evidence Uploaded",
    value: "487",
    icon: Upload,
    color: "text-emerald-500",
    bgColor: "bg-emerald-950",
  },
  {
    label: "Analyses Done",
    value: "1,234",
    icon: Activity,
    color: "text-purple-500",
    bgColor: "bg-purple-950",
  },
  {
    label: "Reports Generated",
    value: "89",
    icon: FileText,
    color: "text-orange-500",
    bgColor: "bg-orange-950",
  },
];

const recentCases = [
  {
    id: "CASE102",
    evidence: "fingerprint.png",
    status: "Analyzed",
    analyst: "Mary",
    date: "Mar 6",
  },
  {
    id: "CASE101",
    evidence: "toolmark.png",
    status: "Pending",
    analyst: "Mary",
    date: "Mar 5",
  },
  {
    id: "CASE100",
    evidence: "fingerprint.jpg",
    status: "Analyzed",
    analyst: "J. Smith",
    date: "Mar 4",
  },
  {
    id: "CASE098",
    evidence: "toolmark.png",
    status: "Analyzed",
    analyst: "Mary",
    date: "Mar 2",
  },
];

const getStatusBadge = (status: string) => {
  switch (status) {
    case "Analyzed":
      return (
        <Badge className="bg-emerald-900 text-emerald-300 border-emerald-700">
          <CheckCircle2 className="size-3 mr-1" />
          {status}
        </Badge>
      );

    case "Pending":
      return (
        <Badge className="bg-yellow-900 text-yellow-300 border-yellow-700">
          <Clock className="size-3 mr-1" />
          {status}
        </Badge>
      );

    case "Processing":
      return (
        <Badge className="bg-blue-900 text-blue-300 border-blue-700">
          <Activity className="size-3 mr-1" />
          {status}
        </Badge>
      );

    default:
      return <Badge variant="outline">{status}</Badge>;
  }
};

export default function DashboardPage() {
  const router = useRouter();
  const [userRole, setUserRole] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);

  useEffect(() => {
    const role = localStorage.getItem("userRole");
    const name = localStorage.getItem("userName");
    
    if (!role) {
      router.push("/login");
    } else {
      setUserRole(role);
      setUserName(name);
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("userRole");
    localStorage.removeItem("userName");
    router.push("/login");
  };

  const navigate = (path: string) => router.push(path);

  if (!userRole) return null; 

  return (
    <div className="space-y-8 p-8 bg-gray-950 min-h-screen">
      {/* HEADER WITH LOGOUT */}
      <div className="flex justify-between items-start border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white uppercase tracking-tight">
            {userRole === "admin" ? "Admin Control Center" : 
             userRole === "ai_engineer" ? "Engineering Terminal" : 
             "Forensic Dashboard"}
          </h1>
          <p className="text-gray-400 mt-1">
            Access Level: <span className="text-amber-500 font-mono uppercase ml-1">{userRole.replace("_", " ")}</span>
          </p>
        </div>
        <Button 
          variant="ghost" 
          onClick={handleLogout}
          className="text-gray-400 hover:text-red-400 hover:bg-red-950/30 transition-all gap-2"
        >
          <LogOut className="size-4" />
          Logout
        </Button>
      </div>

      {/* Stats Section */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">
          {userRole === "ai_engineer" ? "System Throughput" : "Case Overview"}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat) => {
            const Icon = stat.icon;

            return (
              <Card key={stat.label} className="bg-gray-800 border-gray-700">
                <CardContent className="p-6 flex justify-between items-center">
                  <div>
                    <p className="text-sm text-gray-400">{stat.label}</p>
                    <p className="text-3xl font-bold mt-2 text-white">
                      {stat.value}
                    </p>
                  </div>

                  <div className={`${stat.bgColor} p-3 rounded-lg`}>
                    <Icon className={`size-6 ${stat.color}`} />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">
          Management & Actions
        </h2>

        <div className="flex gap-4 flex-wrap">
          {userRole === "analyst" && (
            <>
              <Button
                size="lg"
                className="gap-2 bg-amber-600 hover:bg-amber-700 text-white"
                onClick={() => navigate("/dashboard/upload")}
              >
                <Plus className="size-5" />
                Upload Evidence
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 border-gray-600 text-gray-300 hover:bg-gray-800"
                onClick={() => navigate("/dashboard/analysis")}
              >
                <Play className="size-5" />
                Start Analysis
              </Button>
            </>
          )}

          {userRole === "ai_engineer" && (
            <>
              <Button
                size="lg"
                className="gap-2 bg-blue-600 hover:bg-blue-700 text-white"
                onClick={() => navigate("/dashboard/monitoring")}
              >
                <Activity className="size-5" />
                Monitor Models
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 border-gray-600 text-gray-300 hover:bg-gray-800"
                onClick={() => navigate("/dashboard/feedback")}
              >
                <FileText className="size-5" />
                Retraining Data
              </Button>
            </>
          )}

          {userRole === "admin" && (
            <>
              <Button
                size="lg"
                className="gap-2 bg-red-600 hover:bg-red-700 text-white"
                onClick={() => navigate("/dashboard/admin")}
              >
                <Users className="size-5" />
                User Management
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="gap-2 border-gray-600 text-gray-300 hover:bg-gray-800"
                onClick={() => navigate("/dashboard/history")}
              >
                <ShieldAlert className="size-5" />
                Security Audit
              </Button>
            </>
          )}

          <Button
            size="lg"
            variant="outline"
            className="gap-2 border-gray-600 text-gray-300 hover:bg-gray-800"
            onClick={() => navigate("/dashboard/reports")}
          >
            <FileText className="size-5" />
            Generate Report
          </Button>
        </div>
      </div>

      {/* Recent Investigations */}
      {(userRole === "analyst" || userRole === "admin") && (
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">
            Recent Investigations
          </h2>

          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-gray-700 hover:bg-transparent">
                    <TableHead>Case ID</TableHead>
                    <TableHead>Evidence</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Analyst</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {recentCases.map((case_) => (
                    <TableRow
                      key={case_.id}
                      className="cursor-pointer hover:bg-gray-700 border-gray-700"
                      onClick={() => navigate("/dashboard/history")}
                    >
                      <TableCell className="text-white font-medium">
                        {case_.id}
                      </TableCell>

                      <TableCell className="text-gray-300">
                        {case_.evidence}
                      </TableCell>

                      <TableCell>{getStatusBadge(case_.status)}</TableCell>

                      <TableCell className="text-gray-300">
                        {case_.analyst}
                      </TableCell>

                      <TableCell className="text-gray-400">
                        {case_.date}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Infrastructure Section */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">
          Core Infrastructure
        </h2>

        <Card className="bg-gray-800 border-gray-700">
          <CardContent className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-center gap-4">
              <Cpu className="text-emerald-500" />
              <div>
                <p className="text-gray-400 text-sm">AI Engine</p>
                <p className="text-emerald-400 font-semibold">Running (v4.2)</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Database className="text-emerald-500" />
              <div>
                <p className="text-gray-400 text-sm">Forensic DB</p>
                <p className="text-emerald-400 font-semibold">Healthy</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Calendar className="text-amber-500" />
              <div>
                <p className="text-gray-400 text-sm">Security Patch</p>
                <p className="text-white font-semibold italic">Deployed Mar 2026</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}