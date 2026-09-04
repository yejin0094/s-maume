import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const SESSION_STORAGE_KEY = "s-maume-anonymous-session-id";


function getAnonymousSessionId() {
  const existingSessionId = sessionStorage.getItem(SESSION_STORAGE_KEY);

  if (existingSessionId) {
    return existingSessionId;
  }

  const sessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  return sessionId;
}


function App() {
  const [backendStatus, setBackendStatus] = useState("Backend 연결 확인 중");
  const [input, setInput] = useState("");
  const [agentResult, setAgentResult] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [faqQuestion, setFaqQuestion] = useState("");
  const [faqResult, setFaqResult] = useState(null);
  const [faqError, setFaqError] = useState("");
  const [isSearchingFaq, setIsSearchingFaq] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend request failed");
        }

        return response.json();
      })
      .then((data) => {
        setBackendStatus(
          data.status === "ok" ? "Backend 연결 성공" : "Backend 연결 실패",
        );
      })
      .catch(() => {
        setBackendStatus("Backend 연결 실패");
      });
  }, []);

  async function sendMessage(event) {
    event.preventDefault();
    setIsSending(true);
    setAgentResult("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "AI 채팅 요청에 실패했습니다.");
      }

      setAgentResult(data.message);
    } catch (error) {
      setAgentResult(error.message ?? "AI 채팅 요청에 실패했습니다.");
    } finally {
      setIsSending(false);
    }
  }

  async function searchFaq(event) {
    event.preventDefault();
    setIsSearchingFaq(true);
    setFaqResult(null);
    setFaqError("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/faq/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": getAnonymousSessionId(),
        },
        body: JSON.stringify({ question: faqQuestion }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "FAQ 검색에 실패했습니다.");
      }

      setFaqResult(data);
    } catch (error) {
      setFaqError(error.message ?? "FAQ 검색에 실패했습니다.");
    } finally {
      setIsSearchingFaq(false);
    }
  }

  return (
    <main>
      <p>{backendStatus}</p>

      <form onSubmit={sendMessage}>
        <label htmlFor="agent-message">AI 채팅</label>
        <div>
          <input
            id="agent-message"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="메시지를 입력하세요"
          />
          <button type="submit" disabled={isSending}>
            {isSending ? "전송 중" : "전송"}
          </button>
        </div>
      </form>

      {agentResult && <p>응답: {agentResult}</p>}

      <hr />

      <form onSubmit={searchFaq}>
        <label htmlFor="faq-question">FAQ 테스트</label>
        <div>
          <input
            id="faq-question"
            value={faqQuestion}
            onChange={(event) => setFaqQuestion(event.target.value)}
            placeholder="도서관 몇 시까지 해?"
            required
          />
          <button type="submit" disabled={isSearchingFaq}>
            {isSearchingFaq ? "검색 중" : "질문"}
          </button>
        </div>
      </form>

      {faqResult && (
        <section>
          <p>
            응답: {faqResult.found
              ? faqResult.answer
              : "FAQ에서 해당 정보를 찾지 못했습니다."}
          </p>
          <p>출처: {faqResult.source === "faq" ? "FAQ" : faqResult.source}</p>
          <p>LLM 사용: {faqResult.llm_used ? "예" : "아니오"}</p>
        </section>
      )}
      {faqError && <p>{faqError}</p>}
    </main>
  );
}


createRoot(document.getElementById("root")).render(<App />);
