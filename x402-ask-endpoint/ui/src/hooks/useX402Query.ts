import { useState } from 'react'
import { wrapFetchWithPayment } from 'x402-fetch'
import { privateKeyToAccount } from 'viem/accounts'

// TODO: Replace with Privy wallet integration
const PRIVATE_KEY = import.meta.env.VITE_PRIVATE_KEY
const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'http://localhost:4020'

export function useX402Query() {
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<any>(null)

  const askQuestion = async (endpoint: string, question: string, context: string) => {
    console.log('Starting askQuestion:', { endpoint, question });
    setLoading(true)
    setResponse(null)
    
    try {
      if (!PRIVATE_KEY) {
        console.error('Missing VITE_PRIVATE_KEY')
        return
      }

      // For Privy integration later, replace this with Privy wallet
      const account = privateKeyToAccount(PRIVATE_KEY as `0x${string}`)
      const fetchWithPayment = wrapFetchWithPayment(fetch, account)

      const requestBody = {
        question,
        context: context || undefined
      }

      const url = `${SERVER_URL}/api/docsbuddy/ask/${endpoint}`
      console.log('Sending request to:', url);

      const res = await fetchWithPayment(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (res.ok) {
        const data = await res.json()
        console.log('Response received:', data);
        setResponse(data)
      } else {
        console.error('Response not ok:', res.status, res.statusText);
      }
    } catch (error) {
      console.error('Query failed:', error)
      // No UI error display as requested
    } finally {
      setLoading(false)
    }
  }

  return { askQuestion, loading, response }
}