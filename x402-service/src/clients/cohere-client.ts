import { CohereClient as CohereClientLib } from 'cohere-ai';
import { CircuitBreaker, RetryHandler } from '../utils/circuit-breaker';
import { UpstreamError } from '../utils/error-handler';

export class CohereClient {
  private client: CohereClientLib;
  private rerankCircuitBreaker: CircuitBreaker;
  private chatCircuitBreaker: CircuitBreaker;
  private embedCircuitBreaker: CircuitBreaker;

  constructor(apiKey: string) {
    this.client = new CohereClientLib({ token: apiKey });

    // Separate circuit breakers for different endpoints
    this.rerankCircuitBreaker = new CircuitBreaker('Cohere-Rerank', {
      failureThreshold: 3,
      resetTimeout: 60000,
      monitoringPeriod: 300000,
      expectedRecoveryTime: 30000
    });

    this.chatCircuitBreaker = new CircuitBreaker('Cohere-Chat', {
      failureThreshold: 3,
      resetTimeout: 60000,
      monitoringPeriod: 300000,
      expectedRecoveryTime: 30000
    });

    this.embedCircuitBreaker = new CircuitBreaker('Cohere-Embed', {
      failureThreshold: 3,
      resetTimeout: 60000,
      monitoringPeriod: 300000,
      expectedRecoveryTime: 30000
    });
  }

  async rerank(params: {
    query: string;
    documents: string[];
    top_n?: number;
    model?: string;
  }) {
    return this.rerankCircuitBreaker.execute(async () => {
      return RetryHandler.executeWithRetry(
        async () => {
          const response = await this.client.rerank({
            query: params.query,
            documents: params.documents,
            topN: params.top_n || 5,
            model: params.model as any || 'rerank-english-v3.0',
          });

          if (!response.results || response.results.length === 0) {
            throw new Error('Cohere returned empty rerank results');
          }

          return response.results.map((r: any) => ({
            index: r.index,
            relevance_score: r.relevanceScore,
            document: { text: r.document?.text || '' },
          }));
        },
        3, // max retries
        1000, // base delay 1s
        8000, // max delay 8s
        2, // backoff multiplier
        (error) => this.shouldRetry(error)
      );
    }).catch(error => {
      if (error.message.includes('Circuit breaker')) {
        throw new UpstreamError(error.message, 'Cohere-Rerank', undefined, 60);
      }
      throw new UpstreamError(`Cohere rerank failed: ${error.message}`, 'Cohere-Rerank');
    });
  }

  async chat(params: {
    message: string;
    max_tokens?: number;
    temperature?: number;
  }): Promise<string> {
    return this.chatCircuitBreaker.execute(async () => {
      return RetryHandler.executeWithRetry(
        async () => {
          const response = await this.client.chat({
            message: params.message,
            maxTokens: params.max_tokens || 100,
            temperature: params.temperature || 0.2,
          });

          if (!response.text) {
            throw new Error('Cohere returned empty chat response');
          }

          return response.text;
        },
        3, // max retries
        1000, // base delay 1s
        8000, // max delay 8s
        2, // backoff multiplier
        (error) => this.shouldRetry(error)
      );
    }).catch(error => {
      if (error.message.includes('Circuit breaker')) {
        throw new UpstreamError(error.message, 'Cohere-Chat', undefined, 60);
      }
      throw new UpstreamError(`Cohere chat failed: ${error.message}`, 'Cohere-Chat');
    });
  }

  async embed(params: {
    texts: string[];
    model?: string;
    input_type?: string;
  }): Promise<number[][]> {
    return this.embedCircuitBreaker.execute(async () => {
      return RetryHandler.executeWithRetry(
        async () => {
          if (!params.texts || params.texts.length === 0) {
            throw new Error('No texts provided for embedding');
          }

          const response = await this.client.embed({
            texts: params.texts,
            model: params.model as any || 'embed-multilingual-v3.0',
            inputType: params.input_type as any || 'search_document',
          });

          // Handle different response types
          let embeddings: number[][] = [];
          if (Array.isArray(response.embeddings)) {
            embeddings = response.embeddings;
          } else if ((response.embeddings as any)?.embeddings) {
            embeddings = (response.embeddings as any).embeddings;
          }

          if (embeddings.length === 0) {
            throw new Error('Cohere returned empty embeddings');
          }

          return embeddings;
        },
        3, // max retries
        1000, // base delay 1s
        8000, // max delay 8s
        2, // backoff multiplier
        (error) => this.shouldRetry(error)
      );
    }).catch(error => {
      if (error.message.includes('Circuit breaker')) {
        throw new UpstreamError(error.message, 'Cohere-Embed', undefined, 60);
      }
      throw new UpstreamError(`Cohere embed failed: ${error.message}`, 'Cohere-Embed');
    });
  }

  private shouldRetry(error: any): boolean {
    // Don't retry on these specific errors
    const nonRetryableErrors = [
      'invalid_request',
      'invalid_api_key',
      'permission_denied',
      'model_not_found',
      'token_limit'
    ];

    const errorMessage = error.message || '';
    return !nonRetryableErrors.some(err => errorMessage.includes(err));
  }

  getHealthStatus() {
    return {
      service: 'Cohere',
      rerank: this.rerankCircuitBreaker.getStats(),
      chat: this.chatCircuitBreaker.getStats(),
      embed: this.embedCircuitBreaker.getStats()
    };
  }
}
