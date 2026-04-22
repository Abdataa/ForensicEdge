/**
 * src/pages/dashboard.tsx
 * ─────────────────────────
 * Main dashboard — overview stats and recent comparisons.
 *
 * Layout
 * ───────
 *   Welcome heading
 *   4 stat tiles (images, comparisons, reports, sessions)
 *   Recent comparisons table (last 5)
 *
 * Data loading
 * ─────────────
 * Three parallel API calls on mount:
 *   imageService.list({ limit: 1 })    → images total
 *   compareService.list({ limit: 5 })  → comparison total + recent 5
 *   reportService.list({ limit: 1 })   → reports total
 *
 * Using limit:1 for counts avoids fetching full datasets just to get totals.
 * The compare call uses limit:5 to also populate the recent table.
 *
 * Error handling
 * ───────────────
 * If any call fails, that stat shows "—" and the table shows an
 * empty state. The page never throws — partial data is acceptable.
 */

import { useEffect, useState } from "react";
import Head       from "next/head";
import Link       from "next/link";
import {
  Upload, GitCompare, FileText, Clock, ArrowRight,
} from "lucide-react";
import { useRouter }  from "next/router";

import AppLayout   from "../components/layout/AppLayout";
import { StatCard } from "../components/ui/Card";
import Card         from "../components/ui/Card";
import { EvidenceBadge, MatchBadge } from "../components/ui/Badge";
import Spinner      from "../components/ui/Spinner";
import Button       from "../components/ui/Button";
import { useAuth }  from "../hooks/useAuth";

import { imageService }                          from "../services/imageService";
import { compareService, SimilarityResponse }    from "../services/compareService";
import { reportService }                         from "../services/reportService";

// ── Component ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user }    = useAuth();
  const router      = useRouter();

  // Stat totals
  const [imgTotal,    setImgTotal]    = useState<number | null>(null);
  const [cmpTotal,    setCmpTotal]    = useState<number | null>(null);
  const [repTotal,    setRepTotal]    = useState<number | null>(null);
  // Recent comparisons table
  const [recent,      setRecent]      = useState<SimilarityResponse[]>([]);
  const [loading,     setLoading]     = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [imgs, cmps, reps] = await Promise.allSettled([
          imageService.list({ limit: 1 }),
          compareService.list({ limit: 5 }),
          reportService.list({ limit: 1 }),
        ]);

        if (imgs.status  === "fulfilled") setImgTotal(imgs.value.total);
        if (cmps.status  === "fulfilled") {
          setCmpTotal(cmps.value.total);
          setRecent(cmps.value.results);
        }
        if (reps.status  === "fulfilled") setRepTotal(reps.value.total);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // ── Stat tile config ────────────────────────────────────────────────────────
  const stats = [
    {
      label:   "Images uploaded",
      value:   imgTotal,
      icon:    <Upload    size={20} className="text-blue-400"   />,
      href:    "/upload",
    },
    {
      label:   "Comparisons run",
      value:   cmpTotal,
      icon:    <GitCompare size={20} className="text-purple-400" />,
      href:    "/compare",
    },
    {
      label:   "Reports generated",
      value:   repTotal,
      icon:    <FileText  size={20} className="text-green-400"  />,
      href:    "/reports",
    },
    {
      label:   "Recent sessions",
      value:   recent.length,
      icon:    <Clock     size={20} className="text-yellow-400" />,
      href:    "/logs",
    },
  ];

  return (
    <>
      <Head><title>Dashboard — ForensicEdge</title></Head>

      <AppLayout title="Dashboard">

        {/* ── Welcome heading ───────────────────────────────────────────── */}
        <div>
          <h2 className="text-white text-xl font-semibold">
            Welcome back,{" "}
            <span className="text-blue-400">
              {user?.full_name.split(" ")[0]}
            </span>
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            ForensicEdge AI-Assisted Evidence Analysis
          </p>
        </div>

        {/* ── Stat tiles ────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((s) => (
            <StatCard
              key={s.label}
              label={s.label}
              value={loading ? null : (s.value ?? 0)}
              icon={s.icon}
              onClick={() => router.push(s.href)}
            />
          ))}
        </div>

        {/* ── Recent comparisons ────────────────────────────────────────── */}
        <Card
          title="Recent Comparisons"
          action={
            <Link
              href="/compare"
              className="flex items-center gap-1 text-blue-400 hover:text-blue-300
                         text-sm transition-colors"
            >
              View all
              <ArrowRight size={14} />
            </Link>
          }
        >
          {loading ? (
            /* Loading state */
            <div className="flex justify-center py-10">
              <Spinner size="md" />
            </div>

          ) : recent.length === 0 ? (
            /* Empty state */
            <div className="text-center py-12 space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-gray-800 flex items-center
                              justify-center mx-auto">
                <GitCompare size={24} className="text-gray-600" />
              </div>
              <div>
                <p className="text-gray-400 text-sm font-medium">
                  No comparisons yet
                </p>
                <p className="text-gray-600 text-xs mt-1">
                  Upload two evidence images and run your first analysis.
                </p>
              </div>
              <Button
                size="sm"
                icon={<GitCompare size={14} />}
                onClick={() => router.push("/compare")}
              >
                Run first comparison
              </Button>
            </div>

          ) : (
            /* Table */
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Query image</th>
                    <th>Reference image</th>
                    <th>Type</th>
                    <th>Similarity</th>
                    <th>Result</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((r) => (
                    <tr key={r.id}>
                      {/* Query filename */}
                      <td>
                        <span
                          className="block truncate max-w-[130px] text-white"
                          title={r.image_1?.original_filename}
                        >
                          {r.image_1?.original_filename ?? `#${r.id}`}
                        </span>
                      </td>

                      {/* Reference filename */}
                      <td>
                        <span
                          className="block truncate max-w-[130px]"
                          title={r.image_2?.original_filename}
                        >
                          {r.image_2?.original_filename ?? "—"}
                        </span>
                      </td>

                      {/* Evidence type */}
                      <td>
                        {r.image_1
                          ? <EvidenceBadge type={r.image_1.evidence_type} />
                          : <span className="text-gray-600">—</span>}
                      </td>

                      {/* Similarity % */}
                      <td className="font-mono text-white">
                        {r.similarity_percentage.toFixed(1)}%
                      </td>

                      {/* Match status */}
                      <td>
                        <MatchBadge status={r.match_status} />
                      </td>

                      {/* Date */}
                      <td className="text-gray-500 text-xs whitespace-nowrap">
                        {new Date(r.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day:   "numeric",
                          year:  "numeric",
                        })}
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