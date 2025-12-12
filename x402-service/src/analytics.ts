// Simple payment analytics for x402 service

interface PaymentRecord {
  timestamp: number;
  endpoint: string;
  amount: number;
  client_address: string;
  success: boolean;
}

class PaymentAnalytics {
  private payments: PaymentRecord[] = [];
  private maxRecords = 1000; // Keep last 1000 payments

  recordPayment(endpoint: string, amount: number, client_address: string, success: boolean = true) {
    const record: PaymentRecord = {
      timestamp: Date.now(),
      endpoint,
      amount,
      client_address,
      success,
    };

    this.payments.push(record);

    // Keep only recent records
    if (this.payments.length > this.maxRecords) {
      this.payments = this.payments.slice(-this.maxRecords);
    }

    console.log(`📊 Payment recorded: ${endpoint} - $${amount/100} - ${success ? '✅' : '❌'}`);
  }

  getAnalytics(hours: number = 24) {
    const cutoffTime = Date.now() - (hours * 60 * 60 * 1000);
    const recentPayments = this.payments.filter(p => p.timestamp > cutoffTime);

    const totalRevenue = recentPayments
      .filter(p => p.success)
      .reduce((sum, p) => sum + p.amount, 0);

    const totalTransactions = recentPayments.length;
    const successfulTransactions = recentPayments.filter(p => p.success).length;

    const endpointStats = recentPayments.reduce((stats, p) => {
      if (!stats[p.endpoint]) {
        stats[p.endpoint] = { count: 0, revenue: 0 };
      }
      stats[p.endpoint].count++;
      if (p.success) {
        stats[p.endpoint].revenue += p.amount;
      }
      return stats;
    }, {} as Record<string, { count: number; revenue: number }>);

    return {
      period: `${hours} hours`,
      total_revenue: totalRevenue / 100, // Convert cents to dollars
      total_transactions: totalTransactions,
      successful_transactions: successfulTransactions,
      success_rate: totalTransactions > 0 ? (successfulTransactions / totalTransactions * 100).toFixed(1) + '%' : '0%',
      endpoint_stats: Object.entries(endpointStats).map(([endpoint, stats]) => ({
        endpoint,
        transactions: stats.count,
        revenue: stats.revenue / 100,
      })),
    };
  }

  getAllPayments(limit: number = 100) {
    return this.payments.slice(-limit).reverse();
  }
}

export const analytics = new PaymentAnalytics();
