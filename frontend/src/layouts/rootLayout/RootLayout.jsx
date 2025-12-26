// src/layouts/rootLayout/RootLayout.jsx - FIXED & CLEANED

import { useState, useEffect } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { SignedIn, UserButton, useAuth } from "@clerk/clerk-react";
import { AnimatePresence } from "framer-motion";
import { toast } from "react-hot-toast";
import ThemeToggle from "../../components/ThemeToggle/ThemeToggle";
import PageTransition from "../../components/PageTransition/PageTransition";
import { api, checkHealth } from "../../lib/api";
import "./rootLayout.css";

const RootLayout = () => {
  const hasClerk = Boolean(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY);
  const location = useLocation();
  const navigate = useNavigate();
  const { isSignedIn, getToken } = useAuth();

  // ============================================================================
  // STATE
  // ============================================================================
  
  const [apiStatus, setApiStatus] = useState("checking"); // checking, healthy, unhealthy
  const [userStats, setUserStats] = useState(null);
  const [notifications, setNotifications] = useState([]);

  // ============================================================================
  // CHECK API HEALTH (Silent)
  // ============================================================================
  
  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const healthData = await checkHealth();
        
        // Check if API returned healthy status
        const isHealthy = healthData?.status === "healthy" || healthData?.status === "degraded";
        setApiStatus(isHealthy ? "healthy" : "unhealthy");
        
        console.log("🔍 API Health:", healthData);
      } catch (error) {
        console.error("❌ Health check failed:", error);
        setApiStatus("unhealthy");
      }
    };

    checkApiHealth();

    // Check health every 30 seconds
    const interval = setInterval(checkApiHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // ============================================================================
  // SYNC USER WITH BACKEND
  // ============================================================================
  
  useEffect(() => {
    if (!isSignedIn) return;

    const syncUser = async () => {
      try {
        const token = await getToken();
        if (!token) {
          console.warn("⚠️ No token available");
          return;
        }

        // Get user info from backend
        const response = await api.auth.getMe();
        console.log("✅ User synced with backend:", response);
      } catch (error) {
        console.error("❌ Failed to sync user:", error);
        
        // Only show error if it's auth-related
        if (error.response?.status === 401) {
          toast.error("Session expired. Please sign in again.");
          navigate("/sign-in");
        }
      }
    };

    syncUser();
  }, [isSignedIn, getToken, navigate]);

  // ============================================================================
  // LOAD USER STATS (Optional)
  // ============================================================================
  
  useEffect(() => {
    if (!isSignedIn || apiStatus !== "healthy") return;

    const loadUserStats = async () => {
      try {
        // Get stats from backend
        const statsData = await api.health.getStats();
        
        if (statsData) {
          setUserStats(statsData);
          console.log("📊 User stats loaded:", statsData);
        }
      } catch (error) {
        console.warn("⚠️ Failed to load user stats:", error.message);
        // Silent fail - stats not critical
      }
    };

    loadUserStats();

    // Refresh stats every minute
    const interval = setInterval(loadUserStats, 60000);
    return () => clearInterval(interval);
  }, [isSignedIn, apiStatus]);

  // ============================================================================
  // LOAD RECENT ACTIVITY (Optional)
  // ============================================================================
  
  useEffect(() => {
    if (!isSignedIn || apiStatus !== "healthy") return;

    const loadRecentActivity = async () => {
      try {
        // Get recent history/activities
        const response = await api.history.getAll(1, 5); // Last 5 activities
        
        console.log('📥 Activity response:', response);
        
        // ✅ FIX: Handle response properly
        const activities = response?.activities || [];
        
        // Convert to notifications
        const notifs = activities.map((activity, index) => ({
          id: activity.activity_id || `notif-${index}`,
          type: activity.activity_type || "general",
          message: activity.message || `${activity.action || "Activity"}`,
          timestamp: activity.timestamp || Date.now(),
        }));
        
        setNotifications(notifs);
        console.log("📬 Notifications loaded:", notifs.length);
      } catch (error) {
        console.warn("⚠️ Failed to load activity (endpoint may not exist):", error.message);
        setNotifications([]);
      }
    };

    loadRecentActivity();
  }, [isSignedIn, apiStatus, location.pathname]);

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  const refreshStats = async () => {
    try {
      const statsData = await api.health.getStats();
      if (statsData) {
        setUserStats(statsData);
        toast.success("Stats refreshed");
      }
    } catch (error) {
      console.error("❌ Failed to refresh stats:", error);
      toast.error("Failed to refresh stats");
    }
  };

  const refreshNotifications = async () => {
    try {
      const response = await api.history.getAll(1, 5);
      
      // ✅ FIX: Handle response properly
      const activities = response?.activities || [];
      
      const notifs = activities.map((activity, index) => ({
        id: activity.activity_id || `notif-${index}`,
        type: activity.activity_type || "general",
        message: activity.message || `${activity.action || "Activity"}`,
        timestamp: activity.timestamp || Date.now(),
      }));
      
      setNotifications(notifs);
      toast.success("Notifications refreshed");
    } catch (error) {
      console.warn("⚠️ Failed to refresh notifications:", error.message);
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="rootLayout">
      <header>
        <Link to="/" className="logo">
          <img src="/logo.png" alt="logo" />
          <span>spECTRA</span>
        </Link>

        <div className="headerActions">
          {/* API Status Indicator (Hidden by default, shows on hover) */}
          <div 
            className={`api-status ${apiStatus}`} 
            title={`API Status: ${apiStatus}`}
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 
                apiStatus === 'healthy' ? '#10b981' : 
                apiStatus === 'checking' ? '#f59e0b' : 
                '#ef4444',
              marginRight: '1rem',
              opacity: 0.7,
              transition: 'all 0.3s ease',
            }}
          />

          <ThemeToggle />
          
          {hasClerk ? (
            <SignedIn>
              <UserButton 
                afterSignOutUrl="/"
                appearance={{
                  elements: {
                    avatarBox: "w-10 h-10"
                  }
                }}
              />
            </SignedIn>
          ) : null}
        </div>
      </header>

      <main>
        <AnimatePresence mode="wait">
          <PageTransition key={location.pathname}>
            <Outlet context={{ 
              apiStatus, 
              userStats, 
              notifications,
              refreshStats,
              refreshNotifications,
            }} />
          </PageTransition>
        </AnimatePresence>
      </main>
    </div>
  );
};

export default RootLayout;
