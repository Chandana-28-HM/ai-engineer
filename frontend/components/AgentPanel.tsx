"use client";

import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  Loader2,
  Play,
  CheckCircle2,
  XCircle,
  ListOrdered,
  FileCheck,
} from "lucide-react";
import { streamSSE } from "@/lib/api";
import type { AgentStepEvent } from "@/lib/types";

interface AgentPanelProps {
  projectId: number | null;
  repoId: number | null;
}

const STAGES = ["planner", "coder", "reviewer", "debugger", "documenter"];
const STAGE_LABEL: Record<string, string> = {
  planner: "Planner",
  coder: "Coder",
  reviewer: "Reviewer",
  debugger: "Debugger",
  documenter: "Documenter",
};

interface StepView {
  agent: string;
  title: string;
  status: "running" | "done" | "failed";
  output?: string;
  files?: string[];
  approved?: boolean;
  comments?: string[];
}

export default function AgentPanel({ projectId, repoId }: AgentPanelProps) {
  const [goal, setGoal] = useState("");
  const [kind, setKind] = useState<"multi" | "single">("multi");
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<StepView[]>([]);
  const [toolLogs, setToolLogs] = useState<string[]>([]);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const logsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [toolLogs, steps]);

  const run = () => {
    if (!goal.trim() || !projectId || running) return;
    setRunning(true);
    setSteps([]);
    setToolLogs([]);
    setSummary("");
    setError("");

    streamSSE(
      "/api/agent/run",
      { project_id: projectId, repo_id: repoId, goal: goal.trim(), kind },
      {
        onEvent: (event, data) => {
          const d = data as Record<string, unknown>;
          if (event === "run_start") {
            setSteps([]);
          } else if (event === "step") {
            const s = d as unknown as AgentStepEvent;
            const view: StepView = {
              agent: s.agent,
              title: s.title,
              status: s.status === "done" ? "done" : s.status === "failed" ? "failed" : "running",
              output: s.output,
              files: s.files,
              approved: s.approved,
              comments: s.comments,
            };
            setSteps((prev) => {
              const idx = prev.findIndex((p) => p.title === view.title);
              if (idx === -1) return [...prev, view];
              const next = [...prev];
              next[idx] = view;
              return next;
            });
            if (s.plan) setSteps((prev) => {
              const plan = s.plan!.map((p) => ({
                agent: "coder",
                title: `Plan · ${p.title}`,
                status: "running" as const,
                output: p.description,
              }));
              return plan;
            });
          } else if (event === "agent_tool") {
            const td = d as { kind?: string; command?: string; path?: string };
            setToolLogs((prev) => [...prev, `▸ ${td.kind ?? "tool"} ${td.command ?? td.path ?? ""}`]);
          } else if (event === "agent_token") {
            const td = d as { text?: string };
            if (td.text) setToolLogs((prev) => [...prev, td.text!]);
          } else if (event === "run_done") {
            setSummary((d.summary as string) || "Agent run completed.");
            setRunning(false);
          } else if (event === "run_error" || event === "error") {
            setError((d.message as string) || "Agent run failed.");
            setRunning(false);
          }
        },
        onDone: () => setRunning(false),
        onError: (message) => {
          setError(message);
          setRunning(false);
        },
      },
    );
  };

  const activeStage =
    steps.filter((s) => s.status === "running").map((s) => s.agent)[0] ??
    steps.filter((s) => s.status === "done").map((s) => s.agent).at(-1);

  return (
    <div className="flex h-full w-96 shrink-0 flex-col overflow-y-auto border-l border-zinc-800 bg-zinc-950/80">
      <div className="border-b border-zinc-800 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Sparkles size={15} className="text-cyan-400" />
          Agent Team
        </div>
        <p className="mt-0.5 text-[11px] text-zinc-500">
          Planner → Coder → Reviewer → Debugger → Documenter. LangGraph orchestrates the loop.
        </p>
      </div>

      <div className="space-y-3 p-4">
        {!projectId && (
          <div className="rounded-lg border border-dashed border-zinc-700 p-4 text-center text-xs text-zinc-500">
            Select or create a project to run the agent team.
          </div>
        )}

        {projectId && (
          <>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && run()}
              rows={3}
              placeholder="e.g. Add a REST API endpoint with tests"
              className="w-full resize-none rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-cyan-500"
            />

            <div className="flex items-center gap-2">
              <div className="flex overflow-hidden rounded-lg border border-zinc-700 text-[11px]">
                <button
                  onClick={() => setKind("multi")}
                  className={`px-3 py-1.5 ${kind === "multi" ? "bg-cyan-500/20 text-cyan-200" : "text-zinc-400 hover:bg-zinc-800"}`}
                >
                  Multi-agent
                </button>
                <button
                  onClick={() => setKind("single")}
                  className={`px-3 py-1.5 ${kind === "single" ? "bg-cyan-500/20 text-cyan-200" : "text-zinc-400 hover:bg-zinc-800"}`}
                >
                  Single agent
                </button>
              </div>
              <span className="text-[10px] text-zinc-500">
                {repoId ? "edits attached repo" : "scratch workspace"}
              </span>
              <button
                onClick={run}
                disabled={running || !goal.trim()}
                className="ml-auto flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-violet-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-40"
              >
                {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                {running ? "Running…" : "Run agent"}
              </button>
            </div>

            {error && (
              <div className="rounded-lg border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300">
                {error}
              </div>
            )}

            {/* Stage timeline */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3">
              <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold text-zinc-300">
                <ListOrdered size={12} /> Pipeline
              </div>
              <div className="space-y-1">
                {STAGES.map((stage) => {
                  const step = steps.filter((s) => s.agent === stage).at(-1);
                  const state = running && (activeStage === stage || (step && step.status === "running"))
                    ? "active"
                    : step?.status === "done"
                      ? "done"
                      : step?.status === "failed"
                        ? "failed"
                        : running
                          ? "waiting"
                          : "idle";
                  return (
                    <div
                      key={stage}
                      className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] ${
                        state === "active"
                          ? "bg-cyan-500/10 text-cyan-200"
                          : state === "done"
                            ? "bg-emerald-500/10 text-emerald-300"
                            : state === "failed"
                              ? "bg-red-500/10 text-red-300"
                              : "text-zinc-500"
                      }`}
                    >
                      {state === "active" ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : state === "done" ? (
                        <CheckCircle2 size={12} />
                      ) : state === "failed" ? (
                        <XCircle size={12} />
                      ) : (
                        <span className="h-3 w-3 rounded-full border border-zinc-700" />
                      )}
                      <span className="font-medium">{STAGE_LABEL[stage]}</span>
                      {step?.title && (
                        <span className="truncate opacity-70">· {step.title}</span>
                      )}
                    </div>
                  );
                })}
              </div>

              {steps.length > 0 && (
                <div className="mt-2 space-y-1 border-t border-zinc-800 pt-2">
                  {steps.map((s, i) => (
                    <div key={i} className="rounded-lg bg-black/25 p-2 text-[10px] text-zinc-400">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-300">{s.title}</span>
                        {s.status === "done" && <CheckCircle2 size={11} className="text-emerald-400" />}
                      </div>
                      {s.output && <p className="mt-1 line-clamp-3 whitespace-pre-wrap">{s.output}</p>}
                      {s.files && s.files.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {s.files.map((f) => (
                            <span key={f} className="rounded bg-cyan-950/50 px-1.5 py-0.5 font-mono text-cyan-300">
                              {f}
                            </span>
                          ))}
                        </div>
                      )}
                      {s.comments && s.comments.length > 0 && (
                        <ul className="mt-1 list-disc pl-4 text-red-300">
                          {s.comments.map((c, j) => (
                            <li key={j}>{c}</li>
                          ))}
                        </ul>
                      )}
                      {typeof s.approved === "boolean" && (
                        <div className={`mt-1 ${s.approved ? "text-emerald-300" : "text-red-300"}`}>
                          {s.approved ? "✓ Approved" : "✗ Needs fixes"}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {summary && (
              <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/30 p-3">
                <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold text-emerald-300">
                  <FileCheck size={12} /> Final report
                </div>
                <p className="whitespace-pre-wrap text-[11px] leading-relaxed text-zinc-300">
                  {summary}
                </p>
                {repoId && (
                  <p className="mt-2 text-[10px] text-zinc-500">
                    Report written to <span className="font-mono text-cyan-300">AGENT_REPORT.md</span> in the repository.
                  </p>
                )}
              </div>
            )}

            {toolLogs.length > 0 && (
              <div ref={logsRef} className="max-h-48 overflow-y-auto rounded-xl border border-zinc-800 bg-black/40 p-2 font-mono text-[10px] text-zinc-500">
                {toolLogs.map((line, i) => (
                  <div key={i} className="whitespace-pre-wrap leading-relaxed">
                    {line}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
