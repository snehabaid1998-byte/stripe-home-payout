/** @type {import('next').NextConfig} */
const nextConfig = {
  // Home reads the transactions and the message doc from the repo at runtime.
  outputFileTracingIncludes: {
    "/": ["./docs/**/*", "./data/**/*"],
    "/api/payout-state": ["./docs/**/*", "./data/**/*"],
  },
};
export default nextConfig;
