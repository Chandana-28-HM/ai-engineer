"use client";

import { useCallback, useRef, useState } from "react";
import { api, streamSSE } from "@/lib/api";
import type { Message, SearchSource } from "@/lib/types";

type ChatContext = {
  projectId: number | null;
  repoId: number | null;
};

export interface Chat {
  messages: Message[];
  activeConversationId: number | null;
  busy: boolean;
  openConversation: (id: number) => Promise<void>;
  startNewConversation: () => void;
  send: (text: string, task: string, ctx: ChatContext) => void;
}

function toMessage(
  raw: { id: number; role: string; content: string; sources: string | null },
): Message {
  let sources: SearchSource[] | undefined;
  if (raw.sources) {
    try {
      sources = JSON.parse(raw.sources);
    } catch {
      sources = undefined;
    }
  }
  return { id: raw.id, role: raw.role as Message["role"], content: raw.content, sources };
}

export function useChat(onConversationCreated?: (id: number) => void): Chat {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const counter = useRef(1);

  const nextId = () => counter.current++;

  const openConversation = useCallback(async (id: number) => {
    const history = await api<
      { id: number; role: string; content: string; sources: string | null }[]
    >(`/api/conversations/${id}/messages`);
    counter.current = Math.max(1, ...history.map((h) => h.id)) + 1;
    setMessages(history.map(toMessage));
    setActiveConversationId(id);
  }, []);

  const startNewConversation = useCallback(() => {
    counter.current = 1;
    setMessages([]);
    setActiveConversationId(null);
  }, []);

  const send = useCallback(
    (text: string, task: string, ctx: ChatContext) => {
      const user: Message = { id: nextId(), role: "user", content: text };
      const assistant: Message = {
        id: nextId(),
        role: "assistant",
        content: "",
        streaming: true,
      };
      setMessages((prev) => [...prev, user, assistant]);
      setBusy(true);

      const path = task === "chat" ? "/api/chat" : "/api/code/task";
      const payload = {
        conversation_id: activeConversationId,
        project_id: ctx.projectId,
        repo_id: ctx.repoId,
        message: text,
        ...(task !== "chat" ? { task_type: task } : {}),
      };

      const patch = (patch: Partial<Message>) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistant.id ? { ...m, ...patch } : m)),
        );

      let accumulated = "";
      const finish = (extra: Partial<Message>) => {
        patch({ content: accumulated, ...extra, streaming: false });
        setBusy(false);
      };

      streamSSE(path, payload, {
        onEvent: (event, data) => {
          const d = data as Record<string, unknown>;
          if (event === "intent") {
            const conversationId = d.conversation_id as number | undefined;
            if (conversationId && conversationId !== activeConversationId) {
              setActiveConversationId(conversationId);
              onConversationCreated?.(conversationId);
            }
            patch({ intent: d.intent as string });
          } else if (event === "sources") {
            patch({ sources: (d.sources as SearchSource[]) ?? [] });
          } else if (event === "token") {
            accumulated += String(d.text ?? "");
            patch({ content: accumulated });
          } else if (event === "done") {
            finish({});
          } else if (event === "error") {
            finish({ error: (d.message as string) || "The model returned an error." });
          }
        },
        onDone: () => setBusy(false),
        onError: (message) => finish({ error: message }),
      });
    },
    [activeConversationId, onConversationCreated],
  );

  return { messages, activeConversationId, busy, openConversation, startNewConversation, send };
}
