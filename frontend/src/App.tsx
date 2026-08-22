import { Fragment, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { AnalysisDetails } from "./components/AnalysisDetails";
import { AnalysisResults } from "./components/AnalysisResults";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { sendChatMessage } from "./services/chatApi";
import {
  createLocalChat,
  loadChatWorkspace,
  saveChatWorkspace,
  titleFromQuestion,
} from "./services/chatStorage";
import type { ChatTurn, LocalChat } from "./types/chat";

const examplePrompt = "Compare congestion levels at LAX and Santa Ana airport.";

type ChatWorkspace = {
  activeChatId: string;
  chats: LocalChat[];
};

function initialWorkspace(): ChatWorkspace {
  const savedWorkspace = loadChatWorkspace();
  const chats = savedWorkspace.chats.length > 0
    ? savedWorkspace.chats
    : [createLocalChat()];
  const hasSavedActiveChat = chats.some(chat => chat.id === savedWorkspace.activeChatId);
  return {
    activeChatId: hasSavedActiveChat ? savedWorkspace.activeChatId! : chats[0].id,
    chats,
  };
}

function App() {
  const [workspace, setWorkspace] = useState<ChatWorkspace>(initialWorkspace);
  const [draft, setDraft] = useState(examplePrompt);
  const [loading, setLoading] = useState(false);
  const latestAnswerRef = useRef<HTMLElement>(null);

  const activeChat = workspace.chats.find(chat => chat.id === workspace.activeChatId)
    ?? workspace.chats[0];
  const successfulTurns = activeChat.turns.filter(
    (turn): turn is ChatTurn & { response: NonNullable<ChatTurn["response"]> } => (
      turn.status === "success" && turn.response !== undefined
    ),
  );
  const latestResponse = successfulTurns.at(-1)?.response;

  useEffect(() => {
    saveChatWorkspace(workspace.activeChatId, workspace.chats);
  }, [workspace.activeChatId, workspace.chats]);

  async function submitQuestion(message: string) {
    const trimmed = message.trim();
    if (!trimmed || loading) return;

    const chatId = activeChat.id;
    const conversationId = activeChat.conversationId;
    const turnId = crypto.randomUUID();
    const pendingTurn: ChatTurn = {
      id: turnId,
      question: trimmed,
      status: "pending",
    };

    setWorkspace(previous => updateChat(previous, chatId, chat => ({
      ...chat,
      title: chat.turns.length === 0 ? titleFromQuestion(trimmed) : chat.title,
      updatedAt: new Date().toISOString(),
      turns: [...chat.turns, pendingTurn],
    })));
    setDraft("");
    setLoading(true);

    try {
      const response = await sendChatMessage(trimmed, conversationId);
      setWorkspace(previous => updateChat(previous, chatId, chat => ({
        ...chat,
        conversationId: response.conversation_id,
        updatedAt: new Date().toISOString(),
        turns: chat.turns.map(turn => (
          turn.id === turnId ? { ...turn, status: "success", response } : turn
        )),
      })));
    } catch (requestError) {
      const error = requestError instanceof Error
        ? requestError.message
        : "The analysis could not be completed.";
      setWorkspace(previous => updateChat(previous, chatId, chat => ({
        ...chat,
        updatedAt: new Date().toISOString(),
        turns: chat.turns.map(turn => (
          turn.id === turnId ? { ...turn, status: "error", error } : turn
        )),
      })));
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(draft);
  }

  function createNewAnalysis() {
    const chat = createLocalChat();
    setWorkspace(previous => ({
      activeChatId: chat.id,
      chats: [chat, ...previous.chats],
    }));
    setDraft(examplePrompt);
  }

  function selectChat(chatId: string) {
    setWorkspace(previous => ({ ...previous, activeChatId: chatId }));
    setDraft("");
  }

  useEffect(() => {
    const answer = latestAnswerRef.current;
    if (!answer || successfulTurns.length === 0) return;

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
  }, [activeChat.id, successfulTurns.length]);

  return (
    <div className="workspace">
      <Sidebar
        activeChatId={activeChat.id}
        chats={workspace.chats}
        onNewAnalysis={createNewAnalysis}
        onSelectChat={selectChat}
      />

      <main>
        <Header title={latestResponse?.title ?? activeChat.title} />

        <section className="messages" aria-label="Conversation" aria-live="polite">
          {activeChat.turns.length === 0 && (
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

          {activeChat.turns.map((turn, index) => (
            <Fragment key={turn.id}>
              <article className="message">
                <span className="message-avatar user-avatar">DA</span>
                <div><p className="author">You</p><p className="user-bubble">{turn.question}</p></div>
              </article>

              {turn.status === "success" && turn.response && (
                <article
                  className="message agent-message"
                  ref={index === activeChat.turns.length - 1 ? latestAnswerRef : undefined}
                >
                  <span className="message-avatar agent-avatar">A</span>
                  <div className="answer">
                    <div className="answer-head">
                      <div><p className="author">AirIntel Agent</p><small>AI-orchestrated · deterministic analysis</small></div>
                      <span className={`confidence confidence-${turn.response.confidence}`}>
                        <i /> {turn.response.confidence} confidence
                      </span>
                    </div>
                    <p className="summary">{turn.response.answer}</p>

                    <AnalysisResults response={turn.response} />
                    <AnalysisDetails
                      assumptions={turn.response.assumptions}
                      limitations={turn.response.limitations}
                      sources={turn.response.sources}
                    />
                  </div>
                </article>
              )}

              {turn.status === "error" && (
                <article className="message agent-message">
                  <span className="message-avatar agent-avatar">A</span>
                  <div className="turn-error" role="alert">
                    <p className="author">AirIntel Agent</p>
                    <p>{turn.error}</p>
                  </div>
                </article>
              )}
            </Fragment>
          ))}
        </section>

        {loading && (
          <p className="loading-state">
            Analyzing… The free API may take up to a minute to wake up.
          </p>
        )}

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
          <p>AI selects typed tools; scores come from deterministic aviation data analysis.</p>
        </section>
      </main>
    </div>
  );
}

function updateChat(
  workspace: ChatWorkspace,
  chatId: string,
  update: (chat: LocalChat) => LocalChat,
): ChatWorkspace {
  const chat = workspace.chats.find(item => item.id === chatId);
  if (!chat) return workspace;

  const updatedChat = update(chat);
  return {
    ...workspace,
    chats: [updatedChat, ...workspace.chats.filter(item => item.id !== chatId)],
  };
}

export default App;
