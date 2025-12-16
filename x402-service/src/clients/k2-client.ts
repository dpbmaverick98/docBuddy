import OpenAI from 'openai';
import { CircuitBreaker, RetryHandler } from '../utils/circuit-breaker';
import { UpstreamError } from '../utils/error-handler';

export class K2Client {
  private client: OpenAI;
  private circuitBreaker: CircuitBreaker;

  constructor(apiKey: string) {
    this.client = new OpenAI({
      baseURL: 'https://router.huggingface.co/v1',
      apiKey: apiKey,
    });

    this.circuitBreaker = new CircuitBreaker('K2-Client', {
      failureThreshold: 3,        // Open after 3 failures
      resetTimeout: 60000,         // Try again after 1 minute
      monitoringPeriod: 300000,    // Consider last 5 minutes
      expectedRecoveryTime: 30000   // Expect recovery in 30s
    });
  }

  async generate(params: {
    messages: Array<{ role: string; content: string }>;
    max_tokens: number;
    temperature: number;
  }): Promise<string> {
    return this.circuitBreaker.execute(async () => {
      return RetryHandler.executeWithRetry(
        async () => {
          const completion = await this.client.chat.completions.create({
            model: 'moonshotai/Kimi-K2-Instruct:novita',
            messages: params.messages as any, // Type assertion for compatibility
            max_tokens: params.max_tokens,
            temperature: params.temperature,
          });

          const content = completion.choices[0]?.message?.content || '';
          if (!content) {
            throw new Error('K2 returned empty content');
          }

          return content;
        },
        3, // max retries
        1000, // base delay 1s
        8000, // max delay 8s
        2, // backoff multiplier
        (error) => this.shouldRetry(error) // retry condition
      );
    }).catch(error => {
      if (error.message.includes('Circuit breaker')) {
        throw new UpstreamError(error.message, 'K2', undefined, 60);
      }
      throw new UpstreamError(`K2 generation failed: ${error.message}`, 'K2');
    });
  }

  private shouldRetry(error: any): boolean {
    // Don't retry on these specific errors
    const nonRetryableErrors = [
      'insufficient_quota',
      'invalid_api_key',
      'model_not_found',
      'Invalid API key',
      'Empty content'
    ];

    const errorMessage = error.message || '';
    return !nonRetryableErrors.some(err => errorMessage.includes(err));
  }

  getHealthStatus() {
    return {
      service: 'K2',
      circuitBreaker: this.circuitBreaker.getStats()
    };
  }
}
