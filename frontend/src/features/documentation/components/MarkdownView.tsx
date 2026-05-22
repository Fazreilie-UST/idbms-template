import { useMemo } from "react";
import { renderMarkdown } from "./markdownParser";
import "./markdown.css";

export interface MarkdownViewProps {
  source: string;
}

/**
 * Render a markdown string as React nodes. Uses the in-repo dependency-free
 * parser in `markdownParser.tsx` so we don't have to ship `react-markdown` /
 * `remark-*` packages just for the docs page.
 */
export default function MarkdownView({ source }: MarkdownViewProps) {
  const nodes = useMemo(
    () => renderMarkdown(source || "_This page is empty._"),
    [source],
  );
  return <div className="docs-markdown">{nodes}</div>;
}
