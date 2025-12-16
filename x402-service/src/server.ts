import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { K2Client } from './clients/k2-client';
import { CohereClient } from './clients/cohere-client';
import { PaymentMiddleware } from './middleware/payment';
import { analytics } from './analytics';
import { SessionManager } from './services/session-manager';
import { 
  AppError, 
  createErrorResponse, 
  handleAsyncErrors, 
  getCorrelationId 
} from './utils/error-handler';
import {
  K2ChatRequest,
  CohereRerankRequest,
  CohereChatRequest,
  CohereEmbedRequest,
  K2ChatResponse,
  CohereRerankResponse,
  CohereChatResponse,
  CohereEmbedResponse,
  ErrorResponse,
  PaymentRequiredResponse,
  HealthStatus
} from './types';

// Load environment variables
dotenv.config();

// Initialize clients
const k2Client = new K2Client(process.env.HF_TOKEN!);
const cohereClient = new CohereClient(process.env.COHERE_API_KEY!);

// Initialize session manager
const sessionManager = new SessionManager({
  sessionTimeoutMs: 60 * 60 * 1000, // 1 hour
  maxSessionValueCents: 2000, // $20 per session
  maxRequestsPerSession: 200
});

// Initialize payment middleware
const receivingWalletAddress = process.env.X402_RECEIVING_WALLET_ADDRESS;
if (!receivingWalletAddress) {
  console.error('❌ X402_RECEIVING_WALLET_ADDRESS not set - payments cannot be received!');
  process.exit(1);
}

const paymentMiddleware = new PaymentMiddleware(
  process.env.X402_FACILITATOR_URL || 'https://open.x402.host',
  process.env.X402_NETWORK || 'base',
  receivingWalletAddress,
  sessionManager
);

// Pricing configuration (in USD cents)
const PRICING = {
  K2_CHAT: parseInt(process.env.K2_CHAT_COST || '50'),
  COHERE_RERANK: parseInt(process.env.COHERE_RERANK_COST || '10'),
  COHERE_CHAT: parseInt(process.env.COHERE_CHAT_COST || '5'),
  COHERE_EMBED: parseInt(process.env.COHERE_EMBED_COST || '2'),
};

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Request timing middleware
app.use((req, res, next) => {
  const startTime = Date.now();
  req.startTime = startTime;
  
  res.on('finish', () => {
    const duration = Date.now() - startTime;
    console.log(`⏱️ ${req.method} ${req.path} - ${res.statusCode} - ${duration}ms`);
  });
  
  next();
});

// Enhanced health check endpoint
app.get('/health', handleAsyncErrors(async (req: express.Request, res: express.Response) => {
  const clientIP = req.ip || req.connection.remoteAddress;
  const startTime = Date.now();
  
  try {
    // Check service health
    const k2Health = k2Client.getHealthStatus();
    const cohereHealth = cohereClient.getHealthStatus();
    const sessionStats = sessionManager.getStats();
    
    // Determine overall status
    const servicesHealthy = 
      k2Health.circuitBreaker.state !== 'OPEN' &&
      Object.values(cohereHealth).every((service: any) => service.state !== 'OPEN');
    
    const status: HealthStatus = {
      status: servicesHealthy ? 'healthy' : 'degraded',
      timestamp: new Date().toISOString(),
      version: '2.0.0',
      pricing: PRICING,
      services: {
        k2: k2Health.circuitBreaker.state === 'CLOSED' ? 'healthy' : 'unhealthy',
        cohere: Object.values(cohereHealth).every((service: any) => service.state === 'CLOSED') ? 'healthy' : 'unhealthy',
        facilitator: 'healthy' // TODO: Add actual facilitator health check
      },
      uptime: process.uptime()
    };

    console.log(`🏥 [${clientIP}] GET /health - ${status.status} - ${Date.now() - startTime}ms`);
    
    // Return appropriate status code
    const statusCode = status.status === 'healthy' ? 200 : 503;
    res.status(statusCode).json(status);
  } catch (error: any) {
    console.error(`Health check failed:`, error);
    res.status(503).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      version: '2.0.0',
      error: error.message,
      services: {
        k2: 'unhealthy',
        cohere: 'unhealthy', 
        facilitator: 'unhealthy'
      },
      uptime: process.uptime()
    });
  }
}));

// Analytics endpoints
app.get('/analytics', handleAsyncErrors(async (req: express.Request, res: express.Response) => {
  const hours = parseInt(req.query.hours as string) || 24;
  const data = analytics.getAnalytics(hours);
  res.json(data);
}));

app.get('/analytics/payments', handleAsyncErrors(async (req: express.Request, res: express.Response) => {
  const limit = parseInt(req.query.limit as string) || 50;
  const data = analytics.getAllPayments(limit);
  res.json({ payments: data });
}));

app.get('/analytics/errors', handleAsyncErrors(async (req: express.Request, res: express.Response) => {
  const limit = parseInt(req.query.limit as string) || 50;
  const data = analytics.getRecentErrors(limit);
  res.json({ errors: data });
}));

app.get('/analytics/sessions', handleAsyncErrors(async (req: express.Request, res: express.Response) => {
  const stats = sessionManager.getStats();
  res.json(stats);
}));

// Detailed service health
app.get('/health/services', handleAsyncErrors(async (req: express.Request, res: express.Response) => {
  res.json({
    k2: k2Client.getHealthStatus(),
    cohere: cohereClient.getHealthStatus(),
    sessions: sessionManager.getStats()
  });
}));

// Analytics endpoints
app.get('/analytics', (req, res) => {
  const hours = parseInt(req.query.hours as string) || 24;
  const data = analytics.getAnalytics(hours);
  res.json(data);
});

app.get('/analytics/payments', (req, res) => {
  const limit = parseInt(req.query.limit as string) || 50;
  const data = analytics.getAllPayments(limit);
  res.json({ payments: data });
});

// Enhanced error handling middleware
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  const correlationId = getCorrelationId(req);
  const processingTime = req.startTime ? Date.now() - req.startTime : undefined;
  
  console.error(`❌ Unhandled error [${correlationId}]:`, err);
  
  // Record failed analytics
  if (req.path && req.path.startsWith('/v1/')) {
    analytics.recordPayment(
      req.path, 
      0, 
      'unknown', 
      false, 
      correlationId, 
      err.message, 
      processingTime
    );
  }

  if (err instanceof AppError) {
    const response = createErrorResponse(err);
    res.status(err.statusCode).json(response);
  } else {
    const statusCode = err.statusCode || 500;
    const response: ErrorResponse = {
      error: err.message || 'Internal server error',
      details: process.env.NODE_ENV === 'development' ? err.stack : undefined,
      correlationId
    };
    
    res.status(statusCode).json(response);
  }
});

// ===== K2 ENDPOINTS =====

app.post(
  '/v1/k2/chat/completions',
  paymentMiddleware.createMiddleware(PRICING.K2_CHAT.toString()),
  handleAsyncErrors(async (req: express.Request, res: express.Response) => {
    const correlationId = getCorrelationId(req);
    const clientIP = req.ip || req.connection.remoteAddress;
    const isSessionBased = req.headers['x-session-based'] === 'true';
    
    console.log(`🤖 [${correlationId}] POST /v1/k2/chat/completions - K2 request ${isSessionBased ? '(session)' : '(payment)'}`);

    // Validate request
    const body: K2ChatRequest = req.body;
    if (!body.messages || !Array.isArray(body.messages) || body.messages.length === 0) {
      console.log(`❌ [${correlationId}] /v1/k2/chat/completions - Invalid request: missing messages`);
      return res.status(400).json({
        error: 'Invalid request: messages array is required',
        correlationId
      } as ErrorResponse);
    }

    console.log(`⚡ [${correlationId}] /v1/k2/chat/completions - Calling K2 API with ${body.messages.length} messages`);
    const result = await k2Client.generate({
      messages: body.messages,
      max_tokens: body.max_tokens || 1000,
      temperature: body.temperature || 0.7,
    });

    const processingTime = req.startTime ? Date.now() - req.startTime : undefined;
    
    // Record successful analytics
    analytics.recordPayment(
      req.path, 
      PRICING.K2_CHAT, 
      'session-user', 
      true, 
      correlationId, 
      undefined, 
      processingTime, 
      isSessionBased ? 'v2' : 'v1'
    );

    console.log(`✅ [${correlationId}] /v1/k2/chat/completions - K2 response generated (${result.length} chars) in ${processingTime}ms`);
    
    const response: K2ChatResponse = {
      choices: [{
        message: {
          role: 'assistant',
          content: result,
        },
      }],
    };

    res.json(response);
  })
);

// ===== COHERE ENDPOINTS =====

app.post(
  '/v1/cohere/rerank',
  paymentMiddleware.createMiddleware(PRICING.COHERE_RERANK.toString()),
  handleAsyncErrors(async (req: express.Request, res: express.Response) => {
    const correlationId = getCorrelationId(req);
    const isSessionBased = req.headers['x-session-based'] === 'true';
    
    // Validate request
    const body: CohereRerankRequest = req.body;
    if (!body.query || !body.documents || !Array.isArray(body.documents)) {
      return res.status(400).json({
        error: 'Invalid request: query and documents array are required',
        correlationId
      } as ErrorResponse);
    }

    console.log(`🔍 [${correlationId}] POST /v1/cohere/rerank - Reranking ${body.documents.length} documents`);
    
    const result = await cohereClient.rerank({
      query: body.query,
      documents: body.documents,
      top_n: body.top_n || 5,
      model: body.model || 'rerank-english-v3.0',
    });

    const processingTime = req.startTime ? Date.now() - req.startTime : undefined;
    
    // Record successful analytics
    analytics.recordPayment(
      req.path, 
      PRICING.COHERE_RERANK, 
      'session-user', 
      true, 
      correlationId, 
      undefined, 
      processingTime, 
      isSessionBased ? 'v2' : 'v1'
    );

    console.log(`✅ [${correlationId}] /v1/cohere/rerank - Completed in ${processingTime}ms`);
    
    const response: CohereRerankResponse = {
      results: result,
    };

    res.json(response);
  })
);

app.post(
  '/v1/cohere/chat',
  paymentMiddleware.createMiddleware(PRICING.COHERE_CHAT.toString()),
  handleAsyncErrors(async (req: express.Request, res: express.Response) => {
    const correlationId = getCorrelationId(req);
    const isSessionBased = req.headers['x-session-based'] === 'true';
    
    // Validate request
    const body: CohereChatRequest = req.body;
    if (!body.message) {
      return res.status(400).json({
        error: 'Invalid request: message is required',
        correlationId
      } as ErrorResponse);
    }

    console.log(`💬 [${correlationId}] POST /v1/cohere/chat - Chat request`);
    
    const result = await cohereClient.chat({
      message: body.message,
      max_tokens: body.max_tokens || 100,
      temperature: body.temperature || 0.2,
    });

    const processingTime = req.startTime ? Date.now() - req.startTime : undefined;
    
    // Record successful analytics
    analytics.recordPayment(
      req.path, 
      PRICING.COHERE_CHAT, 
      'session-user', 
      true, 
      correlationId, 
      undefined, 
      processingTime, 
      isSessionBased ? 'v2' : 'v1'
    );

    console.log(`✅ [${correlationId}] /v1/cohere/chat - Completed in ${processingTime}ms`);
    
    const response: CohereChatResponse = {
      text: result,
    };

    res.json(response);
  })
);

app.post(
  '/v1/cohere/embed',
  paymentMiddleware.createMiddleware(PRICING.COHERE_EMBED.toString()),
  handleAsyncErrors(async (req: express.Request, res: express.Response) => {
    const correlationId = getCorrelationId(req);
    const isSessionBased = req.headers['x-session-based'] === 'true';
    
    // Validate request
    const body: CohereEmbedRequest = req.body;
    if (!body.texts || !Array.isArray(body.texts)) {
      return res.status(400).json({
        error: 'Invalid request: texts array is required',
        correlationId
      } as ErrorResponse);
    }

    console.log(`📊 [${correlationId}] POST /v1/cohere/embed - Embedding ${body.texts.length} texts`);
    
    const result = await cohereClient.embed({
      texts: body.texts,
      model: body.model || 'embed-multilingual-v3.0',
      input_type: body.input_type || 'search_document',
    });

    const processingTime = req.startTime ? Date.now() - req.startTime : undefined;
    
    // Record successful analytics
    analytics.recordPayment(
      req.path, 
      PRICING.COHERE_EMBED, 
      'session-user', 
      true, 
      correlationId, 
      undefined, 
      processingTime, 
      isSessionBased ? 'v2' : 'v1'
    );

    console.log(`✅ [${correlationId}] /v1/cohere/embed - Completed in ${processingTime}ms`);
    
    const response: CohereEmbedResponse = {
      embeddings: result,
    };

    res.json(response);
  })
);

// Start server
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`🚀 x402 AI Service v2.0.0 running on port ${PORT}`);
  console.log(`📡 Facilitator: ${process.env.X402_FACILITATOR_URL || 'https://open.x402.host'}`);
  console.log(`🌐 Network: ${process.env.X402_NETWORK || 'base'}`);
  console.log(`💰 Pricing:`, PRICING);
  console.log(`🔒 Payment verification: Enabled (v1 + v2)`);
  console.log(`🎯 Session management: Enabled (1h timeout, $20 max, 200 requests)`);
  console.log(`🔧 Circuit breakers: Enabled for all AI services`);
  console.log(`📊 Analytics: Enhanced with protocol tracking`);
  console.log(`🏥 Health endpoints: /health, /health/services, /analytics/*`);
});
