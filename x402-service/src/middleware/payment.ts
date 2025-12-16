import { Request, Response, NextFunction } from 'express';
import Web3 from 'web3';
import { 
  PaymentPayload, 
  PaymentPayloadV2, 
  PaymentRequiredResponse,
  PaymentRequiredResponseV2,
  SettlementResponse,
  ErrorResponse 
} from '../types';
import { analytics } from '../analytics';
import { SessionManager } from '../services/session-manager';
import crypto from 'crypto';

export class PaymentMiddleware {
  private w3: Web3;
  private facilitatorUrl: string;
  private network: string;
  private receivingWalletAddress: string; // Wallet that receives payments
  private sessionManager?: SessionManager;

  constructor(facilitatorUrl: string, network: string, receivingWalletAddress: string, sessionManager?: SessionManager) {
    this.w3 = new Web3();
    this.facilitatorUrl = facilitatorUrl;
    this.network = network;
    this.receivingWalletAddress = receivingWalletAddress.toLowerCase();
    this.sessionManager = sessionManager;
  }

  createMiddleware(requiredAmount: string) {
    return async (req: Request, res: Response, next: NextFunction) => {
      const endpoint = req.path;
      const clientIP = req.ip || req.connection.remoteAddress;
      const correlationId = crypto.randomUUID();
      console.log(`📨 [${clientIP}] ${req.method} ${endpoint} [${correlationId}] - Checking payment ($${requiredAmount}¢ required)`);

      try {
        // Check for v2 headers first, then fall back to v1
        const v2PaymentHeader = req.headers['payment-signature'] as string;
        const v1PaymentHeader = req.headers['x402-payment'] as string;
        
        if (!v2PaymentHeader && !v1PaymentHeader) {
          console.log(`❌ [${clientIP}] ${endpoint} [${correlationId}] - No payment header provided`);
          return this.sendPaymentRequiredResponse(res, requiredAmount, endpoint, correlationId);
        }

        // Process based on header version
        if (v2PaymentHeader) {
          return this.processV2Payment(req, res, next, v2PaymentHeader, requiredAmount, correlationId);
        } else {
          return this.processV1Payment(req, res, next, v1PaymentHeader, requiredAmount, correlationId);
        }
      } catch (error) {
        console.error(`Payment middleware error [${correlationId}]:`, error);
        res.status(500).json({ 
          error: 'Payment processing error',
          correlationId
        } as ErrorResponse);
      }
    };
  }

  private sendPaymentRequiredResponse(res: Response, requiredAmount: string, endpoint: string, correlationId: string) {
    // Return v2 format by default with v1 fallback in headers
    const paymentRequirements = {
      scheme: 'exact' as const,
      network: this.network,
      maxAmountRequired: requiredAmount,
      resource: `${res.req?.protocol}://${res.req?.get('host')}${endpoint}`,
      description: 'AI service payment',
      mimeType: 'application/json',
      payTo: this.receivingWalletAddress,
      maxTimeoutSeconds: 300,
      asset: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', // USDC on Base
      extra: {
        name: 'USD Coin',
        version: '2'
      }
    };

    res.setHeader('X-Payment-Required', Buffer.from(JSON.stringify(paymentRequirements)).toString('base64'));
    
    return res.status(402).json({
      x402Version: 2,
      error: 'Payment required',
      accepts: [paymentRequirements],
      correlationId
    } as PaymentRequiredResponseV2);
  }

  private async processV1Payment(
    req: Request, 
    res: Response, 
    next: NextFunction, 
    paymentHeader: string, 
    requiredAmount: string,
    correlationId: string
  ) {
    const endpoint = req.path;
    const clientIP = req.ip || req.connection.remoteAddress;

    try {
      const paymentPayload: PaymentPayload = JSON.parse(paymentHeader);

      // Check for existing session to skip payment
      if (this.sessionManager) {
        const walletAddress = paymentPayload.client_address.toLowerCase();
        const sessionCheck = this.sessionManager.canAccessEndpoint(walletAddress, endpoint);
        
        if (sessionCheck.allowed) {
          console.log(`🎯 [${correlationId}] Using existing session for ${walletAddress} - skipping payment verification`);
          
          // Update session usage
          this.sessionManager.createOrUpdateSession(walletAddress, parseInt(requiredAmount), endpoint);
          
          // Record analytics for session usage
          analytics.recordPayment(endpoint, parseInt(requiredAmount), walletAddress, true, correlationId, undefined, undefined, 'v1');
          
          req.headers['x-correlation-id'] = correlationId;
          req.headers['x-session-based'] = 'true';
          return next();
        } else {
          console.log(`🚫 [${correlationId}] Session check failed: ${sessionCheck.reason}`);
        }
      }

      // Verify payment payload structure
      console.log(`🔍 [${clientIP}] ${endpoint} [${correlationId}] - Verifying v1 payment payload structure`);
      if (!this.isValidV1PaymentPayload(paymentPayload)) {
        console.log(`❌ [${clientIP}] ${endpoint} [${correlationId}] - Invalid v1 payment payload structure`);
        return res.status(400).json({ error: 'Invalid payment payload', correlationId } as ErrorResponse);
      }

      // Verify payment with facilitator
      console.log(`🔐 [${clientIP}] ${endpoint} [${correlationId}] - Verifying v1 payment signature`);
      const verificationResult = await this.verifyV1Payment(paymentPayload, req, correlationId);

      if (!verificationResult.valid) {
        console.log(`❌ [${clientIP}] ${endpoint} [${correlationId}] - Payment verification failed: ${verificationResult.error}`);
        return res.status(402).json({
          error: 'Payment verification failed',
          details: verificationResult.error,
          correlationId
        } as ErrorResponse);
      }

      // Payment verified, proceed
      console.log(`✅ [${clientIP}] ${endpoint} [${correlationId}] - Payment verified, proceeding with request`);
      req.headers['x-correlation-id'] = correlationId;
      next();
    } catch (error: any) {
      console.error(`Payment processing error [${correlationId}]:`, error);
      res.status(500).json({ 
        error: 'Payment processing error',
        details: error.message,
        correlationId
      } as ErrorResponse);
    }
  }

  private async processV2Payment(
    req: Request, 
    res: Response, 
    next: NextFunction, 
    paymentHeader: string, 
    requiredAmount: string,
    correlationId: string
  ) {
    const clientIP = req.ip || req.connection.remoteAddress || 'unknown';
    const endpoint = req.path;

    try {
      // v2 payment header is base64 encoded
      const decodedHeader = Buffer.from(paymentHeader, 'base64').toString('utf8');
      const paymentPayload: PaymentPayloadV2 = JSON.parse(decodedHeader);

      // Verify v2 payload structure
      console.log(`🔍 [${clientIP}] ${endpoint} [${correlationId}] - Verifying v2 payment payload structure`);
      if (!this.isValidV2PaymentPayload(paymentPayload)) {
        console.log(`❌ [${clientIP}] ${endpoint} [${correlationId}] - Invalid v2 payment payload structure`);
        return res.status(400).json({ error: 'Invalid payment payload', correlationId } as ErrorResponse);
      }

      // Check for existing session to skip payment
      if (this.sessionManager) {
        const walletAddress = paymentPayload.payload.authorization.from.toLowerCase();
        const sessionCheck = this.sessionManager.canAccessEndpoint(walletAddress, endpoint);
        
        if (sessionCheck.allowed) {
          console.log(`🎯 [${correlationId}] Using existing session for ${walletAddress} - skipping payment verification`);
          
          // Update session usage
          this.sessionManager.createOrUpdateSession(walletAddress, parseInt(requiredAmount), endpoint);
          
          // Record analytics for session usage
          analytics.recordPayment(endpoint, parseInt(requiredAmount), walletAddress, true, correlationId, undefined, undefined, 'v2');
          
          req.headers['x-correlation-id'] = correlationId;
          req.headers['x-session-based'] = 'true';
          return next();
        } else {
          console.log(`🚫 [${correlationId}] Session check failed: ${sessionCheck.reason}`);
        }
      }

      // Verify payment
      console.log(`🔐 [${clientIP}] ${endpoint} [${correlationId}] - Verifying v2 payment signature`);
      const verificationResult = await this.verifyV2Payment(paymentPayload, req, correlationId);

      if (!verificationResult.valid) {
        console.log(`❌ [${clientIP}] ${endpoint} [${correlationId}] - Payment verification failed: ${verificationResult.error}`);
        return res.status(402).json({
          error: 'Payment verification failed',
          details: verificationResult.error,
          correlationId
        } as ErrorResponse);
      }

      // Payment verified, proceed
      console.log(`✅ [${clientIP}] ${endpoint} [${correlationId}] - Payment verified, proceeding with request`);
      req.headers['x-correlation-id'] = correlationId;
      next();
    } catch (error: any) {
      console.error(`Payment processing error [${correlationId}]:`, error);
      res.status(500).json({ 
        error: 'Payment processing error',
        details: error.message,
        correlationId
      } as ErrorResponse);
    }
  }

  private isValidV1PaymentPayload(payload: PaymentPayload): boolean {
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

  private isValidV2PaymentPayload(payload: PaymentPayloadV2): boolean {
    return (
      payload.x402Version === 2 &&
      payload.scheme === 'exact' &&
      payload.network === this.network &&
      !!payload.payload &&
      !!payload.payload.signature &&
      !!payload.payload.authorization &&
      typeof payload.payload.authorization.from === 'string' &&
      typeof payload.payload.authorization.to === 'string' &&
      typeof payload.payload.authorization.value === 'string'
    );
  }

  private async verifyV1Payment(payload: PaymentPayload, req: Request, correlationId: string): Promise<{ valid: boolean; error?: string }> {
    const clientIP = req.ip || req.connection.remoteAddress || 'unknown';
    const endpoint = req.path;
    
    console.log(`🔍 [${clientIP}] ${endpoint} [${correlationId}] - Starting v1 payment verification`);
    console.log(`   Payload received:`, JSON.stringify(payload, null, 2));
    
    try {
      // Check timestamp validity (5 minutes window)
      const currentTime = Math.floor(Date.now() / 1000);
      const timeDiff = Math.abs(currentTime - payload.timestamp);
      
      console.log(`   [${correlationId}] Timestamp check: current=${currentTime}, payload=${payload.timestamp}, diff=${timeDiff}s`);

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
        console.log(`❌ [${clientIP}] ${endpoint} [${correlationId}] - Invalid recipient address: ${payload.recipient_address}. Expected: ${this.receivingWalletAddress}`);
        return { valid: false, error: `Invalid recipient address. Expected: ${this.receivingWalletAddress}` };
      }

      // Create the exact message that was signed (must match client's signed message exactly)
      const messagePayload: any = {
        amount: String(payload.amount),
        client_address: payload.client_address,
        currency: payload.currency,
        network: payload.network,
        scheme: payload.scheme,
        timestamp: payload.timestamp,
      };
      
      if (payload.recipient_address) {
        messagePayload.recipient_address = payload.recipient_address;
      }
      
      const sortedKeys = Object.keys(messagePayload).sort();
      const sortedPayload: any = {};
      for (const key of sortedKeys) {
        sortedPayload[key] = messagePayload[key];
      }
      
      const message = JSON.stringify(sortedPayload);
      const messageHash = crypto.createHash('sha256').update(message).digest('hex');
      
      console.log(`📝 [${clientIP}] ${endpoint} [${correlationId}] - Message reconstruction:`);
      console.log(`   [${correlationId}] Sorted keys: [${sortedKeys.join(', ')}]`);
      console.log(`   [${correlationId}] Message payload object:`, JSON.stringify(messagePayload, null, 2));
      console.log(`   [${correlationId}] Sorted payload object:`, JSON.stringify(sortedPayload, null, 2));
      console.log(`   [${correlationId}] Message SHA256: ${messageHash.substring(0, 16)}...`);

      console.log(`🔐 [${clientIP}] ${endpoint} [${correlationId}] - Verifying signature`);
      console.log(`   [${correlationId}] Reconstructed message: ${message}`);
      console.log(`   [${correlationId}] Message length: ${message.length} bytes`);
      console.log(`   [${correlationId}] Message bytes (first 100): ${message.substring(0, 100)}`);
      console.log(`   [${correlationId}] Client address (from payload): ${payload.client_address}`);
      console.log(`   [${correlationId}] Recipient address (from payload): ${payload.recipient_address || 'N/A'}`);
      console.log(`   [${correlationId}] Signature: ${payload.signature.substring(0, 20)}...`);
      
      let signer: string;
      try {
        signer = this.w3.eth.accounts.recover(message, payload.signature);
        
        console.log(`   [${correlationId}] Recovered signer: ${signer}`);
        console.log(`   [${correlationId}] Expected signer: ${payload.client_address}`);
        console.log(`   [${correlationId}] Match (case-insensitive): ${signer.toLowerCase() === payload.client_address.toLowerCase()}`);
        
        if (signer.toLowerCase() !== payload.client_address.toLowerCase()) {
          console.log(`   [${correlationId}] ❌ Signature mismatch!`);
          console.log(`   [${correlationId}] 💡 This means the message being verified doesn't match what was signed.`);
          console.log(`   [${correlationId}] 💡 Check client logs to see what message was actually signed.`);
          return { valid: false, error: 'Invalid signature' };
        }
        
        console.log(`   [${correlationId}] ✅ Signature verified!`);
      } catch (error: any) {
        console.error(`   [${correlationId}] Signature recovery error: ${error.message}`);
        console.error(`   [${correlationId}] Error stack:`, error.stack);
        return { valid: false, error: `Signature recovery failed: ${error.message}` };
      }

      // Payment is valid - record it and create/update session
      const amount = parseInt(payload.amount);
      analytics.recordPayment(req.path, amount, payload.client_address, true, correlationId, undefined, undefined, 'v1');
      
      if (this.sessionManager) {
        this.sessionManager.createOrUpdateSession(payload.client_address.toLowerCase(), amount, req.path);
      }
      
      console.log(`✅ [${correlationId}] Payment verified: ${payload.amount}¢ from ${payload.client_address} to ${this.receivingWalletAddress} for ${req.path}`);

      return { valid: true };

    } catch (error) {
      console.error(`Payment verification error [${correlationId}]:`, error);
      return { valid: false, error: 'Verification failed' };
    }
  }

  private async verifyV2Payment(payload: PaymentPayloadV2, req: Request, correlationId: string): Promise<{ valid: boolean; error?: string }> {
    const clientIP = req.ip || req.connection.remoteAddress || 'unknown';
    const endpoint = req.path;
    
    console.log(`🔍 [${clientIP}] ${endpoint} [${correlationId}] - Starting v2 payment verification`);
    console.log(`   [${correlationId}] Payload received:`, JSON.stringify(payload, null, 2));
    
    try {
      const auth = payload.payload.authorization;
      
      // Verify timestamp validity (using validBefore)
      const currentTime = Math.floor(Date.now() / 1000);
      const validBefore = parseInt(auth.validBefore);
      
      console.log(`   [${correlationId}] Validity check: current=${currentTime}, validBefore=${validBefore}`);
      
      if (currentTime > validBefore) {
        return { valid: false, error: 'Payment authorization expired' };
      }

      // Verify recipient address matches our receiving wallet
      if (auth.to.toLowerCase() !== this.receivingWalletAddress) {
        console.log(`❌ [${clientIP}] ${endpoint} [${correlationId}] - Invalid recipient address: ${auth.to}. Expected: ${this.receivingWalletAddress}`);
        return { valid: false, error: `Invalid recipient address. Expected: ${this.receivingWalletAddress}` };
      }

      // Create EIP-712 message for verification (simplified version)
      const message = JSON.stringify({
        from: auth.from,
        to: auth.to,
        value: auth.value,
        validAfter: auth.validAfter,
        validBefore: auth.validBefore,
        nonce: auth.nonce
      });

      console.log(`🔐 [${clientIP}] ${endpoint} [${correlationId}] - Verifying v2 signature`);
      console.log(`   [${correlationId}] Message: ${message}`);
      console.log(`   [${correlationId}] Signature: ${payload.payload.signature.substring(0, 20)}...`);
      
      let signer: string;
      try {
        signer = this.w3.eth.accounts.recover(message, payload.payload.signature);
        
        console.log(`   [${correlationId}] Recovered signer: ${signer}`);
        console.log(`   [${correlationId}] Expected signer: ${auth.from}`);
        console.log(`   [${correlationId}] Match (case-insensitive): ${signer.toLowerCase() === auth.from.toLowerCase()}`);
        
        if (signer.toLowerCase() !== auth.from.toLowerCase()) {
          console.log(`   [${correlationId}] ❌ Signature mismatch!`);
          return { valid: false, error: 'Invalid signature' };
        }
        
        console.log(`   [${correlationId}] ✅ Signature verified!`);
      } catch (error: any) {
        console.error(`   [${correlationId}] Signature recovery error: ${error.message}`);
        return { valid: false, error: `Signature recovery failed: ${error.message}` };
      }

      // Payment is valid - record it and create/update session
      const amount = parseInt(auth.value);
      analytics.recordPayment(req.path, amount, auth.from, true, correlationId, undefined, undefined, 'v2');
      
      if (this.sessionManager) {
        this.sessionManager.createOrUpdateSession(auth.from.toLowerCase(), amount, req.path);
      }
      
      console.log(`✅ [${correlationId}] Payment verified: ${auth.value}¢ from ${auth.from} to ${this.receivingWalletAddress} for ${req.path}`);

      return { valid: true };

    } catch (error) {
      console.error(`Payment verification error [${correlationId}]:`, error);
      return { valid: false, error: 'Verification failed' };
    }
  }
}