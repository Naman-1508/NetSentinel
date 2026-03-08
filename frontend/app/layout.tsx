import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NetSentinel — Real-Time Threat Detection",
  description:
    "NetSentinel: AI-powered real-time packet capture and ML threat detection. Monitor live network traffic with deep protocol analysis and intelligent anomaly detection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
