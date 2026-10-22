import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 16 rejects dev asset requests that do not come from localhost, which
  // leaves the app unhydrated (and every client-side fetch dead) when it is
  // opened through 127.0.0.1.
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;
