"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Shield, Eye, EyeOff } from "lucide-react";
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

    // Mock Authentication Logic
    setTimeout(() => {
      let mockRole = "";
      let targetPath = "";

      if (email === "admin@astu.et") {
        mockRole = "admin";
        targetPath = "/admin";
      } else if (email === "analyst@astu.et") {
        mockRole = "analyst";
        targetPath = "/analyst";
      } else if (email === "engineer@astu.et") {
        mockRole = "ai_engineer";
        targetPath = "/engineer";
      }

      if (mockRole && password === "password123") {
        localStorage.setItem("userRole", mockRole);
        localStorage.setItem("userName", "Mary");
        router.push(targetPath);
      } else {
        alert("Invalid credentials.");
      }
      setIsLoading(false);
    }, 1000);
  };

  return (
    <main className="flex min-h-screen w-full overflow-hidden">
      {/* LEFT COLUMN: Login Form (Ochre background) */}
      <section className="w-full lg:w-1/2 flex flex-col justify-center items-center px-8 md:px-16 bg-[#A1773B] z-10">
        <div className="max-w-md w-full space-y-8 text-white">
          <header className="space-y-2">
            <h2 className="text-3xl font-bold tracking-tight">Welcome Back</h2>
            <p className="text-sm opacity-90">Sign in to access your forensic analysis tools</p>
          </header>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium block">Email</label>
                <Input
                  type="email"
                  placeholder="Enter your email"
                  className="bg-black/10 border-none text-white placeholder:text-white/50 h-12 focus-visible:ring-1 focus-visible:ring-white w-full"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium block">Password</label>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your Password"
                    className="bg-black/10 border-none text-white placeholder:text-white/50 h-12 focus-visible:ring-1 focus-visible:ring-white w-full pr-12"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/70 hover:text-white transition-colors"
                  >
                    {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2">
                <Checkbox id="remember" className="border-white/50 data-[state=checked]:bg-white data-[state=checked]:text-[#A1773B]" />
                <label htmlFor="remember" className="cursor-pointer">Remember me</label>
              </div>
              <button type="button" className="hover:underline">Forgot Password?</button>
            </div>

            <Button 
              type="submit" 
              className="w-full bg-black hover:bg-black/80 text-white font-bold h-12 rounded-md transition-all uppercase tracking-wider"
              disabled={isLoading}
            >
              {isLoading ? "Authenticating..." : "Sign in"}
            </Button>
          </form>

          <footer className="text-center space-y-4 pt-4">
            <p className="text-sm">
              Don't have an account? <button className="font-bold hover:underline">Request Access</button>
            </p>
            <p className="text-[10px] opacity-70 uppercase tracking-[0.2em]">Secure encrypted connection</p>
          </footer>
        </div>
      </section>

      {/* RIGHT COLUMN: Full Background Image */}
      <section className="hidden lg:flex w-1/2 flex-col items-center justify-center relative">
        {/* Background Image filling the entire section */}
        <div className="absolute inset-0 z-0">
          <Image
            src="/images/login-bg.jpg"
            alt="Forensic Investigation"
            fill
            className="object-cover"
            priority
          />
          {/* Overlay to ensure text remains readable */}
          <div className="absolute inset-0 bg-black/40" />
        </div>

        {/* Branding content sitting on top of the image */}
        <div className="text-center space-y-6 z-10">
          <div className="flex justify-center">
             <div className="p-4 rounded-full border border-amber-500/30 bg-black/20 backdrop-blur-sm">
                <Shield className="size-12 text-amber-500" strokeWidth={1.5} />
             </div>
          </div>
          <h1 className="text-4xl font-light tracking-[0.4em] text-white uppercase drop-shadow-2xl">
            Forensic<span className="font-bold">Edge</span>
          </h1>
        </div>
        
        {/* Bottom glow effect */}
        <div className="absolute bottom-0 right-0 w-full h-1/3 bg-gradient-to-t from-black to-transparent z-5 pointer-events-none" />
      </section>
    </main>
  );
}