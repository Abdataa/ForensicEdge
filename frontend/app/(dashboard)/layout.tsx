"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Database, 
  Cpu, 
  GitBranch, 
  FolderOpen,      
  User,
  Settings,
  LogOut,
  Search,
  Bell,
  ChevronDown,
  Briefcase,
  History,
  Activity,
  MonitorDot,
} from "lucide-react";

import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  
  const [mounted, setMounted] = useState(false);
  const [userRole, setUserRole] = useState<string>("analyst");

  const getHomePath = (role: string) => {
    if (role === "admin") return "/admin";
    if (role === "ai_engineer") return "/engineer";
    return "/analyst";
  };

  useEffect(() => {
    setMounted(true);
    const storedRole = localStorage.getItem("userRole");
    
    if (pathname.startsWith('/analyst')) {
      setUserRole('analyst');
    } else if (pathname.startsWith('/engineer')) {
      setUserRole('ai_engineer');
    } else if (pathname.startsWith('/admin')) {
      setUserRole('admin');
    } else if (storedRole) {
      setUserRole(storedRole);
    }

    if (!storedRole && pathname !== "/login") {
      router.push("/login");
    }
  }, [router, pathname]);

  const handleLogout = () => {
    localStorage.removeItem("userRole");
    localStorage.removeItem("userName");
    router.push("/login");
  };

  const isActive = (path: string) => {
    if (path === "/analyst" || path === "/admin" || path === "/engineer") {
        return pathname === path;
    }
    return pathname.startsWith(path);
  };

  // Navigation Items
  const analystItems = [
    { path: "/analyst", label: "DashBoard", icon: LayoutDashboard },
    { path: "/analyst/cases", label: "Case Management", icon: FolderOpen },
    { path: "/analyst/profile", label: "User Profile", icon: User },
    { path: "/analyst/settings", label: "Settings", icon: Settings },
    { path: "/analyst/feedback", label: "System Feedback", icon: MonitorDot },
  ];

  const engineerItems = [
    { path: "/engineer", label: "DashBoard", icon: LayoutDashboard },
    { path: "/engineer/datasets", label: "Dataset Management", icon: Database },
    { path: "/engineer/training", label: "Model Training", icon: Cpu },
    { path: "/engineer/versions", label: "Model Version", icon: GitBranch },
  ];

  const adminItems = [
    { path: "/admin", label: "Dashboard", icon: LayoutDashboard },
    { path: "/admin/cases", label: "Case Management", icon: Briefcase },
    { path: "/admin/users", label: "User Management", icon: User },
    { path: "/admin/logs", label: "Activity Logs", icon: History },
    { path: "/admin/monitoring", label: "System Monitoring", icon: Activity },
    { path: "/admin/settings", label: "Settings", icon: Settings },
  ];

  const renderNavLink = (item: { path: string; label: string; icon: any }) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    return (
      <Link
        key={item.path}
        href={item.path}
        className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all border-l-4 ${
          active 
            ? "bg-amber-600/10 text-white border-amber-600 shadow-md shadow-amber-900/5" 
            : "text-gray-400 hover:text-white hover:bg-gray-800 border-transparent"
        }`}
      >
        <Icon className={`size-5 ${active ? "text-amber-500" : ""}`} />
        <span className="font-medium">{item.label}</span>
      </Link>
    );
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen flex flex-col bg-gray-900 text-white font-sans antialiased overflow-x-hidden">
      {/* HEADER */}
      <header className="bg-gray-950 border-b border-gray-800 sticky top-0 z-50 h-[73px]">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-8">
            <Link href={getHomePath(userRole)} className="text-xl font-bold text-amber-500 tracking-tighter uppercase">
              Forensic<span className="text-white">Edge</span>
            </Link>
            <div className="relative hidden md:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
              <Input
                placeholder="Search database..."
                className="pl-10 w-80 bg-gray-900 border-gray-800 text-white focus:border-amber-600 transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Badge variant="outline" className="border-gray-700 text-gray-400 uppercase tracking-widest text-[10px] bg-gray-900 px-2 py-0.5">
              Secure Session
            </Badge>
            <Button variant="ghost" size="icon" className="relative text-gray-400 hover:text-white">
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
                <DropdownMenuItem onClick={() => router.push("/profile")} className="hover:bg-gray-800 cursor-pointer py-3">
                  <User className="size-4 mr-2 text-amber-500" /> Profile Settings
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/settings")} className="hover:bg-gray-800 cursor-pointer py-3">
                  <Settings className="size-4 mr-2 text-amber-500" /> System Preferences
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-gray-800" />
                <DropdownMenuItem onClick={handleLogout} className="text-red-400 hover:bg-red-950/30 cursor-pointer py-3">
                  <LogOut className="size-4 mr-2" /> Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        {/* SIDEBAR */}
        <aside className="w-64 bg-gray-950 border-r border-gray-800 h-[calc(100vh-73px)] sticky top-[73px] overflow-y-auto shrink-0">
          <nav className="p-4 flex flex-col h-full">
            <div className="space-y-1">
              {userRole === "admin" && adminItems.map(renderNavLink)}
              {userRole === "analyst" && analystItems.map(renderNavLink)}
              {userRole === "ai_engineer" && engineerItems.map(renderNavLink)}
            </div>

            <div className="mt-auto pt-4 border-t border-gray-800/50">
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

        {/* MAIN DASHBOARD CONTENT */}
        <main className="flex-1 p-8 bg-gray-900 min-h-[calc(100vh-73px)] relative overflow-y-auto">
          {/* Subtle Ambient Glow */}
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-amber-600/5 blur-[120px] pointer-events-none rounded-full" />
          <div className="relative z-10 max-w-7xl mx-auto w-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}