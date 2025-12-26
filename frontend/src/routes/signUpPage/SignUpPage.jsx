// src/routes/signUpPage/SignUpPage.jsx - WITH BACKEND INTEGRATION

import { SignUp } from "@clerk/clerk-react";
import { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { toast } from "react-hot-toast";
import { ThemeContext } from "../../context/ThemeContext";
import { dark } from "@clerk/themes";
import { api } from "../../lib/api";
import "./signUpPage.css";

const SignUpPage = () => {
  const { theme } = useContext(ThemeContext);
  const { isSignedIn, isLoaded } = useAuth();
  const navigate = useNavigate();
  const hasClerk = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY);

  // ============================================================================
  // BACKEND INTEGRATION - Register new user after sign-up
  // ============================================================================

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      registerUserWithBackend();
    }
  }, [isSignedIn, isLoaded]);

  const registerUserWithBackend = async () => {
    try {
      // Register/verify user with backend
      const response = await api.auth.me();
      console.log("✅ User registered in backend:", response.data);

      // Show welcome message
      toast.success("Welcome to SpectraAI! 🎉", {
        duration: 4000,
        icon: "🚀",
      });

      // Redirect to dashboard
      setTimeout(() => {
        navigate("/dashboard");
      }, 1000);
    } catch (error) {
      console.error("❌ Failed to register user with backend:", error);

      // If backend is down, still allow sign-up
      if (error.code === "ERR_NETWORK") {
        toast.error("Backend is offline. Some features may not work.", {
          duration: 5000,
        });
        navigate("/dashboard");
      } else {
        toast.error("Registration error. Please try again.");
      }
    }
  };

  if (!hasClerk) {
    return (
      <div className="signUpPage">
        <div className="error-container">
          <h2>⚠️ Authentication Not Configured</h2>
          <p>Please add your Clerk Publishable Key to .env file:</p>
          <code>VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_KEY</code>
        </div>
      </div>
    );
  }

  return (
    <div className="signUpPage">
      <div className="signup-container">
        {/* Branding Header */}
        <div className="signup-header">
          <img src="/logo.png" alt="SpectraAI" className="signup-logo" />
          <h1>Join SpectraAI</h1>
          <p>Create your account and unlock AI-powered productivity</p>
        </div>

        {/* Clerk Sign-Up Component */}
        <SignUp
          path="/sign-up"
          routing="path"
          signInUrl="/sign-in"
          afterSignUpUrl="/dashboard"
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


        {/* Social Proof */}
        <div className="signup-footer">
          <p className="footer-text">
            ✨ Join thousands of users already using SpectraAI
          </p>
        </div>
      </div>
    </div>
  );
};

export default SignUpPage;
