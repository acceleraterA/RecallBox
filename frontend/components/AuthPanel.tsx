"use client";

import { FormEvent, useState } from "react";

import { useAuth } from "@/lib/auth";

export function AuthPanel() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);

    try {
      if (mode === "signin") {
        await signIn(email, password);
      } else {
        const nextMessage = await signUp(email, password);
        setMessage(nextMessage ?? "Account created. You are signed in.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel auth-panel">
      <div>
        <p className="eyebrow">Account</p>
        <h2>{mode === "signin" ? "Sign in to RecallBox" : "Create your RecallBox account"}</h2>
        <p className="muted">Your saved links stay private to your account.</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Email</span>
          <input
            required
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            required
            type="password"
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            minLength={6}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {message ? <p className="success-text">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <div className="actions">
          <button className="primary-button" disabled={submitting} type="submit">
            {submitting ? "Working..." : mode === "signin" ? "Sign in" : "Create account"}
          </button>
          <button
            className="ghost-button"
            disabled={submitting}
            type="button"
            onClick={() => {
              setMode(mode === "signin" ? "signup" : "signin");
              setError(null);
              setMessage(null);
            }}
          >
            {mode === "signin" ? "Create account" : "Use existing account"}
          </button>
        </div>
      </form>
    </section>
  );
}

export function AccountBar() {
  const { isAuthEnabled, userEmail, signOut } = useAuth();

  if (!isAuthEnabled || !userEmail) {
    return null;
  }

  return (
    <div className="account-bar">
      <span>{userEmail}</span>
      <button className="ghost-button" type="button" onClick={signOut}>
        Sign out
      </button>
    </div>
  );
}
