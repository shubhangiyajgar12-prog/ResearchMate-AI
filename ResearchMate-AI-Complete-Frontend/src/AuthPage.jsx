import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail, UserRound, Sparkles } from "lucide-react";

const CONFIGURED_API = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const TOKEN_KEY = "researchmate:accessToken";
const USER_KEY = "researchmate:user";

function getApiCandidates() {
  const candidates = [];
  if (CONFIGURED_API) candidates.push(CONFIGURED_API);
  candidates.push("http://127.0.0.1:8001", "http://127.0.0.1:8000", "http://localhost:8001", "http://localhost:8000");
  return [...new Set(candidates)];
}

const getErrorMessage = (data, fallback) => {
  if (typeof data?.detail === "string") return data.detail;
  if (typeof data?.message === "string") return data.message;
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item?.msg).filter(Boolean).join(" ") || fallback;
  return fallback;
};

async function authRequest(path, payload) {
  let lastError = null;
  for (const base of getApiCandidates()) {
    try {
      const response = await fetch(`${base}/auth/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const type = response.headers.get("content-type") || "";
      const data = type.includes("application/json") ? await response.json() : {};

      // A 404 from an old backend instance means the auth router is not mounted
      // there. Try the next local backend candidate instead of showing "Not Found".
      if (response.status === 404 && data?.detail === "Not Found") {
        lastError = new Error("Authentication route was not found on this backend instance.");
        continue;
      }

      return { response, data, base };
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("ResearchMate AI backend is not reachable.");
}

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const isSignup = location.pathname === "/signup";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [keepSignedIn, setKeepSignedIn] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (isSignup && name.trim().length < 2) return setError("Please enter your full name.");
    if (!email.trim()) return setError("Please enter your email address.");
    if (password.length < (isSignup ? 8 : 1)) {
      return setError(isSignup ? "Password must be at least 8 characters." : "Please enter your password.");
    }

    setLoading(true);
    try {
      const { response, data } = await authRequest(
        isSignup ? "signup" : "login",
        isSignup ? { name: name.trim(), email: email.trim(), password } : { email: email.trim(), password }
      );

      if (!response.ok) {
        throw new Error(getErrorMessage(data, isSignup ? "Could not create your account." : "Could not sign you in."));
      }

      const storage = keepSignedIn ? window.localStorage : window.sessionStorage;
      storage.setItem(TOKEN_KEY, data.access_token);
      storage.setItem(USER_KEY, JSON.stringify(data.user || {}));
      const otherStorage = keepSignedIn ? window.sessionStorage : window.localStorage;
      otherStorage.removeItem(TOKEN_KEY);
      otherStorage.removeItem(USER_KEY);

      if (isSignup) {
        setSuccess(
          data.notification_sent
            ? "Account created. A welcome notification has been sent to your email. Opening your workspace…"
            : "Account created. Opening your workspace…"
        );
      } else {
        setSuccess("Welcome back. Opening your workspace…");
      }

      window.setTimeout(() => navigate("/", { replace: true }), 400);
    } catch (err) {
      setError(err.message || "Authentication failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-glow auth-glow-one" />
      <div className="auth-glow auth-glow-two" />
      <section className="auth-brand-panel">
        <div className="auth-brand"><div className="auth-logo"><Sparkles size={22} /></div><div><strong>ResearchMate AI</strong><span>Research → Writing → Publication</span></div></div>
        <div className="auth-brand-content">
          <span className="auth-eyebrow">AI-POWERED RESEARCH WORKSPACE</span>
          <h1>Turn your research idea into a <em>stronger paper.</em></h1>
          <p>Keep your projects, literature, manuscript work and publication workflow together in one focused workspace.</p>
          <div className="auth-feature-list"><div><span>01</span><p>Discover and validate research directions</p></div><div><span>02</span><p>Find and organize academic literature</p></div><div><span>03</span><p>Write, review and prepare for publication</p></div></div>
        </div>
        <div className="auth-brand-footer">Built for focused academic research.</div>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form-card">
          <div className="auth-mobile-brand"><div className="auth-logo"><Sparkles size={20} /></div><strong>ResearchMate AI</strong></div>
          <div className="auth-heading"><span>{isSignup ? "CREATE YOUR WORKSPACE" : "WELCOME BACK"}</span><h2>{isSignup ? "Create your account" : "Sign in to ResearchMate"}</h2><p>{isSignup ? "Start your research workspace in a few seconds." : "Continue where you left off in your research journey."}</p></div>
          <form onSubmit={submit} className="auth-form">
            {isSignup && <label className="auth-field"><span>Full name</span><div className="auth-input-wrap"><UserRound size={17} /><input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your full name" autoComplete="name" /></div></label>}
            <label className="auth-field"><span>Email address</span><div className="auth-input-wrap"><Mail size={17} /><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" /></div></label>
            <label className="auth-field"><span>Password</span><div className="auth-input-wrap"><LockKeyhole size={17} /><input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={isSignup ? "At least 8 characters" : "Enter your password"} autoComplete={isSignup ? "new-password" : "current-password"} /><button type="button" className="auth-eye" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>
            <div className="auth-options"><label className="auth-check"><input type="checkbox" checked={keepSignedIn} onChange={(e) => setKeepSignedIn(e.target.checked)} /><span>Keep me signed in</span></label>{!isSignup && <span className="auth-secure-note">Secure workspace</span>}</div>
            {error && <div className="auth-message auth-error">{error}</div>}
            {success && <div className="auth-message auth-success">{success}</div>}
            <button className="auth-submit" type="submit" disabled={loading}>{loading ? "Creating workspace…" : isSignup ? "Create account" : "Sign in"}{!loading && <ArrowRight size={17} />}</button>
          </form>
          <div className="auth-switch">{isSignup ? "Already have an account?" : "New to ResearchMate AI?"}{" "}<Link to={isSignup ? "/login" : "/signup"}>{isSignup ? "Sign in" : "Create an account"}</Link></div>
        </div>
      </section>
    </div>
  );
}
