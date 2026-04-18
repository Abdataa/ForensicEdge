/**
 * src/components/ui/Input.tsx
 * ────────────────────────────
 * Reusable text input used in all forms across the dashboard.
 *
 * Features
 * ─────────
 *   label    — floats above the field with a consistent style
 *   error    — red message shown below the field on validation failure
 *   suffix   — right-side element (e.g. show/hide password eye icon)
 *   disabled — muted appearance, cursor-not-allowed
 *
 * Extends <input> completely — all native HTML input props are forwarded,
 * including type, value, onChange, placeholder, required, minLength, etc.
 *
 * Uses forwardRef so parent components (e.g. a focus manager or a
 * third-party form library) can hold a ref to the underlying <input>.
 *
 * Usage examples
 * ───────────────
 *   // Email field with label
 *   <Input
 *     label="Email address"
 *     type="email"
 *     value={email}
 *     onChange={(e) => setEmail(e.target.value)}
 *     placeholder="you@forensicedge.et"
 *     required
 *   />
 *
 *   // Password with show/hide toggle
 *   <Input
 *     label="Password"
 *     type={showPassword ? "text" : "password"}
 *     value={password}
 *     onChange={(e) => setPassword(e.target.value)}
 *     error={errors.password}
 *     suffix={
 *       <button type="button" onClick={() => setShowPassword(!showPassword)}
 *               className="text-gray-500 hover:text-white transition-colors">
 *         {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
 *       </button>
 *     }
 *   />
 *
 *   // Disabled during submission
 *   <Input label="Full name" value={name} disabled={submitting} />
 *
 *   // With validation error
 *   <Input
 *     label="New password"
 *     type="password"
 *     error="Password must contain at least one uppercase letter."
 *   />
 *
 *   // Select (for role dropdown in admin form)
 *   Use a plain <select className="field"> directly — Input wraps <input>
 *   only, not <select>. The .field class is defined in globals.css.
 */

import { InputHTMLAttributes, ReactNode, forwardRef } from "react";
import clsx from "clsx";

// ── Props ────────────────────────────────────────────────────────────────────

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Label text rendered above the field */
  label?: string;

  /**
   * Validation error message rendered in red below the field.
   * When truthy, the input border also turns red.
   */
  error?: string;

  /**
   * Node rendered inside the right side of the input box.
   * Typically an icon-button for password visibility toggle.
   * The input gets `pr-10` padding-right automatically to avoid
   * text overlapping the suffix.
   */
  suffix?: ReactNode;
}

// ── Component ─────────────────────────────────────────────────────────────────

const Input = forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, error, suffix, className, id, ...rest }, ref) {
    // If no id is passed, derive one from the label so <label htmlFor> works
    const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="flex flex-col gap-1.5">

        {/* Label */}
        {label && (
          <label
            htmlFor={inputId}
            className="field-label"
          >
            {label}
          </label>
        )}

        {/* Input wrapper — needed for suffix positioning */}
        <div className="relative">
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              "field",
              // Red border when there is a validation error
              error && "border-red-600 focus:ring-red-500",
              // Extra right padding when a suffix is present
              suffix && "pr-10",
              className,
            )}
            {...rest}
          />

          {/* Suffix — positioned absolutely inside the input box */}
          {suffix && (
            <span
              className={clsx(
                "absolute right-3 top-1/2 -translate-y-1/2",
                "flex items-center",
                // Let pointer events pass through to the suffix's own handler
                "pointer-events-none [&>*]:pointer-events-auto",
              )}
            >
              {suffix}
            </span>
          )}
        </div>

        {/* Error message */}
        {error && (
          <p
            role="alert"
            className="text-red-400 text-xs leading-tight"
          >
            {error}
          </p>
        )}

      </div>
    );
  }
);

Input.displayName = "Input";
export default Input;