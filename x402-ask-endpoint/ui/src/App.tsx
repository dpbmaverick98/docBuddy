import { useState } from 'react'
import Hero from './components/Hero'
import EndpointSelector from './components/EndpointSelector'
import QuestionForm from './components/QuestionForm'
import ResponseDisplay from './components/ResponseDisplay'
import { useX402Query } from './hooks/useX402Query'

function App() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<'privy' | 'polymarket'>('privy')
  const { askQuestion, loading, response } = useX402Query()

  const handleAsk = async (question: string, context: string) => {
    await askQuestion(selectedEndpoint, question, context)
  }

  return (
    <div className="min-h-screen bg-background text-gray-200">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Hero />
        <EndpointSelector
          selected={selectedEndpoint}
          onSelect={setSelectedEndpoint}
        />
        <QuestionForm
          endpoint={selectedEndpoint}
          onSubmit={handleAsk}
          loading={loading}
        />
        {response && <ResponseDisplay response={response} />}
      </div>
    </div>
  )
}

export default App