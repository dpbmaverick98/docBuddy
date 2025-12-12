// Type definitions for x402 AI service

export interface PaymentPayload {
  network: string;
  scheme: string;
  amount: string;
  currency: string;
  timestamp: number;
  client_address: string;
  signature: string;
}

export interface K2ChatRequest {
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
  }>;
  max_tokens?: number;
  temperature?: number;
}

export interface CohereRerankRequest {
  query: string;
  documents: string[];
  top_n?: number;
  model?: string;
}

export interface CohereChatRequest {
  message: string;
  max_tokens?: number;
  temperature?: number;
}

export interface CohereEmbedRequest {
  texts: string[];
  model?: string;
  input_type?: string;
}

export interface K2ChatResponse {
  choices: Array<{
    message: {
      role: string;
      content: string;
    };
  }>;
}

export interface CohereRerankResponse {
  results: Array<{
    index: number;
    relevance_score: number;
    document: {
      text: string;
    };
  }>;
}

export interface CohereChatResponse {
  text: string;
}

export interface CohereEmbedResponse {
  embeddings: number[][];
}

export interface PaymentRequiredResponse {
  error: string;
  payment_required: {
    network: string;
    scheme: string;
    amount: string;
    currency: string;
    description: string;
  };
}

export interface ErrorResponse {
  error: string;
  details?: string;
}
