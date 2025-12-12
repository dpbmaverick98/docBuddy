import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { K2Client } from './clients/k2-client';
import { CohereClient } from './clients/cohere-client';
import { PaymentMiddleware } from './middleware/payment';
import { analytics } from './analytics';
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
  PaymentRequiredResponse
} from './types';

// Load environment variables
dotenv.config();

// Initialize clients
const k2Client = new K2Client(process.env.HF_TOKEN!);
const cohereClient = new CohereClient(process.env.COHERE_API_KEY!);

// Initialize payment middleware
const receivingWalletAddress = process.env.X402_RECEIVING_WALLET_ADDRESS;
if (!receivingWalletAddress) {
  console.error('❌ X402_RECEIVING_WALLET_ADDRESS not set - payments cannot be received!');
  process.exit(1);
}

const paymentMiddleware = new PaymentMiddleware(
  process.env.X402_FACILITATOR_URL || 'https://open.x402.host',
  process.env.X402_NETWORK || 'base',
  receivingWalletAddress
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

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    pricing: PRICING
  });
});

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

// Error handling middleware
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  } as ErrorResponse);
});

// ===== K2 ENDPOINTS =====

app.post(
  '/v1/k2/chat/completions',
  paymentMiddleware.createMiddleware(PRICING.K2_CHAT.toString()),
  async (req: express.Request, res: express.Response) => {
    try {
      const body: K2ChatRequest = req.body;

      // Validate request
      if (!body.messages || !Array.isArray(body.messages) || body.messages.length === 0) {
        return res.status(400).json({
          error: 'Invalid request: messages array is required'
        } as ErrorResponse);
      }

      const result = await k2Client.generate({
        messages: body.messages,
        max_tokens: body.max_tokens || 1000,
        temperature: body.temperature || 0.7,
      });

      const response: K2ChatResponse = {
        choices: [{
          message: {
            role: 'assistant',
            content: result,
          },
        }],
      };

      res.json(response);
    } catch (error: any) {
      console.error('K2 error:', error);
      res.status(500).json({
        error: 'Failed to generate K2 response',
        details: process.env.NODE_ENV === 'development' ? error.message : undefined
      } as ErrorResponse);
    }
  }
);

// ===== COHERE ENDPOINTS =====

app.post(
  '/v1/cohere/rerank',
  paymentMiddleware.createMiddleware(PRICING.COHERE_RERANK.toString()),
  async (req: express.Request, res: express.Response) => {
    try {
      const body: CohereRerankRequest = req.body;

      // Validate request
      if (!body.query || !body.documents || !Array.isArray(body.documents)) {
        return res.status(400).json({
          error: 'Invalid request: query and documents array are required'
        } as ErrorResponse);
      }

      const result = await cohereClient.rerank({
        query: body.query,
        documents: body.documents,
        top_n: body.top_n || 5,
        model: body.model || 'rerank-english-v3.0',
      });

      const response: CohereRerankResponse = {
        results: result,
      };

      res.json(response);
    } catch (error: any) {
      console.error('Cohere rerank error:', error);
      res.status(500).json({
        error: 'Failed to rerank documents',
        details: process.env.NODE_ENV === 'development' ? error.message : undefined
      } as ErrorResponse);
    }
  }
);

app.post(
  '/v1/cohere/chat',
  paymentMiddleware.createMiddleware(PRICING.COHERE_CHAT.toString()),
  async (req: express.Request, res: express.Response) => {
    try {
      const body: CohereChatRequest = req.body;

      // Validate request
      if (!body.message) {
        return res.status(400).json({
          error: 'Invalid request: message is required'
        } as ErrorResponse);
      }

      const result = await cohereClient.chat({
        message: body.message,
        max_tokens: body.max_tokens || 100,
        temperature: body.temperature || 0.2,
      });

      const response: CohereChatResponse = {
        text: result,
      };

      res.json(response);
    } catch (error: any) {
      console.error('Cohere chat error:', error);
      res.status(500).json({
        error: 'Failed to generate Cohere response',
        details: process.env.NODE_ENV === 'development' ? error.message : undefined
      } as ErrorResponse);
    }
  }
);

app.post(
  '/v1/cohere/embed',
  paymentMiddleware.createMiddleware(PRICING.COHERE_EMBED.toString()),
  async (req: express.Request, res: express.Response) => {
    try {
      const body: CohereEmbedRequest = req.body;

      // Validate request
      if (!body.texts || !Array.isArray(body.texts)) {
        return res.status(400).json({
          error: 'Invalid request: texts array is required'
        } as ErrorResponse);
      }

      const result = await cohereClient.embed({
        texts: body.texts,
        model: body.model || 'embed-multilingual-v3.0',
        input_type: body.input_type || 'search_document',
      });

      const response: CohereEmbedResponse = {
        embeddings: result,
      };

      res.json(response);
    } catch (error: any) {
      console.error('Cohere embed error:', error);
      res.status(500).json({
        error: 'Failed to generate embeddings',
        details: process.env.NODE_ENV === 'development' ? error.message : undefined
      } as ErrorResponse);
    }
  }
);

// Start server
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`🚀 x402 AI Service running on port ${PORT}`);
  console.log(`📡 Facilitator: ${process.env.X402_FACILITATOR_URL || 'https://open.x402.host'}`);
  console.log(`🌐 Network: ${process.env.X402_NETWORK || 'base'}`);
  console.log(`💰 Pricing:`, PRICING);
  console.log(`🔒 Payment verification: Enabled`);
});
