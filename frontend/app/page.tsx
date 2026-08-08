"use client";

import { useState } from "react";

import AgentPanel from "@/components/AgentPanel";
import ChatArea from "@/components/ChatArea";
import Header from "@/components/Header";
import InputBox from "@/components/InputBox";
import RepoPanel from "@/components/RepoPanel";
import Sidebar from "@/components/Sidebar";

import { useAgentRun } from "@/hooks/useAgentRun";
import { useChat } from "@/hooks/useChat";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { Repository } from "@/lib/types";

export default function Home() {
  const ws = useWorkspace();
  const chat = useChat(() => {
    ws.refreshConversations(ws.activeProjectId);
  });
  const agent = useAgentRun();

  const [activePanel, setActivePanel] = useState<"none" | "repo" | "agent">("none");
  const [agentMode, setAgentMode] = useState(false);
  const [attachedRepoId, setAttachedRepoId] = useState<number | null>(null);

  const attachedRepo = ws.repos.find((r) => r.id === attachedRepoId) ?? null;

  const newConversation = async () => {
    if (!ws.activeProjectId) return;
    const conversation = await ws.createConversation();
    chat.openConversation(conversation.id);
  };

  const selectConversation = (id: number) => {
    chat.openConversation(id);
  };

  const deleteConversation = async (id: number) => {
    await ws.deleteConversation(id);
    if (chat.activeConversationId === id) chat.startNewConversation();
  };

  const sendChat = (text: string, task: string) => {
    chat.send(text, task, { projectId: ws.activeProjectId, repoId: attachedRepoId });
  };

  const runAgentFromInput = (goal: string) => {
    agent.start(ws.activeProjectId, attachedRepoId, goal, "multi");
    setActivePanel("agent");
  };

  const contextLabel = ws.activeProjectId
    ? ws.projects.find((p) => p.id === ws.activeProjectId)?.name ?? "Project"
    : "No project selected";

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        projects={ws.projects}
        conversations={ws.conversations}
        activeProjectId={ws.activeProjectId}
        activeConversationId={chat.activeConversationId}
        onCreateProject={ws.createProject}
        onSelectProject={ws.selectProject}
        onCreateConversation={newConversation}
        onSelectConversation={selectConversation}
        onDeleteConversation={deleteConversation}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          activePanel={activePanel}
          setActivePanel={setActivePanel}
          provider="Gemini"
          model="gemini-2.5-flash"
          contextLabel={contextLabel}
        />

        <ChatArea messages={chat.messages} />

        <InputBox
          busy={chat.busy || agent.running}
          repoAttached={!!attachedRepoId}
          agentMode={agentMode}
          onToggleAgent={setAgentMode}
          onSend={sendChat}
          onRunAgent={runAgentFromInput}
        />
      </div>

      {activePanel === "repo" && (
        <RepoPanel
          projectId={ws.activeProjectId}
          repos={ws.repos}
          onReposChanged={() => ws.refreshRepos(ws.activeProjectId)}
          onAttachRepo={(repo: Repository | null) => setAttachedRepoId(repo?.id ?? null)}
          attachedRepoId={attachedRepoId}
        />
      )}

      {activePanel === "agent" && (
        <AgentPanel projectId={ws.activeProjectId} repoId={attachedRepoId} run={agent} />
      )}
    </div>
  );
}
