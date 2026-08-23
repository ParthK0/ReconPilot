import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReconPilot | AI Finance Reconciliation Controller",
  description: "Deterministic rules + Finance Verification Engine with measured accuracy and honest exception reporting",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-slate-950 text-slate-50 min-h-screen">
        {children}
      </body>
    </html>
  );
}
