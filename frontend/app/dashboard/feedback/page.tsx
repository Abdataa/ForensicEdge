"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle, Send } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function FeedbackPage() {
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <div className="h-[60vh] flex flex-col items-center justify-center text-center space-y-4">
        <div className="size-16 bg-emerald-500/20 text-emerald-500 rounded-full flex items-center justify-center">
          <CheckCircle className="size-10" />
        </div>
        <h2 className="text-2xl font-bold text-white">Feedback Submitted</h2>
        <p className="text-gray-400 max-w-md">The analysis record has been flagged for manual review by a senior technician.</p>
        <Button onClick={() => setSubmitted(false)} variant="outline" className="border-gray-700 text-white">Submit Another</Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Dispute Analysis Result</h1>
        <p className="text-gray-400 mt-1">Flag incorrect AI matches for manual verification</p>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white text-lg">Correction Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm text-gray-400">Related Analysis ID</label>
            <Select>
              <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                <SelectValue placeholder="Select a recent analysis..." />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700 text-white">
                <SelectItem value="EXP-992">EXP-992 (Fingerprint - 98%)</SelectItem>
                <SelectItem value="EXP-991">EXP-991 (Toolmark - 89%)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm text-gray-400">Reason for Flagging</label>
            <Select>
              <SelectTrigger className="bg-gray-900 border-gray-700 text-white">
                <SelectValue placeholder="Select reason..." />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700 text-white">
                <SelectItem value="minutiae">Incorrect Minutiae Points</SelectItem>
                <SelectItem value="false-pos">False Positive Match</SelectItem>
                <SelectItem value="quality">Poor Image Quality</SelectItem>
                <SelectItem value="other">Other / Manual Comment</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm text-gray-400">Investigator Comments</label>
            <Textarea 
              placeholder="Describe why the AI result is being questioned..."
              className="bg-gray-900 border-gray-700 text-white min-h-[150px]"
            />
          </div>

          <Button 
            onClick={() => setSubmitted(true)}
            className="w-full bg-red-600 hover:bg-red-700 text-white gap-2"
          >
            <AlertTriangle className="size-4" />
            Flag for Manual Review
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}