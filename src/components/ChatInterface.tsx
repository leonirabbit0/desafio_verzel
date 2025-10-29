import { useState, useEffect, useRef } from "react";
import type { CSSProperties } from "react";

import { Send, Loader2 } from "lucide-react";
import { motion } from "framer-motion";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [isMobile, setIsMobile] = useState(false);


  const API_BASE_URL = "https://verzel-backend-production.up.railway.app";


  useEffect(() => {
    if (typeof window !== "undefined") {
      setIsMobile(window.innerWidth < 768);
    }
  }, []);

  useEffect(() => {
    const initializeChat = async () => {
      let currentSessionId = localStorage.getItem("verzel_session_id");

      if (!currentSessionId) {
        currentSessionId = `visitor_${Date.now()}_${Math.random()
          .toString(36)
          .substr(2, 9)}`;
        localStorage.setItem("verzel_session_id", currentSessionId);
      }

      setSessionId(currentSessionId);

      try {
        const response = await fetch(
          `${API_BASE_URL}/get_messages?session_id=${currentSessionId}`
        );
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
        } else {
          setMessages([
            {
              role: "assistant",
              content:
                "Olá! Sou o Roberto, da Verzel. Como posso te ajudar hoje?",
            },
          ]);
        }
      } catch (error) {
        console.error("Erro ao carregar mensagens:", error);
        setMessages([
          {
            role: "assistant",
            content:
              "Olá! Sou o Roberto, da Verzel. Como posso te ajudar hoje?",
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    initializeChat();
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/input_message?message_received=${encodeURIComponent(
          input
        )}&session_id=${sessionId}`
      );
      const data = await response.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.response || "Desculpe, não entendi.",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Erro ao conectar com API:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Erro ao conectar com o servidor." },
      ]);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const styles: Record<string, CSSProperties> = {
    wrapper: {
      width: "100%",
      minHeight: "100vh",
      backgroundColor: "#f3f4f6",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
    },
    container: {
      display: "flex",
      flexDirection: "column",
      height: "90vh",
      width: "100%",
      maxWidth: "1200px",
      margin: "0 auto",
      backgroundColor: "#ffffff",
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      borderRadius: "16px",
      boxShadow: "0 10px 40px rgba(0,0,0,0.1)",
      overflow: "hidden",
    },
    header: {
      padding: "24px",
      background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
      color: "white",
      textAlign: "center" as const,
      fontSize: "24px",
      fontWeight: "bold",
      boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
    },
    chatArea: {
      flex: 1,
      overflowY: "auto",
      padding: "32px",
      backgroundColor: "#f9fafb",
      display: "flex",
      flexDirection: "column" as const,
      gap: "20px",
    },
    messageContainer: {
      display: "flex",
      marginBottom: "4px",
      animation: "fadeIn 0.3s ease-in-out",
    },
    messageUser: {
      justifyContent: "flex-end" as const,
    },
    messageAssistant: {
      justifyContent: "flex-start" as const,
    },
    bubble: {
      maxWidth: "65%",
      padding: "14px 20px",
      borderRadius: "20px",
      fontSize: "15px",
      lineHeight: "1.6",
      boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
      wordWrap: "break-word" as const,
      whiteSpace: "pre-wrap" as const,
    },
    bubbleUser: {
      backgroundColor: "#2563eb",
      color: "white",
      borderBottomRightRadius: "4px",
    },
    bubbleAssistant: {
      backgroundColor: "#e5e7eb",
      color: "#1f2937",
      borderBottomLeftRadius: "4px",
    },
    inputArea: {
      padding: "24px 32px",
      backgroundColor: "white",
      borderTop: "1px solid #e5e7eb",
      boxShadow: "0 -2px 10px rgba(0,0,0,0.05)",
    },
    inputContainer: {
      display: "flex",
      gap: "16px",
      alignItems: "center",
      maxWidth: "100%",
    },
    input: {
      flex: 1,
      padding: "14px 24px",
      border: "2px solid #d1d5db",
      borderRadius: "28px",
      fontSize: "15px",
      outline: "none",
      transition: "all 0.2s",
      backgroundColor: "#ffffff",
      color: "#1f2937",
    },
    button: {
      padding: "14px",
      backgroundColor: "#2563eb",
      color: "white",
      border: "none",
      borderRadius: "50%",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "all 0.2s",
      boxShadow: "0 4px 12px rgba(37, 99, 235, 0.3)",
      minWidth: "52px",
      minHeight: "52px",
    },
    buttonDisabled: {
      opacity: 0.5,
      cursor: "not-allowed",
    },
    loading: {
      display: "flex",
      flexDirection: "column" as const,
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      backgroundColor: "#f9fafb",
    },
  };

  // Responsividade
  if (isMobile) {
    styles.wrapper.padding = "0";
    styles.container.height = "100vh";
    styles.container.maxWidth = "100%";
    styles.container.borderRadius = "0";
    styles.header.fontSize = "18px";
    styles.header.padding = "16px";
    styles.chatArea.padding = "16px";
    styles.bubble.maxWidth = "80%";
    styles.bubble.fontSize = "14px";
    styles.inputArea.padding = "16px";
    styles.button.minWidth = "44px";
    styles.button.minHeight = "44px";
  }

  if (loading) {
    return (
      <div style={styles.loading}>
        <Loader2
          style={{ width: "40px", height: "40px", color: "#2563eb" }}
          className="animate-spin"
        />
        <p
          style={{
            marginTop: "16px",
            color: "#6b7280",
            fontWeight: "500",
          }}
        >
          Carregando conversa...
        </p>
      </div>
    );
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.container}>
        {/* Header */}
        <div style={styles.header}>Assistente Virtual - Verzel</div>

        {/* Chat area */}
        <div style={styles.chatArea}>
          {messages.map((msg, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              style={{
                ...styles.messageContainer,
                ...(msg.role === "user"
                  ? styles.messageUser
                  : styles.messageAssistant),
              }}
            >
              <div
                style={{
                  ...styles.bubble,
                  ...(msg.role === "user"
                    ? styles.bubbleUser
                    : styles.bubbleAssistant),
                }}
              >
                {msg.content}
              </div>
            </motion.div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div style={styles.inputArea}>
          <div style={styles.inputContainer}>
            <input
              type="text"
              style={styles.input}
              placeholder="Digite sua mensagem..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              onFocus={(e) => {
                e.target.style.borderColor = "#2563eb";
                e.target.style.boxShadow = "0 0 0 3px rgba(37, 99, 235, 0.1)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "#d1d5db";
                e.target.style.boxShadow = "none";
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim()}
              style={{
                ...styles.button,
                ...(!input.trim() ? styles.buttonDisabled : {}),
              }}
              onMouseEnter={(e) => {
                if (input.trim()) {
                  e.currentTarget.style.backgroundColor = "#1d4ed8";
                  e.currentTarget.style.transform = "scale(1.05)";
                }
              }}
              onMouseLeave={(e) => {
                if (input.trim()) {
                  e.currentTarget.style.backgroundColor = "#2563eb";
                  e.currentTarget.style.transform = "scale(1)";
                }
              }}
              onMouseDown={(e) => {
                if (input.trim())
                  e.currentTarget.style.transform = "scale(0.95)";
              }}
              onMouseUp={(e) => {
                if (input.trim())
                  e.currentTarget.style.transform = "scale(1.05)";
              }}
            >
              <Send style={{ width: "22px", height: "22px" }} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
