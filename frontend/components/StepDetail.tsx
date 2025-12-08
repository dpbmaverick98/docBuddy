"use client";

import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { JourneyStep } from "@/app/page";
import { Copy, Check } from "lucide-react";

interface StepDetailProps {
  step: JourneyStep;
  onClose: () => void;
  enhancedContext?: any;
  selectedModel?: string;
}

interface DocSummary {
  doc_path: string;
  summary: string;
  url: string;
  title: string;
  heading: string;
}

const CodeBlock = ({ inline, className, children, ...props }: any) => {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || "");
  const language = match ? match[1] : "";
  const textToCopy = String(children).replace(/\n$/, "");

  const handleCopy = () => {
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return !inline && language ? (
    <div className="relative group">
      <button
        onClick={handleCopy}
        className="absolute right-2 top-2 p-1.5 rounded-lg bg-[#2d2d2d] text-[#858585] opacity-0 group-hover:opacity-100 transition-all hover:bg-[#3a3a3a] z-10"
        title="Copy code"
      >
        {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
      </button>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language}
        PreTag="div"
        className="rounded-lg mb-2 text-sm"
        {...props}
      >
        {textToCopy}
      </SyntaxHighlighter>
    </div>
  ) : (
    <code
      className="bg-[#252525] px-1.5 py-0.5 rounded text-sm font-mono text-[#d4d4d4] border border-[#3a3a3a]"
      {...props}
    >
      {children}
    </code>
  );
};

export default function StepDetail({ step, onClose, enhancedContext, selectedModel }: StepDetailProps) {
  const [summaries, setSummaries] = useState<DocSummary[]>([]);
  const [loadingSummaries, setLoadingSummaries] = useState(true);

  useEffect(() => {
    // Fetch summaries for this step's docs
    const fetchSummaries = async () => {
      if (step.doc_paths.length === 0) {
        setLoadingSummaries(false);
        return;
      }

      // Use selectedModel prop (captured when expand was clicked) as primary source
      // Fallback to enhancedContext.model, then default to "claude"
      const modelToUse = selectedModel || enhancedContext?.model || "claude";
      console.log("📄 StepDetail fetching summaries with model:", modelToUse, "selectedModel prop:", selectedModel, "enhancedContext.model:", enhancedContext?.model);

      try {
        setLoadingSummaries(true);
        const requestBody = {
          doc_paths: step.doc_paths,
          max_length: 3000,
          step_title: step.title,
          step_description: step.description,
          step_number: step.step_number,
          enhanced_context: enhancedContext,
          model: modelToUse,
        };
        console.log("📤 StepDetail sending request:", requestBody);

        const response = await fetch("/api/docs/summaries", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
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
  }, [step.doc_paths, selectedModel, enhancedContext]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-[#d4d4d4]">
          Step {step.step_number}: {step.title}
        </h3>
        <button
          onClick={onClose}
          className="text-[#858585] hover:text-[#d4d4d4]"
        >
          ← Back to timeline
        </button>
      </div>

      <div className="bg-[#252525] rounded-lg p-4 mb-4 border border-[#3a3a3a]">
        {loadingSummaries ? (
          <div className="animate-pulse">
            <div className="h-4 bg-[#2d2d2d] rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-[#2d2d2d] rounded w-full"></div>
          </div>
        ) : summaries.length > 0 ? (
          <div className="space-y-3">
            <p className="text-[#d4d4d4] font-medium mb-2">What to do:</p>
            {summaries.map((summary, index) => (
              <div key={index} className="prose prose-sm max-w-none prose-invert">
                <ReactMarkdown
                  components={{
                    h1: ({ node, ...props }) => (
                      <h1 className="text-lg font-semibold text-[#d4d4d4] mt-4 mb-2" {...props} />
                    ),
                    h2: ({ node, ...props }) => (
                      <h2 className="text-base font-semibold text-[#d4d4d4] mt-3 mb-2" {...props} />
                    ),
                    h3: ({ node, ...props }) => (
                      <h3 className="text-sm font-semibold text-[#d4d4d4] mt-2 mb-1" {...props} />
                    ),
                    p: ({ node, ...props }) => (
                      <p className="text-[#d4d4d4] mb-2 leading-relaxed" {...props} />
                    ),
                    code: CodeBlock,
                    pre: ({ node, ...props }) => (
                      <pre {...(props as any)} className="bg-[#1e1e1e] rounded-lg p-4 overflow-x-auto border border-[#3a3a3a]" />
                    ),
                    ul: ({ node, ...props }) => (
                      <ul className="list-disc list-inside text-[#d4d4d4] mb-2 space-y-1" {...props} />
                    ),
                    ol: ({ node, ...props }) => (
                      <ol className="list-decimal list-inside text-[#d4d4d4] mb-2 space-y-1" {...props} />
                    ),
                    li: ({ node, ...props }) => (
                      <li className="text-[#d4d4d4]" {...props} />
                    ),
                    strong: ({ node, ...props }) => (
                      <strong className="font-semibold text-[#ffffff]" {...props} />
                    ),
                    em: ({ node, ...props }) => (
                      <em className="italic text-[#d4d4d4]" {...props} />
                    ),
                  }}
                >
                  {summary.summary}
                </ReactMarkdown>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[#d4d4d4]">{step.description}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <span className="text-sm text-[#858585]">Complexity:</span>
          <span className="ml-2 px-2 py-1 bg-[#252525] rounded text-sm border border-[#3a3a3a] text-[#d4d4d4]">
            {step.complexity}
          </span>
        </div>
        <div>
          <span className="text-sm text-[#858585]">Estimated Time:</span>
          <span className="ml-2 font-medium text-[#d4d4d4]">{step.estimated_time}</span>
        </div>
      </div>

      {step.prerequisites.length > 0 && (
        <div className="mb-4">
          <span className="text-sm text-[#858585]">Prerequisites:</span>
          <span className="ml-2 text-[#d4d4d4]">
            Complete Steps {step.prerequisites.join(", ")} first
          </span>
        </div>
      )}

      <div>
        <h4 className="font-semibold text-[#d4d4d4] mb-3">Documentation Links:</h4>
        <div className="space-y-2">
          {step.doc_urls.map((url, index) => {
            const summary = summaries.find(s => s.doc_path === step.doc_paths[index]);
            return (
              <div key={index} className="border border-[#3a3a3a] rounded-lg p-3 bg-[#252525]">
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-2"
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
                  <p className="text-xs text-[#858585] mt-1">{summary.heading}</p>
                )}
                <p className="text-xs text-[#5a5a5a] mt-1 font-mono">
                  {step.doc_paths[index]}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
