"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Shield, Eye, EyeOff, Lock, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    // --- MOCK BACKEND LOGIC (For Friday Demo) ---
    setTimeout(() => {
      let mockRole = "";

      if (email === "analyst@astu.et") mockRole = "analyst";
      else if (email === "engineer@astu.et") mockRole = "ai_engineer";
      else if (email === "admin@astu.et") mockRole = "admin";

      if (mockRole && password === "password123") {
        localStorage.setItem("userRole", mockRole);
        localStorage.setItem("userName", "Mary");
        router.push("/dashboard");
      } else {
        alert("Invalid credentials. Try analyst@astu.et / password123");
      }
      setIsLoading(false);
    }, 1000); 
  };

  return (
    <div className="flex min-h-screen bg-gray-950">
      {/* LEFT COLUMN: Login Form (Using Figma Ochre Color) */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center px-8 md:px-16 lg:px-24 bg-[#A1773B] border-r border-gray-800">
        <div className="max-w-md w-full mx-auto space-y-8">
          <div>
            <h2 className="text-4xl font-bold text-white tracking-tight">Welcome Back</h2>
            <p className="text-white mt-2 font-medium">Enter your credentials to access the ForensicEdge terminal.</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-4">
              {/* Email Input */}
              <div className="relative group">
                <Mail className="absolute left-3 top-3 size-5 text-white group-focus-within:text-white/80 transition-colors" />
                <Input
                  type="email"
                  placeholder="Email Address"
                  className="pl-10 bg-black/20 border-white/20 text-white placeholder:text-white/60 h-12 focus:border-white focus:ring-1 focus:ring-white rounded-xl transition-all"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              {/* Password Input */}
              <div className="relative group">
                <Lock className="absolute left-3 top-3 size-5 text-white group-focus-within:text-white/80 transition-colors" />
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  className="pl-10 bg-black/20 border-white/20 text-white placeholder:text-white/60 h-12 focus:border-white focus:ring-1 focus:ring-white rounded-xl transition-all"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-white/70 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="remember" 
                  className="border-white/50 data-[state=checked]:bg-black data-[state=checked]:border-black" 
                />
                <label htmlFor="remember" className="text-sm text-white cursor-pointer hover:text-gray-100">
                  Remember Me
                </label>
              </div>
              <button type="button" className="text-sm text-white hover:underline transition-colors">
                Forgot Password?
              </button>
            </div>

            <Button 
              type="submit" 
              disabled={isLoading}
              className="w-full bg-black hover:bg-gray-900 text-white font-bold h-12 rounded-xl transition-all shadow-lg active:scale-[0.98]"
            >
              {isLoading ? "Authenticating..." : "Sign In"}
            </Button>
          </form>

          <p className="text-center text-white/80 text-sm">
            Need an account? <button className="text-white font-semibold hover:underline">Request Access</button>
          </p>
        </div>
      </div>

      {/* RIGHT COLUMN: Full Image Branding (RESTORED EXACTLY) */}
      <div className="hidden lg:flex w-1/2 relative bg-gray-950 items-center justify-center overflow-hidden">
        
        {/* Background Image Container */}
        <div className="absolute inset-0 z-0">
          <Image
            src="/images/login-bg.jpg"
            alt="Forensic Investigation Background"
            fill
            unoptimized
            className="object-cover opacity-50 grayscale hover:grayscale-0 transition-all duration-[2000ms]"
            priority
          />
          {/* Deep gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-r from-gray-950 via-gray-950/40 to-transparent" />
        </div>
        
        {/* Foreground Content */}
        <div className="relative z-10 text-center space-y-6">
          <div className="inline-block p-5 bg-gray-900/80 backdrop-blur-md border border-amber-600/30 rounded-3xl shadow-2xl shadow-black/50">
            <Shield className="size-20 text-amber-500" strokeWidth={1.2} />
          </div>
          
          <div className="space-y-2">
            <h1 className="text-5xl font-extrabold tracking-[0.25em] text-white uppercase italic">
              ForensicEdge
            </h1>
            <div className="h-1.5 w-24 bg-amber-600 mx-auto rounded-full shadow-[0_0_15px_rgba(217,119,6,0.6)]" />
          </div>
          
          <p className="text-gray-400 tracking-widest text-xs uppercase font-medium">
            AI OPTIMIZED EVIDENCE ANALYSIS
          </p>
        </div>

        <div className="absolute bottom-0 right-0 size-96 bg-amber-600/10 blur-[120px] rounded-full -mr-48 -mb-48" />
      </div>
    </div>
  );
}