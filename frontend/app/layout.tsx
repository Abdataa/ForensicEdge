import "./globals.css";
import type { ReactNode } from "react";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      {/* Remove the gray background here so it doesn't flash during loading */}
      <body className="bg-[#0a0a0a] antialiased">
        {children}
      </body>
    </html>
  );
}