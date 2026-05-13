import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "RecallBox",
  description: "Save, organize, and find links later.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
