/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
  // Increase timeout for API routes (proxy to backend)
  api: {
    responseLimit: false,
    bodyParser: {
      sizeLimit: '1mb',
    },
  },
  // Increase timeout for server-side operations
  experimental: {
    serverActions: {
      bodySizeLimit: '1mb',
    },
  },
};

module.exports = nextConfig;

