#!/usr/bin/env bun
// Test script for x402 ask endpoint using official x402 libs
// Reads PRIVATE_KEY and SERVER_URL from .env
// Automatically handles payment flow on BASE MAINNET

import { wrapFetchWithPayment } from 'x402-fetch';
import { privateKeyToAccount } from 'viem/accounts';
import 'dotenv/config';

async function testAskEndpoint() {
  console.log('🚀 Starting x402 Ask Endpoint test...');

  const privateKey = process.env.PRIVATE_KEY;
  const serverUrl = process.env.SERVER_URL;

  if (!privateKey || !serverUrl) {
    console.error('❌ Missing PRIVATE_KEY or SERVER_URL in .env');
    process.exit(1);
  }

  // 1. Set up wallet account
  const account = privateKeyToAccount(privateKey as `0x${string}`);

  // 2. Create wrapped fetch with automatic payment handling
  const fetchWithPayment = wrapFetchWithPayment(fetch, account);

  // 3. Prepare the ask request body
  const requestBody = {
    question: "what are the ways to enable gas sponsorship for my app",
    project: "privy",
    context: "i want to enable gas sponsorhsip but dont want to use 3rd party 4337 or paymaster providers to for and its too complex for me"
  };

  // 4. Make the request with automatic x402 payment handling
  console.log('📡 Making ask request with automatic x402 payment handling...');
  try {
    const response = await fetchWithPayment(`${serverUrl}/api/docsbuddy/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (response.ok) {
      console.log('✅ Request successful!');
      const data = await response.json();
      console.log('📦 Ask Response:', JSON.stringify(data, null, 2));
      // Check for settlement header
      const paymentResp = response.headers.get('PAYMENT-RESPONSE');
      if (paymentResp) {
        console.log('💸 Settlement:', JSON.parse(atob(paymentResp)));
      }
    } else {
      console.log(`❌ Request failed: ${response.status}`);
      const error = await response.text();
      console.log('Error:', error);
    }
  } catch (err) {
    console.error('❌ Error:', err.message);
  }
}

// Run the test
testAskEndpoint().catch(console.error);