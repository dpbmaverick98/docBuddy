import { Request, Response, NextFunction } from 'express';
import Web3 from 'web3';
import { PaymentPayload, PaymentRequiredResponse } from '../types';
import { analytics } from '../analytics';

export class PaymentMiddleware {
  private w3: Web3;
  private facilitatorUrl: string;
  private network: string;
  private receivingWalletAddress: string; // Wallet that receives payments

  constructor(facilitatorUrl: string, network: string, receivingWalletAddress: string) {
    this.w3 = new Web3();
    this.facilitatorUrl = facilitatorUrl;
    this.network = network;
    this.receivingWalletAddress = receivingWalletAddress.toLowerCase();
  }

  createMiddleware(requiredAmount: string) {
    return async (req: Request, res: Response, next: NextFunction) => {
      const endpoint = req.path;
      const clientIP = req.ip || req.connection.remoteAddress;
      console.log(`📨 [${clientIP}] ${req.method} ${endpoint} - Checking payment ($${requiredAmount}¢ required)`);

      try {
        const paymentHeader = req.headers['x402-payment'] as string;

        if (!paymentHeader) {
          console.log(`❌ [${clientIP}] ${endpoint} - No X402-Payment header provided`);
          return res.status(402).json({
            error: 'Payment required',
            payment_required: {
              network: this.network,
              scheme: 'exact',
              amount: requiredAmount,
              currency: 'USDC',
              recipient_address: this.receivingWalletAddress, // Where to send payment
              description: 'AI service payment'
            }
          });
        }

        const paymentPayload: PaymentPayload = JSON.parse(paymentHeader);

        // Verify payment payload structure
        console.log(`🔍 [${clientIP}] ${endpoint} - Verifying payment payload structure`);
        if (!this.isValidPaymentPayload(paymentPayload)) {
          console.log(`❌ [${clientIP}] ${endpoint} - Invalid payment payload structure`);
          return res.status(400).json({ error: 'Invalid payment payload' });
        }

        // Verify payment with facilitator
        console.log(`🔐 [${clientIP}] ${endpoint} - Verifying payment signature`);
        const verificationResult = await this.verifyPayment(paymentPayload, req);

        if (!verificationResult.valid) {
          console.log(`❌ [${clientIP}] ${endpoint} - Payment verification failed: ${verificationResult.error}`);
          return res.status(402).json({
            error: 'Payment verification failed',
            details: verificationResult.error
          });
        }

        // Payment verified, proceed
        console.log(`✅ [${clientIP}] ${endpoint} - Payment verified, proceeding with request`);
        next();
      } catch (error) {
        console.error('Payment middleware error:', error);
        res.status(500).json({ error: 'Payment processing error' });
      }
    };
  }

  private isValidPaymentPayload(payload: PaymentPayload): boolean {
    return (
      payload.network === this.network &&
      payload.scheme === 'exact' &&
      payload.currency === 'USDC' &&
      typeof payload.amount === 'string' &&
      typeof payload.timestamp === 'number' &&
      typeof payload.client_address === 'string' &&
      typeof payload.signature === 'string'
    );
  }

  private async verifyPayment(payload: PaymentPayload, req: Request): Promise<{ valid: boolean; error?: string }> {
    const clientIP = req.ip || req.connection.remoteAddress || 'unknown';
    const endpoint = req.path;
    
    console.log(`🔍 [${clientIP}] ${endpoint} - Starting payment verification`);
    console.log(`   Payload received:`, JSON.stringify(payload, null, 2));
    
    try {
      // Check timestamp validity (5 minutes window)
      const currentTime = Math.floor(Date.now() / 1000);
      const timeDiff = Math.abs(currentTime - payload.timestamp);
      
      console.log(`   Timestamp check: current=${currentTime}, payload=${payload.timestamp}, diff=${timeDiff}s`);

      if (timeDiff > 300) { // 5 minutes
        return { valid: false, error: 'Payment timestamp expired' };
      }

      // Verify required fields
      if (payload.network !== this.network ||
          payload.scheme !== 'exact' ||
          payload.currency !== 'USDC' ||
          !payload.amount ||
          !payload.client_address ||
          !payload.signature) {
        return { valid: false, error: 'Invalid payment payload structure' };
      }

      // Verify recipient address matches our receiving wallet
      if (payload.recipient_address && payload.recipient_address.toLowerCase() !== this.receivingWalletAddress) {
        console.log(`❌ [${clientIP}] ${endpoint} - Invalid recipient address: ${payload.recipient_address}. Expected: ${this.receivingWalletAddress}`);
        return { valid: false, error: `Invalid recipient address. Expected: ${this.receivingWalletAddress}` };
      }

      // Create the exact message that was signed (must match client's signed message exactly)
      // CRITICAL: Use addresses exactly as they appear in payload - don't convert to lowercase
      // The message must match byte-for-byte when signing and verifying
      // Client signs: JSON.stringify(payload, sort_keys=True, separators=(',', ':'))
      // This creates compact JSON with sorted keys: {"amount":"5","client_address":"0xBA4A...",...}
      const messagePayload: any = {
        amount: String(payload.amount),  // Ensure string format matches client
        client_address: payload.client_address,  // Use original casing (checksum format)
        currency: payload.currency,
        network: payload.network,
        scheme: payload.scheme,
        timestamp: payload.timestamp,
      };
      
      // Include recipient_address if present (required for payment verification)
      // Use original casing - don't convert to lowercase
      if (payload.recipient_address) {
        messagePayload.recipient_address = payload.recipient_address;
      }
      
      // Sort keys alphabetically to match Python's sort_keys=True behavior
      const sortedKeys = Object.keys(messagePayload).sort();
      const sortedPayload: any = {};
      for (const key of sortedKeys) {
        sortedPayload[key] = messagePayload[key];
      }
      
      // Use compact JSON format (no spaces) to match Python's separators=(',', ':')
      const message = JSON.stringify(sortedPayload);
      
      // Calculate message hash for comparison with client
      const crypto = require('crypto');
      const messageHash = crypto.createHash('sha256').update(message).digest('hex');
      
      // Log the exact message structure for debugging
      console.log(`📝 [${clientIP}] ${endpoint} - Message reconstruction:`);
      console.log(`   Sorted keys: [${sortedKeys.join(', ')}]`);
      console.log(`   Message payload object:`, JSON.stringify(messagePayload, null, 2));
      console.log(`   Sorted payload object:`, JSON.stringify(sortedPayload, null, 2));
      console.log(`   Message SHA256: ${messageHash.substring(0, 16)}...`);

      // Verify signature
      // Client uses encode_defunct which creates: "\x19Ethereum Signed Message:\n" + len(message) + message
      // web3.js hashMessage adds the same prefix automatically
      console.log(`🔐 [${clientIP}] ${endpoint} - Verifying signature`);
      console.log(`   Reconstructed message: ${message}`);
      console.log(`   Message length: ${message.length} bytes`);
      console.log(`   Message bytes (first 100): ${message.substring(0, 100)}`);
      console.log(`   Client address (from payload): ${payload.client_address}`);
      console.log(`   Recipient address (from payload): ${payload.recipient_address || 'N/A'}`);
      console.log(`   Signature: ${payload.signature.substring(0, 20)}...`);
      
      let signer: string;
      try {
        // CRITICAL FIX: Use recover directly from message string
        // Python's encode_defunct creates: "\x19Ethereum Signed Message:\n" + len(message) + message
        // web3.js recover() when given a string automatically adds the same prefix
        // hashMessage() was causing issues - direct recover works correctly
        signer = this.w3.eth.accounts.recover(message, payload.signature);
        
        console.log(`   Recovered signer: ${signer}`);
        console.log(`   Expected signer: ${payload.client_address}`);
        console.log(`   Match (case-insensitive): ${signer.toLowerCase() === payload.client_address.toLowerCase()}`);
        
        if (signer.toLowerCase() !== payload.client_address.toLowerCase()) {
          console.log(`   ❌ Signature mismatch!`);
          console.log(`   💡 This means the message being verified doesn't match what was signed.`);
          console.log(`   💡 Check client logs to see what message was actually signed.`);
          return { valid: false, error: 'Invalid signature' };
        }
        
        console.log(`   ✅ Signature verified!`);
      } catch (error: any) {
        console.error(`   Signature recovery error: ${error.message}`);
        console.error(`   Error stack:`, error.stack);
        return { valid: false, error: `Signature recovery failed: ${error.message}` };
      }

      // TODO: Verify payment was actually sent to receiving wallet via facilitator
      // For now, we trust the signature verification
      // In production, verify with facilitator that payment was sent to this.receivingWalletAddress

      // Payment is valid - record it
      analytics.recordPayment(req.path, parseInt(payload.amount), payload.client_address, true);
      console.log(`✅ Payment verified: ${payload.amount}¢ from ${payload.client_address} to ${this.receivingWalletAddress} for ${req.path}`);

      return { valid: true };

    } catch (error) {
      console.error('Payment verification error:', error);
      return { valid: false, error: 'Verification failed' };
    }
  }
}
