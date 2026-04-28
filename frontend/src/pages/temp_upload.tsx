/** below scripts is old or earlier script before adding side-by-side original vs enhanced comparison 
 * src/pages/upload.tsx
 * ──────────────────────
 * Evidence image upload page.
 *
 * Layout
 * ───────
 *   Evidence type selector (fingerprint | toolmark)
 *   Drop zone uploader — validates, uploads, preprocesses, embeds
 *   Recent uploads table (last 10)
 *
 * Flow
 * ─────
 *   1. Investigator selects evidence type
 *   2. Investigator drops or browses to an image file
 *   3. ImageUploader posts file to POST /images/upload
 *   4. ImageUploader polls GET /images/{id} until status=ready
 *   5. onComplete fires → prepends the new image to the recent list
 *
 * Recent uploads
 * ───────────────
 * Loaded on mount via imageService.list({ limit: 10 }).
 * When a new upload completes it is prepended in state without
 * re-fetching — keeps the table consistent with what was just uploaded.
 * User can refresh the page to get the full latest list.
 * * ──────────────────────
 * Evidence image upload page.
 * After each upload completes, the investigator can open a
 * side-by-side original vs enhanced comparison directly on this page.
 * Delete
 * ───────
 * Each row has a delete button.
 * Calls imageService.delete(id) then removes the row from state.
 * Shows a confirmation toast on success / error.
 */

import { useState, useEffect }  from "react";
import Head            from "next/head";
import { Trash2, Upload as UploadIcon } from "lucide-react";
import toast           from "react-hot-toast";

import AppLayout              from "../components/layout/AppLayout";
import Card                   from "../components/ui/Card";
import Button                 from "../components/ui/Button";
import { EvidenceBadge, StatusBadge } from "../components/ui/Badge";
import Spinner                from "../components/ui/Spinner";
import EvidenceTypeSelector   from "../components/forensic/EvidenceTypeSelector";
import ImageUploader          from "../components/forensic/ImageUploader";

import {
  imageService,
  ImageResponse,
  EvidenceType,
} from "../services/imageService";

// ── Component ─────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("fingerprint");
  const [recentImages, setRecentImages] = useState<ImageResponse[]>([]);
  const [loadingList,  setLoadingList]  = useState(true);
  // Track which row is being deleted so we can show a per-row spinner
  const [deletingId,   setDeletingId]   = useState<number | null>(null);

  // Load recent uploads on mount
  useEffect(() => {
    imageService
      .list({ limit: 10 })
      .then((res) => setRecentImages(res.images))
      .catch(() => toast.error("Could not load recent uploads."))
      .finally(() => setLoadingList(false));
  }, []);

  // Called by ImageUploader when an image reaches status=ready
  const handleUploadComplete = (image: ImageResponse) => {
    setRecentImages((prev) => [image, ...prev.slice(0, 9)]);
  };

  // Delete a single image
  const handleDelete = async (image: ImageResponse) => {
    if (!confirm(`Delete "${image.original_filename}"? This cannot be undone.`)) return;
    setDeletingId(image.id);
    try {
      await imageService.delete(image.id);
      setRecentImages((prev) => prev.filter((i) => i.id !== image.id));
      toast.success("Image deleted.");
    } catch {
      toast.error("Delete failed. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <Head><title>Upload Evidence — ForensicEdge</title></Head>

      <AppLayout title="Upload Evidence">

        {/* ── Evidence type selector ────────────────────────────────────── */}
        <Card>
          <EvidenceTypeSelector
            value={evidenceType}
            onChange={setEvidenceType}
          />
        </Card>

        {/* ── Uploader ──────────────────────────────────────────────────── */}
        <Card title="Upload Image">
          <ImageUploader
            evidenceType={evidenceType}
            label={`Upload ${evidenceType} evidence image`}
            onComplete={handleUploadComplete}
          />

          {/* Accepted formats note */}
          <p className="text-gray-600 text-xs mt-3 leading-relaxed">
            Accepted formats: BMP, PNG, JPG, JPEG · Max file size: 10 MB
            <br />
            The image is validated, enhanced (bilateral filter + CLAHE + ridge
            sharpening), and embedded by the CNN automatically after upload.
          </p>
        </Card>

        {/* ── Recent uploads ────────────────────────────────────────────── */}
        <Card
          title="Recent Uploads"
          padding="p-0"
        >
          {loadingList ? (
            <div className="flex justify-center py-10">
              <Spinner size="md" />
            </div>

          ) : recentImages.length === 0 ? (
            <div className="text-center py-12 space-y-3 px-6">
              <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center
                              justify-center mx-auto">
                <UploadIcon size={24} className="text-gray-600" />
              </div>
              <p className="text-gray-500 text-sm">No images uploaded yet.</p>
              <p className="text-gray-600 text-xs">
                Upload an image above to get started.
              </p>
            </div>

          ) : (
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Uploaded</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {recentImages.map((img) => (
                    <tr key={img.id}>
                      {/* Filename */}
                      <td>
                        <span
                          className="block truncate max-w-[200px] text-white"
                          title={img.original_filename}
                        >
                          {img.original_filename}
                        </span>
                        <span className="text-gray-600 text-xs">
                          ID: {img.id}
                        </span>
                      </td>

                      {/* Evidence type */}
                      <td>
                        <EvidenceBadge type={img.evidence_type} />
                      </td>

                      {/* File size */}
                      <td className="text-gray-400 whitespace-nowrap">
                        {(img.file_size_bytes / 1024).toFixed(1)} KB
                      </td>

                      {/* Processing status */}
                      <td>
                        <StatusBadge status={img.status} />
                      </td>

                      {/* Upload date */}
                      <td className="text-gray-500 text-xs whitespace-nowrap">
                        {new Date(img.upload_date).toLocaleString(undefined, {
                          month:  "short",
                          day:    "numeric",
                          year:   "numeric",
                          hour:   "2-digit",
                          minute: "2-digit",
                        })}
                      </td>

                      {/* Delete */}
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          icon={
                            deletingId === img.id
                              ? <Spinner size="sm" />
                              : <Trash2 size={14} />
                          }
                          disabled={deletingId === img.id}
                          onClick={() => handleDelete(img)}
                          aria-label={`Delete ${img.original_filename}`}
                          className="text-gray-600 hover:text-red-400"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

      </AppLayout>
    </>
  );
}