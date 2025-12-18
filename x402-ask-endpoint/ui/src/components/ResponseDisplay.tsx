import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'

interface ResponseDisplayProps {
  response: {
    answer: string
    sources: Array<{
      doc_path: string
      doc_url: string
      doc_title: string
      heading: string
      content: string
      score: number
    }>
    confidence_score: number
  }
}

export default function ResponseDisplay({ response }: ResponseDisplayProps) {
  return (
    <div className="space-y-6">
      <div className="bg-surface border border-border rounded-lg shadow-lg p-6">
        <h3 className="text-2xl font-bold text-primary mb-4">Answer</h3>
        <div className="prose prose-invert max-w-none">
          <ReactMarkdown
            rehypePlugins={[rehypeRaw]}
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ node, ...props }) => (
                <a {...props} className="text-primary hover:text-purple-400 underline" target="_blank" rel="noopener noreferrer" />
              ),
              pre: ({ node, ...props }) => (
                <pre {...props} className="bg-background border border-border p-4 rounded-lg overflow-x-auto" />
              ),
              code: ({ node, inline, ...props }) => (
                inline 
                  ? <code {...props} className="bg-background px-1 py-0.5 rounded text-primary font-mono text-sm" />
                  : <code {...props} className="text-gray-300 font-mono text-sm block" />
              ),
            }}
          >
            {response.answer}
          </ReactMarkdown>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-lg font-semibold text-gray-300">Sources</h4>
          <span className="text-sm text-gray-400">
            Confidence: {(response.confidence_score * 100).toFixed(1)}%
          </span>
        </div>

        <div className="space-y-3">
          {response.sources.map((source, index) => (
            <div key={index} className="bg-background border border-border rounded-md p-4 hover:border-primary/50 transition-colors">
              <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                  <h5 className="font-medium text-primary text-lg">{source.doc_title}</h5>
                  <p className="text-sm text-gray-400 mt-1 font-semibold">{source.heading}</p>
                </div>
                <div className="ml-4 text-right shrink-0">
                  <span className="text-sm font-medium text-gray-400 bg-surface px-2 py-1 rounded">
                    Match: {(source.score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              
              <div className="bg-surface rounded-md p-3 mb-3 border border-border/50">
                <div className="prose prose-invert prose-sm max-w-none text-gray-300">
                  <ReactMarkdown
                    rehypePlugins={[rehypeRaw]}
                    remarkPlugins={[remarkGfm]}
                    components={{
                      code: ({ node, inline, ...props }) => (
                        inline 
                          ? <code {...props} className="bg-background px-1 py-0.5 rounded text-primary font-mono text-xs" />
                          : <code {...props} className="text-gray-300 font-mono text-xs block" />
                      ),
                    }}
                  >
                    {source.content}
                  </ReactMarkdown>
                </div>
              </div>

              <div className="text-right">
                <a
                  href={source.doc_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:text-purple-400 text-xs inline-flex items-center gap-1 transition-colors"
                  title={source.doc_url}
                >
                  View full source
                  <span className="opacity-70 truncate max-w-[300px]">({source.doc_url})</span>
                  →
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}