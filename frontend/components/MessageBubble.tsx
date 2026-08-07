"use client";

import { Bot, User, FileSearch } from "lucide-react";
import type { Message } from "@/lib/types";
import Markdown from "./Markdown";

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-cyan-400 text-white">
          <Bot size={15} />
        </div>
      )}

      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "rounded-tr-sm bg-gradient-to-br from-violet-600 to-indigo-600 text-white"
            : "rounded-tl-sm border border-zinc-800 bg-zinc-900/70"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            <div
              className={`markdown-body ${message.streaming ? "streaming-caret" : ""}`}
            >
              <Markdown content={message.content || "…"} />
            </div>

            {message.intent && !message.streaming && (
              <div className="mt-2 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-zinc-500">
                <FileSearch size={11} />
                {message.intent}
              </div>
            )}

            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 border-t border-zinc-800 pt-2">
                <div className="mb-1 text-[10px] uppercase tracking-wider text-zinc-500">
                  Sources
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {message.sources.map((s, i) => (
                    <span
                      key={i}
                      className="rounded-md border border-zinc-700 bg-zinc-800/70 px-2 py-0.5 font-mono text-[10px] text-cyan-300"
                      title={`${s.file_path}:${s.line}`}
                    >
                      {s.file_path}
                      {s.line ? `:${s.line}` : ""}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {message.error && (
              <div className="mt-2 rounded-lg border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300">
                {message.error}
              </div>
            )}
          </>
        )}
      </div>

      {isUser && (
        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-zinc-800 text-zinc-300">
          <User size={15} />
        </div>
      )}
    </div>
  );
}
