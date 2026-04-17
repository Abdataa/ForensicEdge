"use client";
import { useState } from "react";
import { GitCompare, AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";

import Navbar               from "../../../components/layout/Navbar";
import Card                 from "../../../components/ui/Card";
import Button               from "../../../components/ui/Button";
import EvidenceTypeSelector from "../../../components/forensic/EvidenceTypeSelector";
import ImageUploader        from "../../../components/forensic/ImageUploader";
import SimilarityResultCard from "../../../components/forensic/SimilarityResultCard";
import FeedbackForm         from "../../../components/forensic/FeedbackForm";

import { EvidenceType, ImageResponse } from "../../../services/imageService";
import { compareService, SimilarityResponse } from "../../../services/compareService";
import { reportService } from "../../../services/reportService";

export default function ComparePage() {
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("fingerprint");
  const [image1,       setImage1]       = useState<ImageResponse | null>(null);
  const [image2,       setImage2]       = useState<ImageResponse | null>(null);
  const [result,       setResult]       = useState<SimilarityResponse | null>(null);
  const [comparing,    setComparing]    = useState(false);
  const [generating,   setGenerating]   = useState(false);
  const [error,        setError]        = useState("");

  // Feedback modal
  const [feedbackOpen,    setFeedbackOpen]    = useState(false);
  const [feedbackCorrect, setFeedbackCorrect] = useState(true);

  const canCompare = image1?.status === "ready" && image2?.status === "ready";

  const handleTypeChange = (t: EvidenceType) => {
    setEvidenceType(t);
    setImage1(null); setImage2(null);
    setResult(null); setError("");
  };

  const handleCompare = async () => {
    if (!image1 || !image2) return;
    setError(""); setComparing(true); setResult(null);
    try {
      const res = await compareService.compare(image1.id, image2.id);
      setResult(res);
      toast.success("Analysis complete.");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail || "Comparison failed.";
      setError(msg);
      toast.error(msg);
    } finally {
      setComparing(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!result) return;
    setGenerating(true);
    try {
      const report = await reportService.generate(result.id, `Analysis Report #${result.id}`);
      await reportService.download(report.id, `report_${result.id}.pdf`);
      toast.success("Report downloaded.");
    } catch {
      toast.error("Report generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  const handleFeedback = (correct: boolean) => {
    setFeedbackCorrect(correct);
    setFeedbackOpen(true);
  };

  return (
    <>
      <Navbar title="Compare Evidence" />
      <main className="page-body">

        {/* Evidence type */}
        <Card>
          <EvidenceTypeSelector
            value={evidenceType}
            onChange={handleTypeChange}
            disabled={comparing}
          />
        </Card>

        {/* Two uploaders side by side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <ImageUploader
              evidenceType={evidenceType}
              label="Query image (evidence to identify)"
              onComplete={setImage1}
            />
          </Card>
          <Card>
            <ImageUploader
              evidenceType={evidenceType}
              label="Reference image (known sample)"
              onComplete={setImage2}
            />
          </Card>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 bg-red-950 border border-red-800
                          rounded-xl px-4 py-3 text-red-400 text-sm">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        {/* Compare button */}
        <div className="flex flex-col items-center gap-2">
          <Button
            size="lg"
            icon={<GitCompare size={18} />}
            loading={comparing}
            disabled={!canCompare}
            onClick={handleCompare}
            className="px-10"
          >
            {comparing ? "Analysing…" : "Run Forensic Comparison"}
          </Button>
          {!canCompare && (image1 || image2) && (
            <p className="text-gray-600 text-xs">
              Waiting for both images to reach status: <span className="text-green-500">ready</span>
            </p>
          )}
        </div>

        {/* Result */}
        {result && (
          <div className="max-w-lg mx-auto w-full">
            <SimilarityResultCard
              result={result}
              onGenerateReport={handleGenerateReport}
              onFeedback={handleFeedback}
              isGenerating={generating}
            />
          </div>
        )}

      </main>

      {/* Feedback modal */}
      {feedbackOpen && result && (
        <FeedbackForm
          resultId={result.id}
          isCorrect={feedbackCorrect}
          onClose={() => setFeedbackOpen(false)}
        />
      )}
    </>
  );
}