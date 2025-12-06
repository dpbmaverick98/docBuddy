"use client";

import { useState, useEffect } from "react";
import JourneyChat from "@/components/JourneyChat";
import JourneyCanvas from "@/components/canvas/JourneyCanvas";
import { ReactFlowProvider } from "reactflow";
import { Rabbit, Map, History } from 'lucide-react';

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
}

export default function Home() {
  const [journey, setJourney] = useState<Journey | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProject, setSelectedProject] = useState<string>("privy");
  const [availableProjects, setAvailableProjects] = useState<string[]>(["privy", "stripe", "aws"]);

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
    setLoading(true);
    setError(null);
    setJourney(null);

    try {
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
      
      const response = await fetch("/api/journey/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, max_steps: 10, project: selectedProject }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        // Check if response is JSON
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to generate journey");
        } else {
          // Non-JSON error response (likely HTML error page)
          const errorText = await response.text();
          throw new Error(`Server error (${response.status}): ${errorText.substring(0, 100)}`);
        }
      }

      // Ensure response is JSON
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        const text = await response.text();
        throw new Error(`Expected JSON but got: ${contentType}. Response: ${text.substring(0, 200)}`);
      }

      const data = await response.json();
      console.log("✅ Journey data received:", data);
      console.log("✅ Steps count:", data.steps?.length);
      console.log("✅ Total steps:", data.total_steps);
      console.log("✅ Goal:", data.goal);
      console.log("✅ Intent:", data.intent);
      
      // Ensure data structure matches interface
      if (data.steps && Array.isArray(data.steps) && data.steps.length > 0) {
        setJourney(data);
      } else {
        console.error("❌ No steps in response:", data);
        throw new Error("No steps generated");
      }
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          setError("Request timed out. The journey generation is taking longer than expected. Please try again.");
        } else {
          setError(err.message);
        }
      } else {
        setError("An unexpected error occurred");
      }
      console.error("Journey generation error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex h-screen w-full bg-[#1e1e1e] overflow-hidden">
      {/* Sidebar */}
      <div className="w-[400px] border-r border-[#3a3a3a] bg-[#252525] flex flex-col z-10 shadow-xl h-full flex-shrink-0">
        <div className="p-6 border-b border-[#3a3a3a]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
              <Rabbit size={20} />
            </div>
            <h1 className="text-xl font-bold text-[#d4d4d4]">
              Docs Buddy
          </h1>
          </div>
          <p className="text-sm text-[#858585]">
            Plan your integration path with user journeys in mind.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="mb-8">
            <label className="block text-sm font-medium text-[#d4d4d4] mb-2">
              What do you want to build?
            </label>
            <JourneyChat
              onGenerate={handleGenerateJourney}
              loading={loading}
              selectedProject={selectedProject}
              onProjectChange={setSelectedProject}
              availableProjects={availableProjects}
            />
            {error && (
              <div className="mt-4 p-4 bg-red-900/20 border border-red-500/30 rounded-lg">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}
          </div>

          {/* Recent Journeys or Tips could go here */}
          {!journey && !loading && (
            <div className="bg-blue-900/20 rounded-lg p-4 border border-blue-500/30">
              <div className="flex items-center gap-2 mb-2 text-blue-400 font-semibold">
                <Map size={16} />
                <span>Example Queries</span>
              </div>
              <ul className="space-y-2 text-sm text-blue-300">
                <li className="cursor-pointer hover:underline" onClick={() => handleGenerateJourney("How do I set up authentication?")}>
                  • "How do I set up authentication?"
                </li>
                <li className="cursor-pointer hover:underline" onClick={() => handleGenerateJourney("Create a user dashboard with charts")}>
                  • "Create a user dashboard with charts"
                </li>
                <li className="cursor-pointer hover:underline" onClick={() => handleGenerateJourney("Deploy to production using Docker")}>
                  • "Deploy to production using Docker"
                </li>
              </ul>
              </div>
            )}
        </div>

        <div className="p-4 border-t border-[#3a3a3a] bg-[#1e1e1e]">
          <div className="text-xs text-[#5a5a5a] text-center">
            Built by dpbmaverick98 with ❤️
          </div>
        </div>
      </div>
      
      {/* Main Canvas */}
      <div className="flex-1 relative h-full bg-[#1e1e1e]">
        {loading && (
          <div className="absolute inset-0 z-50 bg-[#1e1e1e]/80 backdrop-blur-sm flex flex-col items-center justify-center">
            <div className="bg-[#252525] p-8 rounded-2xl shadow-2xl flex flex-col items-center animate-in fade-in zoom-in duration-300 border border-[#3a3a3a]">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-lg font-medium text-[#d4d4d4]">Generating your journey...</p>
              <p className="text-sm text-[#858585] mt-2">Analyzing documentation and creating steps</p>
            </div>
          </div>
        )}
        
        <ReactFlowProvider>
          <JourneyCanvas journey={journey} />
        </ReactFlowProvider>
      </div>
    </main>
  );
}
