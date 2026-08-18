import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  allowedDevOrigins: ["192.168.0.200", "localhost", "127.0.0.1"]
};

export default nextConfig;
