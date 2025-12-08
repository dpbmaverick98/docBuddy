"use client";

import { useState } from "react";

interface JourneyChatProps {
  onGenerate: (query: string, model?: string) => void;
  loading: boolean;
  selectedProject: string;
  onProjectChange: (project: string) => void;
  availableProjects: string[];
}

export default function JourneyChat({ onGenerate, loading, selectedProject, onProjectChange, availableProjects }: JourneyChatProps) {
  const [query, setQuery] = useState("");
  const [selectedModel, setSelectedModel] = useState("claude");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !loading) {
      onGenerate(query.trim(), selectedModel);
      setQuery("");
    }
  };

  return (
    <div className="bg-[#1e1e1e] rounded-lg shadow p-6 border border-[#3a3a3a]">
      <h2 className="text-xl font-semibold mb-4 text-[#d4d4d4]">
        What do you want to accomplish?
      </h2>

      <div className="mb-4">
        <label className="block text-sm font-medium text-[#d4d4d4] mb-2">
          Documentation Source
        </label>
        <select
          value={selectedProject}
          onChange={(e) => onProjectChange(e.target.value)}
          className="w-full px-3 py-2 bg-[#252525] border border-[#3a3a3a] rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-[#d4d4d4]"
          disabled={loading}
        >
          {availableProjects.map((project) => (
            <option key={project} value={project} className="bg-[#252525] text-[#d4d4d4]">
              {project.charAt(0).toUpperCase() + project.slice(1)} Docs
            </option>
          ))}
        </select>
        <p className="text-xs text-[#858585] mt-1">
          Choose which project's documentation to search
        </p>
      </div>

      {/* Model Selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-[#d4d4d4] mb-2">
          LLM Model
        </label>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full px-3 py-2 bg-[#252525] border border-[#3a3a3a] rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-[#d4d4d4]"
          disabled={loading}
        >
          <option value="claude">Claude Sonnet 4.5</option>
          <option value="hf-k2-openai">HuggingFace K2-Instruct</option>
        </select>
        <p className="text-xs text-[#858585] mt-1">
          Choose which LLM model to use for generation
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`e.g., I want to set up authentication with ${selectedProject.charAt(0).toUpperCase() + selectedProject.slice(1)}`}
          className="w-full px-4 py-3 bg-[#252525] border border-[#3a3a3a] rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-[#d4d4d4] placeholder-[#5a5a5a]"
          rows={4}
          disabled={loading}
        />
        
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-[#2d2d2d] disabled:text-[#5a5a5a] disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Generating..." : "Generate Journey"}
        </button>
      </form>

      <div className="mt-6 pt-6 border-t border-[#3a3a3a]">
        <p className="text-sm text-[#858585] mb-2">Example queries:</p>
        <ul className="space-y-2 text-sm">
          <li className="text-[#5a5a5a]">
            • "Set up authentication"
          </li>
          <li className="text-[#5a5a5a]">
            • "Create a user dashboard"
          </li>
          <li className="text-[#5a5a5a]">
            • "Integrate payment processing"
          </li>
        </ul>
      </div>
    </div>
  );
}
