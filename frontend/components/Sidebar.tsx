"use client";

import { useState } from "react";
import { MessageSquarePlus, Plus, Trash2, FolderGit2, Bot } from "lucide-react";
import type { Conversation, Project } from "@/lib/types";

interface SidebarProps {
  projects: Project[];
  conversations: Conversation[];
  activeProjectId: number | null;
  activeConversationId: number | null;
  onCreateProject: (name: string) => void;
  onSelectProject: (id: number) => void;
  onCreateConversation: () => void;
  onSelectConversation: (id: number) => void;
  onDeleteConversation: (id: number) => void;
}

export default function Sidebar({
  projects,
  conversations,
  activeProjectId,
  activeConversationId,
  onCreateProject,
  onSelectProject,
  onCreateConversation,
  onSelectConversation,
  onDeleteConversation,
}: SidebarProps) {
  const [showNewProject, setShowNewProject] = useState(false);
  const [projectName, setProjectName] = useState("");

  const submitProject = () => {
    if (!projectName.trim()) return;
    onCreateProject(projectName.trim());
    setProjectName("");
    setShowNewProject(false);
  };

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950/80">
      <div className="flex items-center gap-2 border-b border-zinc-800 px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-cyan-400 text-white">
          <Bot size={18} />
        </div>
        <div>
          <div className="text-sm font-bold leading-none tracking-tight">
            AI <span className="gradient-text">Engineer</span>
          </div>
          <div className="mt-0.5 text-[10px] text-zinc-500">Autonomous dev assistant</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {projects.length === 0 && (
          <div className="mt-6 px-2 text-center text-xs text-zinc-500">
            Create a project to store conversations,
            <br />
            repositories and agent runs.
          </div>
        )}

        {projects.map((project) => (
          <div key={project.id} className="mb-1">
            <button
              onClick={() => onSelectProject(project.id)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                activeProjectId === project.id
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-300 hover:bg-zinc-900"
              }`}
            >
              <FolderGit2 size={15} className="shrink-0 text-zinc-500" />
              <span className="truncate">{project.name}</span>
            </button>

            {activeProjectId === project.id && (
              <div className="ml-4 mt-1 space-y-0.5 border-l border-zinc-800 pl-2">
                {conversations.map((c) => (
                  <div
                    key={c.id}
                    className={`group flex items-center gap-1 rounded-md px-2 py-1 text-xs ${
                      activeConversationId === c.id
                        ? "bg-zinc-800/80 text-white"
                        : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                    }`}
                  >
                    <button
                      onClick={() => onSelectConversation(c.id)}
                      className="flex-1 truncate text-left"
                      title={c.title}
                    >
                      <MessageSquarePlus size={11} className="mr-1.5 inline opacity-60" />
                      {c.title}
                    </button>
                    <button
                      onClick={() => onDeleteConversation(c.id)}
                      className="hidden rounded p-1 text-zinc-500 hover:text-red-400 group-hover:block"
                      title="Delete conversation"
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="space-y-2 border-t border-zinc-800 p-3">
        {showNewProject ? (
          <div className="flex gap-1">
            <input
              autoFocus
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitProject()}
              onBlur={() => setTimeout(() => setShowNewProject(false), 200)}
              placeholder="Project name"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs outline-none focus:border-violet-500"
            />
          </div>
        ) : (
          <button
            onClick={() => setShowNewProject(true)}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-zinc-700 px-3 py-2 text-xs text-zinc-400 hover:border-violet-500 hover:text-violet-300"
          >
            <Plus size={14} /> New Project
          </button>
        )}
        <button
          onClick={onCreateConversation}
          disabled={!activeProjectId}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-cyan-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
        >
          <MessageSquarePlus size={14} /> New Chat
        </button>
      </div>
    </aside>
  );
}
