import { Request } from 'express';
import { ErrorResponse } from '../types';

export enum ErrorCode {
  PAYMENT_REQUIRED = 'PAYMENT_REQUIRED',
  INVALID_PAYMENT = 'INVALID_PAYMENT', 
  PAYMENT_EXPIRED = 'PAYMENT_EXPIRED',
  SIGNATURE_INVALID = 'SIGNATURE_INVALID',
  RECIPIENT_INVALID = 'RECIPIENT_INVALID',
  FACILITATOR_ERROR = 'FACILITATOR_ERROR',
  UPSTREAM_ERROR = 'UPSTREAM_ERROR',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  INVALID_REQUEST = 'INVALID_REQUEST',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'
}

export class AppError extends Error {
  public readonly statusCode: number;
  public readonly code: ErrorCode;
  public readonly isOperational: boolean;
  public readonly retryAfter?: number;
  public readonly correlationId?: string;

  constructor(
    message: string,
    statusCode: number = 500,
    code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    isOperational: boolean = true,
    retryAfter?: number,
    correlationId?: string
  ) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.isOperational = isOperational;
    this.retryAfter = retryAfter;
    this.correlationId = correlationId;
    
    Error.captureStackTrace(this, this.constructor);
  }
}

export class PaymentError extends AppError {
  constructor(message: string, code: ErrorCode, correlationId?: string) {
    super(message, 402, code, true, undefined, correlationId);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, correlationId?: string) {
    super(message, 400, ErrorCode.INVALID_REQUEST, true, undefined, correlationId);
  }
}

export class UpstreamError extends AppError {
  constructor(message: string, service: string, correlationId?: string, retryAfter?: number) {
    super(`${service} error: ${message}`, 502, ErrorCode.UPSTREAM_ERROR, true, retryAfter, correlationId);
  }
}

export class RateLimitError extends AppError {
  constructor(message: string, retryAfter: number, correlationId?: string) {
    super(message, 429, ErrorCode.RATE_LIMIT_EXCEEDED, true, retryAfter, correlationId);
  }
}

export class CircuitBreakerError extends AppError {
  constructor(service: string, correlationId?: string) {
    super(`${service} circuit breaker is open`, 503, ErrorCode.SERVICE_UNAVAILABLE, true, 60, correlationId);
  }
}

export function createErrorResponse(error: AppError): ErrorResponse {
  const response: ErrorResponse = {
    error: error.message,
    code: error.code,
    correlationId: error.correlationId
  };

  if (error.retryAfter) {
    response.retryAfter = error.retryAfter;
  }

  return response;
}

export function handleAsyncErrors(fn: Function) {
  return (req: Request, res: any, next: any) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

export function getCorrelationId(req: Request): string {
  return req.headers['x-correlation-id'] as string || 
         req.headers['x-request-id'] as string || 
         Math.random().toString(36).substring(2, 15);
}

export function sanitizeErrorForLogs(error: any): any {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      code: (error as AppError).code,
      statusCode: (error as AppError).statusCode,
      isOperational: (error as AppError).isOperational
    };
  }
  return error;
}