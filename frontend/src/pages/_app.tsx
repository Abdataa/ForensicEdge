/**
 * src/pages/_app.tsx
 * ────────────────────
 * Next.js Pages Router custom App component.
 * Wraps every page with global providers and styles.
 *
 * Responsibilities
 * ─────────────────
 *   1. Import global CSS (Tailwind base + component classes)
 *   2. Wrap the entire tree with <AuthProvider> so every page
 *      and component can call useAuth()
 *   3. Mount <Toaster> once so toast notifications work everywhere
 *      without each page having to include it
 *
 * Why AuthProvider lives here
 * ────────────────────────────
 * AuthProvider holds the session state (user, isLoading) and runs
 * the session-restore effect on mount.  Placing it here means it
 * runs exactly once when the app loads, not once per page navigation.
 * If it were inside each page component, navigating between pages
 * would re-trigger the restore effect and briefly flash a spinner.
 *
 * Toast configuration
 * ────────────────────
 * Dark theme matches the app's gray-900 cards.
 * Position "top-right" is standard for non-blocking notifications.
 * Success uses green, error uses red — matching the Badge colours.
 */

import type { AppProps } from "next/app";
import { Toaster }       from "react-hot-toast";
import { AuthProvider }  from "../context/AuthContext";
import "../styles/globals.css";


export default function App({ Component, pageProps }: AppProps) {
  return (
    <AuthProvider>

      {/* Page component — receives pageProps from getServerSideProps etc. */}
      <Component {...pageProps} />

      {/* Global toast notification container */}
      <Toaster
        position="top-right"
        gutter={8}
        toastOptions={{
          // Default duration for all toasts
          duration: 4000,

          // Base style — dark to match the dashboard theme
          style: {
            background:   "#1f2937",   // gray-800
            color:        "#f9fafb",   // gray-50
            border:       "1px solid #374151",  // gray-700
            borderRadius: "0.75rem",   // rounded-xl
            fontSize:     "14px",
            padding:      "12px 16px",
          },

          // Success — green icon
          success: {
            iconTheme: {
              primary:   "#22c55e",   // green-500
              secondary: "#1f2937",   // gray-800
            },
          },

          // Error — red icon
          error: {
            duration: 5000,   // errors stay a bit longer
            iconTheme: {
              primary:   "#ef4444",   // red-500
              secondary: "#1f2937",
            },
          },
        }}
      />

    </AuthProvider>
  );
}