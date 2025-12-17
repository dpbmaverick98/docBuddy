# x402 Ask Endpoint Server

This is a Bun-based gateway server that monetizes the DocsBuddy ask endpoint using the x402 payment protocol. It acts as a proxy in front of the FastAPI backend, requiring USDC payments on Base mainnet for access to the Q&A service.

## Overview

The server protects the `POST /api/docsbuddy/ask` endpoint with x402 payments. External requests must include valid payment signatures, or receive a 402 Payment Required response. Upon verification, requests are forwarded to the FastAPI backend with modifications (project validation, model locking).

Key features:
- x402 protocol integration
- Base network USDC payments (1 cent per request for testing)
- Project validation (privy/polymarket)
- Model forced to hf-k2-openai
- Automatic settlement after successful responses

## Prerequisites

- Node.js / Bun runtime
- Access to Base mainnet wallet for receiving payments
- Facilitator URL (e.g., https://x402.org/facilitator for testing, or production from CDP)
- Running FastAPI backend at configured URL
- Install dependencies: `bun install`

## Installation

1. Navigate to the server directory:
   ```bash
   cd x402-ask-endpoint
   ```

2. Install dependencies:
   ```bash
   bun install
   ```

## Configuration

Copy `.env.example` to `.env` and update with your values:

```env
X402_CHAIN=base  # Base network (testnet facilitator)
X402_RECIPIENT_ADDRESS=0xYourBaseWalletAddress  # Replace with your actual Base wallet
X402_PRICE_USD=0.01  # Price in USD (0.01 = 1 cent for testing)
X402_FACILITATOR_URL=https://x402.org/facilitator  # Test facilitator; replace for production
ALLOWED_PROJECTS=privy,polymarket
FASTAPI_URL=http://localhost:8000  # URL of your FastAPI backend
```

**Important**: This is configured for Base network with test facilitator. Get test USDC from faucets. Replace `X402_RECIPIENT_ADDRESS` with your wallet. For production mainnet, use a production facilitator URL.

## Running the Server

1. Ensure your FastAPI backend is running on the configured URL.

2. Create `.env` file from `.env.example` and fill in your values.

3. Start the server:
    ```bash
    bun run dev
    ```

    The server will start on port 4020.

4. Health check:
    ```bash
    curl http://localhost:4020/health
    ```

    Expected response: `{"status": "healthy"}`

## Architecture

- **middleware/payment.ts**: Uses x402-hono paymentMiddleware to handle payment verification and return 402 if unpaid.
- **utils/proxy.ts**: Proxies verified requests to FastAPI, validates projects, locks model, handles settlement.
- **index.ts**: Hono server setup with CORS, routes, and middleware application.

## Testing

- **Without Payment**: Send a POST to `/api/docsbuddy/ask` without payment. Should return 402 Payment Required with payment instructions.
- **With Invalid Payment**: Provide invalid payment; should return 402 error.
- **With Valid Payment**: Use x402-fetch client to pay and call; should proxy to FastAPI and return response with settlement header.
- **Project Validation**: Requests with invalid projects should fail with 400.

Use the provided `test-client.ts` script to test the full payment flow. Ensure your .env has PRIVATE_KEY and SERVER_URL set.

## Deployment

- Deploy to a Bun-compatible host (e.g., Railway, Vercel, or self-hosted).
- Ensure env variables are set securely.
- Monitor logs for facilitator errors or settlement failures.
- In production, use a production facilitator URL.

## Troubleshooting

- **Port in use**: Change port in `index.ts` if 4020 is occupied.
- **Env errors**: Check console for missing required env vars on startup.
- **Facilitator failures**: Verify facilitator URL and network connectivity.
- **FastAPI proxy issues**: Ensure FastAPI is running and accessible.

## Security Notes

- Payments are verified via facilitator; no sensitive data stored.
- Requests are proxied with minimal modification.
- Use HTTPS in production for secure header transmission.</content>
<parameter name="filePath">x402-ask-endpoint/README.md