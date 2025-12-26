# clerk_auth.py - Clerk Authentication Helper

import streamlit as st
import requests
import jwt
from typing import Optional, Dict
from datetime import datetime, timedelta

class ClerkAuth:
    """Clerk authentication helper for Streamlit"""
    
    def __init__(self):
        self.publishable_key = st.secrets["clerk"]["publishable_key"]
        self.secret_key = st.secrets["clerk"]["secret_key"]
        self.frontend_api = st.secrets["clerk"]["frontend_api"]
        
        # Session state initialization
        if 'clerk_user' not in st.session_state:
            st.session_state.clerk_user = None
        if 'clerk_token' not in st.session_state:
            st.session_state.clerk_token = None
    
    def get_jwks_url(self) -> str:
        """Get JWKS URL for token verification"""
        return f"{self.frontend_api}/.well-known/jwks.json"
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify Clerk JWT token"""
        try:
            # Get JWKS for verification
            jwks_url = self.get_jwks_url()
            jwks_client = jwt.PyJWKClient(jwks_url)
            
            # Get signing key
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            # Verify and decode token
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_exp": True}
            )
            
            return decoded
            
        except Exception as e:
            st.error(f"Token verification failed: {e}")
            return None
    
    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """Get user info from token"""
        decoded = self.verify_token(token)
        
        if decoded:
            return {
                "user_id": decoded.get("sub"),
                "email": decoded.get("email"),
                "username": decoded.get("username"),
                "first_name": decoded.get("first_name"),
                "last_name": decoded.get("last_name"),
                "full_name": decoded.get("name"),
                "image_url": decoded.get("picture")
            }
        return None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.clerk_user is not None
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user"""
        return st.session_state.clerk_user
    
    def login_with_token(self, token: str) -> bool:
        """Login user with JWT token"""
        user = self.get_user_from_token(token)
        
        if user:
            st.session_state.clerk_user = user
            st.session_state.clerk_token = token
            return True
        return False
    
    def logout(self):
        """Logout current user"""
        st.session_state.clerk_user = None
        st.session_state.clerk_token = None
    
    def get_token(self) -> Optional[str]:
        """Get current auth token"""
        return st.session_state.clerk_token


# Global instance
clerk = ClerkAuth()
