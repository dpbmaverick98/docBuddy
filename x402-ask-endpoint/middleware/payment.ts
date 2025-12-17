import { paymentMiddleware as x402PaymentMiddleware } from 'x402-hono';
import 'dotenv/config';

type SupportedNetwork = "base" | "base-sepolia" | "abstract" | "abstract-testnet" | "avalanche-fuji" | "avalanche" | "iotex" | "solana-devnet" | "solana" | "sei" | "sei-testnet" | "polygon" | "polygon-amoy" | "peaq" | "story" | "educhain" | "skale-base-sepolia";

// Define the payment middleware using the official x402-hono API
export const paymentMiddleware = x402PaymentMiddleware(
  process.env.X402_RECIPIENT_ADDRESS! as `0x${string}`, // your receiving wallet address
  {  // Route configurations for protected endpoints
    'POST /api/docsbuddy/ask': {
      price: `$${process.env.X402_PRICE_USD!}`, // Price in USD, e.g., "$0.20"
      network: process.env.X402_CHAIN! as SupportedNetwork, // e.g., "base"
      config: {
        description: 'Access DocsBuddy Q&A for polymarket/privy projects',
        mimeType: 'application/json',
      }
    }
  },
  {
    url: process.env.X402_FACILITATOR_URL! as `https://${string}`, // Facilitator URL
  }
);