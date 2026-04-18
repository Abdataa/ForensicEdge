/**
 * src/components/ui/Modal.tsx
 * ────────────────────────────
 * Accessible overlay dialog used for confirmations and short forms.
 *
 * Features
 * ─────────
 *   - Dark overlay backdrop (black/60 opacity)
 *   - Closes on ESC keypress
 *   - Closes on backdrop click (click outside the dialog)
 *   - Stops propagation inside the dialog to prevent accidental close
 *   - Title + X close button in header
 *   - Configurable max-width for different content sizes
 *   - Renders nothing when open=false (no DOM overhead when hidden)
 *
 * Used by
 * ────────
 *   FeedbackForm   — "Confirm correct" / "Report incorrect" modal
 *   AdminPage      — delete user confirmation (pass children with two buttons)
 *   ComparePage    — optional report title/notes input before PDF generation
 *
 * Usage examples
 * ───────────────
 *   // Simple confirmation dialog
 *   <Modal
 *     open={showConfirm}
 *     onClose={() => setShowConfirm(false)}
 *     title="Delete user"
 *   >
 *     <p className="text-gray-400 text-sm">
 *       Are you sure you want to permanently delete this account?
 *     </p>
 *     <div className="flex gap-3 mt-4">
 *       <Button variant="secondary" fullWidth onClick={() => setShowConfirm(false)}>
 *         Cancel
 *       </Button>
 *       <Button variant="danger" fullWidth onClick={handleDelete}>
 *         Delete
 *       </Button>
 *     </div>
 *   </Modal>
 *
 *   // Wider modal for a form
 *   <Modal
 *     open={open}
 *     onClose={onClose}
 *     title="Report details"
 *     maxWidth="max-w-lg"
 *   >
 *     <Input label="Report title" ... />
 *     <Button fullWidth className="mt-4">Generate PDF</Button>
 *   </Modal>
 */

import { ReactNode, useEffect } from "react";
import { X } from "lucide-react";
import clsx from "clsx";

// ── Props ────────────────────────────────────────────────────────────────────

interface ModalProps {
  /** Controls whether the modal is rendered and visible */
  open:       boolean;
  /** Called when the user closes the modal (ESC, backdrop click, or X) */
  onClose:    () => void;
  /** Heading displayed in the modal header */
  title:      string;
  /** Content rendered inside the modal body */
  children:   ReactNode;
  /**
   * Tailwind max-width class for the dialog panel.
   * Default "max-w-md" (~448px) suits most confirmation dialogs and short forms.
   * Use "max-w-lg" or "max-w-xl" for wider content.
   */
  maxWidth?:  string;
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Modal({
  open,
  onClose,
  title,
  children,
  maxWidth  = "max-w-md",
  className,
}: ModalProps) {

  // ── Close on ESC ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // ── Prevent body scroll when modal is open ───────────────────────────────
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [open]);

  // Nothing in the DOM when closed
  if (!open) return null;

  return (
    // ── Backdrop ─────────────────────────────────────────────────────────────
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Translucent dark overlay */}
      <div
        className="absolute inset-0 bg-black/60"
        aria-hidden="true"
      />

      {/* ── Dialog panel ───────────────────────────────────────────────────── */}
      <div
        className={clsx(
          // Positioning above the overlay
          "relative z-10",
          // Container
          "w-full bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl",
          // Inner spacing
          "p-6 space-y-5",
          // Width
          maxWidth,
          className,
        )}
        // Stop clicks inside the dialog from closing it via the backdrop handler
        onClick={(e) => e.stopPropagation()}
      >

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <h2
            id="modal-title"
            className="text-white font-semibold text-base leading-none"
          >
            {title}
          </h2>

          <button
            onClick={onClose}
            aria-label="Close dialog"
            className={clsx(
              "p-1 rounded-lg",
              "text-gray-500 hover:text-white",
              "hover:bg-gray-800",
              "transition-colors",
            )}
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Body ───────────────────────────────────────────────────────── */}
        {children}

      </div>
    </div>
  );
}