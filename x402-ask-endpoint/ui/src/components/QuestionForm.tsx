import { useState } from 'react'

interface QuestionFormProps {
  endpoint: 'privy' | 'polymarket'
  onSubmit: (question: string, context: string) => void
  loading: boolean
}

export default function QuestionForm({ endpoint, onSubmit, loading }: QuestionFormProps) {
  const [question, setQuestion] = useState('')
  const [context, setContext] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (question.trim()) {
      onSubmit(question.trim(), context.trim())
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-lg shadow-lg p-6 mb-8">
      <div className="mb-6">
        <label className="block text-gray-300 font-medium mb-2">
          Question
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask your question about the documentation..."
          className="w-full h-24 p-3 bg-background border border-border text-gray-200 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary placeholder-gray-500"
          required
        />
      </div>

      <div className="mb-6">
        <label className="block text-gray-300 font-medium mb-2">
          Context (optional)
        </label>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Additional context or previous conversation..."
          className="w-full h-20 p-3 bg-background border border-border text-gray-200 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary placeholder-gray-500"
        />
      </div>

      <div className="text-center">
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-8 py-3 bg-primary text-white font-semibold rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Processing Payment...' : `Ask ${endpoint} (0.10 USD)`}
        </button>
      </div>
    </form>
  )
}