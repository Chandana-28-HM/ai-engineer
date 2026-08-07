"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { PrismAsyncLight as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function Markdown({ content }: { content: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { children, className, ...rest } = props;
            const match = /language-(\w+)/.exec(className || "");
            if (match) {
              return (
                <div className="my-2 overflow-hidden rounded-lg border border-zinc-800">
                  <div className="flex items-center justify-between bg-zinc-900 px-3 py-1.5 text-[11px] text-zinc-500">
                    <span>{match[1]}</span>
                  </div>
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    customStyle={{
                      margin: 0,
                      padding: "0.75rem 1rem",
                      background: "#0b0d12",
                      fontSize: "0.8125rem",
                      lineHeight: "1.55",
                    }}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                </div>
              );
            }
            return (
              <code
                className="rounded bg-zinc-800/80 px-1.5 py-0.5 text-[0.85em] text-emerald-300"
                {...rest}
              >
                {children}
              </code>
            );
          },
          a(props) {
            return (
              <a {...props} target="_blank" rel="noreferrer" className="text-sky-400 underline">
                {props.children}
              </a>
            );
          },
          table(props) {
            return (
              <div className="my-2 overflow-x-auto">
                <table className="min-w-full border-collapse text-sm" {...props} />
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
