import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white antialiased">
        {/* This 'children' will be:
            1. The Login page (if you are on /login)
            2. The DashboardLayout (if you are on /dashboard)
        */}
        {children}
      </body>
    </html>
  );
}