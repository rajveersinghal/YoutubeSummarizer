// src/pages/ChatPage/ChatPage.jsx - FIXED WITH YOUTUBE SUPPORT

import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { toast } from "react-hot-toast";
import ReactMarkdown from "react-markdown";
import NewPrompt from "../../components/newPrompt/NewPrompt";
import { api } from "../../lib/api";
import "./chatPage.css";

const YOUTUBE_URL_REGEX =
  /(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/(watch\?v=|embed\/|v\/|.+\?v=)?([^&=%\?]{11})/;

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [chatInfo, setChatInfo] = useState(null);

  const hasInitialized = useRef(null);
  const hasAutoSent = useRef(false);
  const messagesEndRef = useRef(null);

  const { id } = useParams();
  const { getToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat on mount
  useEffect(() => {
    if (!id) {
      console.error("Chat ID is undefined");
      navigate("/dashboard");
      return;
    }

    if (hasInitialized.current === id) return;

    const loadChat = async () => {
      hasInitialized.current = id;
      setIsLoading(true);

      try {
        const token = await getToken();
        if (!token) {
          console.error("No token found");
          navigate("/sign-in");
          return;
        }

        console.log("🔄 Loading conversation:", id);

        const response = await api.chat.getConversation(id);
        
        console.log("📥 Raw response:", response);

        // Handle different response structures
        let conversation, messagesData;
        
        if (response.data) {
          conversation = response.data.conversation || response.data;
          messagesData = response.data.messages || [];
        } else {
          conversation = response.conversation || response;
          messagesData = response.messages || [];
        }

        console.log("📦 Conversation:", conversation);
        console.log("💬 Messages data:", messagesData);

        setChatInfo({
          title: conversation.title || "New Chat",
          created_at: conversation.created_at,
          message_count: conversation.message_count || messagesData.length,
        });

        // Format messages
        const formattedHistory = messagesData.map((msg, index) => {
          const messageContent = msg.content || msg.text || msg.message || "";

          return {
            id: msg.message_id || msg.id || `${id}-${index}`,
            role: msg.role,
            text: messageContent,
            timestamp: msg.timestamp,
          };
        });

        console.log("✅ Formatted messages:", formattedHistory);
        setMessages(formattedHistory);

        // Auto-send first prompt if available
        if (
          formattedHistory.length === 0 &&
          location.state?.firstPrompt &&
          !hasAutoSent.current
        ) {
          hasAutoSent.current = true;
          setTimeout(() => {
            handleSend(location.state.firstPrompt, location.state.file);
            navigate(location.pathname, { replace: true, state: {} });
          }, 100);
        }
      } catch (error) {
        console.error("❌ Error loading chat:", error);
        
        // If 404, conversation doesn't exist - start fresh
        if (error.response?.status === 404 || error.message?.includes("404")) {
          console.log("⚠️ Conversation not found, starting fresh");
          setChatInfo({
            title: "New Chat",
            created_at: Date.now() / 1000,
            message_count: 0,
          });
          setMessages([]);
        } else {
          toast.error("Failed to load chat");
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadChat();
  }, [id, getToken, location.state, navigate]);

  // Handle sending messages
  const handleSend = async (prompt, file = null) => {
    if (isSending || !prompt.trim()) return;

    console.log("📤 Sending message:", prompt);

    setIsSending(true);

    const userMsgId = crypto.randomUUID();
    const aiMsgId = crypto.randomUUID();

    // Add user message
    setMessages((prev) => [
      ...prev,
      { 
        id: userMsgId, 
        role: "user", 
        text: prompt,
        timestamp: Date.now() / 1000
      },
      { 
        id: aiMsgId, 
        role: "assistant", 
        text: "Thinking...", 
        isThinking: true 
      },
    ]);

    try {
      const token = await getToken();
      if (!token) {
        throw new Error("No authentication token");
      }

      let aiResponse;
      let newConversationId = id;

      // Handle file upload
      if (file) {
        toast.loading("Uploading document...", { id: "upload" });

        const uploadResponse = await api.documents.upload(
          file,
          file.name,
          "Uploaded from chat"
        );

        toast.success("Document uploaded!", { id: "upload" });

        const chatResponse = await api.chat.send(
          `Analyze this document: ${file.name}`,
          id
        );

        console.log("📥 Chat response (file):", chatResponse);
        aiResponse = chatResponse.message || chatResponse.response || chatResponse.data?.message || chatResponse.data?.response;
        newConversationId = chatResponse.conversation_id || chatResponse.data?.conversation_id || id;
      }
      // ✅ FIXED: Handle YouTube URL
      else if (YOUTUBE_URL_REGEX.test(prompt)) {
        const match = prompt.match(YOUTUBE_URL_REGEX);
        const youtubeUrl = match ? match[0] : null;

        if (!youtubeUrl) {
          throw new Error("Invalid YouTube URL");
        }

        console.log("🎥 Processing YouTube URL:", youtubeUrl);

        toast.loading("Processing YouTube video...", { id: "youtube" });

        try {
          // ✅ Call YouTube endpoint
          const videoResponse = await api.videos.uploadYouTube(
            youtubeUrl,
            null  // Let backend get the title
          );

          console.log("✅ YouTube response:", videoResponse);

          toast.success(`Video processed: ${videoResponse.title}`, { id: "youtube" });

          // Extract transcript
          const transcript = videoResponse.transcript || "";
          const transcriptPreview = transcript.substring(0, 3000);

          console.log("📝 Transcript length:", transcript.length);

          // Send chat message to summarize
          const chatResponse = await api.chat.send(
            `Please provide a comprehensive summary of this YouTube video:\n\n**Title:** ${videoResponse.title}\n\n**Transcript:**\n${transcriptPreview}${transcript.length > 3000 ? "\n\n...(transcript continues)" : ""}`,
            id
          );

          console.log("💬 Chat response:", chatResponse);
          
          aiResponse = chatResponse.message || chatResponse.response || chatResponse.data?.message || chatResponse.data?.response;
          newConversationId = chatResponse.conversation_id || chatResponse.data?.conversation_id || id;

        } catch (videoError) {
          console.error("❌ YouTube error:", videoError);
          console.error("Error details:", videoError.response?.data);
          
          const errorMsg = videoError.response?.data?.detail || videoError.message;
          toast.error(`YouTube error: ${errorMsg}`, { id: "youtube" });
          throw videoError;
        }
      }
      // Regular chat message
      else {
        const chatResponse = await api.chat.send(prompt, id);
        
        console.log("📥 Chat response (regular):", chatResponse);
        
        // Try multiple possible response field names
        aiResponse = 
          chatResponse.message || 
          chatResponse.response || 
          chatResponse.data?.message || 
          chatResponse.data?.response ||
          chatResponse.text ||
          chatResponse.content ||
          "No response received";
          
        newConversationId = 
          chatResponse.conversation_id || 
          chatResponse.data?.conversation_id || 
          id;

        console.log("✅ Extracted AI response:", aiResponse);
        console.log("✅ Conversation ID:", newConversationId);
      }

      // ✅ Update AI message with response
      setMessages((prev) => {
        const updated = prev.map((msg) =>
          msg.id === aiMsgId
            ? { 
                ...msg, 
                text: aiResponse || "Empty response", 
                isThinking: false,
                timestamp: Date.now() / 1000
              }
            : msg
        );
        return updated;
      });

      // Navigate to new conversation if created
      if (newConversationId && newConversationId !== id) {
        console.log("🔀 Navigating to new conversation:", newConversationId);
        navigate(`/dashboard/chats/${newConversationId}`, { replace: true });
      }

      // Update chat info
      setChatInfo((prev) => ({
        ...prev,
        message_count: (prev?.message_count || 0) + 2,
      }));

      toast.success("Message sent!");

    } catch (error) {
      console.error("❌ Send message error:", error);
      console.error("Error response:", error.response?.data);

      const errorMessage =
        error.response?.data?.detail ||
        error.message ||
        "Failed to send message";

      toast.error(errorMessage);

      // Update AI message with error
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMsgId
            ? {
                ...msg,
                text: `❌ Error: ${errorMessage}`,
                isError: true,
                isThinking: false,
              }
            : msg
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  // Handle delete chat
  const handleDeleteChat = async () => {
    if (!window.confirm("Are you sure you want to delete this chat?")) {
      return;
    }

    try {
      await api.chat.deleteConversation(id);
      toast.success("Chat deleted");
      navigate("/dashboard");
    } catch (error) {
      console.error("Delete error:", error);
      toast.error("Failed to delete chat");
    }
  };

  // Handle clear history
  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to clear this chat history?")) {
      return;
    }

    try {
      await api.chat.clearHistory(id);
      setMessages([]);
      setChatInfo(prev => ({ ...prev, message_count: 0 }));
      toast.success("Chat history cleared");
    } catch (error) {
      console.error("Clear error:", error);
      toast.error("Failed to clear history");
    }
  };

  if (isLoading) {
    return (
      <div className="chatPage loading">
        <div className="spinner-container">
          <div className="spinner"></div>
          <p>Loading chat...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chatPage">
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-info">
          <h2>{chatInfo?.title || "New Chat"}</h2>
          <span className="message-count">
            {chatInfo?.message_count || messages.length} messages
          </span>
        </div>
        <div className="chat-actions">
          <button
            className="btn-icon"
            onClick={handleClearHistory}
            title="Clear history"
            disabled={messages.length === 0}
          >
            🗑️
          </button>
          <button
            className="btn-icon"
            onClick={handleDeleteChat}
            title="Delete chat"
          >
            ❌
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="wrapper">
        <div className="chat">
          {messages.length === 0 && !isLoading && !isSending && (
            <div className="empty-state">
              <div className="empty-icon">💬</div>
              <h3>Start a conversation</h3>
              <p>Ask anything, paste a YouTube link, or upload a document!</p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`message ${msg.role} ${msg.isError ? "error" : ""} ${
                msg.isThinking ? "thinking" : ""
              }`}
            >
              <div className="message-avatar">
                {msg.role === "user" ? "👤" : "🤖"}
              </div>
              <div className="message-content">
                <div className="message-text">
                  {msg.role === "assistant" ? (
                    msg.text ? (
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                    ) : (
                      <p style={{color: 'red'}}>❌ No text content</p>
                    )
                  ) : (
                    <p>{msg.text || "Empty message"}</p>
                  )}
                </div>
                {msg.timestamp && !msg.isThinking && (
                  <span className="message-time">
                    {new Date(msg.timestamp * 1000).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                )}
              </div>
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <NewPrompt
        onSend={handleSend}
        isLoading={isLoading}
        isSending={isSending}
      />
    </div>
  );
};

export default ChatPage;
