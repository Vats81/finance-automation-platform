/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // The original AP-automation screens are not part of the product and their
  // API is not mounted; send anyone who finds the old URLs to the real app.
  async redirects() {
    const legacy = ["dashboard", "vendors", "payments", "invoices", "purchase-orders", "approvals", "audit"];
    return [
      { source: "/login", destination: "/app/login", permanent: false },
      ...legacy.flatMap((name) => [
        { source: `/${name}`, destination: "/app/dashboard", permanent: false },
        { source: `/${name}/:path*`, destination: "/app/dashboard", permanent: false },
      ]),
    ];
  },
};

module.exports = nextConfig;
