import { isChatResponse } from "../types/analysis";
import type { ChatResponse } from "../types/analysis";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = 75_000;

export async function sendChatMessage(
  message: string,
  conversationId: string | null,
): Promise<ChatResponse> {
  let response: Response;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        "The free analysis service took too long to wake up. Please try again.",
      );
    }
    if (error instanceof TypeError) {
      throw new Error(
        "The analysis service is unavailable. Please wait a moment and try again.",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    const detail = isErrorPayload(payload) ? payload.detail : null;
    throw new Error(
      detail
      ?? `The analysis service returned an error (${response.status}).`,
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
