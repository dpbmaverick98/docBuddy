"use client";

import { useState } from "react";
import { Journey, JourneyStep } from "@/app/page";
import StepDetail from "./StepDetail";

interface JourneyTimelineProps {
  journey: Journey;
}

export default function JourneyTimeline({ journey }: JourneyTimelineProps) {
  const [selectedStep, setSelectedStep] = useState<JourneyStep | null>(null);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {journey.goal}
        </h2>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>{journey.total_steps} steps</span>
          <span>•</span>
          <span>{journey.estimated_time}</span>
        </div>
      </div>

      {selectedStep ? (
        <StepDetail
          step={selectedStep}
          onClose={() => setSelectedStep(null)}
        />
      ) : (
        <div className="space-y-4">
          {journey.steps.map((step, index) => (
            <div
              key={step.step_number}
              className="border-l-4 border-blue-500 pl-6 pb-6 relative"
            >
              {/* Connector line */}
              {index < journey.steps.length - 1 && (
                <div className="absolute left-[-2px] top-12 bottom-0 w-0.5 bg-gray-200"></div>
              )}

              {/* Step number circle */}
              <div className="absolute left-[-18px] top-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                {step.step_number}
              </div>

              {/* Step content */}
              <div className="pt-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  {step.title}
                </h3>
                <p className="text-gray-600 text-sm mb-3">
                  {step.description}
                </p>

                <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                  <span className="px-2 py-1 bg-gray-100 rounded">
                    {step.complexity}
                  </span>
                  <span>{step.estimated_time}</span>
                  {step.prerequisites.length > 0 && (
                    <span>
                      Requires: Steps {step.prerequisites.join(", ")}
                    </span>
                  )}
                </div>

                <button
                  onClick={() => setSelectedStep(step)}
                  className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  View Details →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

