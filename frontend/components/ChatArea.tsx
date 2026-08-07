"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/lib/types";
import MessageBubble from "./MessageBubble";

interface ChatAreaProps {
  messages: Message[];
}

export default function ChatArea({ messages }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
        {messages.length === 0 && (
          <div className="app-grid-bg mt-10 rounded-2xl border border-zinc-800/70 p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-cyan-400 text-white">
              <span className="text-xl font-black">⌬</span>
            </div>
            <h2 className="text-lg font-bold">
              AI <span className="gradient-text">Engineer</span>
            </h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-zinc-400">
              Your autonomous software engineering teammate. Generate code, explain
              codebases, fix bugs, search a connected repository, or hand it a goal and
              watch the agent team plan, code, review, and document.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
