"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText } from "lucide-react";

import Navbar       from "../../../components/layout/Navbar";
import Card         from "../../../components/ui/Card";
import Button       from "../../../components/ui/Button";
import Spinner      from "../../../components/ui/Spinner";
import ReportViewer from "../../../components/forensic/ReportViewer";

import { reportService, ReportResponse } from "../../../services/reportService";

const LIMIT = 20;

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    reportService.list({ page, limit: LIMIT })
      .then((res) => { setReports(res.reports); setTotal(res.total); })
      .finally(() => setLoading(false));
  }, [page]);

  const pages = Math.ceil(total / LIMIT);

  return (
    <>
      <Navbar title="Forensic Reports" />
      <main className="page-body">

        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-white font-semibold text-lg">Reports</h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {total} report{total !== 1 ? "s" : ""} generated
            </p>
          </div>
          <Link href="/compare">
            <Button size="sm">New comparison</Button>
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-16"><Spinner size="lg" /></div>
        ) : reports.length === 0 ? (
          <Card className="text-center py-16 space-y-4">
            <FileText size={40} className="text-gray-700 mx-auto" />
            <p className="text-gray-400">No reports yet.</p>
            <p className="text-gray-600 text-sm">
              Run a comparison and click "Generate PDF Report" on the result.
            </p>
            <Link href="/compare">
              <Button className="mt-1">Start a comparison</Button>
            </Link>
          </Card>
        ) : (
          <div className="space-y-3">
            {reports.map((r) => <ReportViewer key={r.id} report={r} />)}
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-center gap-3">
            <Button
              variant="secondary" size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="text-gray-500 text-sm">Page {page} of {pages}</span>
            <Button
              variant="secondary" size="sm"
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        )}

      </main>
    </>
  );
}
