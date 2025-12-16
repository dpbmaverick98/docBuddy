# x402 AI Service Gateway v2.0.0

x402 payment-gated AI service that provides access to Kimi K2 and Cohere APIs with USDC payments. Now with x402 v2 protocol support and enhanced robustness features.

## Features

- 🔒 Payment-gated API access using x402 v1 and v2 protocols
- 🎯 **NEW**: Wallet-based session management to reduce repeated payments
- 🛡️ **NEW**: Circuit breakers and retry logic for enhanced reliability
- 📊 **NEW**: Enhanced analytics with protocol tracking and error breakdown
- 🤖 Kimi K2-Instruct LLM via HuggingFace
- 🔍 Cohere Rerank, Chat, and Embeddings
- 💰 Configurable pricing per endpoint
- 🌐 HTTP-based API with OpenAI-compatible interface
- 🔐 Wallet-based payment verification
- 🏥 **NEW**: Comprehensive health check endpoints

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
# Edit .env with your API keys and receiving wallet address
```

**Important Wallet Configuration:**
- **`X402_RECEIVING_WALLET_ADDRESS`**: Your wallet address that **receives** USDC payments
- This is the service operator's wallet (where fees go)
- DocsBuddy (the client) has its own wallet with private key for signing payments

### 3. Build and Run

```bash
npm run build
npm start
```

## API Endpoints

### AI Endpoints

- `POST /v1/k2/chat/completions` - Chat completions (50¢)
- `POST /v1/cohere/rerank` - Document reranking (10¢)
- `POST /v1/cohere/chat` - Chat/completion (5¢)
- `POST /v1/cohere/embed` - Text embeddings (2¢)

### Monitoring & Analytics

- `GET /health` - Service health status (200/503 based on service health)
- `GET /health/services` - Detailed service health with circuit breaker status
- `GET /analytics` - Payment analytics (default 24h, customizable with `?hours=`)
- `GET /analytics/payments` - Recent payment history (default 50, customizable with `?limit=`)
- `GET /analytics/errors` - Recent error breakdown (default 50, customizable with `?limit=`)
- `GET /analytics/sessions` - Active session statistics

## Payment Flow

### x402 v1 (Legacy)
1. Client includes `X402-Payment` header with signed payment payload
2. Server verifies payment signature and amount
3. Server verifies payment execution with facilitator
4. If valid, API call proceeds and response is returned

### x402 v2 (Recommended)
1. Client includes `PAYMENT-SIGNATURE` header with base64-encoded v2 payload
2. Server validates structured EIP-712 signature and authorization
3. **Session Management**: If wallet has active session, payment verification is skipped
4. If valid, API call proceeds and response is returned

## Session Management (v2 Feature)

- **Session Duration**: 1 hour (configurable)
- **Max Value per Session**: $20 (2,000 cents, configurable)
- **Max Requests per Session**: 200 (configurable)
- **Benefits**: Reduced latency, lower gas costs, improved user experience

## Circuit Breakers & Reliability

- **Automatic Failure Detection**: Circuit breakers trigger after 3 consecutive failures
- **Graceful Recovery**: Half-open state tests service recovery
- **Retry Logic**: Exponential backoff for transient failures
- **Service-Specific**: Separate breakers for K2, Cohere Rerank/Chat/Embed

## Configuration

### Pricing

Configure costs in `.env`:

```bash
K2_CHAT_COST=50          # $0.50 per request
COHERE_RERANK_COST=10    # $0.10 per request
COHERE_CHAT_COST=5       # $0.05 per request
COHERE_EMBED_COST=2      # $0.02 per request
```

### Session Management

```bash
# Optional: Override default session settings
SESSION_TIMEOUT_MS=3600000        # 1 hour in ms
MAX_SESSION_VALUE_CENTS=2000      # $20 per session
MAX_REQUESTS_PER_SESSION=200      # 200 requests per session
```

### Facilitator

```bash
X402_FACILITATOR_URL=https://open.x402.host
X402_NETWORK=base
```

## x402 v2 Headers

- **v1**: `X402-Payment: {JSON payload}`
- **v2**: `PAYMENT-SIGNATURE: {base64-encoded-v2-payload}`
- **Response**: `PAYMENT-REQUIRED: {base64-encoded-requirements}` (when payment needed)

## Integration with DocsBuddy

DocsBuddy can use this service instead of calling AI APIs directly. With x402 v2 and session management:

1. **First Request**: Full payment verification
2. **Subsequent Requests (1h)**: Automatic session access, no additional payments
3. **Enhanced Experience**: Lower latency, reduced gas costs

## Error Responses

All errors include:
- `error`: Human-readable error message
- `code`: Machine-readable error code (e.g., `PAYMENT_REQUIRED`, `SERVICE_UNAVAILABLE`)
- `correlationId`: Unique request identifier for debugging
- `retryAfter`: Seconds to wait (for rate limiting, service unavailability)

## Monitoring

The service provides comprehensive monitoring:
- **Health Status**: Real-time service health with circuit breaker states
- **Analytics**: Payment analytics by protocol, endpoint, and error type
- **Session Stats**: Active sessions, usage patterns, and limits
- **Error Tracking**: Detailed error categorization and trends

## Development

```bash
# Development mode
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

## Migration from v1 to v2

1. **No Breaking Changes**: Existing v1 clients continue to work
2. **Gradual Upgrade**: Update clients to use PAYMENT-SIGNATURE header
3. **Session Benefits**: Implement v2 to enable session management
4. **Enhanced Monitoring**: Use new analytics endpoints for insights</contents>
</xai:function_call name="run_terminal_cmd">
<parameter name="command">cd /Users/dpbmaverick98/docsBuddy/docBuddy/x402-service && npm install
