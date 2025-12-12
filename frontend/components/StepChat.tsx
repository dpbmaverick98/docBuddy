"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { JourneyStep } from "@/app/page";
import { Copy, Check } from "lucide-react";

// Define the backend URL directly
const API_BASE_URL = "http://localhost:8000/api";

interface DocSummary {
  doc_path: string;
  summary: string;
  url: string;
  title: string;
  heading: string;
}

interface StepChatProps {
  step: JourneyStep;
  summaries: DocSummary[];
  enhancedContext?: any;
}

export default function StepChat({ step, summaries, enhancedContext }: StepChatProps) {
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const timeoutIdRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    // Cancel any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (timeoutIdRef.current) {
      clearTimeout(timeoutIdRef.current);
    }

    // Create new abort controller
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const selectedModel = enhancedContext?.model || "claude";

      // Combine summaries for context
      const context = summaries.map(s => `${s.title || s.heading}: ${s.summary}`).join("\n\n");

      // Set up timeout (2 minutes)
      const timeoutId = setTimeout(() => {
        console.log("⏱️ StepChat: Request timeout after 120s");
        abortController.abort();
      }, 120000);
      timeoutIdRef.current = timeoutId;

      // Use direct URL
      const response = await fetch(`${API_BASE_URL}/journey/ask-step`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          step_title: step.title,
          step_description: step.description,
          context: context,
          question: userMessage,
          model: selectedModel,
        }),
        signal: abortController.signal,
      });

      // Clear timeout
      clearTimeout(timeoutId);
      timeoutIdRef.current = null;

      if (!response.ok) {
        throw new Error("Failed to get answer");
      }

      const data = await response.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch (error: any) {
      // Clear timeout
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current);
        timeoutIdRef.current = null;
      }

      if (error.name === 'AbortError') {
        console.log("🚫 StepChat: Request aborted");
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Request timed out. Please try again." },
        ]);
        return;
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process your question. Please try again." },
      ]);
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current);
    }
  };
  }, []);

  return (
    <div className="space-y-4 h-full flex flex-col">
      <h4 className="font-semibold text-[#d4d4d4] flex-shrink-0">Ask questions about this step</h4>
      
      <div 
        className={`bg-[#252525] rounded-lg p-4 overflow-y-auto space-y-3 transition-all duration-300 flex-1 border border-[#3a3a3a]`}
        style={{ 
          scrollbarWidth: 'thin',
          scrollbarColor: '#3a3a3a #252525'
        }}
      >
        {messages.length === 0 ? (
          <p className="text-sm text-[#858585] text-center py-4">
            Ask a question about this step to get help with implementation
          </p>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[90%] rounded-lg px-4 py-2 relative group ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-[#1e1e1e] border border-[#3a3a3a] text-[#d4d4d4] pr-10"
                }`}
              >
                {msg.role === "assistant" && (
                  <button
                    onClick={() => handleCopy(msg.content, index)}
                    className="absolute top-2 right-2 p-1 text-[#858585] hover:text-[#d4d4d4] opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Copy response"
                  >
                    {copiedIndex === index ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                  </button>
                )}

                {msg.role === "user" ? (
                  <p className="text-sm text-white">{msg.content}</p>
                ) : (
                  <div className="prose prose-sm max-w-none prose-invert">
                    <ReactMarkdown
                      components={{
                        h1: ({ node, ...props }) => (
                          <h1 className="text-base font-semibold text-[#d4d4d4] mt-2 mb-1" {...props} />
                        ),
                        h2: ({ node, ...props }) => (
                          <h2 className="text-sm font-semibold text-[#d4d4d4] mt-2 mb-1" {...props} />
                        ),
                        h3: ({ node, ...props }) => (
                          <h3 className="text-sm font-medium text-[#d4d4d4] mt-1 mb-1" {...props} />
                        ),
                        p: ({ node, ...props }) => (
                          <p className="text-sm text-[#d4d4d4] mb-1.5 leading-relaxed" {...props} />
                        ),
                        code: ({ node, inline, className, children, ...props }: any) => {
                          const match = /language-(\w+)/.exec(className || "");
                          const language = match ? match[1] : "";
                          return !inline && language ? (
                            <SyntaxHighlighter
                              style={vscDarkPlus}
                              language={language}
                              PreTag="div"
                              className="rounded mb-2 text-xs"
                              {...props}
                            >
                              {String(children).replace(/\n$/, "")}
                            </SyntaxHighlighter>
                          ) : (
                            <code
                              className="bg-[#252525] px-1 py-0.5 rounded text-xs font-mono text-[#d4d4d4] border border-[#3a3a3a]"
                              {...props}
                            >
                              {children}
                            </code>
                          );
                        },
                        pre: ({ node, ...props }: any) => {
                          const { ref, ...restProps } = props;
                          return <div {...restProps} />;
                        },
                        ul: ({ node, ...props }) => (
                          <ul className="list-disc list-inside text-sm text-[#d4d4d4] mb-1.5 space-y-0.5" {...props} />
                        ),
                        ol: ({ node, ...props }) => (
                          <ol className="list-decimal list-inside text-sm text-[#d4d4d4] mb-1.5 space-y-0.5" {...props} />
                        ),
                        li: ({ node, ...props }) => (
                          <li className="text-sm text-[#d4d4d4]" {...props} />
                        ),
                        strong: ({ node, ...props }) => (
                          <strong className="font-semibold text-[#ffffff]" {...props} />
                        ),
                        em: ({ node, ...props }) => (
                          <em className="italic text-[#d4d4d4]" {...props} />
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#1e1e1e] border border-[#3a3a3a] rounded-lg px-4 py-2">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#858585]"></div>
                <span className="text-sm text-[#858585]">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 flex-shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g., How do I configure this? What code do I need?"
          className="flex-1 px-4 py-2 bg-[#252525] border border-[#3a3a3a] rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-[#d4d4d4] placeholder-[#5a5a5a]"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-[#2d2d2d] disabled:text-[#5a5a5a] disabled:cursor-not-allowed transition-colors"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
