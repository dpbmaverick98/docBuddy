// Enhanced payment analytics for x402 service with persistent storage support

interface PaymentRecord {
  timestamp: number;
  endpoint: string;
  amount: number;
  client_address: string;
  success: boolean;
  correlationId?: string;
  error?: string;
  processingTimeMs?: number;
  protocol?: 'v1' | 'v2';
}

interface ServiceMetrics {
  endpoint: string;
  successCount: number;
  failureCount: number;
  totalAmount: number;
  averageProcessingTime: number;
  errorRates: Map<string, number>;
  protocolUsage: Map<'v1' | 'v2', number>;
}

class PaymentAnalytics {
  private payments: PaymentRecord[] = [];
  private maxRecords = 10000; // Increased from 1000
  private startTime = Date.now();
  private metrics: Map<string, ServiceMetrics> = new Map();

  recordPayment(
    endpoint: string, 
    amount: number, 
    client_address: string, 
    success: boolean = true,
    correlationId?: string,
    error?: string,
    processingTimeMs?: number,
    protocol?: 'v1' | 'v2'
  ) {
    const record: PaymentRecord = {
      timestamp: Date.now(),
      endpoint,
      amount,
      client_address,
      success,
      correlationId,
      error,
      processingTimeMs,
      protocol
    };

    this.payments.push(record);
    this.updateMetrics(record);

    // Keep only recent records
    if (this.payments.length > this.maxRecords) {
      this.payments = this.payments.slice(-this.maxRecords);
    }

    console.log(`📊 Payment recorded: ${endpoint} - $${(amount/100).toFixed(2)} - ${success ? '✅' : '❌'} - ${protocol || 'v1'}`);
  }

  private updateMetrics(record: PaymentRecord) {
    const key = record.endpoint;
    if (!this.metrics.has(key)) {
      this.metrics.set(key, {
        endpoint: key,
        successCount: 0,
        failureCount: 0,
        totalAmount: 0,
        averageProcessingTime: 0,
        errorRates: new Map(),
        protocolUsage: new Map()
      });
    }

    const metrics = this.metrics.get(key)!;
    
    if (record.success) {
      metrics.successCount++;
      metrics.totalAmount += record.amount;
    } else {
      metrics.failureCount++;
      if (record.error) {
        const errorType = this.categorizeError(record.error);
        metrics.errorRates.set(errorType, (metrics.errorRates.get(errorType) || 0) + 1);
      }
    }

    if (record.processingTimeMs) {
      // Update rolling average
      const totalRequests = metrics.successCount + metrics.failureCount;
      metrics.averageProcessingTime = 
        (metrics.averageProcessingTime * (totalRequests - 1) + record.processingTimeMs) / totalRequests;
    }

    if (record.protocol) {
      metrics.protocolUsage.set(record.protocol, (metrics.protocolUsage.get(record.protocol) || 0) + 1);
    }
  }

  private categorizeError(error: string): string {
    if (error.includes('signature') || error.includes('Invalid signature')) return 'SIGNATURE';
    if (error.includes('expired') || error.includes('timeout')) return 'EXPIRED';
    if (error.includes('amount') || error.includes('payment')) return 'PAYMENT';
    if (error.includes('upstream') || error.includes('Cohere') || error.includes('K2')) return 'UPSTREAM';
    if (error.includes('rate limit') || error.includes('throttle')) return 'RATE_LIMIT';
    return 'OTHER';
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
        stats[p.endpoint] = { count: 0, revenue: 0, errors: 0, avgProcessingTime: 0 };
      }
      stats[p.endpoint].count++;
      if (p.success) {
        stats[p.endpoint].revenue += p.amount;
      } else {
        stats[p.endpoint].errors++;
      }
      if (p.processingTimeMs) {
        stats[p.endpoint].avgProcessingTime = 
          (stats[p.endpoint].avgProcessingTime + p.processingTimeMs) / 2;
      }
      return stats;
    }, {} as Record<string, { count: number; revenue: number; errors: number; avgProcessingTime: number }>);

    // Protocol usage stats
    const protocolStats = recentPayments.reduce((stats, p) => {
      if (p.protocol) {
        stats[p.protocol] = (stats[p.protocol] || 0) + 1;
      }
      return stats;
    }, {} as Record<string, number>);

    // Error breakdown
    const errorBreakdown = recentPayments
      .filter(p => !p.success && p.error)
      .reduce((stats, p) => {
        const errorType = this.categorizeError(p.error!);
        stats[errorType] = (stats[errorType] || 0) + 1;
        return stats;
      }, {} as Record<string, number>);

    return {
      period: `${hours} hours`,
      uptime: this.getServiceUptime(),
      total_revenue: totalRevenue / 100, // Convert cents to dollars
      total_transactions: totalTransactions,
      successful_transactions: successfulTransactions,
      success_rate: totalTransactions > 0 ? (successfulTransactions / totalTransactions * 100).toFixed(1) + '%' : '0%',
      average_processing_time: recentPayments.reduce((sum, p) => sum + (p.processingTimeMs || 0), 0) / recentPayments.length,
      protocol_distribution: protocolStats,
      error_breakdown: errorBreakdown,
      endpoint_stats: Object.entries(endpointStats).map(([endpoint, stats]) => ({
        endpoint,
        transactions: stats.count,
        revenue: stats.revenue / 100,
        errors: stats.errors,
        success_rate: stats.count > 0 ? ((stats.count - stats.errors) / stats.count * 100).toFixed(1) + '%' : '0%',
        avg_processing_time: Math.round(stats.avgProcessingTime),
      })),
    };
  }

  getServiceUptime(): string {
    const uptimeMs = Date.now() - this.startTime;
    const hours = Math.floor(uptimeMs / (1000 * 60 * 60));
    const minutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  }

  getAllPayments(limit: number = 100) {
    return this.payments
      .slice(-limit)
      .reverse()
      .map(p => ({
        ...p,
        timestamp: new Date(p.timestamp).toISOString(),
        amount_dollars: (p.amount / 100).toFixed(2)
      }));
  }

  getEndpointMetrics(endpoint: string) {
    return this.metrics.get(endpoint);
  }

  getTopEndpoints(limit: number = 10) {
    return Array.from(this.metrics.values())
      .sort((a, b) => (b.successCount + b.failureCount) - (a.successCount + a.failureCount))
      .slice(0, limit);
  }

  getRecentErrors(limit: number = 50) {
    return this.payments
      .filter(p => !p.success && p.error)
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, limit)
      .map(p => ({
        timestamp: new Date(p.timestamp).toISOString(),
        endpoint: p.endpoint,
        client_address: p.client_address,
        error: p.error,
        correlationId: p.correlationId
      }));
  }

  // Export data for persistence
  exportData() {
    return {
      payments: this.payments,
      metrics: Array.from(this.metrics.entries()),
      startTime: this.startTime
    };
  }

  // Import data for persistence (for future database integration)
  importData(data: any) {
    if (data.payments) this.payments = data.payments;
    if (data.metrics) this.metrics = new Map(data.metrics);
    if (data.startTime) this.startTime = data.startTime;
  }
}

export const analytics = new PaymentAnalytics();
