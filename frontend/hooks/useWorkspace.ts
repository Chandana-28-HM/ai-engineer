"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Conversation, Project, Repository } from "@/lib/types";

export interface Workspace {
  projects: Project[];
  conversations: Conversation[];
  repos: Repository[];
  activeProjectId: number | null;
  refreshProjects: () => Promise<void>;
  refreshConversations: (projectId: number | null) => Promise<void>;
  refreshRepos: (projectId: number | null) => Promise<void>;
  createProject: (name: string) => Promise<Project>;
  selectProject: (id: number) => void;
  createConversation: () => Promise<Conversation>;
  deleteConversation: (id: number) => Promise<void>;
}

export function useWorkspace(): Workspace {
  const [projects, setProjects] = useState<Project[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);

  const refreshProjects = useCallback(async () => {
    setProjects(await api<Project[]>("/api/projects"));
  }, []);

  const refreshConversations = useCallback(async (projectId: number | null) => {
    if (!projectId) {
      setConversations([]);
      return;
    }
    setConversations(await api<Conversation[]>(`/api/conversations?project_id=${projectId}`));
  }, []);

  const refreshRepos = useCallback(async (projectId: number | null) => {
    if (!projectId) {
      setRepos([]);
      return;
    }
    setRepos(await api<Repository[]>(`/api/repos?project_id=${projectId}`));
  }, []);

  useEffect(() => {
    refreshProjects().catch(() => {});
  }, [refreshProjects]);

  useEffect(() => {
    refreshConversations(activeProjectId).catch(() => {});
    refreshRepos(activeProjectId).catch(() => {});
  }, [activeProjectId, refreshConversations, refreshRepos]);

  const createProject = async (name: string) => {
    const project = await api<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    setProjects((prev) => [project, ...prev]);
    setActiveProjectId(project.id);
    return project;
  };

  const selectProject = (id: number) => setActiveProjectId(id);

  const createConversation = async () => {
    if (!activeProjectId) throw new Error("Select a project first");
    const conversation = await api<Conversation>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({ project_id: activeProjectId, title: "New chat" }),
    });
    setConversations((prev) => [conversation, ...prev]);
    return conversation;
  };

  const deleteConversation = async (id: number) => {
    await api(`/api/conversations/${id}`, { method: "DELETE" });
    setConversations((prev) => prev.filter((c) => c.id !== id));
  };

  return {
    projects,
    conversations,
    repos,
    activeProjectId,
    refreshProjects,
    refreshConversations,
    refreshRepos,
    createProject,
    selectProject,
    createConversation,
    deleteConversation,
  };
}
