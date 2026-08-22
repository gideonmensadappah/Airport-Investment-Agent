import { isChatResponse } from "../types/analysis";
import type { ChatResponse } from "../types/analysis";

export async function sendChatMessage(
  message: string,
  conversationId: string | null,
): Promise<ChatResponse> {
  let response: Response;

  try {
    response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "The analysis service is unavailable. "
        + "Start the backend on port 8000 and try again.",
      );
    }
    throw error;
  }

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    const detail = isErrorPayload(payload) ? payload.detail : null;
    throw new Error(
      detail
      ?? `Backend unavailable (${response.status}). Start the FastAPI server on port 8000.`,
    );
  }
  if (!isChatResponse(payload)) {
    throw new Error("The backend returned an empty or invalid response.");
  }

  return payload;
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  const responseText = await response.text();
  if (!responseText) return null;

  try {
    return JSON.parse(responseText) as unknown;
  } catch {
    return null;
  }
}

function isErrorPayload(value: unknown): value is { detail: string } {
  return typeof value === "object"
    && value !== null
    && "detail" in value
    && typeof value.detail === "string";
}
