"use client";

import React, { useState } from 'react';
import { 
  Cpu, 
  Play, 
  ChevronDown, 
  Target, 
  Activity, 
  Clock, 
  HardDrive,
  Pause,
  CheckCircle2
} from 'lucide-react';

export default function ModelTraining() {
  // Form State
  const [modelName, setModelName] = useState("");
  const [description, setDescription] = useState("CNN(Convolutional Neural Network)");
  const [evidenceType, setEvidenceType] = useState("Fingerprint Set A-301");
  const [trainingSplit, setTrainingSplit] = useState("80/20(Train/Val)");
  const [epochs, setEpochs] = useState("50");
  const [learningRate, setLearningRate] = useState("0.0001");

  // Active Training Jobs State
  const [activeJobs, setActiveJobs] = useState([
    {
      id: 1,
      name: "Fingerprint CNN v2.4",
      dataset: "Fingerprint Set A-301",
      type: "CNN",
      progress: 67,
      metrics: { accuracy: "92.4%", loss: "0.042", started: "2h ago", gpu: "78%" }
    },
    {
      id: 2,
      name: "Toolmark Siamese v2.0",
      dataset: "Toolmark Collection B",
      type: "Siamese",
      progress: 50,
      metrics: { accuracy: "88.1%", loss: "0.102", started: "5h ago", gpu: "45%" }
    }
  ]);

  const handleStartTraining = () => {
    if (!modelName) return alert("Please enter a model name");
    console.log("Starting training for:", modelName);
    // Logic to add a new job would go here
  };

  return (
    <div className="space-y-10 animate-in fade-in duration-700">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-3xl font-bold text-white tracking-tight">Model Training</h1>
        <p className="text-sm text-gray-500 font-medium">
          Configure and <span className="text-[#b8860b]">monitor</span> training jobs
        </p>
      </div>

      {/* New Training Configuration Card */}
      <div className="bg-[#1e1b16] border border-gray-800/50 rounded-[2.5rem] p-10 shadow-2xl">
        <h3 className="text-sm font-bold text-white mb-8">New Training</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8">
          {/* Left Column */}
          <div className="space-y-8">
            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Model Name</label>
              <input 
                type="text" 
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="e.g Fingerprint CNN v2.5"
                className="w-full bg-black/40 border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 focus:border-amber-900/50 outline-none transition-colors"
              />
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Description</label>
              <div className="relative">
                <select 
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-black border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 appearance-none focus:border-amber-900/50 outline-none cursor-pointer"
                >
                  <option value="CNN(Convolutional Neural Network)">CNN(Convolutional Neural Network)</option>
                  <option value="Siamese network">Siamese network</option>
                </select>
                <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 size-4 text-gray-600 pointer-events-none" />
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Epochs</label>
              <input 
                type="number" 
                value={epochs}
                onChange={(e) => setEpochs(e.target.value)}
                className="w-full bg-black border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 focus:border-amber-900/50 outline-none"
              />
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-8">
            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Evidence Type</label>
              <div className="relative">
                <select 
                  value={evidenceType}
                  onChange={(e) => setEvidenceType(e.target.value)}
                  className="w-full bg-black border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 appearance-none focus:border-amber-900/50 outline-none cursor-pointer"
                >
                  <option value="Fingerprint Set A-301">Fingerprint Set A-301</option>
                  <option value="Toolmark Collection B">Toolmark Collection B</option>
                  <option value="Fingerprint Set B-402">Fingerprint Set B-402</option>
                </select>
                <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 size-4 text-gray-600 pointer-events-none" />
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Training Split</label>
              <div className="relative">
                <select 
                  value={trainingSplit}
                  onChange={(e) => setTrainingSplit(e.target.value)}
                  className="w-full bg-black border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 appearance-none focus:border-amber-900/50 outline-none cursor-pointer"
                >
                  <option value="80/20(Train/Val)">80/20(Train/Val)</option>
                  <option value="70/30(Train/Val)">70/30(Train/Val)</option>
                </select>
                <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 size-4 text-gray-600 pointer-events-none" />
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500 ml-2">Learning Rate</label>
              <input 
                type="text" 
                value={learningRate}
                onChange={(e) => setLearningRate(e.target.value)}
                className="w-full bg-black border border-gray-800 rounded-2xl px-6 py-4 text-sm text-gray-300 focus:border-amber-900/50 outline-none"
              />
            </div>
          </div>
        </div>

        <button 
          onClick={handleStartTraining}
          className="mt-10 bg-[#b8860b] hover:bg-amber-600 text-black px-10 py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center gap-3 shadow-lg active:scale-95"
        >
          <Play className="size-3 fill-black" />
          Start Training
        </button>
      </div>

      {/* Active Training Section */}
      <div className="space-y-6">
        <h3 className="text-sm font-bold text-white ml-2 uppercase tracking-widest">Active Training</h3>
        
        <div className="space-y-6">
          {activeJobs.map((job) => (
            <div key={job.id} className="bg-[#1e1b16] border border-gray-800/50 rounded-[2.5rem] p-10 shadow-xl relative overflow-hidden">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h4 className="text-lg font-bold text-white">{job.name}</h4>
                  <p className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Dataset: {job.dataset} • Type: {job.type}</p>
                </div>
                <Pause className="size-5 text-gray-600 cursor-pointer hover:text-amber-600 transition-colors" />
              </div>

              {/* Progress Bar */}
              <div className="space-y-3 mb-10">
                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
                  <span className="text-gray-500">Training Progress</span>
                  <span className="text-white">{job.progress}%</span>
                </div>
                <div className="h-2 w-full bg-black rounded-full overflow-hidden border border-gray-800">
                  <div 
                    className="h-full bg-[#b8860b] transition-all duration-1000 shadow-[0_0_15px_rgba(184,134,11,0.4)]" 
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Accuracy", value: job.metrics.accuracy, icon: Target },
                  { label: "Loss", value: job.metrics.loss, icon: Activity },
                  { label: "Started", value: job.metrics.started, icon: Clock },
                  { label: "Gpu Usage", value: job.metrics.gpu, icon: Cpu },
                ].map((metric, i) => (
                  <div key={i} className="bg-black/40 border border-gray-800/50 rounded-3xl p-6 flex flex-col items-center justify-center gap-2 group hover:border-amber-900/30 transition-colors">
                    <metric.icon className="size-4 text-gray-600 group-hover:text-amber-700 transition-colors" />
                    <p className="text-[9px] font-black uppercase tracking-widest text-gray-500">{metric.label}</p>
                    <p className="text-sm font-bold text-white tracking-tight">{metric.value}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}