/**
 * src/components/forensic/FeedbackForm.tsx
 * ──────────────────────────────────────────
 * Modal form for submitting investigator feedback on a similarity result.
 *
 * Rendered inside the Modal component from components/ui/Modal.tsx.
 * Opened from the thumbs up / thumbs down buttons on SimilarityResultCard.
 *
 * Structure
 * ──────────
 *   Status banner  — green (confirming correct) | red (flagging incorrect)
 *   Description    — explains what the submission means
 *   Comment field  — textarea, max 500 chars
 *                    optional when is_correct=true
 *                    recommended when is_correct=false
 *   Cancel button  — closes without submitting
 *   Submit button  — calls feedbackService.submit()
 *
 * Props
 * ──────
 *   resultId    — ID of the SimilarityResult being reviewed
 *   isCorrect   — pre-set by whichever thumb button was pressed
 *   onClose     — called to close the modal (cancel or after submit)
 *   onSubmitted — called after a successful submission (optional)
 *                 use to update parent state (e.g. disable feedback buttons)
 *
 * Duplicate submissions
 * ──────────────────────
 *   The backend rejects a second submission for the same result from
 *   the same user with HTTP 409.  This component surfaces that as a
 *   toast error.  The parent (compare.tsx) should hide the feedback
 *   buttons once onSubmitted fires to prevent reaching this state.
 */

import { useState } from "react";
import toast        from "react-hot-toast";
import clsx         from "clsx";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { feedbackService }      from "../../services/feedbackService";
import Modal  from "../ui/modal";
import Button from "../ui/Button";

// ── Props ───────────────────────────────────────────────────────────────────
interface FeedbackFormProps {
  resultId:     number;
  isCorrect:    boolean;
  onClose:      () => void;
  onSubmitted?: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function FeedbackForm({
  resultId,
  isCorrect,
  onClose,
  onSubmitted,
}: FeedbackFormProps) {
  const [comment,    setComment]    = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await feedbackService.submit(
        resultId,
        isCorrect,
        comment.trim() || undefined,   // don't send empty string
      );
      toast.success("Feedback submitted. Thank you.");
      onSubmitted?.();
      onClose();
    } catch (err: unknown) {
      // Surface the backend error message when available
      const detail = (
        err as { response?: { data?: { detail?: string } } }
      )?.response?.data?.detail;
      toast.error(detail ?? "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={isCorrect ? "Confirm correct result" : "Report incorrect result"}
    >

      {/* ── Status banner ───────────────────────────────────────────────── */}
      <div
        className={clsx(
          "flex items-start gap-2.5 rounded-lg px-4 py-3",
          "text-sm font-medium border",
          isCorrect
            ? "bg-green-950 text-green-300 border-green-800"
            : "bg-red-950  text-red-300   border-red-800",
        )}
      >
        {/* Icon */}
        <span className="mt-0.5 shrink-0">
          {isCorrect
            ? <ThumbsUp   size={15} />
            : <ThumbsDown size={15} />}
        </span>

        {/* Message */}
        <span>
          {isCorrect
            ? "You are confirming that this AI result is correct. " +
              "This helps validate the model's predictions."
            : "You are flagging this result as incorrect. " +
              "This feedback is used to retrain the model and improve future predictions."}
        </span>
      </div>

      {/* ── Comment textarea ─────────────────────────────────────────────── */}
      <div className="space-y-1.5">
        <label htmlFor="feedback-comment" className="field-label">
          Comment{" "}
          {!isCorrect && (
            <span className="text-gray-600 font-normal">(recommended)</span>
          )}
          {isCorrect && (
            <span className="text-gray-600 font-normal">(optional)</span>
          )}
        </label>

        <textarea
          id="feedback-comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          maxLength={500}
          rows={4}
          placeholder={
            isCorrect
              ? "Any additional observations about this result…"
              : "Please explain why this result is incorrect, " +
                "e.g. 'These are clearly different fingers — the loop patterns are completely different.'"
          }
          className={clsx(
            "field resize-none",
            // Extra space for the character counter
            "pb-7",
          )}
        />

        {/* Character counter */}
        <div className="flex justify-end">
          <span
            className={clsx(
              "text-xs",
              comment.length > 450 ? "text-yellow-400" : "text-gray-600",
            )}
          >
            {comment.length} / 500
          </span>
        </div>
      </div>

      {/* ── Action buttons ───────────────────────────────────────────────── */}
      <div className="flex gap-3">
        <Button
          variant="secondary"
          fullWidth
          onClick={onClose}
          disabled={submitting}
        >
          Cancel
        </Button>

        <Button
          fullWidth
          loading={submitting}
          onClick={handleSubmit}
        >
          {submitting ? "Submitting…" : "Submit Feedback"}
        </Button>
      </div>

    </Modal>
  );
}