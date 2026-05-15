"use client";

import { useState, useEffect } from "react";
import { Search, Calendar, FileDown, MoreVertical, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

// Mock data reflecting your 2 main modules: Fingerprint & Toolmark
const historyData = [
  { id: "EXP-992", case: "C-2026-04", type: "Fingerprint", date: "2026-03-28", expert: "Admin", status: "Verified" },
  { id: "EXP-991", case: "C-2026-03", type: "Toolmark", date: "2026-03-25", expert: "Mary", status: "Pending" },
  { id: "EXP-990", case: "C-2026-03", type: "Fingerprint", date: "2026-03-24", expert: "Admin", status: "Verified" },
  { id: "EXP-989", case: "C-2026-01", type: "Toolmark", date: "2026-03-20", expert: "Mary", status: "Flagged" },
];

export default function HistoryPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return null;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Analysis History</h1>
          <p className="text-gray-400 mt-1">Archive of all forensic processing tasks</p>
        </div>
        <Button className="bg-amber-600 hover:bg-amber-700 text-white gap-2">
          <FileDown className="size-4" />
          Export Archive
        </Button>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <CardTitle className="text-white text-lg">Case Logs</CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-500" />
                <Input 
                  placeholder="Search by ID..." 
                  className="pl-9 bg-gray-900 border-gray-700 text-white w-64"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <Button variant="outline" className="border-gray-700 text-gray-400 gap-2">
                <Filter className="size-4" /> Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-gray-700 overflow-hidden">
            <Table>
              <TableHeader className="bg-gray-900/50">
                <TableRow className="border-gray-700">
                  <TableHead className="text-gray-400">Analysis ID</TableHead>
                  <TableHead className="text-gray-400">Case Ref</TableHead>
                  <TableHead className="text-gray-400">Modality</TableHead>
                  <TableHead className="text-gray-400">Processed Date</TableHead>
                  <TableHead className="text-gray-400">Status</TableHead>
                  <TableHead className="text-right text-gray-400">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historyData.map((row) => (
                  <TableRow key={row.id} className="border-gray-700 hover:bg-gray-800/40">
                    <TableCell className="font-mono text-amber-500">{row.id}</TableCell>
                    <TableCell className="text-white font-medium">{row.case}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="bg-gray-700 text-gray-300 border-none">
                        {row.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-400 flex items-center gap-2">
                      <Calendar className="size-3" /> {row.date}
                    </TableCell>
                    <TableCell>
                      <Badge 
                        className={
                          row.status === "Verified" ? "bg-emerald-900/40 text-emerald-400 border-emerald-800" :
                          row.status === "Flagged" ? "bg-red-900/40 text-red-400 border-red-800" :
                          "bg-blue-900/40 text-blue-400 border-blue-800"
                        }
                      >
                        {row.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" className="text-gray-500 hover:text-white">
                        <MoreVertical className="size-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}