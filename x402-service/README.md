# x402 AI Service Gateway

x402 payment-gated AI service that provides access to Kimi K2 and Cohere APIs with USDC payments.

## Features

- 🔒 Payment-gated API access using x402 protocol
- 🤖 Kimi K2-Instruct LLM via HuggingFace
- 🔍 Cohere Rerank, Chat, and Embeddings
- 💰 Configurable pricing per endpoint
- 🌐 HTTP-based API with OpenAI-compatible interface
- 🔐 Wallet-based payment verification

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

### K2 Endpoints

- `POST /v1/k2/chat/completions` - Chat completions (50¢)

### Cohere Endpoints

- `POST /v1/cohere/rerank` - Document reranking (10¢)
- `POST /v1/cohere/chat` - Chat/completion (5¢)
- `POST /v1/cohere/embed` - Text embeddings (2¢)

## Payment Flow

1. Client includes `X402-Payment` header with signed payment payload
2. Server verifies payment signature and amount
3. Server verifies payment execution with facilitator
4. If valid, API call proceeds and response is returned

## Configuration

### Pricing

Configure costs in `.env`:

```bash
K2_CHAT_COST=50          # $0.50 per request
COHERE_RERANK_COST=10    # $0.10 per request
COHERE_CHAT_COST=5       # $0.05 per request
COHERE_EMBED_COST=2      # $0.02 per request
```

### Facilitator

```bash
X402_FACILITATOR_URL=https://open.x402.host
X402_NETWORK=base
```

## Integration with DocsBuddy

DocsBuddy can use this service instead of calling AI APIs directly. Each request will require payment verification, ensuring pay-per-use billing.

## Development

```bash
# Development mode
npm run dev

# Build for production
npm run build

# Run tests
npm test
```</contents>
</xai:function_call name="run_terminal_cmd">
<parameter name="command">cd /Users/dpbmaverick98/docsBuddy/docBuddy/x402-service && npm install
