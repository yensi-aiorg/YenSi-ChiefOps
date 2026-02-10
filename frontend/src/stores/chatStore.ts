import { create } from "zustand";
import { devtools } from "zustand/middleware";
import api from "@/lib/api";
import { TurnRole } from "@/types";
import type { ConversationTurn } from "@/types";

// ---------------------------------------------------------------------------
// State & actions
// ---------------------------------------------------------------------------

interface ChatState {
  messages: ConversationTurn[];
  isStreaming: boolean;
  activeProjectId: string | null;
  error: string | null;
}

interface ChatActions {
  /**
   * Send a user message and stream the assistant response via SSE.
   * Appends the user turn immediately, then opens an EventSource to
   * `/v1/conversation/message` and incrementally builds the assistant turn.
   */
  sendMessage: (content: string, projectId?: string) => Promise<void>;

  /**
   * Fetch conversation history from the backend.
   */
  fetchHistory: (projectId?: string, skip?: number, limit?: number) => Promise<void>;

  /** Clear all messages from local state. */
  clearHistory: () => void;

  /** Set the active project context for the conversation. */
  setActiveProject: (id: string | null) => void;

  /** Clear the error state. */
  clearError: () => void;
}

type ChatStore = ChatState & ChatActions;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateTurnId(): string {
  return `turn_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Resolve the base URL used by the axios instance so we can construct
 * an absolute URL for the EventSource (SSE) connection.
 */
function resolveBaseUrl(): string {
  const base = api.defaults.baseURL ?? "/api";
  // If the baseURL is already absolute, use it as-is.
  if (base.startsWith("http://") || base.startsWith("https://")) {
    return base;
  }
  // Otherwise it is a relative path -- prefix with the current origin.
  return `${window.location.origin}${base}`;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useChatStore = create<ChatStore>()(
  devtools(
    (set, get) => ({
      // -- state --
      messages: [],
      isStreaming: false,
      activeProjectId: null,
      error: null,

      // -- actions --

      sendMessage: async (content, projectId?) => {
        const resolvedProjectId = projectId ?? get().activeProjectId;

        // 1. Append the user turn immediately for optimistic UI.
        const userTurn: ConversationTurn = {
          turn_id: generateTurnId(),
          role: TurnRole.USER,
          content,
          project_id: resolvedProjectId,
          stream_type: "coo_chat",
          timestamp: new Date().toISOString(),
          turn_number: get().messages.length + 1,
          sources_used: [],
        };

        set(
          (s) => ({
            messages: [...s.messages, userTurn],
            isStreaming: true,
            error: null,
          }),
          false,
          "sendMessage/userTurn",
        );

        // 2. Create a placeholder assistant turn that will be filled by SSE.
        const assistantTurnId = generateTurnId();
        const assistantTurn: ConversationTurn = {
          turn_id: assistantTurnId,
          role: TurnRole.ASSISTANT,
          content: "",
          project_id: resolvedProjectId,
          stream_type: "coo_chat",
          timestamp: new Date().toISOString(),
          turn_number: get().messages.length + 1,
          sources_used: [],
        };

        set(
          (s) => ({ messages: [...s.messages, assistantTurn] }),
          false,
          "sendMessage/assistantPlaceholder",
        );

        try {
          // 3. POST the message to kick off SSE streaming.
          //    The backend returns an SSE stream from this endpoint.
          const baseUrl = resolveBaseUrl();
          const params = new URLSearchParams();
          params.set("content", content);
          if (resolvedProjectId) {
            params.set("project_id", resolvedProjectId);
          }

          const eventSourceUrl = `${baseUrl}/v1/conversation/message?${params.toString()}`;

          const eventSource = new EventSource(eventSourceUrl);

          eventSource.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data as string) as {
                content?: string;
                done?: boolean;
                error?: string;
                turn_id?: string;
                sources_used?: ConversationTurn["sources_used"];
                metadata?: Record<string, unknown>;
              };

              if (data.error) {
                set(
                  { error: data.error, isStreaming: false },
                  false,
                  "sendMessage/sseError",
                );
                eventSource.close();
                return;
              }

              if (data.done) {
                // Finalise the assistant turn.
                set(
                  (s) => ({
                    isStreaming: false,
                    messages: s.messages.map((m) =>
                      m.turn_id === assistantTurnId
                        ? {
                            ...m,
                            turn_id: data.turn_id ?? m.turn_id,
                            sources_used:
                              data.sources_used ?? m.sources_used,
                          }
                        : m,
                    ),
                  }),
                  false,
                  "sendMessage/done",
                );

                // Refresh briefing if the AI updated it
                if (data.metadata?.briefing_updated && resolvedProjectId) {
                  import("@/stores/cooBriefingStore").then(({ useCooBriefingStore }) => {
                    useCooBriefingStore.getState().fetchBriefing(resolvedProjectId!);
                  });
                }

                eventSource.close();
                return;
              }

              if (data.content) {
                // Append content incrementally to the assistant turn.
                set(
                  (s) => ({
                    messages: s.messages.map((m) =>
                      m.turn_id === assistantTurnId
                        ? { ...m, content: m.content + data.content }
                        : m,
                    ),
                  }),
                  false,
                  "sendMessage/chunk",
                );
              }
            } catch {
              // If the SSE frame is not JSON, treat the whole data as content.
              set(
                (s) => ({
                  messages: s.messages.map((m) =>
                    m.turn_id === assistantTurnId
                      ? { ...m, content: m.content + (event.data as string) }
                      : m,
                  ),
                }),
                false,
                "sendMessage/rawChunk",
              );
            }
          };

          eventSource.onerror = () => {
            // EventSource fires onerror both for transient hiccups and
            // permanent failures. If we are no longer streaming, ignore.
            if (!get().isStreaming) return;

            set(
              {
                error: "Connection to the assistant was lost. Please try again.",
                isStreaming: false,
              },
              false,
              "sendMessage/sseConnectionError",
            );
            eventSource.close();
          };
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to send message";
          set(
            { error: message, isStreaming: false },
            false,
            "sendMessage/error",
          );
          throw err;
        }
      },

      fetchHistory: async (projectId?, skip = 0, limit = 50) => {
        set({ error: null }, false, "fetchHistory/start");
        try {
          const params: Record<string, string | number> = { skip, limit };
          if (projectId) params.project_id = projectId;

          const { data } = await api.get<
            ConversationTurn[] | { messages: ConversationTurn[] }
          >("/v1/conversation/history", { params });

          const messages = Array.isArray(data)
            ? data
            : (data as Record<string, unknown>).messages as ConversationTurn[] ??
              [];
          set({ messages }, false, "fetchHistory/success");
        } catch (err) {
          const message =
            err instanceof Error ? err.message : "Failed to load conversation history";
          set({ error: message }, false, "fetchHistory/error");
          throw err;
        }
      },

      clearHistory: () => {
        set({ messages: [], error: null }, false, "clearHistory");
      },

      setActiveProject: (id) => {
        set({ activeProjectId: id }, false, "setActiveProject");
      },

      clearError: () => {
        set({ error: null }, false, "clearError");
      },
    }),
    { name: "ChatStore" },
  ),
);
