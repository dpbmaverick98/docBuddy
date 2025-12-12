"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { JourneyStep } from "@/app/page";
import { Copy, Check } from "lucide-react";

// Define the backend URL directly
const API_BASE_URL = "http://localhost:8000/api";

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
  const [error, setError] = useState<string | null>(null);
  const [copiedDetails, setCopiedDetails] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);
  const lastRequestKeyRef = useRef<string>("");
  const timeoutIdRef = useRef<NodeJS.Timeout | null>(null);
  const isFetchingRef = useRef(false); // Track if we're currently fetching

  const handleCopyDetails = () => {
    const textToCopy = summaries.map(s => s.summary).join("\n\n");
    navigator.clipboard.writeText(textToCopy);
    setCopiedDetails(true);
    setTimeout(() => setCopiedDetails(false), 2000);
  };

  // Create a stable key for this request based on actual values
  const requestKey = useMemo(() => {
    const docPathsKey = step.doc_paths.sort().join(',');
    const modelKey = selectedModel || enhancedContext?.model || "claude";
    return `${docPathsKey}|${modelKey}|${step.step_number}`;
  }, [step.doc_paths, step.step_number, selectedModel, enhancedContext?.model]);

  useEffect(() => {
    // Skip if we're already fetching the same request (prevents duplicate calls from React StrictMode)
    if (requestKey === lastRequestKeyRef.current && isFetchingRef.current) {
      console.log("⏭️ Already fetching request with key:", requestKey);
      return;
    }

    // If it's a different request key, cancel the previous one
    if (requestKey !== lastRequestKeyRef.current && abortControllerRef.current) {
      console.log("🔄 New request key, aborting previous request");
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Update the last request key
    lastRequestKeyRef.current = requestKey;

    // Cancel any previous timeout
    if (timeoutIdRef.current) {
      clearTimeout(timeoutIdRef.current);
      timeoutIdRef.current = null;
    }

    // Create new abort controller for this request
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    
    // Increment request ID to track the latest request
    const currentRequestId = ++requestIdRef.current;

    // Fetch summaries for this step's docs
    const fetchSummaries = async () => {
      if (step.doc_paths.length === 0) {
        setLoadingSummaries(false);
        isFetchingRef.current = false;
        return;
      }

      // Use selectedModel prop (captured when expand was clicked) as primary source
      // Fallback to enhancedContext.model, then default to "claude"
      const modelToUse = selectedModel || enhancedContext?.model || "claude";
      console.log(`📄 [Request ${currentRequestId}] StepDetail fetching summaries with model:`, modelToUse, "key:", requestKey);

      try {
        isFetchingRef.current = true; // Mark as fetching
        setLoadingSummaries(true);
        setError(null); // Clear any previous errors
        setSummaries([]); // Clear previous summaries to avoid showing stale data
        
        const requestBody = {
          doc_paths: step.doc_paths,
          max_length: 3000,
          step_title: step.title,
          step_description: step.description,
          step_number: step.step_number,
          enhanced_context: enhancedContext,
          model: modelToUse,
        };
        console.log(`📤 [Request ${currentRequestId}] StepDetail sending request:`, requestBody);

        // Set up timeout (2 minutes - same as journey generation)
        const timeoutId = setTimeout(() => {
          console.log(`⏱️ [Request ${currentRequestId}] Request timeout after 120s`);
          abortController.abort();
        }, 120000); // 2 minute timeout
        timeoutIdRef.current = timeoutId;

        // Use direct URL with abort signal
        const response = await fetch(`${API_BASE_URL}/docs/summaries`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
          signal: abortController.signal, // Add abort signal
        });

        // Clear timeout since we got a response
        clearTimeout(timeoutId);
        timeoutIdRef.current = null;

        // Check if this is still the latest request
        if (currentRequestId !== requestIdRef.current) {
          console.log(`⚠️ [Request ${currentRequestId}] Ignoring stale response`);
          return;
        }

        if (response.ok) {
          const data = await response.json();
          console.log(`✅ [Request ${currentRequestId}] Received summaries:`, data.summaries?.length || 0);
          
          // Double-check this is still the latest request before updating state
          if (currentRequestId === requestIdRef.current) {
            setSummaries(data.summaries || []);
            setError(null);
          }
        } else {
          const errorText = await response.text().catch(() => `Status ${response.status}`);
          console.error(`❌ [Request ${currentRequestId}] Response not OK:`, response.status, errorText);
          if (currentRequestId === requestIdRef.current) {
            setError(`Failed to load summaries: ${response.status} ${response.statusText}`);
          }
        }
      } catch (error: any) {
        // Clear timeout if error occurred
        if (timeoutIdRef.current) {
          clearTimeout(timeoutIdRef.current);
          timeoutIdRef.current = null;
        }

        // Ignore abort errors (they're expected for timeouts and cancellations)
        if (error.name === 'AbortError') {
          console.log(`🚫 [Request ${currentRequestId}] Request aborted`);
          // Only show timeout error if this is still the latest request
          if (currentRequestId === requestIdRef.current) {
            // Don't set error if it was aborted due to a new request
            if (requestKey === lastRequestKeyRef.current) {
              setError("Request timed out. The backend is taking longer than expected. Please try again.");
            }
          }
          return;
        }
        
        // Only log/update if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          console.error(`❌ [Request ${currentRequestId}] Error fetching summaries:`, error);
          setError(error.message || "Failed to load summaries. Please try again.");
        }
      } finally {
        // Only update loading state if this is still the latest request
        if (currentRequestId === requestIdRef.current) {
          setLoadingSummaries(false);
        }
        isFetchingRef.current = false; // Mark as not fetching
      }
    };

    fetchSummaries();

    // Cleanup: only abort if this is a different request key
    return () => {
      // Only abort if the request key has changed (meaning a new request started)
      // Don't abort if it's the same key (React StrictMode re-run)
      if (requestKey !== lastRequestKeyRef.current) {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }
        if (timeoutIdRef.current) {
          clearTimeout(timeoutIdRef.current);
          timeoutIdRef.current = null;
        }
        isFetchingRef.current = false;
      }
    };
  }, [requestKey, step.doc_paths, step.title, step.description, step.step_number, selectedModel, enhancedContext]);

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

      <div className="bg-[#252525] rounded-lg p-4 mb-4 border border-[#3a3a3a] relative group">
        {!loadingSummaries && summaries.length > 0 && (
          <button
            onClick={handleCopyDetails}
            className="absolute right-4 top-4 p-2 rounded-lg bg-[#2d2d2d] text-[#858585] opacity-0 group-hover:opacity-100 transition-all hover:bg-[#3a3a3a] hover:text-[#d4d4d4] z-10"
            title="Copy details"
          >
            {copiedDetails ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
          </button>
        )}
        {loadingSummaries ? (
          <div className="space-y-2">
            <div className="animate-pulse">
              <div className="h-4 bg-[#2d2d2d] rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-[#2d2d2d] rounded w-full"></div>
            </div>
            <p className="text-xs text-[#858585] mt-2">Loading implementation summary...</p>
          </div>
        ) : error ? (
          <div className="space-y-2">
            <p className="text-red-400 font-medium">Error loading summaries</p>
            <p className="text-[#858585] text-sm">{error}</p>
            <button
              onClick={() => {
                // Reset to trigger a new fetch
                lastRequestKeyRef.current = "";
                setError(null);
                setLoadingSummaries(true);
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm mt-2"
            >
              Retry
            </button>
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
          {(step.doc_urls || step.doc_paths || []).map((url, index) => {
            const docPath = step.doc_paths?.[index] || '';
            const summary = summaries.find(s => s.doc_path === docPath);
            return (
              <div key={index} className="border border-[#3a3a3a] rounded-lg p-3 bg-[#252525]">
                <a
                  href={url || docPath}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 hover:underline flex items-center gap-2"
                >
                  <span className="font-medium">
                    {summary?.title || summary?.heading || docPath || url}
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
                  {docPath}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
