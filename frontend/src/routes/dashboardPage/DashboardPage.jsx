// src/pages/DashboardPage/DashboardPage.jsx - FIXED

import { useState, useRef } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import { api } from "../../lib/api";
import "./dashboardPage.css";

const YOUTUBE_URL_REGEX =
  /(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/(watch\?v=|embed\/|v\/|.+\?v=)?([^&=%\?]{11})/;

const ModernInputIcon = ({ type }) => {
  const paths = {
    upload: "M12 5v14m-7-7h14",
    submit: "M12 5v14M12 5l-5 5M12 5l5 5",
  };
  const path = paths[type];
  return (
    <svg
      viewBox="0 0 24 24"
      className={`input-icon icon-${type}`}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={path} />
    </svg>
  );
};

const DashboardPage = () => {
  const { user } = useUser();
  const navigate = useNavigate();
  const { handleCreateChat } = useOutletContext();
  const fileInputRef = useRef(null);
  const formRef = useRef(null);
  const textareaRef = useRef(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const containerVariants = {
    hidden: { opacity: 1 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.15, delayChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30, scale: 0.95 },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: { type: "spring", stiffness: 260, damping: 20, mass: 0.8 },
    },
  };

  // ============================================================================
  // HANDLE CHAT CREATION
  // ============================================================================

  const handleLocalCreateChat = async (prompt, mode = "question", file = null) => {
  try {
    setIsSubmitting(true);

    if (mode === "youtube") {
      // Extract YouTube link
      const match = prompt.match(YOUTUBE_URL_REGEX);
      const youtubeUrl = match ? match[0] : null;

      if (!youtubeUrl) {
        toast.error("Invalid YouTube URL");
        return;
      }

      const uploadToast = toast.loading("Processing YouTube video...");

      // Upload YouTube URL as video
      const videoResponse = await api.videos.uploadYouTube(youtubeUrl);
      
      console.log('📥 Video response:', videoResponse);
      
      toast.success("Video processed successfully!", { id: uploadToast });

      // ✅ FIX: Use conversation_id from video response
      const conversationId = videoResponse?.conversation_id;

      if (!conversationId) {
        throw new Error('No conversation ID returned');
      }

      // Navigate to chat
      navigate(`/dashboard/chats/${conversationId}`);
      
    } else if (mode === "document") {
      // ... document handling
    } else {
      // ... regular chat
    }

  } catch (error) {
    console.error("Error:", error);
    toast.error(error.message || "An error occurred");
  } finally {
    setIsSubmitting(false);
    
    // Reset form
    if (formRef.current) {
      formRef.current.reset();
    }
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }
};

  const onSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;

    const data = new FormData(e.currentTarget);
    const prompt = (data.get("prompt") || "").toString().trim();

    if (!prompt) {
      toast.error("Please enter a message");
      return;
    }

    // Detect mode
    const hasYouTubeLink = YOUTUBE_URL_REGEX.test(prompt);
    const mode = hasYouTubeLink ? "youtube" : "question";

    // Use context handler if available, otherwise use local
    if (handleCreateChat) {
      await handleCreateChat(prompt, mode);
    } else {
      await handleLocalCreateChat(prompt, mode);
    }
  };

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    
    if (!file) return;

    // Validate file type
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain'
    ];

    if (!allowedTypes.includes(file.type)) {
      toast.error("Invalid file type. Please upload PDF, DOCX, or TXT files.");
      return;
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      toast.error("File size exceeds 10MB limit");
      return;
    }

    if (!isSubmitting) {
      // Use context handler if available, otherwise use local
      if (handleCreateChat) {
        await handleCreateChat(file.name, "document", file);
      } else {
        await handleLocalCreateChat(file.name, "document", file);
      }
    }

    event.target.value = null;
  };

  const handleUploadClick = () => {
    if (!isSubmitting) {
      fileInputRef.current.click();
    }
  };

  const handleInputResize = (e) => {
    const textarea = e.target;
    textarea.style.height = "auto";
    const newHeight = `${textarea.scrollHeight}px`;
    textarea.style.height = newHeight;
    if (formRef.current) {
      const container = formRef.current.querySelector(".input-container");
      if (container) {
        container.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !isSubmitting) {
      e.preventDefault();
      formRef.current.requestSubmit();
    }
  };

  return (
    <motion.div
      className="learn-dashboard"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h2 className="page-title" variants={itemVariants}>
        Hello, {user?.firstName || "Guest"}
      </motion.h2>

      <motion.div className="synced-content" variants={itemVariants}>
        <p className="page-subtitle">What do you want to learn?</p>

        <div className="form-container">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            style={{ display: "none" }}
            accept=".pdf,.docx,.doc,.txt"
            disabled={isSubmitting}
          />

          <form
            ref={formRef}
            className="modern-input-wrapper"
            onSubmit={onSubmit}
          >
            <div className="input-container">
              <button
                type="button"
                className={`input-button upload-btn ${isSubmitting ? 'disabled' : ''}`}
                aria-label="Upload file"
                onClick={handleUploadClick}
                disabled={isSubmitting}
              >
                <ModernInputIcon type="upload" />
              </button>

              <div className="input-fields-container">
                <textarea
                  ref={textareaRef}
                  className="modern-input"
                  name="prompt"
                  placeholder="Ask anything, paste a YouTube link, or upload a document..."
                  autoComplete="off"
                  rows="1"
                  onInput={handleInputResize}
                  onKeyDown={handleKeyDown}
                  disabled={isSubmitting}
                />
              </div>

              <button
                type="submit"
                className={`input-button modern-submit-btn ${isSubmitting ? 'disabled' : ''}`}
                aria-label="Submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <div className="spinner" />
                ) : (
                  <ModernInputIcon type="submit" />
                )}
              </button>
            </div>
          </form>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default DashboardPage;
