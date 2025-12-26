# streamlit_app.py - COMPLETE STREAMLIT DASHBOARD WITH CLERK AUTH

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from clerk_auth import clerk

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="SpectraAI Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = st.secrets["api"]["backend_url"]

# ============================================================================
# AUTHENTICATION UI
# ============================================================================

def show_auth_page():
    """Show authentication page"""
    st.title("🔐 SpectraAI Authentication")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Sign in to continue")
        
        # Method 1: Paste Token
        with st.expander("🔑 Method 1: Paste Token", expanded=True):
            st.markdown("""
            **Get your token:**
            1. Go to your Clerk-protected app
            2. Open browser console (F12)
            3. Run: `await window.Clerk.session.getToken()`
            4. Copy and paste below
            """)
            
            token_input = st.text_area(
                "Paste your Clerk JWT token",
                height=150,
                placeholder="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
            )
            
            if st.button("🚀 Sign In", use_container_width=True):
                if token_input:
                    with st.spinner("Verifying token..."):
                        if clerk.login_with_token(token_input.strip()):
                            st.success("✅ Successfully signed in!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid token")
                else:
                    st.warning("Please enter a token")
        
        # Method 2: Test Mode (Development)
        with st.expander("🧪 Method 2: Test Mode (Development Only)"):
            st.markdown("""
            **For testing without authentication:**
            - Uses a test user
            - Only works if backend is in DEBUG mode
            """)
            
            if st.button("🧪 Use Test Mode", use_container_width=True):
                # Set test user
                st.session_state.clerk_user = {
                    "user_id": "test_user_123",
                    "email": "test@example.com",
                    "username": "testuser",
                    "first_name": "Test",
                    "last_name": "User",
                    "full_name": "Test User",
                    "is_test": True
                }
                st.session_state.clerk_token = "test_mode"
                st.success("✅ Test mode enabled!")
                st.rerun()
        
        # Method 3: Get Token Helper
        with st.expander("📖 Method 3: How to Get Token"):
            st.markdown("""
            **Browser Console Method:**
            ```
            // Run this in your browser console
            await window.Clerk.session.getToken()
            ```
            
            **Long-Lived Token (10 years):**
            1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
            2. JWT Templates → Create Template
            3. Name: `testing-template`
            4. Lifetime: `315360000` (10 years)
            5. Save
            6. Run in console:
            ```
            await window.Clerk.session.getToken({ 
              template: "testing-template" 
            })
            ```
            """)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def make_request(method: str, endpoint: str, data=None, files=None):
    """Make authenticated API request"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {}
    
    # Add auth token if available
    token = clerk.get_token()
    if token and token != "test_mode":
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if files:
            response = requests.request(method, url, headers=headers, files=files, data=data)
        elif data:
            headers["Content-Type"] = "application/json"
            response = requests.request(method, url, headers=headers, json=data)
        else:
            response = requests.request(method, url, headers=headers)
        
        return response
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None

# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar with user info and navigation"""
    with st.sidebar:
        st.title("🚀 SpectraAI")
        
        # User info
        user = clerk.get_current_user()
        if user:
            st.markdown("---")
            st.markdown("### 👤 User Info")
            
            if user.get("image_url"):
                st.image(user["image_url"], width=80)
            
            st.write(f"**Name:** {user.get('full_name', 'N/A')}")
            st.write(f"**Email:** {user.get('email', 'N/A')}")
            
            if user.get("is_test"):
                st.warning("🧪 Test Mode")
            
            if st.button("🚪 Sign Out", use_container_width=True):
                clerk.logout()
                st.rerun()
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### 📋 Navigation")
        page = st.radio(
            "Select Page",
            [
                "🏠 Home",
                "💬 Chat",
                "📄 Documents",
                "🎥 Videos",
                "📊 History",
                "🧪 API Testing"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # System status
        st.markdown("### 📡 System Status")
        if st.button("Check Health", use_container_width=True):
            response = make_request("GET", "/health")
            if response and response.status_code == 200:
                health = response.json()
                status = health.get("status", "unknown")
                
                if status == "healthy":
                    st.success("✅ Healthy")
                else:
                    st.warning(f"⚠️ {status}")
        
        return page

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application"""
    
    # Check authentication
    if not clerk.is_authenticated():
        show_auth_page()
        return
    
    # Render sidebar and get selected page
    page = render_sidebar()
    
    # Render selected page
    if page == "🏠 Home":
        render_home_page()
    elif page == "💬 Chat":
        render_chat_page()
    elif page == "📄 Documents":
        render_documents_page()
    elif page == "🎥 Videos":
        render_videos_page()
    elif page == "📊 History":
        render_history_page()
    elif page == "🧪 API Testing":
        render_api_testing_page()

# ============================================================================
# PAGES
# ============================================================================

def render_home_page():
    """Render home page"""
    st.title("🏠 Welcome to SpectraAI")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("API Status", "🟢 Online")
    
    with col2:
        st.metric("API URL", API_BASE_URL)
    
    with col3:
        response = make_request("GET", "/info")
        if response and response.status_code == 200:
            info = response.json()
            st.metric("Version", info.get("version", "N/A"))
    
    st.markdown("---")
    
    # System info
    st.subheader("📋 System Information")
    response = make_request("GET", "/info")
    if response and response.status_code == 200:
        info = response.json()
        st.json(info)

def render_chat_page():
    """Render chat page"""
    st.title("💬 AI Chat")
    st.info("Chat functionality - implement as needed")
    
    user_message = st.text_area("Your message", height=100)
    
    if st.button("📤 Send"):
        if user_message:
            response = make_request("POST", "/api/chat/", data={
                "message": user_message,
                "stream": False
            })
            
            if response and response.status_code == 200:
                result = response.json()
                st.success("✅ Response received")
                st.write(result.get("message", "No response"))

def render_documents_page():
    """Render documents page"""
    st.title("📄 Documents")
    
    # Upload
    uploaded_file = st.file_uploader("Upload Document", type=['pdf', 'txt', 'docx'])
    
    if uploaded_file and st.button("📤 Upload"):
        files = {'file': (uploaded_file.name, uploaded_file.getvalue())}
        data = {'title': uploaded_file.name}
        
        response = make_request("POST", "/api/documents/upload", data=data, files=files)
        
        if response and response.status_code == 201:
            st.success("✅ Uploaded!")

def render_videos_page():
    """Render videos page"""
    st.title("🎥 Videos")
    st.info("Video functionality - implement as needed")

def render_history_page():
    """Render history page"""
    st.title("📊 Activity History")
    
    if st.button("Load Activities"):
        response = make_request("GET", "/api/history/activities")
        if response and response.status_code == 200:
            data = response.json()
            st.json(data)

def render_api_testing_page():
    """Render API testing page"""
    st.title("🧪 API Testing")
    
    method = st.selectbox("Method", ["GET", "POST", "PUT", "DELETE"])
    endpoint = st.text_input("Endpoint", "/health")
    
    if st.button("Send Request"):
        response = make_request(method, endpoint)
        if response:
            st.write(f"**Status:** {response.status_code}")
            st.json(response.json())

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == "__main__":
    main()
