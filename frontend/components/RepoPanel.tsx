"use client";

import { useCallback, useEffect, useState } from "react";
import {
  UploadCloud,
  GitBranch,
  Loader2,
  FileCode2,
  Search,
  Trash2,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Database,
} from "lucide-react";
import { api, ApiError, API_BASE } from "@/lib/api";
import type {
  RepoFileNode,
  RepoStructure,
  Repository,
  SearchResponse,
} from "@/lib/types";

interface RepoPanelProps {
  projectId: number | null;
  repos: Repository[];
  onReposChanged: () => void;
  onAttachRepo: (repo: Repository | null) => void;
  attachedRepoId: number | null;
}

export default function RepoPanel({
  projectId,
  repos,
  onReposChanged,
  onAttachRepo,
  attachedRepoId,
}: RepoPanelProps) {
  const [busy, setBusy] = useState(false);
  const [gitUrl, setGitUrl] = useState("");
  const [structure, setStructure] = useState<RepoStructure | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchRes, setSearchRes] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");

  const clear = () => {
    setStructure(null);
    setSearchRes(null);
    setError("");
  };

  useEffect(() => {
    clear();
  }, [projectId]);

  const upload = async (file: File) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("project_id", String(projectId));
      form.append("name", file.name.replace(/\.zip$/i, ""));
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/repos/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) throw new ApiError(res.status, (await res.text()) || "Upload failed");
      onReposChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const connectGit = async () => {
    if (!projectId || !gitUrl.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/repos/git`, {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, url: gitUrl.trim() }),
      });
      setGitUrl("");
      onReposChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Git connect failed");
    } finally {
      setBusy(false);
    }
  };

  const indexRepo = async (id: number) => {
    setError("");
    try {
      await api(`/api/repos/${id}/index`, { method: "POST" });
      onReposChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Indexing failed");
    }
  };

  const loadStructure = async (id: number) => {
    setError("");
    try {
      const s = await api<RepoStructure>(`/api/repos/${id}/structure`);
      setStructure(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Structure failed");
    }
  };

  const runSearch = async () => {
    if (!query.trim() || !attachedRepoId) return;
    setSearching(true);
    setError("");
    try {
      const s = await api<SearchResponse>(`/api/repos/${attachedRepoId}/search`, {
        method: "POST",
        body: JSON.stringify({ repo_id: attachedRepoId, query: query.trim(), limit: 6 }),
      });
      setSearchRes(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const toggleDir = useCallback((path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const renderTree = (nodes: RepoFileNode[], depth = 0) =>
    nodes.map((node) => {
      if (node.type === "dir") {
        const isOpen = expanded.has(node.path);
        return (
          <div key={node.path || "root"}>
            <button
              onClick={() => toggleDir(node.path)}
              className="flex w-full items-center gap-1 rounded px-1.5 py-0.5 text-left text-[11px] text-zinc-400 hover:bg-zinc-800"
              style={{ paddingLeft: `${depth * 12 + 6}px` }}
            >
              {isOpen ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
              <span className="text-amber-400">📁</span> {node.name || "/"}
            </button>
            {isOpen && renderTree(node.children, depth + 1)}
          </div>
        );
      }
      return (
        <div
          key={node.path}
          className="flex items-center gap-1.5 rounded px-1.5 py-0.5 text-[11px] text-zinc-400 hover:bg-zinc-800"
          style={{ paddingLeft: `${depth * 12 + 14}px` }}
        >
          <FileCode2 size={11} className="shrink-0 text-cyan-500" />
          <span className="truncate">{node.name}</span>
        </div>
      );
    });

  return (
    <div className="flex h-full w-96 shrink-0 flex-col overflow-y-auto border-l border-zinc-800 bg-zinc-950/80">
      <div className="border-b border-zinc-800 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Database size={15} className="text-violet-400" />
          Repository
          {attachedRepoId && (
            <span className="ml-auto rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300">
              attached
            </span>
          )}
        </div>
        <p className="mt-0.5 text-[11px] text-zinc-500">
          Upload a zip or clone a git repo, index it into Qdrant, then search it semantically.
        </p>
      </div>

      <div className="space-y-3 p-4">
        {!projectId && (
          <div className="rounded-lg border border-dashed border-zinc-700 p-4 text-center text-xs text-zinc-500">
            Select or create a project to attach a repository.
          </div>
        )}

        {projectId && (
          <>
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-zinc-700 px-3 py-3 text-xs text-zinc-400 transition-colors hover:border-violet-500 hover:text-violet-300">
              <UploadCloud size={15} />
              {busy ? "Uploading…" : "Upload repository (.zip)"}
              <input
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload(f);
                  e.target.value = "";
                }}
              />
            </label>

            <div className="flex gap-1.5">
              <input
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && connectGit()}
                placeholder="https://github.com/user/repo.git"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs outline-none focus:border-cyan-500"
              />
              <button
                onClick={connectGit}
                disabled={busy || !gitUrl.trim()}
                className="flex shrink-0 items-center gap-1 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
              >
                <GitBranch size={13} /> Clone
              </button>
            </div>

            {error && (
              <div className="rounded-lg border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300">
                {error}
              </div>
            )}
          </>
        )}

        <div className="space-y-1.5">
          {repos.map((repo) => (
            <div key={repo.id} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-2.5">
              <div className="flex items-center gap-2">
                <FileCode2 size={14} className="shrink-0 text-zinc-500" />
                <span className="truncate text-xs font-medium text-zinc-200">{repo.name}</span>
                <span
                  className={`ml-auto rounded-full px-2 py-0.5 text-[9px] uppercase tracking-wide ${
                    repo.status === "indexed"
                      ? "bg-emerald-500/15 text-emerald-300"
                      : repo.status === "failed"
                        ? "bg-red-500/15 text-red-300"
                        : repo.status === "indexing"
                          ? "bg-amber-500/15 text-amber-300"
                          : "bg-zinc-700/40 text-zinc-400"
                  }`}
                >
                  {repo.status}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-1 text-[10px] text-zinc-500">
                <span>{repo.file_count} files</span>
                <span>·</span>
                <span>{repo.indexed_chunks} chunks</span>
                {repo.source === "git" && <span>· git</span>}
              </div>
              {repo.error && <div className="mt-1 text-[10px] text-red-400">{repo.error}</div>}

              <div className="mt-2 flex flex-wrap gap-1">
                <button
                  onClick={() => indexRepo(repo.id)}
                  disabled={repo.status === "indexing"}
                  className="flex items-center gap-1 rounded-lg bg-zinc-800 px-2 py-1 text-[10px] text-zinc-300 hover:bg-zinc-700 disabled:opacity-40"
                >
                  <RefreshCw size={10} /> Index
                </button>
                <button
                  onClick={() => loadStructure(repo.id)}
                  className="flex items-center gap-1 rounded-lg bg-zinc-800 px-2 py-1 text-[10px] text-zinc-300 hover:bg-zinc-700"
                >
                  <FileCode2 size={10} /> Structure
                </button>
                <button
                  onClick={() => onAttachRepo(attachedRepoId === repo.id ? null : repo)}
                  className={`rounded-lg px-2 py-1 text-[10px] ${
                    attachedRepoId === repo.id
                      ? "bg-emerald-500/20 text-emerald-300"
                      : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                  }`}
                >
                  {attachedRepoId === repo.id ? "Detach" : "Attach"}
                </button>
                <button
                  onClick={async () => {
                    await api(`/api/repos/${repo.id}`, { method: "DELETE" });
                    if (attachedRepoId === repo.id) onAttachRepo(null);
                    onReposChanged();
                  }}
                  className="ml-auto rounded-lg bg-zinc-800 p-1.5 text-zinc-500 hover:bg-red-950 hover:text-red-400"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {structure && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-1 text-[11px] font-semibold text-zinc-300">Structure</div>
            <p className="text-[11px] leading-relaxed text-zinc-400">{structure.summary}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {Object.entries(structure.language_stats)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 6)
                .map(([lang, count]) => (
                  <span key={lang} className="rounded-md bg-zinc-800 px-2 py-0.5 text-[10px] text-violet-300">
                    {lang}: {count}
                  </span>
                ))}
            </div>
            {structure.dependency_files.length > 0 && (
              <div className="mt-2">
                <div className="mb-1 text-[10px] uppercase tracking-wider text-zinc-500">Dependencies</div>
                {structure.dependency_files.map((d) => (
                  <div key={d} className="font-mono text-[10px] text-cyan-300">
                    {d}
                  </div>
                ))}
              </div>
            )}
            <div className="mt-2 max-h-64 overflow-y-auto rounded-lg bg-black/30 p-1.5">
              {renderTree(structure.file_tree)}
            </div>
          </div>
        )}

        {attachedRepoId && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="mb-2 flex gap-1.5">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runSearch()}
                placeholder="Search the codebase…"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs outline-none focus:border-violet-500"
              />
              <button
                onClick={runSearch}
                disabled={searching || !query.trim()}
                className="flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
              >
                {searching ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
              </button>
            </div>

            {searchRes && (
              <div className="space-y-1.5">
                {searchRes.answered && (
                  <p className="text-[11px] leading-relaxed text-zinc-300">{searchRes.answered}</p>
                )}
                {searchRes.results.map((r, i) => (
                  <div key={i} className="rounded-lg bg-black/30 p-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-cyan-300">
                        {r.file_path}:{r.line}
                      </span>
                      <span className="text-[9px] text-zinc-500">{(r.score * 100).toFixed(1)}%</span>
                    </div>
                    <pre className="mt-1 max-h-24 overflow-hidden whitespace-pre-wrap text-[9px] text-zinc-400">
                      {r.snippet}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
