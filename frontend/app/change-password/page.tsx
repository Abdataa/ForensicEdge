/**
 * app/(protected)/change-password/page.tsx
 * Route: /change-password
 * Allows any authenticated user to update their password.
 * Particularly important for first login after admin creates the account.
 */
import Navbar             from "../../../components/layout/Navbar";
import ChangePasswordForm from "../../../components/auth/ChangePasswordForm";

export const metadata = { title: "Change Password — ForensicEdge" };

export default function ChangePasswordPage() {
  return (
    <>
      <Navbar title="Change Password" />
      <main className="page-body">
        <ChangePasswordForm />
      </main>
    </>
  );
}