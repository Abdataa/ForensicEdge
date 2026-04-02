"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  Activity,
  History,
  FileText,
  User,
  Settings,
  LogOut,
  Search,
  Bell,
  ChevronDown,
  ArrowRightLeft,
  MessageSquare,
  ShieldAlert,
} from "lucide-react";

import { Input } from "../../components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  
  const [mounted, setMounted] = useState(false);
  const [userRole, setUserRole] = useState<string>("analyst");

  useEffect(() => {
    setMounted(true);
    const storedRole = localStorage.getItem("userRole");
    
    if (!storedRole) {
      router.push("/login");
    } else {
      setUserRole(storedRole);
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("userRole");
    localStorage.removeItem("userName");
    router.push("/login");
  };

  const isActive = (path: string) => {
    if (path === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(path);
  };

  // 1. Shared links visible to everyone
  const sharedItems = [
    { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { path: "/dashboard/profile", label: "User Profile", icon: User },
    { path: "/dashboard/settings", label: "Settings", icon: Settings },
  ];

  // 2. Forensic Analyst Toolkit
  const analystItems = [
    { path: "/dashboard/upload", label: "Upload Evidence", icon: Upload },
    { path: "/dashboard/analysis", label: "Analysis Results", icon: Activity },
    { path: "/dashboard/compare", label: "Cross-Case Compare", icon: ArrowRightLeft },
    { path: "/dashboard/history", label: "Evidence History", icon: History },
    { path: "/dashboard/reports", label: "Reports", icon: FileText },
  ];

  // 3. AI Engineer Toolkit
  const engineerItems = [
    { path: "/dashboard/monitoring", label: "System Monitoring", icon: Activity },
    { path: "/dashboard/feedback", label: "Review Flags", icon: MessageSquare },
  ];

  // 4. Admin Toolkit
  const adminItems = [
    { path: "/dashboard/admin", label: "User Management", icon: ShieldAlert },
    { path: "/dashboard/history", label: "Audit Logs", icon: History },
  ];

  const renderNavLink = (item: { path: string; label: string; icon: any }) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    return (
      <Link
        key={item.path}
        href={item.path}
        className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
          active 
            ? "bg-amber-600 text-white shadow-lg shadow-amber-900/20" 
            : "text-gray-400 hover:text-white hover:bg-gray-800"
        }`}
      >
        <Icon className="size-5" />
        <span className="font-medium">{item.label}</span>
      </Link>
    );
  };

  if (!mounted) {
    return <div className="min-h-screen bg-gray-950" />;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white font-sans">
      {/* Top Navigation */}
      <header className="bg-gray-950 border-b border-gray-800 sticky top-0 z-50">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="text-xl font-bold text-amber-500 tracking-tighter uppercase">
              Forensic<span className="text-white">Edge</span>
            </Link>
            <div className="relative hidden md:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
              <Input
                placeholder="Search database..."
                className="pl-10 w-80 bg-gray-900 border-gray-800 text-white placeholder:text-gray-500 focus:border-amber-600 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Badge variant="outline" className="border-gray-700 text-gray-400 uppercase tracking-widest text-[10px] bg-gray-900 px-2 py-0.5">
              Secure Session
            </Badge>
            
            <Button variant="ghost" size="icon" className="relative text-gray-400 hover:text-white hover:bg-gray-800">
              <Bell className="size-5" />
              <Badge className="absolute -top-1 -right-1 size-4 flex items-center justify-center p-0 text-[10px] bg-amber-600 border-none">3</Badge>
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="gap-3 text-gray-300 hover:bg-gray-800 transition-all">
                  <div className="size-8 rounded-md bg-gray-800 flex items-center justify-center text-gray-400 border border-gray-700 shadow-md">
                    <User className="size-5" />
                  </div>
                  <div className="text-left hidden lg:block">
                    <p className="text-sm font-semibold leading-none">Account</p>
                    <p className="text-[10px] text-gray-500 uppercase mt-1 tracking-tighter">{userRole.replace('_', ' ')}</p>
                  </div>
                  <ChevronDown className="size-4 text-gray-500" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 bg-gray-900 border-gray-800 text-white">
                <DropdownMenuItem onClick={() => router.push("/dashboard/profile")} className="hover:bg-gray-800 cursor-pointer py-3">
                  <User className="size-4 mr-2 text-amber-500" /> Profile Settings
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/dashboard/settings")} className="hover:bg-gray-800 cursor-pointer py-3">
                  <Settings className="size-4 mr-2 text-amber-500" /> System Preferences
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-gray-800" />
                <DropdownMenuItem onClick={handleLogout} className="text-red-400 hover:bg-red-950/30 cursor-pointer py-3 focus:text-red-400">
                  <LogOut className="size-4 mr-2" /> Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-gray-950 border-r border-gray-800 min-h-[calc(100vh-73px)] sticky top-[73px] overflow-y-auto scrollbar-hide">
          <nav className="p-4 space-y-8">
            
            <div className="space-y-1">
              <p className="px-4 text-[10px] font-bold text-gray-600 uppercase tracking-[0.2em] mb-3">Dashboard</p>
              {sharedItems.map(renderNavLink)}
            </div>

            {userRole === "analyst" && (
              <div className="space-y-1 animate-in fade-in slide-in-from-left-2 duration-300">
                <p className="px-4 text-[10px] font-bold text-gray-600 uppercase tracking-[0.2em] mb-3">Forensic Lab</p>
                {analystItems.map(renderNavLink)}
              </div>
            )}

            {userRole === "ai_engineer" && (
              <div className="space-y-1 animate-in fade-in slide-in-from-left-2 duration-300">
                <p className="px-4 text-[10px] font-bold text-gray-600 uppercase tracking-[0.2em] mb-3">ML Infrastructure</p>
                {engineerItems.map(renderNavLink)}
              </div>
            )}

            {userRole === "admin" && (
              <div className="space-y-1 animate-in fade-in slide-in-from-left-2 duration-300">
                <p className="px-4 text-[10px] font-bold text-gray-600 uppercase tracking-[0.2em] mb-3">System Control</p>
                {adminItems.map(renderNavLink)}
              </div>
            )}

            <div className="pt-4 border-t border-gray-800/50">
              <button
                className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-950/10 w-full transition-all group"
                onClick={handleLogout}
              >
                <LogOut className="size-5 transition-transform group-hover:-translate-x-1" />
                <span className="font-medium text-sm">Logout</span>
              </button>
            </div>
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-8 bg-gray-900 min-h-[calc(100vh-73px)] relative overflow-x-hidden">
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-amber-600/5 blur-[120px] pointer-events-none rounded-full" />
          <div className="relative z-10">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}