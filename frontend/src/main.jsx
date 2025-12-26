import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import { Toaster } from "react-hot-toast";
import { ThemeProvider } from "./context/ThemeContext";

// Layouts
import RootLayout from "./layouts/rootLayout/RootLayout";
import DashboardLayout from "./layouts/dashboardLayout/DashboardLayout";

// Pages
import Homepage from "./routes/homepage/Homepage";
import DashboardPage from "./routes/dashboardPage/DashboardPage";
import ChatPage from "./routes/chatPage/ChatPage";
import SignInPage from "./routes/signInPage/SignInPage";
import SignUpPage from "./routes/signUpPage/SignUpPage";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing Publishable Key");
}

const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      // Public routes
      { 
        path: "/", 
        element: <Homepage /> 
      },
      { 
        path: "/sign-in/*", 
        element: <SignInPage /> 
      },
      { 
        path: "/sign-up/*", 
        element: <SignUpPage /> 
      },
      
      // Protected routes (Dashboard)
      {
        element: <DashboardLayout />,
        children: [
          { 
            path: "/dashboard", 
            element: <DashboardPage /> 
          },
          { 
            path: "/dashboard/chats/:id", 
            element: <ChatPage /> 
          },
        ],
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {/* ✅ UPDATED: Added afterSignInUrl and afterSignUpUrl */}
    <ClerkProvider 
      publishableKey={PUBLISHABLE_KEY}
      afterSignInUrl="/dashboard"
      afterSignUpUrl="/dashboard"
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
    >
      <ThemeProvider>
        <RouterProvider router={router} />
        <Toaster 
          position="top-center"
          toastOptions={{
            duration: 3000,
            style: {
              background: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
            },
            success: {
              iconTheme: {
                primary: 'var(--color-success)',
                secondary: 'white',
              },
            },
            error: {
              iconTheme: {
                primary: 'var(--color-error)',
                secondary: 'white',
              },
            },
          }}
        />
      </ThemeProvider>
    </ClerkProvider>
  </React.StrictMode>
);
