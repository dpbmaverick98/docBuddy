"use client";

import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { JourneyStep } from "@/app/page";
import StepChat from "./StepChat";

interface StepDetailProps {
  step: JourneyStep;
  onClose: () => void;
}

interface DocSummary {
  doc_path: string;
  summary: string;
  url: string;
  title: string;
  heading: string;
}

export default function StepDetail({ step, onClose }: StepDetailProps) {
  const [summaries, setSummaries] = useState<DocSummary[]>([]);
  const [loadingSummaries, setLoadingSummaries] = useState(true);

  useEffect(() => {
    // Fetch summaries for this step's docs
    const fetchSummaries = async () => {
      if (step.doc_paths.length === 0) {
        setLoadingSummaries(false);
        return;
      }

      try {
        setLoadingSummaries(true);
        const response = await fetch("/api/docs/summaries", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            doc_paths: step.doc_paths,
            max_length: 3000,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setSummaries(data.summaries || []);
        }
      } catch (error) {
        console.error("Error fetching summaries:", error);
      } finally {
        setLoadingSummaries(false);
      }
    };

    fetchSummaries();
  }, [step.doc_paths]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-900">
          Step {step.step_number}: {step.title}
        </h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700"
        >
          ← Back to timeline
        </button>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        {loadingSummaries ? (
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-full"></div>
          </div>
        ) : summaries.length > 0 ? (
          <div className="space-y-3">
            <p className="text-gray-700 font-medium mb-2">What to do:</p>
            {summaries.map((summary, index) => (
              <div key={index} className="prose prose-sm max-w-none">
                <ReactMarkdown
                  components={{
                    h1: ({ node, ...props }) => (
                      <h1 className="text-lg font-semibold text-gray-900 mt-4 mb-2" {...props} />
                    ),
                    h2: ({ node, ...props }) => (
                      <h2 className="text-base font-semibold text-gray-900 mt-3 mb-2" {...props} />
                    ),
                    h3: ({ node, ...props }) => (
                      <h3 className="text-sm font-semibold text-gray-900 mt-2 mb-1" {...props} />
                    ),
                    p: ({ node, ...props }) => (
                      <p className="text-gray-700 mb-2 leading-relaxed" {...props} />
                    ),
                    code: ({ node, inline, className, children, ...props }: any) => {
                      const match = /language-(\w+)/.exec(className || "");
                      const language = match ? match[1] : "";
                      return !inline && language ? (
                        <SyntaxHighlighter
                          style={vscDarkPlus}
                          language={language}
                          PreTag="div"
                          className="rounded-lg mb-2 text-sm"
                          {...props}
                        >
                          {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      ) : (
                        <code
                          className="bg-gray-200 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    },
                    pre: ({ node, ...props }) => (
                      <pre {...(props as any)} className="bg-gray-900 rounded-lg p-4 overflow-x-auto" />
                    ),
                    ul: ({ node, ...props }) => (
                      <ul className="list-disc list-inside text-gray-700 mb-2 space-y-1" {...props} />
                    ),
                    ol: ({ node, ...props }) => (
                      <ol className="list-decimal list-inside text-gray-700 mb-2 space-y-1" {...props} />
                    ),
                    li: ({ node, ...props }) => (
                      <li className="text-gray-700" {...props} />
                    ),
                    strong: ({ node, ...props }) => (
                      <strong className="font-semibold text-gray-900" {...props} />
                    ),
                    em: ({ node, ...props }) => (
                      <em className="italic text-gray-700" {...props} />
                    ),
                  }}
                >
                  {summary.summary}
                </ReactMarkdown>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-700">{step.description}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <span className="text-sm text-gray-500">Complexity:</span>
          <span className="ml-2 px-2 py-1 bg-gray-100 rounded text-sm">
            {step.complexity}
          </span>
        </div>
        <div>
          <span className="text-sm text-gray-500">Estimated Time:</span>
          <span className="ml-2 font-medium">{step.estimated_time}</span>
        </div>
      </div>

      {step.prerequisites.length > 0 && (
        <div className="mb-4">
          <span className="text-sm text-gray-500">Prerequisites:</span>
          <span className="ml-2">
            Complete Steps {step.prerequisites.join(", ")} first
          </span>
        </div>
      )}

      <div>
        <h4 className="font-semibold text-gray-900 mb-3">Documentation Links:</h4>
        <div className="space-y-2">
          {step.doc_urls.map((url, index) => {
            const summary = summaries.find(s => s.doc_path === step.doc_paths[index]);
            return (
              <div key={index} className="border border-gray-200 rounded-lg p-3 bg-white">
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-2"
                >
                  <span className="font-medium">
                    {summary?.title || summary?.heading || step.doc_paths[index] || url}
                  </span>
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
                {summary?.heading && summary.heading !== summary.title && (
                  <p className="text-xs text-gray-500 mt-1">{summary.heading}</p>
                )}
                <p className="text-xs text-gray-400 mt-1 font-mono">
                  {step.doc_paths[index]}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Chat with Summary */}
      {summaries.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <StepChat step={step} summaries={summaries} />
        </div>
      )}
    </div>
  );
}

