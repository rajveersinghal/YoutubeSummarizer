// src/components/TestAuth.jsx

import { useAuth } from "@clerk/clerk-react";
import { useEffect } from "react";

const TestAuth = () => {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    const testToken = async () => {
      console.log('🔐 Testing authentication...');
      console.log('✅ Is signed in:', isSignedIn);
      
      if (isSignedIn) {
        try {
          const token = await getToken();
          console.log('✅ Token retrieved:', token ? 'YES' : 'NO');
          console.log('📝 Token preview:', token?.substring(0, 50) + '...');
        } catch (error) {
          console.error('❌ Error getting token:', error);
        }
      } else {
        console.warn('⚠️ User not signed in');
      }
    };

    testToken();
  }, [isSignedIn, getToken]);

  return null;
};

export default TestAuth;
