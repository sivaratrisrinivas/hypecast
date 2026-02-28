import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "HypeCast",
  description: "Real-time AI sports commentary",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
