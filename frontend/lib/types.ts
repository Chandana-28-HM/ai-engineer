export type Role = "user" | "assistant";

export interface SearchSource {
  file_path: string;
  score: number;
  line: number;
  snippet?: string;
}

export interface Message {
  id: number;
  role: Role;
  content: string;
  intent?: string;
  sources?: SearchSource[];
  streaming?: boolean;
  error?: string;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: number;
  project_id: number | null;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Repository {
  id: number;
  project_id: number;
  name: string;
  source: string;
  remote_url: string | null;
  local_path: string;
  status: string;
  error: string | null;
  file_count: number;
  indexed_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface RepoFileNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children: RepoFileNode[];
}

export interface RepoStructure {
  summary: string;
  language_stats: Record<string, number>;
  dependency_files: string[];
  file_tree: RepoFileNode[];
}

export interface SearchResponse {
  query: string;
  results: { file_path: string; score: number; snippet: string; line: number }[];
  answered: string;
}

export interface AgentStepEvent {
  agent: string;
  title: string;
  status: "running" | "done" | "failed";
  plan?: { title: string; description: string; files: string[] }[];
  files?: string[];
  output?: string;
  approved?: boolean;
  comments?: string[];
}

export interface AgentRun {
  id: number;
  project_id: number;
  conversation_id: number | null;
  repo_id: number | null;
  kind: string;
  goal: string;
  status: string;
  summary: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AgentStep {
  id: number;
  run_id: number;
  step_index: number;
  agent: string;
  title: string;
  status: string;
  output: string;
  files_changed: string[];
}

export interface AgentRunDetail extends AgentRun {
  steps: AgentStep[];
}
