import type { Metadata } from "next";
import { Fraunces, Inter, Source_Serif_4 } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({ subsets: ["latin", "latin-ext"], variable: "--font-fraunces" });
const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-inter" });
const sourceSerif = Source_Serif_4({ subsets: ["latin", "latin-ext"], variable: "--font-source-serif" });

export const metadata: Metadata = {
  title: { default: "Móyee — Research with clarity", template: "%s · Móyee" },
  description:
    "Móyee is an evidence-grounded research workspace: discover sources, understand papers, synthesise literature and write with citations you can trust.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fraunces.variable} ${inter.variable} ${sourceSerif.variable}`}>
      <body className="min-h-dvh font-sans">{children}</body>
    </html>
  );
}
