import { Fragment, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { AnalysisDetails } from "./components/AnalysisDetails";
import { AnalysisResults } from "./components/AnalysisResults";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { sendChatMessage } from "./services/chatApi";
import type { ChatResponse } from "./types/analysis";

const examplePrompt = "Compare congestion levels at LAX and Santa Ana airport.";

function App() {
  const [draft, setDraft] = useState(examplePrompt);
  const [questions, setQuestions] = useState<Array<string>>([]);
  const [responses, setResponse] = useState<Array<ChatResponse>>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);


  const latestAnswerRef = useRef<HTMLElement>(null);

  async function submitQuestion(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) return;

    setQuestions(prev => [...prev, trimmed]);
    setLoading(true);
    setError(null);

    try {
      const chatResponse = await sendChatMessage(trimmed, conversationId);
      setResponse(prev => [...prev, chatResponse]);
      setConversationId(chatResponse.conversation_id);
      setDraft("");
    } catch (requestError) {
      setResponse([]);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The analysis could not be completed.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(draft);
  }

  function resetConversation() {
    setDraft(examplePrompt);
    setQuestions([]);
    setResponse([]);
    setConversationId(null);
    setError(null);
  }

  useEffect(() => {
    const answer = latestAnswerRef.current;
    if (!answer || responses.length === 0) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const headerOffset = 94;
    const start = window.scrollY;
    const destination = Math.max(0, answer.getBoundingClientRect().top + start - headerOffset);

    if (reduceMotion) {
      window.scrollTo({ top: destination });
      return;
    }

    const duration = 1100;
    const startedAt = performance.now();
    let animationFrame = 0;

    const scroll = (now: number) => {
      const progress = Math.min((now - startedAt) / duration, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      window.scrollTo({ top: start + (destination - start) * easedProgress });

      if (progress < 1) animationFrame = requestAnimationFrame(scroll);
    };

    animationFrame = requestAnimationFrame(scroll);
    return () => cancelAnimationFrame(animationFrame);
  }, [responses.length]);

  return (
    <div className="workspace">
      <Sidebar onNewAnalysis={resetConversation} />

      <main>
        <Header title={responses[responses.length - 1]?.title} />

        <section className="messages" aria-label="Conversation" aria-live="polite">
          {!questions.length && (
            <section className="empty-state">
              <span className="agent-avatar message-avatar">A</span>
              <h2>Hi, let's get started</h2>
              <p>
                Ask about airport congestion or potential nonstop opportunities.

                Examples:
                • Compare LAX and SFO congestion
                • Show unmet demand from LAX
              </p>
              <button type="button" onClick={() => void submitQuestion(examplePrompt)}>
                Run the LAX vs SNA example
              </button>
            </section>
          )}



          {responses.length > 0 && (
            responses.map((response, index) => (
              <Fragment key={`${response.conversation_id}-${index}`}>
                {questions[index] && (
                  <article className="message">
                    <span className="message-avatar user-avatar">DA</span>
                    <div><p className="author">You</p><p className="user-bubble">{questions[index]}</p></div>
                  </article>
                )}

                <article
                  className="message agent-message"
                  ref={index === responses.length - 1 ? latestAnswerRef : undefined}
                >
                  <span className="message-avatar agent-avatar">A</span>
                  <div className="answer">
                    <div className="answer-head">
                      <div><p className="author">AirIntel Agent</p><small>Deterministic tool complete</small></div>
                      <span className={`confidence confidence-${response.confidence}`}>
                        <i /> {response.confidence} confidence
                      </span>
                    </div>
                    <p className="summary">{response.answer}</p>

                    <AnalysisResults response={response} />
                    <AnalysisDetails
                      assumptions={response.assumptions}
                      limitations={response.limitations}
                      sources={response.sources}
                    />
                  </div>
                </article>
              </Fragment>
            ))
          )}
        </section>

        {loading && <p className="loading-state">loading...</p>}
        {error && <p className="error-state" role="alert">{error}</p>}

        <section className="composer-area">
          <div className="suggestions">
            <button type="button" onClick={() => setDraft(examplePrompt)}>LAX vs SNA</button>
            <button type="button" onClick={() => setDraft("Compare SFO and LAX congestion.")}>SFO vs LAX</button>
            <button type="button" onClick={() => setDraft("Show unmet demand from LAX.")}>LAX unmet demand</button>
            <button type="button" onClick={() => setDraft("Rank New England airports.")}>New England ranking</button>
          </div>
          <form className="composer" onSubmit={handleSubmit}>
            <label className="sr-only" htmlFor="message">Ask for a question</label>
            <textarea
              id="message"
              rows={1}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask about airport congestion or route opportunities…"
            />
            <button type="submit" aria-label="Send message" disabled={loading}>↑</button>
          </form>
          <p>Current stage uses a bundled snapshot. Live AeroDataBox integration comes in soon.</p>
        </section>
      </main>
    </div>
  );
}

export default App;
