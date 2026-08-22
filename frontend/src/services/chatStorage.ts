import { isChatResponse } from "../types/analysis";
import type { ChatTurn, LocalChat } from "../types/chat";

const storageKey = "airport-investment-agent.chats";
const storageVersion = 1;

type StoredChats = {
  version: typeof storageVersion;
  activeChatId?: string;
  chats: LocalChat[];
};

export type StoredChatWorkspace = {
  activeChatId: string | null;
  chats: LocalChat[];
};

export function createLocalChat(): LocalChat {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    conversationId: null,
    title: "New analysis",
    createdAt: now,
    updatedAt: now,
    turns: [],
  };
}

export function loadChatWorkspace(): StoredChatWorkspace {
  try {
    const stored = localStorage.getItem(storageKey);
    if (!stored) return { activeChatId: null, chats: [] };

    const value = JSON.parse(stored) as unknown;
    if (!isStoredChats(value)) return { activeChatId: null, chats: [] };

    const chats = value.chats
      .filter(chat => chat.turns.length > 0)
      .map(chat => ({
        ...chat,
        turns: chat.turns.map(turn => (
          turn.status === "pending"
            ? {
                ...turn,
                status: "error" as const,
                error: "This analysis was interrupted. Please send it again.",
              }
            : turn
        )),
      }));
    const activeChatId = typeof value.activeChatId === "string"
      && chats.some(chat => chat.id === value.activeChatId)
      ? value.activeChatId
      : null;

    return { activeChatId, chats };
  } catch {
    return { activeChatId: null, chats: [] };
  }
}

export function saveChatWorkspace(activeChatId: string, chats: LocalChat[]): void {
  try {
    const startedChats = chats.filter(chat => chat.turns.length > 0);
    const value: StoredChats = {
      version: storageVersion,
      chats: startedChats,
      ...(startedChats.some(chat => chat.id === activeChatId) ? { activeChatId } : {}),
    };
    localStorage.setItem(storageKey, JSON.stringify(value));
  } catch {
    // The in-memory workspace remains usable when browser storage is unavailable.
  }
}

export function titleFromQuestion(question: string): string {
  const compact = question.replace(/\s+/g, " ").trim();
  return compact.length > 44 ? `${compact.slice(0, 41)}…` : compact;
}

function isStoredChats(value: unknown): value is StoredChats {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;
  return candidate.version === storageVersion
    && Array.isArray(candidate.chats)
    && candidate.chats.every(isLocalChat);
}

function isLocalChat(value: unknown): value is LocalChat {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;
  return typeof candidate.id === "string"
    && (candidate.conversationId === null || typeof candidate.conversationId === "string")
    && typeof candidate.title === "string"
    && typeof candidate.createdAt === "string"
    && typeof candidate.updatedAt === "string"
    && Array.isArray(candidate.turns)
    && candidate.turns.every(isChatTurn);
}

function isChatTurn(value: unknown): value is ChatTurn {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;
  if (
    typeof candidate.id !== "string"
    || typeof candidate.question !== "string"
    || !["pending", "success", "error"].includes(String(candidate.status))
  ) {
    return false;
  }

  if (candidate.status === "success") return isChatResponse(candidate.response);
  if (candidate.status === "error") return typeof candidate.error === "string";
  return true;
}
