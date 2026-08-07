"use client";

import { FileCode2, Sparkles, Cpu } from "lucide-react";

interface HeaderProps {
  activePanel: "none" | "repo" | "agent";
  setActivePanel: (panel: "none" | "repo" | "agent") => void;
  provider: string;
  model: string;
  contextLabel: string;
}

export default function Header({
  activePanel,
  setActivePanel,
  provider,
  model,
  contextLabel,
}: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-950/60 px-4 py-2.5 backdrop-blur">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm font-medium text-zinc-300 truncate">{contextLabel}</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="hidden items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-[11px] text-zinc-400 sm:flex">
          <Sparkles size={11} className="text-violet-400" />
          {provider}
          <span className="text-zinc-600">·</span>
          <Cpu size={11} className="text-cyan-400" />
          {model}
        </span>

        <button
          onClick={() => setActivePanel(activePanel === "repo" ? "none" : "repo")}
          className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors ${
            activePanel === "repo"
              ? "border-violet-500 bg-violet-500/15 text-violet-200"
              : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <FileCode2 size={14} />
          Repo
        </button>

        <button
          onClick={() => setActivePanel(activePanel === "agent" ? "none" : "agent")}
          className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors ${
            activePanel === "agent"
              ? "border-cyan-500 bg-cyan-500/15 text-cyan-200"
              : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <Sparkles size={14} />
          Agent
        </button>
      </div>
    </header>
  );
}
