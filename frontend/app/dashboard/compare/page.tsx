"use client";

import { useState, useEffect } from "react";
import { Upload, ArrowRightLeft, ShieldCheck, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function ComparePage() {
  const [isMounted, setIsMounted] = useState(false);
  const [imageA, setImageA] = useState<string | null>(null);
  const [imageB, setImageB] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [score, setScore] = useState<number | null>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, side: 'A' | 'B') => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        side === 'A' ? setImageA(reader.result as string) : setImageB(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const runComparison = () => {
    setComparing(true);
    // This is where you'll call the FastAPI /compare endpoint later
    setTimeout(() => {
      setScore(94.2); // Mock score for the demo
      setComparing(false);
    }, 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white">Cross-Case Analysis</h1>
          <p className="text-gray-400 mt-1">Manual one-to-one evidence verification</p>
        </div>
        {imageA && imageB && (
          <Button 
            onClick={runComparison} 
            disabled={comparing}
            className="bg-amber-600 hover:bg-amber-700 text-white"
          >
            {comparing ? "Analyzing Pattern..." : "Run AI Comparison"}
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative">
        {/* Connection Icon */}
        <div className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 size-12 bg-gray-900 border border-gray-700 rounded-full items-center justify-center text-amber-500">
          <ArrowRightLeft className="size-6" />
        </div>

        {/* Side A */}
        <Card className="bg-gray-800 border-gray-700 overflow-hidden">
          <CardHeader className="bg-gray-900/50 border-b border-gray-700">
            <CardTitle className="text-sm font-medium text-gray-400 uppercase tracking-wider">Evidence Sample A</CardTitle>
          </CardHeader>
          <CardContent className="p-0 aspect-square flex items-center justify-center bg-gray-950 relative">
            {imageA ? (
              <img src={imageA} alt="Evidence A" className="object-contain h-full w-full" />
            ) : (
              <label className="cursor-pointer flex flex-col items-center gap-2 text-gray-500 hover:text-amber-500 transition-colors">
                <Upload className="size-10" />
                <span>Upload Primary Print</span>
                <input type="file" className="hidden" onChange={(e) => handleFileChange(e, 'A')} />
              </label>
            )}
          </CardContent>
        </Card>

        {/* Side B */}
        <Card className="bg-gray-800 border-gray-700 overflow-hidden">
          <CardHeader className="bg-gray-900/50 border-b border-gray-700">
            <CardTitle className="text-sm font-medium text-gray-400 uppercase tracking-wider">Evidence Sample B</CardTitle>
          </CardHeader>
          <CardContent className="p-0 aspect-square flex items-center justify-center bg-gray-950">
             {imageB ? (
              <img src={imageB} alt="Evidence B" className="object-contain h-full w-full" />
            ) : (
              <label className="cursor-pointer flex flex-col items-center gap-2 text-gray-500 hover:text-amber-500 transition-colors">
                <Upload className="size-10" />
                <span>Upload Comparison Print</span>
                <input type="file" className="hidden" onChange={(e) => handleFileChange(e, 'B')} />
              </label>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Results Section */}
      {score && (
        <Card className="bg-gray-800 border-amber-900/30">
          <CardContent className="p-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="size-16 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-500 text-2xl font-bold">
                {score}%
              </div>
              <div>
                <h3 className="text-white font-semibold flex items-center gap-2">
                  High Similarity Detected <ShieldCheck className="size-4 text-emerald-500" />
                </h3>
                <p className="text-sm text-gray-400">Pattern minutiae suggest these samples likely originate from the same source.</p>
              </div>
            </div>
            <Button variant="outline" className="border-gray-700 text-gray-300">View Feature Map</Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}