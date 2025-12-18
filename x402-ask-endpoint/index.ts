import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { paymentMiddleware } from './middleware/payment';
import { proxyToFastAPI } from './utils/proxy';
import 'dotenv/config';

// Validate env vars
const requiredEnv = ['X402_CHAIN', 'X402_RECIPIENT_ADDRESS', 'X402_PRICE_USD', 'X402_FACILITATOR_URL', 'ALLOWED_PROJECTS', 'FASTAPI_URL'];
for (const env of requiredEnv) {
  if (!process.env[env]) {
    console.error(`Missing required env var: ${env}`);
    process.exit(1);
  }
}

const app = new Hono();

// CORS middleware
app.use('*', cors({
  origin: '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowHeaders: ['Content-Type', 'PAYMENT-SIGNATURE', 'PAYMENT-REQUIRED', 'PAYMENT-RESPONSE'],
}));

// Apply payment middleware to all routes
app.use('*', paymentMiddleware);

// Proxy protected routes to FastAPI after payment verification
app.use('/api/docsbuddy/ask/:project', async (c) => {
  return proxyToFastAPI(c, process.env.FASTAPI_URL!);
});

// Health check
app.get('/health', (c) => c.json({ status: 'healthy' }));

// Root
app.get('/', (c) => c.json({
  message: 'x402 Ask Endpoint Gateway',
  status: 'running',
  protectedRoutes: ['POST /api/docsbuddy/ask/privy', 'POST /api/docsbuddy/ask/polymarket'],
}));

export default {
  port: 4020,
  fetch: app.fetch,
};