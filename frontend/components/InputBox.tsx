"use client";

import { useState } from "react";
import {
  Send,
  SquarePen,
  Wrench,
  Bug,
  FileSearch,
  Bot,
  Loader2,
} from "lucide-react";

export type TaskType = "chat" | "generate" | "explain" | "fix" | "search";

interface InputBoxProps {
  busy: boolean;
  repoAttached: boolean;
  agentMode: boolean;
  onToggleAgent: (v: boolean) => void;
  onSend: (message: string, task: TaskType) => void;
  onRunAgent: (goal: string) => void;
}

const TASKS: { type: TaskType; label: string; icon: typeof SquarePen }[] = [
  { type: "generate", label: "Code", icon: SquarePen },
  { type: "explain", label: "Explain", icon: Wrench },
  { type: "fix", label: "Fix", icon: Bug },
  { type: "search", label: "Search", icon: FileSearch },
];

export default function InputBox({
  busy,
  repoAttached,
  agentMode,
  onToggleAgent,
  onSend,
  onRunAgent,
}: InputBoxProps) {
  const [message, setMessage] = useState("");
  const [task, setTask] = useState<TaskType>("chat");

  const submit = () => {
    if (!message.trim() || busy) return;
    if (agentMode) {
      onRunAgent(message.trim());
    } else {
      onSend(message.trim(), task);
    }
    setMessage("");
  };

  const pickTask = (type: TaskType) => {
    if (type === "search" && !repoAttached) return;
    setTask(type === task ? "chat" : type);
  };

  return (
    <div className="border-t border-zinc-800 bg-zinc-950/60 px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-2xl border border-zinc-700/80 bg-zinc-900/80 shadow-lg shadow-black/20 transition-colors focus-within:border-violet-500/70">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={Math.min(4, Math.max(1, message.split("\n").length))}
            placeholder={
              agentMode
                ? "Describe a goal for the agent team… e.g. Add a REST API with tests"
                : "Ask AI Engineer to generate, explain or fix code…"
            }
            className="w-full resize-none bg-transparent px-4 pt-3 text-sm text-zinc-100 placeholder-zinc-500 outline-none"
          />

          <div className="flex items-center justify-between gap-2 px-2 pb-2">
            <div className="flex flex-wrap items-center gap-1">
              <button
                onClick={() => pickTask("generate")}
                className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-colors ${
                  task === "generate"
                    ? "bg-violet-500/20 text-violet-200"
                    : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                <SquarePen size={11} /> Code
              </button>
              <button
                onClick={() => pickTask("explain")}
                className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-colors ${
                  task === "explain"
                    ? "bg-violet-500/20 text-violet-200"
                    : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                <Wrench size={11} /> Explain
              </button>
              <button
                onClick={() => pickTask("fix")}
                className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-colors ${
                  task === "fix"
                    ? "bg-violet-500/20 text-violet-200"
                    : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                <Bug size={11} /> Fix
              </button>
              <button
                onClick={() => pickTask("search")}
                disabled={!repoAttached}
                title={repoAttached ? "Search the connected repository" : "Connect a repo first"}
                className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-colors disabled:cursor-not-allowed disabled:opacity-30 ${
                  task === "search"
                    ? "bg-violet-500/20 text-violet-200"
                    : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                <FileSearch size={11} /> Search repo
              </button>

              <span className="mx-1 h-4 w-px bg-zinc-800" />

              <button
                onClick={() => onToggleAgent(!agentMode)}
                title="Run the autonomous agent team instead of chat"
                className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-colors ${
                  agentMode
                    ? "bg-cyan-500/20 text-cyan-200"
                    : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
                }`}
              >
                <Bot size={11} /> Agent mode
              </button>
            </div>

            <button
              onClick={submit}
              disabled={busy || !message.trim()}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-cyan-600 text-white transition-opacity disabled:opacity-40"
              title="Send"
            >
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>

        <p className="mt-1.5 px-1 text-center text-[10px] text-zinc-600">
          AI Engineer can make mistakes — verify important code.{" "}
          {agentMode && <span className="text-cyan-600">Agent mode edits files in the connected repository workspace.</span>}
        </p>
      </div>
    </div>
  );
}
