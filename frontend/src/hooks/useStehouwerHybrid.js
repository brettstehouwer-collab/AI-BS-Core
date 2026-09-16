import { useState } from "react";

export function useStehouwerHybrid() {
  const [messages, setMessages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);

  const sendMessage = async (userPrompt) => {
    setIsGenerating(true);
    setMessages((prev) => [...prev, { role: "user", text: userPrompt }]);
    
    let assistantMessage = "";
    setMessages((prev) => [...prev, { role: "assistant", text: "" }]);

    // Dynamic backend URL fallback
    const BACKEND_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
        ? "http://localhost:8080" 
        : ""; // Use relative path in prod if hosted on same origin, or specify prod backend URL here.

    try {
        const response = await fetch(${BACKEND_URL}/api/v1/hybrid-chat/stream, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: userPrompt }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          assistantMessage += chunk;
          
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", text: assistantMessage };
            return updated;
          });
        }
    } catch (error) {
        console.error("[useStehouwerHybrid] Error streaming response:", error);
        setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = { role: "assistant", text: "Sorry, the hybrid connection failed." };
            return updated;
        });
    } finally {
        setIsGenerating(false);
    }
  };

  return { messages, sendMessage, isGenerating };
}
