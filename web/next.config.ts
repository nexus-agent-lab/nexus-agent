import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {
    serverActions: {
      allowedOrigins: ["localhost:8000", "127.0.0.1:8000"],
    },
  },
};

export default nextConfig;
