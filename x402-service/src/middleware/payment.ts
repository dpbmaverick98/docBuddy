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
      try {
        const paymentHeader = req.headers['x402-payment'] as string;

        if (!paymentHeader) {
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
        if (!this.isValidPaymentPayload(paymentPayload)) {
          return res.status(400).json({ error: 'Invalid payment payload' });
        }

        // Verify payment with facilitator
        const verificationResult = await this.verifyPayment(paymentPayload, req);

        if (!verificationResult.valid) {
          return res.status(402).json({
            error: 'Payment verification failed',
            details: verificationResult.error
          });
        }

        // Payment verified, proceed
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
    try {
      // Check timestamp validity (5 minutes window)
      const currentTime = Math.floor(Date.now() / 1000);
      const timeDiff = Math.abs(currentTime - payload.timestamp);

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

      // Create the exact message that was signed
      const message = JSON.stringify({
        network: payload.network,
        scheme: payload.scheme,
        amount: payload.amount,
        currency: payload.currency,
        timestamp: payload.timestamp,
        client_address: payload.client_address,
      }, Object.keys(payload).sort());

      // Verify signature
      const signer = this.w3.eth.accounts.recover(message, payload.signature);

      if (signer.toLowerCase() !== payload.client_address.toLowerCase()) {
        return { valid: false, error: 'Invalid signature' };
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
