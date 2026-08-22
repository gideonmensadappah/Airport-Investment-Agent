import type { ChatResponse } from "./analysis";

export type ChatTurn = {
  id: string;
  question: string;
  status: "pending" | "success" | "error";
  response?: ChatResponse;
  error?: string;
};

export type LocalChat = {
  id: string;
  conversationId: string | null;
  title: string;
  createdAt: string;
  updatedAt: string;
  turns: ChatTurn[];
};
