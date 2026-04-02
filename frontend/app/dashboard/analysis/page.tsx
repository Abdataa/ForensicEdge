"use client";

import { useState, useEffect } from "react";
import { Search, Filter, Download, Eye, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../../components/ui/table";
import { Badge } from "../../../components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../../components/ui/select";

// Initial mock data - for Friday, this will be replaced by an API call
const initialData = [
  {
    id: "A-1045",
    caseId: "CASE102",
    type: "Fingerprint",
    confidence: 98.5,
    result: "Match Found",
    date: "Mar 6, 2026",
    status: "Complete",
  },
 
 {
    id: "A-1046",
    caseId: "CASE097",
    type: "Toolmark",
    confidence: 89.7,
    result: "Screwdriver Match",
    date: "Mar 1, 2026",
    status: "Complete",
  },
];

export default function AnalysisResultsPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [analysisData, setAnalysisData] = useState(initialData);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    // INTEGRATION POINT: 
    // fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/analysis`).then(...)
  }, []);

  if (!isMounted) return null;

  const filteredData = analysisData.filter((item) => {
    const matchesSearch =
      item.caseId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter =
      filterType === "all" ||
      item.type.toLowerCase() === filterType.toLowerCase();
    return matchesSearch && matchesFilter;
  });

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 95) {
      return (
        <Badge className="bg-emerald-950 text-emerald-400 border-emerald-800">
          {confidence}% Match
        </Badge>
      );
    } else if (confidence >= 85) {
      return (
        <Badge className="bg-amber-950 text-amber-500 border-amber-800">
          {confidence}% Match
        </Badge>
      );
    }
    return (
      <Badge className="bg-red-950 text-red-400 border-red-800">
        {confidence}% Match
      </Badge>
    );
  };

  return (
    <div className="space-y-6 bg-gray-950 min-h-screen">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-white">Analysis Results</h1>
          <p className="text-gray-400 mt-1">
            Reviewing AI-generated forensic matches and insights
          </p>
        </div>
        <Button variant="outline" className="gap-2 border-gray-700 text-gray-300 hover:bg-gray-800">
          <Download className="size-4" />
          Export Reports
        </Button>
      </div>

      <Card className="bg-gray-800 border-gray-700 shadow-xl">
        <CardContent className="p-6 space-y-6">
          {/* Filters and Search */}
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-500" />
              <Input
                placeholder="Search by Case or Analysis ID..."
                className="pl-10 bg-gray-900 border-gray-700 text-white placeholder:text-gray-600 focus:border-amber-500"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-full md:w-56 bg-gray-900 border-gray-700 text-white">
                <div className="flex items-center gap-2">
                  <Filter className="size-4 text-amber-500" />
                  <SelectValue placeholder="Evidence Type" />
                </div>
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700 text-white">
                <SelectItem value="all">All Modalities</SelectItem>
                <SelectItem value="fingerprint">Fingerprint</SelectItem>
                
                <SelectItem value="toolmark">Toolmark</SelectItem>
               
              </SelectContent>
            </Select>
          </div>

          {/* Results Table */}
          <div className="rounded-md border border-gray-700 overflow-hidden">
            <Table>
              <TableHeader className="bg-gray-900/50">
                <TableRow className="border-gray-700">
                  <TableHead className="text-gray-400 font-semibold">Analysis ID</TableHead>
                  <TableHead className="text-gray-400 font-semibold">Case ID</TableHead>
                  <TableHead className="text-gray-400 font-semibold">Type</TableHead>
                  <TableHead className="text-gray-400 font-semibold">Confidence</TableHead>
                  <TableHead className="text-gray-400 font-semibold">Result</TableHead>
                  <TableHead className="text-gray-400 font-semibold">Date</TableHead>
                  <TableHead className="text-right text-gray-400 font-semibold">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredData.map((item) => (
                  <TableRow key={item.id} className="border-gray-700 hover:bg-gray-700/50 transition-colors">
                    <TableCell className="font-mono text-amber-500">{item.id}</TableCell>
                    <TableCell className="text-white font-medium">{item.caseId}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-gray-600 text-gray-400">
                        {item.type}
                      </Badge>
                    </TableCell>
                    <TableCell>{getConfidenceBadge(item.confidence)}</TableCell>
                    <TableCell className="text-gray-300 italic">{item.result}</TableCell>
                    <TableCell className="text-gray-400 text-sm">{item.date}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-amber-500 hover:text-amber-400 hover:bg-amber-500/10">
                        <Eye className="size-4 mr-2" />
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {filteredData.length === 0 && (
            <div className="text-center py-20 bg-gray-900/20 rounded-lg border border-dashed border-gray-800">
              <p className="text-gray-500">No matching forensic records found.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}