// src/routes/signInPage/SignInPage.jsx - WITH BACKEND SYNC

import { SignIn } from "@clerk/clerk-react";
import { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { toast } from "react-hot-toast";
import { ThemeContext } from "../../context/ThemeContext";
import { dark } from "@clerk/themes";
import { api } from "../../lib/api";
import "./signInPage.css";

const SignInPage = () => {
  const { theme } = useContext(ThemeContext);
  const { isSignedIn, isLoaded } = useAuth();
  const navigate = useNavigate();
  const hasClerk = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY);

  // ============================================================================
  // BACKEND INTEGRATION - Sync user after sign-in
  // ============================================================================

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      syncUserWithBackend();
    }
  }, [isSignedIn, isLoaded]);

  const syncUserWithBackend = async () => {
    try {
      // Verify user with backend
      const response = await api.auth.me();
      console.log("✅ User synced with backend:", response.data);

      // Show welcome message
      toast.success("Welcome back! 👋", {
        duration: 3000,
        icon: "🎉",
      });

      // Redirect to dashboard
      setTimeout(() => {
        navigate("/dashboard");
      }, 500);
    } catch (error) {
      console.error("❌ Failed to sync user with backend:", error);

      // If backend is down, still allow sign-in
      if (error.code === "ERR_NETWORK") {
        toast.error("Backend is offline. Some features may not work.", {
          duration: 5000,
        });
        navigate("/dashboard");
      } else {
        toast.error("Authentication error. Please try again.");
      }
    }
  };

  if (!hasClerk) {
    return (
      <div className="signInPage">
        <div className="error-container">
          <h2>⚠️ Authentication Not Configured</h2>
          <p>Please add your Clerk Publishable Key to .env file:</p>
          <code>VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY</code>
        </div>
      </div>
    );
  }

  return (
    <div className="signInPage">
      <div className="signin-container">
        {/* Optional: Add branding/logo */}
        <div className="signin-header">
          <img src="/logo.png" alt="SpectraAI" className="signin-logo" />
          <h1>Welcome to SpectraAI</h1>
          <p>Sign in to access your AI-powered workspace</p>
        </div>

        <SignIn
          path="/sign-in"
          routing="path"
          signUpUrl="/sign-up"
          afterSignInUrl="/dashboard"
          appearance={{
            baseTheme: theme === "dark" ? dark : undefined,
            elements: {
              rootBox: "mx-auto",
              card: "shadow-xl",
            },
            variables: {
              colorPrimary: "#667eea",
              colorBackground: theme === "dark" ? "#1a1a1a" : "#ffffff",
              colorText: theme === "dark" ? "#ffffff" : "#000000",
            },
          }}
        />

      </div>
    </div>
  );
};

export default SignInPage;
