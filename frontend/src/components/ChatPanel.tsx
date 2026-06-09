import { Send } from "lucide-react";
import { useState } from "react";
import { askCandidateQuestion } from "../api/client";

interface ChatPanelProps {
  symbol: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ChatPanel({ symbol }: ChatPanelProps) {
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend() {
    const message = input.trim();
    if (!message || loading) {
      return;
    }
    setInput("");
    setError(null);
    setLoading(true);
    setMessages((current) => [...current, { role: "user", content: message }]);
    try {
      const response = await askCandidateQuestion(symbol, message, sessionId);
      setSessionId(response.session_id);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="chat">
      <h3>Research Chat</h3>
      <div className="messages">
        {messages.length === 0 ? (
          <p className="empty-message">围绕 {symbol} 追问风险、因子贡献或机会假设。</p>
        ) : (
          messages.map((message, index) => (
            <div className={`message ${message.role}`} key={`${message.role}-${index}`}>
              {message.content}
            </div>
          ))
        )}
      </div>
      {error && <div className="chat-error">{error}</div>}
      <div className="chat-input">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void handleSend();
            }
          }}
          placeholder="例如：最大的反证是什么？"
        />
        <button onClick={handleSend} disabled={loading} title="Send question">
          <Send size={16} />
        </button>
      </div>
    </section>
  );
}
