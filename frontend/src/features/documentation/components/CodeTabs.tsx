import React, { useState } from "react";

export interface CodeBlock {
  language: string;
  content: string;
}

export interface CodeTabsProps {
  blocks: CodeBlock[];
}

const LANG_LABELS: Record<string, string> = {
  python: "Python",
  js: "JavaScript",
  javascript: "JavaScript",
  ts: "TypeScript",
  typescript: "TypeScript",
  java: "Java",
  csharp: "C#",
  cs: "C#",
  cpp: "C++",
  c: "C",
};

function getLabel(lang: string) {
  return LANG_LABELS[lang.toLowerCase()] || lang || "Code";
}

export default function CodeTabs({ blocks }: CodeTabsProps) {
  const [active, setActive] = useState(0);
  if (!blocks.length) return null;
  return (
    <div className="code-tabs-wrapper">
      <div className="code-tab-bar">
        {blocks.map((b, i) => (
          <button
            key={b.language + i}
            className={"code-tab" + (i === active ? " active" : "")}
            onClick={() => setActive(i)}
            type="button"
          >
            {getLabel(b.language)}
          </button>
        ))}
      </div>
      <div className="code-tab-panel">
        <pre>
          <code className={blocks[active].language ? `language-${blocks[active].language}` : undefined}>
            {blocks[active].content}
          </code>
        </pre>
      </div>
    </div>
  );
}
