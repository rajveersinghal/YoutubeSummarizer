// src/context/ThemeContext.jsx - FIXED BACKEND INTEGRATION

import React, { createContext, useState, useEffect, useContext } from "react";
import { useAuth } from "@clerk/clerk-react";
import { api } from "../lib/api";

export const ThemeContext = createContext();

// Custom hook for easier usage
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  const { isSignedIn, isLoaded } = useAuth();
  
  // Initialize state from localStorage or default to 'light'
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem("theme");
    return savedTheme || "light";
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // ============================================================================
  // APPLY THEME TO DOM
  // ============================================================================

  useEffect(() => {
    const root = document.documentElement;
    
    // Method 1: Using data-theme attribute (recommended)
    root.setAttribute("data-theme", theme);
    
    // Method 2: Using class (if you prefer)
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }

    // Save to localStorage
    localStorage.setItem("theme", theme);
  }, [theme]);

  // ============================================================================
  // BACKEND INTEGRATION - Load user's saved theme
  // ============================================================================

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      loadUserTheme();
    }
  }, [isLoaded, isSignedIn]);

  const loadUserTheme = async () => {
    setIsLoading(true);
    try {
      const response = await api.auth.me();
      
      console.log('📥 User theme response:', response);
      
      // ✅ FIX: Handle different response structures
      const userTheme = 
        response?.preferences?.theme || 
        response?.user?.preferences?.theme ||
        response?.theme ||
        null;
      
      if (userTheme && (userTheme === "light" || userTheme === "dark")) {
        // Only update if different from current theme
        if (userTheme !== theme) {
          console.log(`✅ Loaded user theme: ${userTheme}`);
          setTheme(userTheme);
        }
      } else {
        console.log('ℹ️ No user theme preference found, using localStorage');
      }
    } catch (error) {
      console.warn("⚠️ Failed to load user theme:", error.message);
      // Silently fail - use localStorage theme
    } finally {
      setIsLoading(false);
    }
  };

  // ============================================================================
  // TOGGLE THEME WITH BACKEND SYNC
  // ============================================================================

  const toggleTheme = async () => {
    const newTheme = theme === "light" ? "dark" : "light";
    
    // Update immediately for better UX
    setTheme(newTheme);

    // Sync to backend if user is signed in
    if (isSignedIn && !isSyncing) {
      setIsSyncing(true);
      try {
        const response = await api.auth.updatePreferences({ theme: newTheme });
        
        if (response?.success !== false) {
          console.log(`✅ Theme synced to backend: ${newTheme}`);
        } else {
          console.warn('⚠️ Theme sync response unsuccessful (endpoint may not exist)');
        }
      } catch (error) {
        console.warn("⚠️ Failed to sync theme to backend:", error.message);
        // Don't revert theme - localStorage is enough
      } finally {
        setIsSyncing(false);
      }
    }
  };

  // ============================================================================
  // MANUAL THEME SET (with backend sync)
  // ============================================================================

  const setThemeManually = async (newTheme) => {
    if (newTheme !== "light" && newTheme !== "dark") {
      console.error("Invalid theme. Use 'light' or 'dark'");
      return;
    }

    setTheme(newTheme);

    // Sync to backend
    if (isSignedIn && !isSyncing) {
      setIsSyncing(true);
      try {
        const response = await api.auth.updatePreferences({ theme: newTheme });
        
        if (response?.success !== false) {
          console.log(`✅ Theme synced to backend: ${newTheme}`);
        }
      } catch (error) {
        console.warn("⚠️ Failed to sync theme:", error.message);
      } finally {
        setIsSyncing(false);
      }
    }
  };

  return (
    <ThemeContext.Provider 
      value={{ 
        theme, 
        toggleTheme, 
        setTheme: setThemeManually,
        isLoading, 
        isSyncing 
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};
