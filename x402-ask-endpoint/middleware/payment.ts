import { paymentMiddleware as x402PaymentMiddleware } from 'x402-hono';
import 'dotenv/config';

type SupportedNetwork = "base" | "base-sepolia" | "abstract" | "abstract-testnet" | "avalanche-fuji" | "avalanche" | "iotex" | "solana-devnet" | "solana" | "sei" | "sei-testnet" | "polygon" | "polygon-amoy" | "peaq" | "story" | "educhain" | "skale-base-sepolia";

// Define the payment middleware using the official x402-hono API
const recipientAddress = process.env.X402_RECIPIENT_ADDRESS! as `0x${string}`;
const price = `$${process.env.X402_PRICE_USD!}`;
const network = process.env.X402_CHAIN! as SupportedNetwork;
const facilitatorUrl = process.env.X402_FACILITATOR_URL!;

console.log('💰 Payment middleware config:', { recipientAddress, price, network, facilitatorUrl });

export const paymentMiddleware = x402PaymentMiddleware(
  recipientAddress, // your receiving wallet address
  {  // Route configurations for protected endpoints
    'POST /api/docsbuddy/ask/*': {
      price, // Price in USD, e.g., "$0.01"
      network, // e.g., "base"
      config: {
        description: 'Access DocsBuddy Q&A for polymarket/privy projects',
        mimeType: 'application/json',
      }
    }
  },
  {
    url: facilitatorUrl, // Facilitator URL
  }
);