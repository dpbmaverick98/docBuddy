"use client";

import { useState } from "react";

interface JourneyChatProps {
  onGenerate: (query: string) => void;
  loading: boolean;
}

export default function JourneyChat({ onGenerate, loading }: JourneyChatProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !loading) {
      onGenerate(query.trim());
      setQuery("");
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold mb-4 text-gray-900">
        What do you want to accomplish?
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., I want to set up authentication with Privy"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          rows={4}
          disabled={loading}
        />
        
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "Generating..." : "Generate Journey"}
        </button>
      </form>

      <div className="mt-6 pt-6 border-t border-gray-200">
        <p className="text-sm text-gray-600 mb-2">Example queries:</p>
        <ul className="space-y-2 text-sm">
          <li className="text-gray-500">
            • "Set up authentication"
          </li>
          <li className="text-gray-500">
            • "Create a wallet integration"
          </li>
          <li className="text-gray-500">
            • "Configure gas sponsorship"
          </li>
        </ul>
      </div>
    </div>
  );
}

