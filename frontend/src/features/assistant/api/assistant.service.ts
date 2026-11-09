import type {
  ActionConfirmOverrides,
  AssistantAction,
  AssistantActivityItem,
  AssistantConversation,
  AssistantConversationSummary,
  AssistantDigest,
  AssistantTurnResponse,
  Paginated,
} from "@/features/assistant/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/assistant";
const ASSISTANT_TURN_TIMEOUT_MS = 110_000;

export class AssistantService {
  static async listConversations(): Promise<Paginated<AssistantConversationSummary>> {
    const response = await api.get<Paginated<AssistantConversationSummary>>(
      `${ROOT}/conversations/`,
    );
    return response.data;
  }

  static async getConversation(id: number): Promise<AssistantConversation> {
    const response = await api.get<AssistantConversation>(`${ROOT}/conversations/${id}/`);
    return response.data;
  }

  static async deleteConversation(id: number): Promise<void> {
    await api.delete(`${ROOT}/conversations/${id}/`);
  }

  static async createConversation(): Promise<AssistantConversation> {
    const response = await api.post<AssistantConversation>(`${ROOT}/conversations/`, {});
    return response.data;
  }

  static async sendMessage(
    message: string,
    conversationId?: number,
  ): Promise<AssistantTurnResponse> {
    // A turn can chain several model calls (each takes seconds), so it gets a longer limit than
    // the 30s default. Kept under the server's 120s worker timeout so the server never kills it first.
    const response = await api.post<AssistantTurnResponse>(
      `${ROOT}/messages/`,
      { message, conversation_id: conversationId },
      { timeout: ASSISTANT_TURN_TIMEOUT_MS },
    );
    return response.data;
  }

  static async listActions(status?: string): Promise<Paginated<AssistantAction>> {
    const response = await api.get<Paginated<AssistantAction>>(`${ROOT}/actions/`, {
      params: { status },
    });
    return response.data;
  }

  static async confirmAction(
    id: number,
    overrides: ActionConfirmOverrides = {},
  ): Promise<AssistantAction> {
    const response = await api.post<AssistantAction>(`${ROOT}/actions/${id}/confirm/`, overrides);
    return response.data;
  }

  static async rejectAction(id: number): Promise<AssistantAction> {
    const response = await api.post<AssistantAction>(`${ROOT}/actions/${id}/reject/`, {});
    return response.data;
  }

  static async getDigest(): Promise<AssistantDigest> {
    const response = await api.get<AssistantDigest>(`${ROOT}/digest/`);
    return response.data;
  }

  static async listActivity(): Promise<Paginated<AssistantActivityItem>> {
    const response = await api.get<Paginated<AssistantActivityItem>>(`${ROOT}/activity/`);
    return response.data;
  }
}
