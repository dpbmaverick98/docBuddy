"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ArrowRight, FileText, Code2, Database, Box, Layers, Zap, ChevronDown } from 'lucide-react';
import JourneyCanvas from "@/components/canvas/JourneyCanvas";
import { ReactFlowProvider } from "reactflow";

// --- TYPES ---
export interface JourneyStep {
  step_number: number;
  title: string;
  description: string;
  doc_paths: string[];
  doc_urls: string[];
  prerequisites: number[];
  estimated_time: string;
  complexity: string;
}

export interface Journey {
  goal: string;
  intent?: {
    goal: string;
    platform?: string;
    complexity: string;
    keywords?: string[];
    requirements?: string[];
  };
  steps: JourneyStep[];
  total_steps: number;
  estimated_time: string;
  enhanced_context?: {
    docs?: any[];
    query?: string;
    intent?: any;
    model?: string;
  };
}

// --- MOCK BACKGROUND / CANVAS WRAPPER ---
const ReactFlowCanvas = ({ active, journey, loading, selectedModel }: { active: boolean, journey: Journey | null, loading: boolean, selectedModel: string }) => {
  return (
    <div 
      className={`absolute inset-0 z-0 bg-neutral-950 transition-opacity duration-1000 ${
        active ? 'opacity-100' : 'opacity-20'
      }`}
    >
      {/* Grid Pattern */}
      <div className="w-full h-full opacity-20 pointer-events-none"
        style={{
            backgroundImage: `linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px)`,
            backgroundSize: '40px 40px'
        }}
      ></div>

      {/* Real Journey Canvas when available */}
      {active && (journey || loading) && (
        <div className="absolute inset-0 z-10">
           {loading ? (
             <div className="flex h-full w-full items-center justify-center">
                <div className="bg-[#252525] p-8 rounded-2xl shadow-2xl flex flex-col items-center animate-in fade-in zoom-in duration-300 border border-[#3a3a3a]">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                  <p className="text-lg font-medium text-[#d4d4d4]">Generating your journey...</p>
                  <p className="text-sm text-[#858585] mt-2">Analyzing documentation and creating steps</p>
                </div>
             </div>
           ) : (
             <ReactFlowProvider>
                <JourneyCanvas journey={journey} enhancedContext={journey?.enhanced_context} selectedModel={selectedModel} />
             </ReactFlowProvider>
           )}
        </div>
      )}
    </div>
  );
};

// --- MODEL SELECTOR COMPONENT ---
const ModelSelector = ({ selected, setSelected }: { selected: string, setSelected: (m: string) => void }) => {
    const [isOpen, setIsOpen] = useState(false);
    const models = [
        { id: 'claude', name: 'Claude Sonnet 4.5', icon: <Sparkles size={12} className="text-purple-400" /> },
        { id: 'hf-k2-openai', name: 'Kimi K2-Instruct', icon: <Zap size={12} className="text-yellow-500" /> },
    ];

    const currentModel = models.find(m => m.id === selected) || models[0];

    return (
        <div className="relative z-50">
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-neutral-800/50 hover:bg-neutral-800 transition-colors text-xs text-neutral-300 font-medium border border-transparent hover:border-neutral-700"
            >
                {currentModel.icon}
                <span>{currentModel.name}</span>
                <ChevronDown size={12} className="ml-1 transition-transform" style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }} />
            </button>
            
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        transition={{ duration: 0.2 }}
                        className="absolute bottom-full mb-2 left-0 w-max bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl py-1 overflow-hidden"
                    >
                        {models.map((model) => (
                            <button
                                key={model.id}
                                onClick={() => {
                                    setSelected(model.id);
                                    setIsOpen(false);
                                }}
                                className={`flex items-center gap-2 w-full px-3 py-2 text-sm text-neutral-300 hover:bg-neutral-700/50 transition-colors ${selected === model.id ? 'font-bold bg-neutral-700/30' : ''}`}
                            >
                                {model.icon}
                                {model.name}
                            </button>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// --- MAIN COMPONENT ---
export default function Home() {
  const [hasStarted, setHasStarted] = useState(false);
  const [inputValue, setInputValue] = useState('');
  
  // App Logic State
  const [journey, setJourney] = useState<Journey | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<string>("privy");
  const [availableProjects, setAvailableProjects] = useState<string[]>(["privy", "stripe", "aws"]);
  const [selectedModel, setSelectedModel] = useState<string>("claude");

  // Floating icons data
  const DOCS_ICONS = [
    { name: 'Privy', id: 'privy', icon: <FileText size={14} />, color: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' },
    { name: 'Stripe', id: 'stripe', icon: <Code2 size={14} />, color: 'bg-violet-500/10 text-violet-400 border-violet-500/20' },
    { name: 'Supabase', id: 'supabase', icon: <Database size={14} />, color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    { name: 'Figma', id: 'figma', icon: <Box size={14} />, color: 'bg-pink-500/10 text-pink-400 border-pink-500/20' },
  ];

  // Fetch available projects from backend
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const response = await fetch("/api/projects/");
        if (response.ok) {
          const projects = await response.json();
          const projectNames = projects.map((p: any) => p.name);
          setAvailableProjects(projectNames);
        }
      } catch (error) {
        console.warn("Could not fetch projects from backend, using defaults:", error);
      }
    };

    fetchProjects();
  }, []);

  const handleGenerateJourney = async (query: string) => {
    if (!query.trim()) return;
    
    setHasStarted(true);
    setLoading(true);
    setError(null);
    setJourney(null);

    try {
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout

      const requestBody = { query, max_steps: 10, project: selectedProject, model: selectedModel };
      
      const response = await fetch("/api/journey/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to generate journey");
        } else {
          const errorText = await response.text();
          throw new Error(`Server error (${response.status}): ${errorText.substring(0, 100)}`);
        }
      }

      const data = await response.json();
      
      if (data.steps && Array.isArray(data.steps) && data.steps.length > 0) {
        setJourney(data);
      } else {
        throw new Error("No steps generated");
      }
    } catch (err: any) {
        if (err.name === 'AbortError') {
          setError("Request timed out. Please try again.");
        } else {
          setError(err.message || "An unexpected error occurred");
        }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleGenerateJourney(inputValue);
  };

  const handleDocClick = (docId: string, docName: string) => {
      setSelectedProject(docId);
      setInputValue(`How do I integrate ${docName}?`);
  };

  return (
    <div className="relative w-full h-screen bg-neutral-950 text-white overflow-hidden font-sans selection:bg-blue-500/30">
      
      {/* 1. BACKGROUND LAYER (Canvas) */}
      <ReactFlowCanvas active={hasStarted} journey={journey} loading={loading} selectedModel={selectedModel} />

      {/* 2. ATMOSPHERE LAYER (Glows & Effects) */}
      {/* Bolt-like bottom horizon glow */}
      <motion.div 
        animate={{ opacity: hasStarted ? 0 : 1 }}
        transition={{ duration: 1 }}
        className="absolute bottom-0 left-0 w-full h-[60vh] bg-gradient-to-t from-blue-600/10 via-transparent to-transparent pointer-events-none z-0" 
      />
      
      {/* The "Planet" Arc */}
      <motion.div 
        animate={{ 
            opacity: hasStarted ? 0 : 1,
            y: hasStarted ? 200 : 0
        }}
        transition={{ duration: 1 }}
        className="absolute -bottom-[40vw] left-1/2 -translate-x-1/2 w-[120vw] h-[60vw] rounded-[100%] border-t border-blue-500/20 bg-blue-500/5 blur-[60px] pointer-events-none z-0" 
      />

      {/* 3. INTERACTIVE UI LAYER */}
      {/* Centering the main content block vertically */}
      <div className={`relative z-10 w-full h-full flex flex-col items-center pointer-events-none ${hasStarted ? 'justify-end pb-8' : 'justify-center'}`}>
        
        {/* HERO SECTION - Fades out on start */}
        <AnimatePresence>
          {!hasStarted && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20, filter: 'blur(10px)' }}
              transition={{ duration: 0.5 }}
              className="text-center pointer-events-auto z-20 flex flex-col items-center mb-10"
            >
              
              <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-4 text-white">
                DocsBuddy <span className="text-blue-500">-</span> Your AI DevRel
              </h1>
              
              <p className="text-lg text-neutral-400 max-w-xl mx-auto leading-relaxed mb-4">
                Create integrations, generate flows, and chat with documentation instantly.
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* INPUT BAR CONTAINER - Morphs position */}
        <motion.div
          layout 
          className="pointer-events-auto w-full max-w-3xl px-6"
          transition={{ 
            type: 'spring', 
            damping: 30, 
            stiffness: 200 
          }}
        >
          <form onSubmit={handleSubmit} className="relative group w-full">
            {/* Glowing Border Gradient */}
            <div className={`absolute -inset-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 rounded-xl opacity-30 group-hover:opacity-60 transition duration-500 blur-sm ${hasStarted ? 'opacity-20' : ''}`}></div>
            
            {/* Main Input Box */}
            <div className="relative flex flex-col bg-neutral-950/90 border border-neutral-800/50 rounded-xl shadow-2xl backdrop-blur-xl overflow-hidden">
               <textarea
                value={inputValue}
                onChange={(e) => {
                    setInputValue(e.target.value);
                }}
                placeholder={`How do I integrate ${selectedProject.charAt(0).toUpperCase() + selectedProject.slice(1)}?`}
                className="w-full bg-transparent text-white placeholder-neutral-500 text-lg px-5 py-4 focus:outline-none resize-none"
                rows={hasStarted ? 1 : 2}
                onKeyDown={(e) => {
                  if(e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault(); 
                    handleSubmit(e);
                  }
                }}
              />
              
              {/* Footer inside Input (Models & Button) */}
              <div className="flex items-center justify-between px-4 pb-3 pt-1">
                <div className="flex items-center gap-2">
                    {/* ModelSelector component */}
                    <ModelSelector selected={selectedModel} setSelected={setSelectedModel} />
                    
                    {/* Mock Context Selector */}
                    <button type="button" className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-neutral-800 transition-colors text-xs text-neutral-400 font-medium">
                        <Layers size={12} className="text-blue-400" />
                        <span>{selectedProject.charAt(0).toUpperCase() + selectedProject.slice(1)} Docs</span>
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    {/* Character count / hints could go here */}
                    <button 
                        type="submit"
                        className={`p-2 rounded-lg transition-all duration-200 flex items-center gap-2 text-sm font-medium ${
                            inputValue.trim() 
                            ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_15px_rgba(37,99,235,0.5)]' 
                            : 'bg-neutral-800 text-neutral-500 cursor-not-allowed'
                        }`}
                        disabled={!inputValue.trim()}
                    >
                        {/* Always show the arrow for consistency */}
                        {inputValue.trim() ? <span>Start Building</span> : <span>Enter Query</span>}
                        <ArrowRight size={16} /> 
                    </button>
                </div>
              </div>
            </div>
            {error && (
                <div className="absolute top-full left-0 right-0 mt-2 p-2 bg-red-900/50 border border-red-500/30 rounded-lg text-red-200 text-sm">
                    {error}
                </div>
            )}
          </form>

          {/* FLOATING DOCS SUGGESTIONS */}
          <AnimatePresence>
            {!hasStarted && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1, transition: { delay: 0.2 } }}
                exit={{ opacity: 0, y: 10 }}
                className="flex flex-wrap items-center justify-center gap-3 mt-6"
              >
                <span className="text-neutral-500 text-xs uppercase tracking-wider font-semibold mr-2">Import Docs:</span>
                {DOCS_ICONS.map((doc, idx) => (
                  <motion.button 
                    key={doc.name}
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleDocClick(doc.id, doc.name)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${doc.color} bg-opacity-10 hover:bg-opacity-20`}
                  >
                    {doc.icon}
                    {doc.name}
                  </motion.button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* 4. OVERLAY CONTROLS (Top Right - Optional) */}
      <div className="absolute top-6 right-6 z-50 flex items-center gap-4">
        {hasStarted && (
             <button onClick={() => {
                setHasStarted(false);
                setJourney(null);
                setInputValue("");
             }} className="text-xs text-neutral-500 hover:text-white transition-colors underline bg-neutral-900/50 px-3 py-1.5 rounded-full border border-neutral-800">
                Reset Demo
             </button>
        )}
      </div>

    </div>
  );
}
