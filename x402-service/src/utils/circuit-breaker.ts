export enum CircuitState {
  CLOSED = 'CLOSED',     // Normal operation
  OPEN = 'OPEN',         // Failing, reject requests
  HALF_OPEN = 'HALF_OPEN' // Testing if service has recovered
}

export interface CircuitBreakerOptions {
  failureThreshold: number;    // Number of failures before opening
  resetTimeout: number;        // Time in milliseconds before attempting reset
  monitoringPeriod: number;     // Time in milliseconds to consider for failure count
  expectedRecoveryTime: number; // Expected time for service to recover
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failureCount: number = 0;
  private lastFailureTime: number = 0;
  private successCount: number = 0;
  private nextAttempt: number = 0;

  constructor(
    private serviceName: string,
    private options: CircuitBreakerOptions
  ) {}

  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() < this.nextAttempt) {
        throw new Error(`Circuit breaker for ${this.serviceName} is OPEN. Next attempt in ${Math.ceil((this.nextAttempt - Date.now()) / 1000)}s`);
      }
      this.state = CircuitState.HALF_OPEN;
      this.successCount = 0;
    }

    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.failureCount = 0;
    
    if (this.state === CircuitState.HALF_OPEN) {
      this.successCount++;
      if (this.successCount >= 3) { // Need 3 consecutive successes to close
        this.state = CircuitState.CLOSED;
        console.log(`✅ Circuit breaker for ${this.serviceName} CLOSED after ${this.successCount} successful requests`);
      }
    }
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.state === CircuitState.HALF_OPEN) {
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.options.resetTimeout;
      console.log(`🔴 Circuit breaker for ${this.serviceName} OPEN again after failure in HALF_OPEN state`);
    } else if (this.failureCount >= this.options.failureThreshold) {
      this.state = CircuitState.OPEN;
      this.nextAttempt = Date.now() + this.options.resetTimeout;
      console.log(`🔴 Circuit breaker for ${this.serviceName} OPEN after ${this.failureCount} failures. Will retry in ${this.options.resetTimeout / 1000}s`);
    }
  }

  getState(): CircuitState {
    return this.state;
  }

  getStats() {
    return {
      service: this.serviceName,
      state: this.state,
      failureCount: this.failureCount,
      lastFailureTime: this.lastFailureTime,
      nextAttempt: this.nextAttempt,
      successCount: this.successCount
    };
  }

  forceOpen(): void {
    this.state = CircuitState.OPEN;
    this.nextAttempt = Date.now() + this.options.resetTimeout;
  }

  forceClose(): void {
    this.state = CircuitState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
  }
}

// Retry utility with exponential backoff
export class RetryHandler {
  static async executeWithRetry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000,
    maxDelay: number = 10000,
    backoffMultiplier: number = 2,
    shouldRetry: (error: any) => boolean = (error) => true
  ): Promise<T> {
    let lastError: any;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error: any) {
        lastError = error;

        if (attempt === maxRetries) {
          console.error(`❌ Operation failed after ${maxRetries + 1} attempts:`, error.message);
          throw error;
        }

        if (!shouldRetry(error)) {
          console.error(`❌ Operation failed with non-retryable error:`, error.message);
          throw error;
        }

        const delay = Math.min(baseDelay * Math.pow(backoffMultiplier, attempt), maxDelay);
        console.warn(`⚠️ Operation failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms:`, error.message);
        
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError;
  }
}