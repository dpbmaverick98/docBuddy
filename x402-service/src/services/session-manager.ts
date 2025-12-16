export interface WalletSession {
  walletAddress: string;
  createdAt: number;
  lastAccessed: number;
  expiresAt: number;
  totalSpent: number; // in cents
  requestCount: number;
  endpointAccess: Map<string, number>; // endpoint -> count
}

export interface SessionConfig {
  sessionTimeoutMs: number;        // How long session lasts (default: 1 hour)
  maxSessionValueCents: number;   // Max value per session (default: 1000 cents = $10)
  maxRequestsPerSession: number;   // Max requests per session (default: 100)
}

export class SessionManager {
  private sessions: Map<string, WalletSession> = new Map();
  private config: SessionConfig;

  constructor(config?: Partial<SessionConfig>) {
    this.config = {
      sessionTimeoutMs: 60 * 60 * 1000, // 1 hour
      maxSessionValueCents: 1000, // $10
      maxRequestsPerSession: 100,
      ...config
    };

    // Clean up expired sessions every 5 minutes
    setInterval(() => this.cleanupExpiredSessions(), 5 * 60 * 1000);
  }

  createOrUpdateSession(walletAddress: string, amountCents: number, endpoint: string): WalletSession {
    const now = Date.now();
    const address = walletAddress.toLowerCase();
    const existing = this.sessions.get(address);

    if (existing && existing.expiresAt > now) {
      // Update existing session
      existing.lastAccessed = now;
      existing.totalSpent += amountCents;
      existing.requestCount++;
      existing.endpointAccess.set(endpoint, (existing.endpointAccess.get(endpoint) || 0) + 1);
      
      console.log(`🔄 Updated session for ${address}: $${(existing.totalSpent / 100).toFixed(2)}, ${existing.requestCount} requests`);
      return existing;
    } else {
      // Create new session
      const session: WalletSession = {
        walletAddress: address,
        createdAt: now,
        lastAccessed: now,
        expiresAt: now + this.config.sessionTimeoutMs,
        totalSpent: amountCents,
        requestCount: 1,
        endpointAccess: new Map([[endpoint, 1]])
      };

      this.sessions.set(address, session);
      console.log(`✅ Created new session for ${address}: expires at ${new Date(session.expiresAt).toISOString()}`);
      return session;
    }
  }

  hasValidSession(walletAddress: string): boolean {
    const session = this.sessions.get(walletAddress.toLowerCase());
    if (!session) return false;
    
    return session.expiresAt > Date.now() && 
           session.totalSpent < this.config.maxSessionValueCents &&
           session.requestCount < this.config.maxRequestsPerSession;
  }

  getSession(walletAddress: string): WalletSession | null {
    const session = this.sessions.get(walletAddress.toLowerCase());
    if (!session || session.expiresAt <= Date.now()) {
      return null;
    }
    return session;
  }

  canAccessEndpoint(walletAddress: string, endpoint: string): { allowed: boolean; reason?: string } {
    const session = this.getSession(walletAddress);
    
    if (!session) {
      return { allowed: false, reason: 'No active session' };
    }

    if (session.expiresAt <= Date.now()) {
      return { allowed: false, reason: 'Session expired' };
    }

    if (session.totalSpent >= this.config.maxSessionValueCents) {
      return { allowed: false, reason: 'Session value limit reached' };
    }

    if (session.requestCount >= this.config.maxRequestsPerSession) {
      return { allowed: false, reason: 'Session request limit reached' };
    }

    return { allowed: true };
  }

  invalidateSession(walletAddress: string): void {
    const address = walletAddress.toLowerCase();
    this.sessions.delete(address);
    console.log(`🗑️ Invalidated session for ${address}`);
  }

  cleanupExpiredSessions(): void {
    const now = Date.now();
    let cleanedCount = 0;

    for (const [address, session] of this.sessions.entries()) {
      if (session.expiresAt <= now) {
        this.sessions.delete(address);
        cleanedCount++;
      }
    }

    if (cleanedCount > 0) {
      console.log(`🧹 Cleaned up ${cleanedCount} expired sessions. Active sessions: ${this.sessions.size}`);
    }
  }

  getStats() {
    const activeSessions = Array.from(this.sessions.values()).filter(
      session => session.expiresAt > Date.now()
    );

    const totalValueSpent = activeSessions.reduce((sum, session) => sum + session.totalSpent, 0);
    const totalRequests = activeSessions.reduce((sum, session) => sum + session.requestCount, 0);

    return {
      config: this.config,
      totalSessions: this.sessions.size,
      activeSessions: activeSessions.length,
      totalValueSpent,
      totalRequests,
      averageSessionValue: activeSessions.length > 0 ? totalValueSpent / activeSessions.length : 0,
      sessions: activeSessions.map(session => ({
        walletAddress: session.walletAddress,
        createdAt: session.createdAt,
        lastAccessed: session.lastAccessed,
        expiresAt: session.expiresAt,
        totalSpent: session.totalSpent,
        requestCount: session.requestCount,
        remainingValue: Math.max(0, this.config.maxSessionValueCents - session.totalSpent),
        remainingRequests: Math.max(0, this.config.maxRequestsPerSession - session.requestCount)
      }))
    };
  }

  extendSession(walletAddress: string, additionalMs?: number): boolean {
    const session = this.getSession(walletAddress);
    if (!session) return false;

    session.expiresAt += additionalMs || this.config.sessionTimeoutMs;
    console.log(`⏰ Extended session for ${walletAddress} to ${new Date(session.expiresAt).toISOString()}`);
    return true;
  }

  // For analytics - get recent sessions
  getRecentSessions(limit: number = 50): WalletSession[] {
    const allSessions = Array.from(this.sessions.values());
    return allSessions
      .sort((a, b) => b.lastAccessed - a.lastAccessed)
      .slice(0, limit);
  }
}