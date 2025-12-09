"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, ArrowRight, FileText, Code2, Database, Box, Layers, Zap, ChevronDown } from 'lucide-react';
import JourneyCanvas from "@/components/canvas/JourneyCanvas";
import { ReactFlowProvider } from "reactflow";

// Define the backend URL directly to avoid Next.js proxy timeouts
const API_BASE_URL = "http://localhost:8000/api";

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

// --- ICONS ---
const Icons = {
  Privy: () => (
    <div className="w-3.5 h-3.5 relative overflow-hidden rounded-sm">
        <img 
            src="/privy-logo.png" 
            alt="Privy Logo" 
            className="w-full h-full object-contain"
        />
    </div>
  ),
  Stripe: () => (
    <svg viewBox="0 0 40 40" fill="currentColor" className="w-3.5 h-3.5">
       <path d="M35.1 23.3c0-2.7-2-5-6-5-6.5 0-6.1-4-6.1-5.3 0-1.7 1.6-2.9 4.3-2.9 3.2 0 6.4 1 6.4 1l1.1-5.4s-3.2-1-6.7-1c-7.3 0-11 3.7-11 9.4 0 7.8 7.3 8.3 8.9 10 1.1 1.2.7 3.2-2.1 3.2-2.3 0-7.3-1.7-7.3-1.7L15 31.4s4.8 2.2 8.7 2.2c7.6 0 11.4-3.6 11.4-9.3v-1z"/>
    </svg>
  ),
  Supabase: () => (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
        <path d="M21.362 9.354H10.034L13.513 0H2.638C1.526 0 .638.868.638 1.95v11.751h11.328l-3.48 9.354h10.876c1.112 0 2.001-.868 2.001-1.95V11.304c0-1.082-.889-1.95-2.001-1.95z"/>
    </svg>
  ),
  Figma: () => (
    <svg viewBox="0 0 38 57" fill="none" className="w-3.5 h-3.5">
        <path fill="#1ABCFE" d="M19 28.5a9.5 9.5 0 1 1 19 0 9.5 9.5 0 0 1-19 0Z"/>
        <path fill="#0ACF83" d="M0 47.5a9.5 9.5 0 0 1 9.5-9.5H19v9.5a9.5 9.5 0 1 1-19 0Z"/>
        <path fill="#FF7262" d="M19 0v19h9.5a9.5 9.5 0 1 0 0-19H19Z"/>
        <path fill="#F24E1E" d="M0 9.5a9.5 9.5 0 0 0 9.5 9.5H19V0H9.5A9.5 9.5 0 0 0 0 9.5Z"/>
        <path fill="#A259FF" d="M0 28.5a9.5 9.5 0 0 0 9.5 9.5H19V19H9.5A9.5 9.5 0 0 0 0 28.5Z"/>
    </svg>
  )
};

// --- MOCK REACT FLOW BACKGROUND ---
const ReactFlowCanvas = ({ active, journey, loading, selectedModel }: { active: boolean, journey: Journey | null, loading: boolean, selectedModel: string }) => {
  return (
    <div 
      className="absolute inset-0 z-0 bg-[#1e1e1e]"
    >
      {/* Grid Pattern */}
      <div className="w-full h-full opacity-20 pointer-events-none"
        style={{
            backgroundImage: `linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px)`,
            backgroundSize: '40px 40px'
        }}
      ></div>

      {/* Content Layer with Smooth Transitions */}
      <AnimatePresence mode="wait">
        {active && loading && (
           <motion.div 
             key="loading"
             initial={{ opacity: 0 }}
             animate={{ opacity: 1 }}
             exit={{ opacity: 0 }}
             transition={{ duration: 0.3 }}
             className="absolute inset-0 z-10 flex h-full w-full items-center justify-center bg-[#1e1e1e]/50 backdrop-blur-sm"
           >
              <div className="bg-[#252525] p-8 rounded-2xl shadow-2xl flex flex-col items-center border border-[#3a3a3a]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                <p className="text-lg font-medium text-[#d4d4d4]">Generating your journey...</p>
                <p className="text-sm text-[#858585] mt-2">Analyzing documentation and creating steps</p>
              </div>
           </motion.div>
         )}

         {active && journey && !loading && (
           <motion.div 
             key="canvas"
             initial={{ opacity: 0, scale: 0.98 }}
             animate={{ opacity: 1, scale: 1 }}
             transition={{ duration: 0.5, ease: "easeOut" }}
             className="absolute inset-0 z-10"
           >
             <ReactFlowProvider>
                <JourneyCanvas journey={journey} enhancedContext={journey?.enhanced_context} selectedModel={selectedModel} />
             </ReactFlowProvider>
           </motion.div>
         )}
      </AnimatePresence>
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
  const [isExiting, setIsExiting] = useState(false); // New state for sequence
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
    { name: 'Privy', id: 'privy', icon: <Icons.Privy /> },
    { name: 'Stripe', id: 'stripe', icon: <Icons.Stripe /> },
    { name: 'Supabase', id: 'supabase', icon: <Icons.Supabase /> },
    { name: 'Figma', id: 'figma', icon: <Icons.Figma /> },
  ];

  // Fetch available projects from backend
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        // Use direct URL
        const response = await fetch(`${API_BASE_URL}/projects/`);
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
      
      // Use direct URL
      const response = await fetch(`${API_BASE_URL}/journey/generate`, {
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

  const startSequence = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    // 1. Start exit animation
    setIsExiting(true);
    
    // Note: We removed the setTimeout. We rely on AnimatePresence's onExitComplete 
    // in the JSX to trigger the layout change once the textarea has finished collapsing.
  };

  const handleDocClick = (docId: string, docName: string) => {
      setSelectedProject(docId);
      // Slight delay to allow state update before starting sequence if we want auto-start
      // Or just pre-fill:
      setInputValue(`How do I integrate ${docName}?`);
  };

  return (
    <div className="relative w-full h-screen bg-[#1e1e1e] text-[#d4d4d4] overflow-hidden font-sans selection:bg-blue-500/30">
      
      {/* 1. BACKGROUND LAYER (Canvas) */}
      <ReactFlowCanvas active={hasStarted} journey={journey} loading={loading} selectedModel={selectedModel} />

      {/* 3. INTERACTIVE UI LAYER */}
      {/* Centering the main content block vertically */}
      <div className={`relative z-10 w-full h-full flex flex-col items-center pointer-events-none ${hasStarted ? 'justify-end pb-4' : 'justify-center'}`}>
        
        {/* HERO SECTION - Fades out on start */}
        <AnimatePresence>
          {!hasStarted && !isExiting && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20, filter: 'blur(10px)' }}
              transition={{ duration: 0.5 }}
              className="text-center pointer-events-auto z-20 flex flex-col items-center mb-10"
            >
              
              <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-4 text-[#d4d4d4]">
                DocsBuddy <span className="text-blue-500">-</span> Your AI DevRel
              </h1>
              
              <p className="text-lg text-[#858585] max-w-xl mx-auto leading-relaxed mb-4">
                Start building with user journey in minutes.
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* INPUT BAR CONTAINER - Morphs position */}
        <motion.div
          layout 
          className={`pointer-events-auto w-full px-6 transition-all duration-500 ${hasStarted ? 'max-w-xl opacity-80 hover:opacity-100' : 'max-w-3xl'}`}
          transition={{ 
            type: 'spring', 
            damping: 30, 
            stiffness: 200,
            layout: { duration: 0.5 } // Explicit duration for layout change
          }}
        >
          <form onSubmit={startSequence} className="relative group w-full">
            {/* Glowing Border Gradient - Only show when not started/exiting */}
            {!hasStarted && !isExiting && (
                <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 rounded-xl opacity-30 group-hover:opacity-60 transition duration-500 blur-sm"></div>
            )}
            
            {/* Main Input Box */}
            <div className={`relative flex flex-col bg-[#252525]/90 border border-[#3a3a3a] rounded-xl shadow-2xl backdrop-blur-xl overflow-hidden transition-all duration-500 ${hasStarted ? 'scale-90' : ''}`}>
               {/* Text Area - Fade out content first */}
               <AnimatePresence mode="wait" onExitComplete={() => {
                   // This triggers ONLY after the textarea has fully collapsed
                   setHasStarted(true);
                   setIsExiting(false);
                   handleGenerateJourney(inputValue);
               }}>
                  {!isExiting && !hasStarted && (
                    <motion.div
                      key="input-area"
                      initial={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                      transition={{ 
                        duration: 0.4, 
                        ease: "easeInOut" 
                      }}
                      className="w-full"
                    >
                      <textarea
                       value={inputValue}
                       onChange={(e) => {
                           setInputValue(e.target.value);
                       }}
                       placeholder={`How do I integrate ${selectedProject.charAt(0).toUpperCase() + selectedProject.slice(1)}?`}
                       className="w-full bg-transparent text-[#d4d4d4] placeholder-[#5a5a5a] text-lg px-5 py-4 focus:outline-none resize-none block"
                       rows={2}
                       onKeyDown={(e) => {
                           if(e.key === 'Enter' && !e.shiftKey) {
                               e.preventDefault(); 
                               startSequence(e);
                           }
                       }}
                   />
                    </motion.div>
                  )}
                </AnimatePresence>
              
              {/* Footer inside Input (Models & Button) */}
              <div className={`flex items-center justify-between px-4 ${hasStarted ? 'py-2' : 'pb-3 pt-1'} transition-all duration-300`}>
                <div className="flex items-center gap-2">
                    {/* ModelSelector component */}
                    <ModelSelector selected={selectedModel} setSelected={setSelectedModel} />
                    
                    {/* Mock Context Selector */}
                    <button type="button" className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-[#2d2d2d] transition-colors text-xs text-[#858585] font-medium border border-transparent hover:border-[#3a3a3a]">
                        <Layers size={12} className="text-blue-400" />
                        <span>{selectedProject.charAt(0).toUpperCase() + selectedProject.slice(1)} Docs</span>
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    {/* Start Button */}
                    <button 
                        type="submit"
                        className={`p-2 rounded-lg transition-all duration-200 flex items-center gap-2 text-sm font-medium ${
                            (inputValue.trim() || hasStarted)
                            ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_15px_rgba(37,99,235,0.5)]' 
                            : 'bg-[#2d2d2d] text-[#5a5a5a] cursor-not-allowed'
                        }`}
                        disabled={!inputValue.trim() && !hasStarted}
                        onClick={(e) => {
                            if (hasStarted) {
                                e.preventDefault();
                                setHasStarted(false);
                                setJourney(null);
                                setInputValue("");
                            }
                        }}
                    >
                        {hasStarted ? <span>New Journey</span> : (inputValue.trim() ? <span>Start Building</span> : <span>Enter Query</span>)}
                        <ArrowRight size={16} /> 
                    </button>
                </div>
              </div>
            </div>
            {/* Error Message */}
            {error && (
                <div className="absolute top-full left-0 right-0 mt-2 p-2 bg-red-900/50 border border-red-500/30 rounded-lg text-red-200 text-sm">
                    {error}
                </div>
            )}
          </form>

          {/* FLOATING DOCS SUGGESTIONS */}
          <AnimatePresence>
            {!hasStarted && !isExiting && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1, transition: { delay: 0.2 } }}
                exit={{ opacity: 0, y: 10, transition: { duration: 0.3 } }}
                className="flex flex-wrap items-center justify-center gap-3 mt-6"
              >
                <span className="text-[#5a5a5a] text-xs uppercase tracking-wider font-semibold mr-2">Import Docs:</span>
                {DOCS_ICONS.map((doc, idx) => (
                  <motion.button 
                    key={doc.name}
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleDocClick(doc.id, doc.name)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border border-[#3a3a3a] bg-[#252525] hover:bg-[#3a3a3a] hover:border-[#4a4a4a] text-[#d4d4d4] transition-all"
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

      {/* 4. OVERLAY CONTROLS */}
    </div>
  );
}
