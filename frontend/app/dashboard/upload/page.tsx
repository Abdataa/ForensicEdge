"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileImage, X, CheckCircle2, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Label } from "../../../components/ui/label";
import { Textarea } from "../../../components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../../components/ui/select";

export default function UploadEvidencePage() {
  const router = useRouter();
  const [isMounted, setIsMounted] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);

  // Form states for integration
  const [caseId, setCaseId] = useState("");
  const [evidenceType, setEvidenceType] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUploading(true);

    // INTEGRATION POINT: This is where you connect to FastAPI
    try {
      const formData = new FormData();
      formData.append("case_id", caseId);
      formData.append("evidence_type", evidenceType);
      formData.append("description", description);
      files.forEach((file) => formData.append("files", file));

      // Example: await fetch('http://localhost:8000/api/upload', { method: 'POST', body: formData });
      
      // Mocking the delay for the MVP demo
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      setUploaded(true);
      
      router.push('/dashboard/analysis');
      setFiles([]);
      setCaseId("");
      setDescription("");
      
      setTimeout(() => setUploaded(false), 5000);
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6 bg-gray-950 min-h-screen">
      <div>
        <h1 className="text-3xl font-bold text-white">Upload Evidence</h1>
        <p className="text-gray-400 mt-1">
          Submit forensic data to the AI Analysis Engine
        </p>
      </div>

      {uploaded && (
        <div className="bg-emerald-950 border border-emerald-800 rounded-lg p-4 flex items-center gap-3 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="size-5 text-emerald-400" />
          <p className="text-emerald-300 font-medium">
            Evidence successfully queued for processing!
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Case Information Card */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white text-lg">Case Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="caseId" className="text-gray-300">Case Identifier</Label>
                <Input
                  id="caseId"
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  placeholder="e.g., FRNSC-2026-001"
                  required
                  className="bg-gray-900 border-gray-700 text-white placeholder:text-gray-600 focus:border-amber-500"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="evidenceType" className="text-gray-300">Evidence Classification</Label>
                <Select onValueChange={setEvidenceType} required>
                  <SelectTrigger
                    id="evidenceType"
                    className="bg-gray-900 border-gray-700 text-white focus:ring-amber-500"
                  >
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-800 border-gray-700 text-white">
                    <SelectItem value="fingerprint">Latent Fingerprint</SelectItem>
                    <SelectItem value="toolmark">Striation Toolmark</SelectItem>
      
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description" className="text-gray-300">Case Description & Notes</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Details for the AI model context..."
                rows={4}
                className="bg-gray-900 border-gray-700 text-white placeholder:text-gray-600 focus:border-amber-500"
              />
            </div>
          </CardContent>
        </Card>

        {/* File Upload Card */}
        <Card className="bg-gray-800 border-gray-700">
          <CardHeader>
            <CardTitle className="text-white text-lg">Evidence Files</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="group border-2 border-dashed border-gray-700 rounded-xl p-10 text-center hover:border-amber-500 hover:bg-gray-900/50 transition-all duration-200">
              <input
                type="file"
                id="fileUpload"
                className="hidden"
                onChange={handleFileChange}
                multiple
                accept="image/*"
              />
              <label
                htmlFor="fileUpload"
                className="cursor-pointer flex flex-col items-center gap-3"
              >
                <div className="bg-amber-950/50 p-4 rounded-full group-hover:scale-110 transition-transform">
                  <Upload className="size-8 text-amber-500" />
                </div>
                <div className="space-y-1">
                  <p className="font-semibold text-white text-lg">
                    Click to browse or drag and drop
                  </p>
                  <p className="text-sm text-gray-400">
                    High-resolution JPEG or PNG (Max 50MB per file)
                  </p>
                </div>
              </label>
            </div>

            {/* File List Area */}
            {files.length > 0 && (
              <div className="grid grid-cols-1 gap-3 mt-4">
                {files.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 bg-gray-900 border border-gray-700 rounded-lg group animate-in slide-in-from-left-2"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-gray-800 rounded">
                        <FileImage className="size-5 text-amber-500" />
                      </div>
                      <div>
                        <p className="font-medium text-sm text-white">{file.name}</p>
                        <p className="text-xs text-gray-500">
                          {(file.size / (1024 * 1024)).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveFile(index)}
                      className="text-gray-500 hover:text-red-400 hover:bg-red-400/10"
                    >
                      <X className="size-5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex items-center gap-4 pt-2">
          <Button
            type="submit"
            size="lg"
            disabled={files.length === 0 || isUploading}
            className="bg-amber-600 hover:bg-amber-700 text-white min-w-[200px] shadow-lg shadow-amber-900/20"
          >
            {isUploading ? (
              <>
                <Loader2 className="size-5 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="size-5 mr-2" />
                Initialize Analysis
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="lg"
            className="border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-white"
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}