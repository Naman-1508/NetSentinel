import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for Electron (generates frontend/out/)
  output: "export",

  // Required for Next.js static export + Electron file:// loading
  trailingSlash: true,

  // Disable image optimization (not available in static export)
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
