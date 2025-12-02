"use client";

import { useState } from "react";
import JourneyChat from "@/components/JourneyChat";
import JourneyTimeline from "@/components/JourneyTimeline";

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
  steps: JourneyStep[];
  total_steps: number;
  estimated_time: string;
}

export default function Home() {
  const [journey, setJourney] = useState<Journey | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerateJourney = async (query: string) => {
    setLoading(true);
    setError(null);
    setJourney(null);

    try {
      const response = await fetch("/api/journey/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, max_steps: 10 }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate journey");
      }

      const data = await response.json();
      setJourney(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Docs Journey Builder
          </h1>
          <p className="text-gray-600">
            Describe what you want to accomplish, and we'll create a step-by-step journey through the documentation.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chat Input */}
          <div className="lg:col-span-1">
            <JourneyChat
              onGenerate={handleGenerateJourney}
              loading={loading}
            />
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}
          </div>

          {/* Timeline */}
          <div className="lg:col-span-2">
            {journey ? (
              <JourneyTimeline journey={journey} />
            ) : (
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                {loading ? (
                  <div className="flex flex-col items-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                    <p>Generating your journey...</p>
                  </div>
                ) : (
                  <p>Enter a goal above to generate a journey</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

