import type { NextConfig } from 'next'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:9090'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/:path*`
      }
    ]
  }
}

export default nextConfig
