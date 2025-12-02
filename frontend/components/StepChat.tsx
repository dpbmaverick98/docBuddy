"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { JourneyStep } from "@/app/page";

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
}

export default function StepChat({ step, summaries }: StepChatProps) {
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      // Combine summaries for context
      const context = summaries.map(s => `${s.title || s.heading}: ${s.summary}`).join("\n\n");

      const response = await fetch("/api/journey/ask-step", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          step_title: step.title,
          step_description: step.description,
          context: context,
          question: userMessage,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get answer");
      }

      const data = await response.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process your question. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-gray-900">Ask questions about this step</h4>
      
      <div 
        className={`bg-gray-50 rounded-lg p-4 overflow-y-auto space-y-3 transition-all duration-300 ${
          messages.length === 0 
            ? "max-h-32" 
            : "min-h-[800px] max-h-[1800px]"
        }`}
      >
        {messages.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">
            Ask a question about this step to get help with implementation
          </p>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-white border border-gray-200 text-gray-900"
                }`}
              >
                {msg.role === "user" ? (
                  <p className="text-sm text-white">{msg.content}</p>
                ) : (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      components={{
                        h1: ({ node, ...props }) => (
                          <h1 className="text-base font-semibold text-gray-900 mt-2 mb-1" {...props} />
                        ),
                        h2: ({ node, ...props }) => (
                          <h2 className="text-sm font-semibold text-gray-900 mt-2 mb-1" {...props} />
                        ),
                        h3: ({ node, ...props }) => (
                          <h3 className="text-sm font-medium text-gray-900 mt-1 mb-1" {...props} />
                        ),
                        p: ({ node, ...props }) => (
                          <p className="text-sm text-gray-700 mb-1.5 leading-relaxed" {...props} />
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
                              className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800"
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
                          <ul className="list-disc list-inside text-sm text-gray-700 mb-1.5 space-y-0.5" {...props} />
                        ),
                        ol: ({ node, ...props }) => (
                          <ol className="list-decimal list-inside text-sm text-gray-700 mb-1.5 space-y-0.5" {...props} />
                        ),
                        li: ({ node, ...props }) => (
                          <li className="text-sm text-gray-700" {...props} />
                        ),
                        strong: ({ node, ...props }) => (
                          <strong className="font-semibold text-gray-900" {...props} />
                        ),
                        em: ({ node, ...props }) => (
                          <em className="italic text-gray-700" {...props} />
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
            <div className="bg-white border border-gray-200 rounded-lg px-4 py-2">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                <span className="text-sm text-gray-500">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g., How do I configure this? What code do I need?"
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          Ask
        </button>
      </form>
    </div>
  );
}

