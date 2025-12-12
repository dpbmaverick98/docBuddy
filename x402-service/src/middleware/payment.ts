import { Request, Response, NextFunction } from 'express';
import Web3 from 'web3';

interface PaymentPayload {
  network: string;
  scheme: string;
  amount: string;
  currency: string;
  timestamp: number;
  client_address: string;
  signature: string;
}

export class PaymentMiddleware {
  private w3: Web3;
  private facilitatorUrl: string;
  private network: string;

  constructor(facilitatorUrl: string, network: string) {
    this.w3 = new Web3();
    this.facilitatorUrl = facilitatorUrl;
    this.network = network;
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
        const verificationResult = await this.verifyPayment(paymentPayload);

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

  private async verifyPayment(payload: PaymentPayload): Promise<{ valid: boolean; error?: string }> {
    try {
      // For now, implement basic verification
      // In production, this would verify with facilitator
      const currentTime = Math.floor(Date.now() / 1000);
      const timeDiff = currentTime - payload.timestamp;

      // Check if payment is not too old (5 minutes max)
      if (Math.abs(timeDiff) > 300) {
        return { valid: false, error: 'Payment timestamp expired' };
      }

      // Verify signature
      const message = JSON.stringify({
        network: payload.network,
        scheme: payload.scheme,
        amount: payload.amount,
        currency: payload.currency,
        timestamp: payload.timestamp,
        client_address: payload.client_address,
      }, Object.keys(payload).sort());

      const signer = this.w3.eth.accounts.recover(message, payload.signature);

      if (signer.toLowerCase() !== payload.client_address.toLowerCase()) {
        return { valid: false, error: 'Invalid signature' };
      }

      // TODO: Verify with facilitator that payment was executed
      // For now, accept the signature as valid
      return { valid: true };

    } catch (error) {
      console.error('Payment verification error:', error);
      return { valid: false, error: 'Verification failed' };
    }
  }
}</contents>
</xai:function_call name="write">
<parameter name="file_path">/Users/dpbmaverick98/docsBuddy/docBuddy/x402-service/src/server.ts
