import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Docs Journey Builder",
  description: "Create step-by-step journeys through documentation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

