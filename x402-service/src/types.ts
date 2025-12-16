// Type definitions for x402 AI service

// v2 Payment Payload Structure
export interface PaymentPayloadV2 {
  x402Version: number;
  scheme: "exact";
  network: string;
  payload: ExactEvmPayload;
}

export interface ExactEvmPayload {
  signature: string;
  authorization: {
    from: string;
    to: string;
    value: string;
    validAfter: string;
    validBefore: string;
    nonce: string;
  };
}

// v2 Payment Requirements for 402 responses
export interface PaymentRequirements {
  scheme: "exact";
  network: string;
  maxAmountRequired: string;
  resource: string;
  description: string;
  mimeType: string;
  payTo: string;
  maxTimeoutSeconds: number;
  asset: string;
  outputSchema?: Record<string, any>;
  extra?: Record<string, any>;
}

// v2 Payment Required Response
export interface PaymentRequiredResponseV2 {
  x402Version: number;
  error: string;
  accepts: PaymentRequirements[];
}

// v2 Settlement Response
export interface SettlementResponse {
  success: boolean;
  transaction: string;
  network: string;
  payer: string;
}

// Legacy v1 Payment Payload (for backward compatibility)
export interface PaymentPayload {
  network: string;
  scheme: string;
  amount: string;
  currency: string;
  timestamp: number;
  client_address: string;
  recipient_address?: string; // Optional - included when signing payment
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
  code?: string;
  retryAfter?: number;
  correlationId?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  pricing: Record<string, number>;
  services: {
    k2: 'healthy' | 'unhealthy';
    cohere: 'healthy' | 'unhealthy';
    facilitator: 'healthy' | 'unhealthy';
  };
  uptime: number;
}
