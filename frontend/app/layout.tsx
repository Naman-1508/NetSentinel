import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PacketCapture — Real-Time Network Monitor",
  description:
    "Wireshark-inspired real-time packet capture and analysis tool. Monitor live network traffic with protocol-level breakdown.",
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
