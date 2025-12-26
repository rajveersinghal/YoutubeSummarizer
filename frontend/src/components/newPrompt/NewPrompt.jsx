// src/components/newPrompt/NewPrompt.jsx - INTEGRATED WITH BACKEND

import { useEffect, useRef, useState } from "react";
import { toast } from "react-hot-toast";
import "./newPrompt.css";

// Icons
const ModernInputIcon = ({ type }) => {
  const paths = {
    upload: "M12 5v14m-7-7h14",
    submit: "M12 5v14M12 5l-5 5M12 5l5 5",
    loading: "M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83",
  };
  return (
    <svg
      viewBox="0 0 24 24"
      className={`input-icon icon-${type}`}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[type]} />
    </svg>
  );
};

const NewPrompt = ({ onSend, isLoading, isSending }) => {
  const [text, setText] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  
  const endRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // ============================================================================
  // AUTO-SCROLL
  // ============================================================================

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [text, isSending, isLoading]);

  // ============================================================================
  // SUBMIT TEXT MESSAGE
  // ============================================================================

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!text.trim() || isSending || isLoading || isUploading) {
      return;
    }

    const message = text.trim();
    setText("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      await onSend(message);
    } catch (error) {
      console.error("Send error:", error);
      toast.error("Failed to send message");
      // Restore text on error
      setText(message);
    }
  };

  // ============================================================================
  // FILE UPLOAD WITH VALIDATION
  // ============================================================================

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    
    if (!file) return;

    // Validate file type
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'text/plain',
    ];

    if (!allowedTypes.includes(file.type)) {
      toast.error("Invalid file type. Please upload PDF, DOCX, DOC, or TXT files.");
      e.target.value = null;
      return;
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      toast.error("File size exceeds 10MB limit");
      e.target.value = null;
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Simulate upload progress (you can replace with actual progress tracking)
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Send file to parent component
      await onSend(file.name, file);

      clearInterval(progressInterval);
      setUploadProgress(100);

      // Reset after short delay
      setTimeout(() => {
        setUploadProgress(0);
        setIsUploading(false);
      }, 1000);

    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Failed to upload file");
      setUploadProgress(0);
      setIsUploading(false);
    }

    // Reset file input
    e.target.value = null;
  };

  // ============================================================================
  // TEXTAREA AUTO-RESIZE
  // ============================================================================

  const handleInputResize = (e) => {
    const target = e.target;
    target.style.height = "auto";
    target.style.height = `${target.scrollHeight}px`;
    setText(target.value);
  };

  // ============================================================================
  // KEYBOARD SHORTCUTS
  // ============================================================================

  const handleKeyDown = (e) => {
    // Enter = Submit (Shift+Enter = New Line)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }

    // Escape = Clear text
    if (e.key === "Escape") {
      setText("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  // ============================================================================
  // PASTE HANDLER (For images/files)
  // ============================================================================

  const handlePaste = async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      
      // Handle pasted files
      if (item.kind === 'file') {
        e.preventDefault();
        const file = item.getAsFile();
        
        if (file) {
          // Trigger file upload
          const event = { target: { files: [file], value: null } };
          await handleFileChange(event);
        }
      }
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  const isDisabled = isSending || isLoading || isUploading;

  return (
    <>
      <div className="endChat" ref={endRef}></div>

      {/* Form */}
      <form className="newForm" onSubmit={handleSubmit}>
        {/* Hidden File Input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: "none" }}
          accept=".pdf,.docx,.doc,.txt"
          disabled={isDisabled}
        />

        {/* Upload Progress Bar */}
        {isUploading && uploadProgress > 0 && (
          <div className="upload-progress-container">
            <div className="upload-progress-bar">
              <div
                className="upload-progress-fill"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <span className="upload-progress-text">{uploadProgress}%</span>
          </div>
        )}

        {/* Input Container */}
        <div className="input-container">
          {/* Upload Button */}
          <button
            type="button"
            className={`input-button upload-btn ${isDisabled ? "disabled" : ""}`}
            onClick={() => fileInputRef.current?.click()}
            disabled={isDisabled}
            title="Upload document (PDF, DOCX, TXT)"
          >
            {isUploading ? (
              <div className="spinner-small" />
            ) : (
              <ModernInputIcon type="upload" />
            )}
          </button>

          {/* Text Area */}
          <div className="input-fields-container">
            <textarea
              ref={textareaRef}
              className="modern-input"
              placeholder={
                isLoading
                  ? "Loading..."
                  : isSending
                  ? "Sending..."
                  : isUploading
                  ? "Uploading..."
                  : "Ask anything or paste a YouTube link..."
              }
              value={text}
              onInput={handleInputResize}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              rows="1"
              disabled={isDisabled}
            />

            {/* Character Count (Optional) */}
            {text.length > 0 && (
              <span className="char-count">{text.length}</span>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className={`input-button modern-submit-btn ${
              isDisabled || !text.trim() ? "disabled" : ""
            }`}
            disabled={isDisabled || !text.trim()}
            title="Send message (Enter)"
          >
            {isSending ? (
              <div className="spinner-small" />
            ) : (
              <ModernInputIcon type="submit" />
            )}
          </button>
        </div>

        {/* Keyboard Shortcuts Hint */}
        <div className="input-hints">
          <span>Press <kbd>Enter</kbd> to send</span>
          <span><kbd>Shift</kbd> + <kbd>Enter</kbd> for new line</span>
          <span><kbd>Esc</kbd> to clear</span>
        </div>
      </form>
    </>
  );
};

export default NewPrompt;
