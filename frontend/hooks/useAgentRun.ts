"use client";

import { useCallback, useRef, useState } from "react";
import { streamSSE } from "@/lib/api";
import type { AgentStepEvent } from "@/lib/types";

export interface StepView {
  agent: string;
  title: string;
  status: "running" | "done" | "failed";
  output?: string;
  files?: string[];
  approved?: boolean;
  comments?: string[];
}

export interface AgentRun {
  running: boolean;
  steps: StepView[];
  toolLogs: string[];
  summary: string;
  error: string;
  activeStage: string | undefined;
  start: (projectId: number | null, repoId: number | null, goal: string, kind: "multi" | "single") => void;
}

export const AGENT_STAGES = ["planner", "coder", "reviewer", "debugger", "documenter"];

export function useAgentRun(): AgentRun {
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<StepView[]>([]);
  const [toolLogs, setToolLogs] = useState<string[]>([]);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const runningRef = useRef(false);

  const start = useCallback(
    (projectId: number | null, repoId: number | null, goal: string, kind: "multi" | "single") => {
      if (!goal.trim() || !projectId || runningRef.current) return;
      runningRef.current = true;
      setRunning(true);
      setSteps([]);
      setToolLogs([]);
      setSummary("");
      setError("");

      const upsert = (view: StepView) =>
        setSteps((prev) => {
          const idx = prev.findIndex((s) => s.title === view.title);
          if (idx === -1) return [...prev, view];
          const next = [...prev];
          next[idx] = view;
          return next;
        });

      streamSSE(
        "/api/agent/run",
        { project_id: projectId, repo_id: repoId, goal: goal.trim(), kind },
        {
          onEvent: (event, data) => {
            const d = data as Record<string, unknown>;
            if (event === "step") {
              const s = d as unknown as AgentStepEvent;
              if (s.plan) {
                const plan = s.plan.map((p) => ({
                  agent: "coder" as const,
                  title: `Plan · ${p.title}`,
                  status: "running" as const,
                  output: p.description,
                }));
                setSteps(plan);
              }
              upsert({
                agent: s.agent,
                title: s.title,
                status: s.status === "done" ? "done" : s.status === "failed" ? "failed" : "running",
                output: s.output,
                files: s.files,
                approved: s.approved,
                comments: s.comments,
              });
            } else if (event === "agent_tool") {
              const td = d as { kind?: string; command?: string; path?: string };
              setToolLogs((prev) => [...prev, `▸ ${td.kind ?? "tool"} ${td.command ?? td.path ?? ""}`]);
            } else if (event === "agent_token") {
              const td = d as { text?: string };
              if (td.text) setToolLogs((prev) => [...prev, td.text as string]);
            } else if (event === "run_done") {
              setSummary((d.summary as string) || "Agent run completed.");
              setRunning(false);
              runningRef.current = false;
            } else if (event === "run_error" || event === "error") {
              setError((d.message as string) || "Agent run failed.");
              setRunning(false);
              runningRef.current = false;
            }
          },
          onDone: () => {
            setRunning(false);
            runningRef.current = false;
          },
          onError: (message) => {
            setError(message);
            setRunning(false);
            runningRef.current = false;
          },
        },
      );
    },
    [],
  );

  const activeStage =
    steps.filter((s) => s.status === "running").map((s) => s.agent)[0] ??
    steps.filter((s) => s.status === "done").map((s) => s.agent).at(-1);

  return { running, steps, toolLogs, summary, error, activeStage, start };
}
