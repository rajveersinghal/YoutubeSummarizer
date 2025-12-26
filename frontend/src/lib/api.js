// src/lib/api.js - FIXED RESPONSE HANDLING

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
axiosInstance.interceptors.request.use(
  async (config) => {
    // Get token from Clerk
    const token = await window.Clerk?.session?.getToken();
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('✅ Auth token attached to request');
    } else {
      console.warn('⚠️ No auth token available');
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error(`❌ ${error.response.status} ${error.response.statusText}:`, error.response.data?.detail || error.response.data);
    } else if (error.request) {
      console.error('❌ No response received:', error.request);
    } else {
      console.error('❌ Request error:', error.message);
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// STANDALONE HEALTH CHECK
// ============================================================================

export const checkHealth = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  } catch (error) {
    console.error('❌ Health check failed:', error);
    return { 
      status: 'error', 
      error: error.message,
      services: {}
    };
  }
};

// ============================================================================
// API METHODS
// ============================================================================

export const api = {
  // Health endpoints
  health: {
    check: checkHealth,
    
    getInfo: async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/info`);
        return response.data;
      } catch (error) {
        console.error('❌ Info fetch failed:', error);
        return null;
      }
    },
    
    getStats: async () => {
      try {
        const response = await axiosInstance.get('/stats');
        return response.data;
      } catch (error) {
        console.error('❌ Stats fetch failed:', error);
        return null;
      }
    },
  },

  // Auth endpoints
  auth: {
    syncUser: async (userData) => {
      try {
        const response = await axiosInstance.post('/api/auth/sync', userData);
        return response.data;
      } catch (error) {
        console.error('❌ Sync user failed:', error);
        throw error;
      }
    },
    
    getMe: async () => {
      try {
        const response = await axiosInstance.get('/api/auth/me');
        return response.data;
      } catch (error) {
        console.error('❌ Get me failed:', error);
        throw error;
      }
    },

    // ✅ FIXED: Get user preferences/theme
    me: async () => {
      try {
        const response = await axiosInstance.get('/api/auth/me');
        console.log('📥 User response:', response.data);
        
        // Return full response.data
        return response.data;
      } catch (error) {
        console.error('❌ Get user failed:', error);
        // Return safe default
        return { 
          user: {},
          preferences: { theme: 'light' }
        };
      }
    },

    // ✅ FIXED: Update user preferences
    updatePreferences: async (preferences) => {
      try {
        const response = await axiosInstance.patch('/api/auth/preferences', preferences);
        return response.data;
      } catch (error) {
        console.warn('⚠️ Update preferences failed (endpoint may not exist):', error.message);
        // Silent fail - preferences not critical
        return { success: false };
      }
    },
  },

  // Chat endpoints
  chat: {
    // ✅ FIXED: Send message
    send: async (message, conversationId = null) => {
      try {
        const response = await axiosInstance.post('/api/chat/', {
          message,
          conversation_id: conversationId,
        });
        
        console.log('📥 Chat send response:', response.data);
        
        // Return response.data directly
        return response.data;
      } catch (error) {
        console.error('❌ Send message failed:', error);
        throw error;
      }
    },

    // ✅ FIXED: Get conversations
    getConversations: async (page = 1, pageSize = 50) => {
      try {
        const response = await axiosInstance.get('/api/chat/conversations', {
          params: { page, page_size: pageSize },
        });
        
        console.log('📥 Conversations response:', response.data);
        
        // Return response.data directly
        return response.data;
      } catch (error) {
        console.error('❌ Get conversations failed:', error);
        // Return empty instead of throwing
        return {
          success: true,
          conversations: [],
          total: 0,
          page: 1,
          page_size: pageSize
        };
      }
    },

    // ✅ FIXED: Get conversation
    getConversation: async (conversationId) => {
      try {
        const response = await axiosInstance.get(`/api/chat/conversations/${conversationId}`);
        
        console.log('📥 Conversation response:', response.data);
        
        // Return response.data directly
        return response.data;
      } catch (error) {
        console.error('❌ Get conversation failed:', error);
        throw error;
      }
    },

    deleteConversation: async (conversationId) => {
      try {
        const response = await axiosInstance.delete(`/api/chat/conversations/${conversationId}`);
        return response.data;
      } catch (error) {
        console.error('❌ Delete conversation failed:', error);
        throw error;
      }
    },

    clearHistory: async (conversationId) => {
      try {
        const response = await axiosInstance.delete(`/api/chat/conversations/${conversationId}/messages`);
        return response.data;
      } catch (error) {
        console.error('❌ Clear history failed:', error);
        throw error;
      }
    },

    updateConversation: async (conversationId, title) => {
      try {
        const response = await axiosInstance.patch(`/api/chat/conversations/${conversationId}`, {
          title,
        });
        return response.data;
      } catch (error) {
        console.error('❌ Update conversation failed:', error);
        throw error;
      }
    },

    // ✅ FIXED: Create conversation
    createConversation: async (title = "New Chat") => {
      try {
        // Send first message to create conversation
        const response = await axiosInstance.post('/api/chat/', {
          message: title,
          conversation_id: null,
        });
        
        console.log('📥 Create conversation response:', response.data);
        
        // Return response.data directly
        return response.data;
      } catch (error) {
        console.error('❌ Create conversation failed:', error);
        throw error;
      }
    },
  },

  // Video endpoints
  videos: {
    uploadYouTube: async (youtubeUrl, title = null) => {
      try {
        console.log('📹 Uploading YouTube video:', youtubeUrl);
        
        const response = await axiosInstance.post('/api/videos/youtube', {
          youtube_url: youtubeUrl,
          title: title,
        });
        
        console.log('✅ YouTube upload response:', response.data);
        return response.data;
      } catch (error) {
        console.error('❌ YouTube upload failed:', error);
        throw error;
      }
    },

    upload: async (file, title, description = null) => {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', title);
        if (description) {
          formData.append('description', description);
        }

        const response = await axiosInstance.post('/api/videos/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        
        return response.data;
      } catch (error) {
        console.error('❌ Video upload failed:', error);
        throw error;
      }
    },

    getAll: async (page = 1, pageSize = 20, status = null, search = null) => {
      try {
        const params = { page, page_size: pageSize };
        if (status) params.status = status;
        if (search) params.search = search;

        const response = await axiosInstance.get('/api/videos/', { params });
        return response.data;
      } catch (error) {
        console.error('❌ Get videos failed:', error);
        return { videos: [], total: 0 };
      }
    },

    getById: async (videoId) => {
      try {
        const response = await axiosInstance.get(`/api/videos/${videoId}`);
        return response.data;
      } catch (error) {
        console.error('❌ Get video failed:', error);
        throw error;
      }
    },

    getStatus: async (videoId) => {
      try {
        const response = await axiosInstance.get(`/api/videos/${videoId}/status`);
        return response.data;
      } catch (error) {
        console.error('❌ Get video status failed:', error);
        throw error;
      }
    },

    update: async (videoId, title, description = null) => {
      try {
        const response = await axiosInstance.patch(`/api/videos/${videoId}`, {
          title,
          description,
        });
        return response.data;
      } catch (error) {
        console.error('❌ Update video failed:', error);
        throw error;
      }
    },

    delete: async (videoId) => {
      try {
        const response = await axiosInstance.delete(`/api/videos/${videoId}`);
        return response.data;
      } catch (error) {
        console.error('❌ Delete video failed:', error);
        throw error;
      }
    },

    getStreamUrl: (videoId) => {
      return `${API_BASE_URL}/api/videos/${videoId}/stream`;
    },

    getDownloadUrl: (videoId) => {
      return `${API_BASE_URL}/api/videos/${videoId}/download`;
    },
  },

  // Document endpoints
  documents: {
    upload: async (file, title, description = null) => {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', title);
        if (description) {
          formData.append('description', description);
        }

        const response = await axiosInstance.post('/api/documents/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        
        return response.data;
      } catch (error) {
        console.error('❌ Document upload failed:', error);
        throw error;
      }
    },

    getAll: async (page = 1, pageSize = 20, status = null, search = null) => {
      try {
        const params = { page, page_size: pageSize };
        if (status) params.status = status;
        if (search) params.search = search;

        const response = await axiosInstance.get('/api/documents/', { params });
        return response.data;
      } catch (error) {
        console.error('❌ Get documents failed:', error);
        return { documents: [], total: 0 };
      }
    },

    getById: async (documentId) => {
      try {
        const response = await axiosInstance.get(`/api/documents/${documentId}`);
        return response.data;
      } catch (error) {
        console.error('❌ Get document failed:', error);
        throw error;
      }
    },

    update: async (documentId, title, description = null) => {
      try {
        const response = await axiosInstance.patch(`/api/documents/${documentId}`, {
          title,
          description,
        });
        return response.data;
      } catch (error) {
        console.error('❌ Update document failed:', error);
        throw error;
      }
    },

    delete: async (documentId) => {
      try {
        const response = await axiosInstance.delete(`/api/documents/${documentId}`);
        return response.data;
      } catch (error) {
        console.error('❌ Delete document failed:', error);
        throw error;
      }
    },

    getDownloadUrl: (documentId) => {
      return `${API_BASE_URL}/api/documents/${documentId}/download`;
    },

    search: async (query, page = 1, pageSize = 20) => {
      try {
        const response = await axiosInstance.get('/api/documents/search', {
          params: { query, page, page_size: pageSize },
        });
        return response.data;
      } catch (error) {
        console.error('❌ Document search failed:', error);
        return { documents: [], total: 0 };
      }
    },
  },

  // History endpoints
  history: {
    getAll: async (page = 1, pageSize = 50) => {
      try {
        const response = await axiosInstance.get('/api/history/', {
          params: { page, page_size: pageSize },
        });
        
        console.log('📥 History response:', response.data);
        
        // Return response.data directly
        return response.data;
      } catch (error) {
        console.warn('⚠️ Get history failed (endpoint may not exist):', error.message);
        // Return empty instead of throwing
        return {
          success: true,
          activities: [],
          total: 0,
          page: 1,
          page_size: pageSize
        };
      }
    },

    clear: async () => {
      try {
        const response = await axiosInstance.delete('/api/history/');
        return response.data;
      } catch (error) {
        console.error('❌ Clear history failed:', error);
        throw error;
      }
    },

    getByDateRange: async (startDate, endDate) => {
      try {
        const response = await axiosInstance.get('/api/history/range', {
          params: { 
            start_date: startDate,
            end_date: endDate,
          },
        });
        return response.data;
      } catch (error) {
        console.error('❌ Get history by date failed:', error);
        return { activities: [] };
      }
    },

    // Alias for compatibility
    activities: async (limit = 5) => {
      return await api.history.getAll(1, limit);
    },

    // ✅ NEW: Get stats
    stats: async () => {
      try {
        const response = await axiosInstance.get('/api/history/stats');
        return response.data;
      } catch (error) {
        console.warn('⚠️ Get history stats failed:', error.message);
        return {
          success: true,
          stats: {
            total_activities: 0,
            activities_by_type: {},
            recent_activities_7days: 0
          }
        };
      }
    },
  },
};

export default api;
