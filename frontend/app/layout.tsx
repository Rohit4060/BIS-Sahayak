import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BIS Sahayak AI — Indian Standards & Compliance Copilot",
  description:
    "Find applicable Indian Standards, certification guidance, testing requirements and recognised laboratories — all in one place.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
