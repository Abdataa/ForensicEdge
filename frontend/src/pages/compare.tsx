/**
 * src/pages/compare.tsx
 * ───────────────────────
 * Forensic evidence comparison page.
 * The core workflow page of the entire application.
 *
 * Workflow
 * ─────────
 *   1. Select evidence type (fingerprint | toolmark)
 *   2. Upload query image   → left ImageUploader
 *   3. Upload reference image → right ImageUploader
 *   4. Both images reach status="ready" → Compare button activates
 *   5. POST /compare → SimilarityResultCard renders the result
 *   6. Investigator can: generate PDF report | submit feedback
 *
 * State transitions
 * ──────────────────
 *   Changing evidence type resets both images and clears the result.
 *   Successful comparison reveals the result card below the uploaders.
 *   FeedbackForm modal opens from the thumbs up/down buttons on the card.
 *   After feedback is submitted, the thumbs buttons are disabled.
 */

import { useState }         from "react";
import Head                 from "next/head";
import { GitCompare, AlertTriangle } from "lucide-react";
import toast                from "react-hot-toast";

import AppLayout            from "../components/layout/AppLayout";
import Card                 from "../components/ui/Card";
import Button               from "../components/ui/Button";
import EvidenceTypeSelector from "../components/forensic/EvidenceTypeSelector";
import ImageUploader        from "../components/forensic/ImageUploader";
import SimilarityResultCard from "../components/forensic/SimilarityResultCard";
import FeedbackForm         from "../components/forensic/FeedbackForm";

import { EvidenceType, ImageResponse } from "../services/imageService";
import { compareService, SimilarityResponse } from "../services/compareService";
import { reportService }               from "../services/reportService";

export default function ComparePage() {
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("fingerprint");
  const [image1,       setImage1]       = useState<ImageResponse | null>(null);
  const [image2,       setImage2]       = useState<ImageResponse | null>(null);
  const [result,       setResult]       = useState<SimilarityResponse | null>(null);
  const [comparing,    setComparing]    = useState(false);
  const [generating,   setGenerating]   = useState(false);
  const [error,        setError]        = useState("");

  // Feedback modal state
  const [feedbackOpen,     setFeedbackOpen]     = useState(false);
  const [feedbackCorrect,  setFeedbackCorrect]  = useState(true);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  // Both images must be "ready" for the compare button to activate
  const canCompare = image1?.status === "ready" && image2?.status === "ready";

  // Reset both uploaders and result when evidence type changes
  const handleTypeChange = (type: EvidenceType) => {
    setEvidenceType(type);
    setImage1(null);
    setImage2(null);
    setResult(null);
    setError("");
    setFeedbackSubmitted(false);
  };

  const handleCompare = async () => {
    if (!image1 || !image2) return;
    setError("");
    setComparing(true);
    setResult(null);
    setFeedbackSubmitted(false);

    try {
      const res = await compareService.compare(image1.id, image2.id);
      setResult(res);
      toast.success("Analysis complete.");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Comparison failed. Please try again.";
      setError(detail);
    } finally {
      setComparing(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!result) return;
    setGenerating(true);
    try {
      const report = await reportService.generate(
        result.id,
        `Analysis Report — Result #${result.id}`,
      );
      await reportService.download(report.id, `forensic_report_${result.id}.pdf`);
      toast.success("Report downloaded.");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? "Report generation failed.";
      // 409 means report already exists — try to download it
      if ((err as { response?: { status?: number } })?.response?.status === 409) {
        toast.error("A report already exists for this result. Check the Reports page.");
      } else {
        toast.error(detail);
      }
    } finally {
      setGenerating(false);
    }
  };

  const handleFeedback = (isCorrect: boolean) => {
    setFeedbackCorrect(isCorrect);
    setFeedbackOpen(true);
  };

  return (
    <>
      <Head><title>Compare Evidence — ForensicEdge</title></Head>

      <AppLayout title="Compare Evidence">

        {/* ── Evidence type ──────────────────────────────────────────────── */}
        <Card>
          <EvidenceTypeSelector
            value={evidenceType}
            onChange={handleTypeChange}
            disabled={comparing}
          />
        </Card>

        {/* ── Two uploaders ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <ImageUploader
              evidenceType={evidenceType}
              label="Query image — evidence to identify"
              onComplete={(img) => { setImage1(img); setResult(null); }}
            />
          </Card>
          <Card>
            <ImageUploader
              evidenceType={evidenceType}
              label="Reference image — known sample"
              onComplete={(img) => { setImage2(img); setResult(null); }}
            />
          </Card>
        </div>

        {/* ── Error banner ──────────────────────────────────────────────── */}
        {error && (
          <div className="flex items-start gap-2.5 bg-red-950 border border-red-800
                          rounded-xl px-4 py-3 text-red-300 text-sm">
            <AlertTriangle size={16} className="shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {/* ── Compare button ────────────────────────────────────────────── */}
        <div className="flex flex-col items-center gap-2">
          <Button
            size="lg"
            icon={<GitCompare size={18} />}
            loading={comparing}
            disabled={!canCompare || comparing}
            onClick={handleCompare}
            className="px-10"
          >
            {comparing ? "Analysing…" : "Run Forensic Comparison"}
          </Button>

          {/* Waiting hint — only shown when at least one image is uploading */}
          {!canCompare && (image1 || image2) && (
            <p className="text-gray-600 text-xs text-center">
              Waiting for both images to finish processing
              (status: <span className="text-green-500">ready</span>)
            </p>
          )}

          {/* Guide for first-time users */}
          {!image1 && !image2 && (
            <p className="text-gray-600 text-xs text-center">
              Upload a query image and a reference image above, then click Compare.
            </p>
          )}
        </div>

        {/* ── Result card ───────────────────────────────────────────────── */}
        {result && (
          <div className="max-w-lg mx-auto w-full">
            <SimilarityResultCard
              result={result}
              onGenerateReport={handleGenerateReport}
              onFeedback={feedbackSubmitted ? undefined : handleFeedback}
              isGenerating={generating}
            />
            {feedbackSubmitted && (
              <p className="text-center text-gray-600 text-xs mt-2">
                Feedback submitted — thank you.
              </p>
            )}
          </div>
        )}

      </AppLayout>

      {/* ── Feedback modal ─────────────────────────────────────────────── */}
      {feedbackOpen && result && (
        <FeedbackForm
          resultId={result.id}
          isCorrect={feedbackCorrect}
          onClose={() => setFeedbackOpen(false)}
          onSubmitted={() => setFeedbackSubmitted(true)}
        />
      )}
    </>
  );
}