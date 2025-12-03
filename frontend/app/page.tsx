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
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout
      
      const response = await fetch("/api/journey/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, max_steps: 10 }),
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

