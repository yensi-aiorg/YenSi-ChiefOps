import { useState, useRef, useCallback } from "react";

/* ------------------------------------------------------------------ */
/*  useStreamingResponse – SSE / streaming fetch via ReadableStream    */
/* ------------------------------------------------------------------ */

export interface UseStreamingResponseReturn {
  /** Start a streaming request. Resolves when the stream ends. */
  startStream: (url: string, body?: unknown) => Promise<void>;
  /** Accumulated content received so far */
  content: string;
  /** Whether a stream is currently in progress */
  isStreaming: boolean;
  /** Error message if the stream failed */
  error: string | null;
  /** Cancel the in-flight stream */
  cancel: () => void;
}

export function useStreamingResponse(): UseStreamingResponseReturn {
  const [content, setContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const startStream = useCallback(
    async (url: string, body?: unknown): Promise<void> => {
      // Cancel any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setContent("");
      setError(null);
      setIsStreaming(true);

      try {
        const response = await fetch(url, {
          method: body ? "POST" : "GET",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: body ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });

        if (!response.ok) {
          const errText = await response.text().catch(() => "Stream request failed");
          throw new Error(`HTTP ${response.status}: ${errText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("Response body is not readable");
        }

        const decoder = new TextDecoder();
        let accumulated = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });

          // Parse SSE format: lines starting with "data: "
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const payload = line.slice(6); // Remove "data: " prefix

              // [DONE] sentinel signals end of stream
              if (payload.trim() === "[DONE]") {
                continue;
              }

              try {
                const parsed = JSON.parse(payload) as { content?: string; text?: string; delta?: string };
                const text = parsed.content ?? parsed.text ?? parsed.delta ?? "";
                accumulated += text;
                setContent(accumulated);
              } catch {
                // If not JSON, treat the raw payload as text content
                accumulated += payload;
                setContent(accumulated);
              }
            }
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // User cancelled – not an error
          return;
        }
        const message =
          err instanceof Error ? err.message : "Streaming failed";
        setError(message);
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [],
  );

  return { startStream, content, isStreaming, error, cancel };
}
