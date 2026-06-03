/**
 * Minimal, dependency-free markdown → React renderer.
 *
 * Supports the subset that's actually useful inside in-app documentation:
 *   - ATX headings (`# … ######`)
 *   - paragraphs
 *   - fenced code blocks (``` … ```)
 *   - blockquotes (`> …`, single line per block)
 *   - unordered (`-`, `*`, `+`) and ordered (`1.`) lists, flat
 *   - GFM-style pipe tables
 *   - horizontal rules (`---`, `***`, `___`)
 *   - inline: **bold**, *italic*, `code`, [text](url), ![alt](url)
 *
 * Everything is rendered through React (no `dangerouslySetInnerHTML`) so any
 * stray `<script>` or HTML in the markdown is treated as plain text — safe by
 * construction even for admin-authored content.
 */

import type { ReactNode } from "react";
import { resolveBackendUrl } from "@/config";

// ---------------------------------------------------------------------------
// Inline parsing
// ---------------------------------------------------------------------------

function resolveImageSrc(src: string): string {
  if (src.startsWith("/static/")) {
    return resolveBackendUrl(src) ?? src;
  }
  return src;
}

/**
 * Parse the alt text for trailing Word-style alignment / sizing hints so
 * documentation authors can flow images alongside text the way they would in
 * a word processor. Examples:
 *
 *   ![Screenshot](…)                 → inline, default size
 *   ![Screenshot|left](…)            → floats left, text wraps to the right
 *   ![Screenshot|right:280](…)       → floats right, 280px wide
 *   ![Screenshot|center:60%](…)      → centered block, 60% of column width
 *   ![Screenshot|block](…)           → full-width block (no float, no center)
 */
type ImageHint = {
  alt: string;
  className: string;
  width?: string;
};

function parseImageHint(rawAlt: string): ImageHint {
  const pipe = rawAlt.indexOf("|");
  if (pipe === -1) {
    return { alt: rawAlt, className: "md-img" };
  }
  const alt = rawAlt.slice(0, pipe).trim();
  const directive = rawAlt.slice(pipe + 1).trim().toLowerCase();
  const [posRaw, sizeRaw] = directive.split(":");
  const pos = (posRaw || "").trim();
  const size = (sizeRaw || "").trim();

  const classes = ["md-img"];
  switch (pos) {
    case "left":
      classes.push("md-img--left");
      break;
    case "right":
      classes.push("md-img--right");
      break;
    case "center":
      classes.push("md-img--center");
      break;
    case "block":
      classes.push("md-img--block");
      break;
    default:
      // Unknown directive — fall back to default inline behaviour.
      break;
  }

  let width: string | undefined;
  if (size) {
    width = /^\d+$/.test(size) ? `${size}px` : size;
  }

  return { alt: alt || rawAlt, className: classes.join(" "), width };
}

/**
 * Parse a single line of markdown to an array of React nodes. Handled in a
 * single left-to-right scan so the ordering of constructs (e.g. links nested
 * inside bold) stays predictable.
 */
function parseInline(text: string, keyPrefix: string): ReactNode[] {
  const out: ReactNode[] = [];
  let buf = "";
  let i = 0;
  let counter = 0;

  const flush = () => {
    if (buf) {
      out.push(buf);
      buf = "";
    }
  };
  const push = (node: ReactNode) => {
    flush();
    out.push(node);
  };
  const k = () => `${keyPrefix}-${counter++}`;

  while (i < text.length) {
    const ch = text[i];

    // Escape: \X -> literal X
    if (ch === "\\" && i + 1 < text.length) {
      buf += text[i + 1];
      i += 2;
      continue;
    }

    // Inline code: `…` (no embedded backticks)
    if (ch === "`") {
      const end = text.indexOf("`", i + 1);
      if (end > i) {
        push(<code key={k()} className="md-inline-code">{text.slice(i + 1, end)}</code>);
        i = end + 1;
        continue;
      }
    }

    // Image: ![alt](url) — alt may carry a trailing |position[:size] hint.
    if (ch === "!" && text[i + 1] === "[") {
      const closeBracket = text.indexOf("]", i + 2);
      if (closeBracket > 0 && text[closeBracket + 1] === "(") {
        const closeParen = text.indexOf(")", closeBracket + 2);
        if (closeParen > 0) {
          const rawAlt = text.slice(i + 2, closeBracket);
          const src = text.slice(closeBracket + 2, closeParen);
          const hint = parseImageHint(rawAlt);
          push(
            <img
              key={k()}
              src={resolveImageSrc(src)}
              alt={hint.alt}
              className={hint.className}
              style={hint.width ? { width: hint.width } : undefined}
            />,
          );
          i = closeParen + 1;
          continue;
        }
      }
    }

    // Link: [text](url)
    if (ch === "[") {
      const closeBracket = text.indexOf("]", i + 1);
      if (closeBracket > 0 && text[closeBracket + 1] === "(") {
        const closeParen = text.indexOf(")", closeBracket + 2);
        if (closeParen > 0) {
          const label = text.slice(i + 1, closeBracket);
          const href = text.slice(closeBracket + 2, closeParen);
          const external = /^https?:\/\//i.test(href);
          push(
            <a
              key={k()}
              href={href}
              target={external ? "_blank" : undefined}
              rel={external ? "noopener noreferrer" : undefined}
            >
              {parseInline(label, `${keyPrefix}-l${counter}`)}
            </a>,
          );
          i = closeParen + 1;
          continue;
        }
      }
    }

    // Bold: **text**
    if (ch === "*" && text[i + 1] === "*") {
      const end = text.indexOf("**", i + 2);
      if (end > i + 1) {
        push(
          <strong key={k()}>
            {parseInline(text.slice(i + 2, end), `${keyPrefix}-b${counter}`)}
          </strong>,
        );
        i = end + 2;
        continue;
      }
    }

    // Italic: *text* or _text_
    if ((ch === "*" || ch === "_") && text[i + 1] !== ch) {
      const end = text.indexOf(ch, i + 1);
      if (end > i && text[end - 1] !== " ") {
        push(
          <em key={k()}>
            {parseInline(text.slice(i + 1, end), `${keyPrefix}-i${counter}`)}
          </em>,
        );
        i = end + 1;
        continue;
      }
    }

    buf += ch;
    i += 1;
  }
  flush();
  return out;
}

// ---------------------------------------------------------------------------
// Block parsing
// ---------------------------------------------------------------------------

interface CodeBlock {
  type: "code";
  language: string;
  content: string;
}
interface HeadingBlock {
  type: "heading";
  level: 1 | 2 | 3 | 4 | 5 | 6;
  text: string;
}
interface ParagraphBlock {
  type: "paragraph";
  text: string;
}
interface QuoteBlock {
  type: "quote";
  text: string;
}
interface ListBlock {
  type: "list";
  ordered: boolean;
  items: string[];
}
interface TableBlock {
  type: "table";
  header: string[];
  rows: string[][];
}
interface HrBlock {
  type: "hr";
}

type Block =
  | CodeBlock
  | HeadingBlock
  | ParagraphBlock
  | QuoteBlock
  | ListBlock
  | TableBlock
  | HrBlock;

const HR_RE = /^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$/;
const HEADING_RE = /^(#{1,6})\s+(.*)$/;
const QUOTE_RE = /^>\s?(.*)$/;
const UL_RE = /^\s{0,3}[-*+]\s+(.*)$/;
const OL_RE = /^\s{0,3}\d+\.\s+(.*)$/;
const FENCE_RE = /^```(\w*)\s*$/;
const TABLE_DIVIDER_RE = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/;

function splitRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\||\|$/g, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Blank line — skip
    if (line.trim() === "") {
      i += 1;
      continue;
    }

    // Fenced code block
    const fence = line.match(FENCE_RE);
    if (fence) {
      const language = fence[1] ?? "";
      const buf: string[] = [];
      i += 1;
      while (i < lines.length && !FENCE_RE.test(lines[i])) {
        buf.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) i += 1; // consume closing fence
      blocks.push({ type: "code", language, content: buf.join("\n") });
      continue;
    }

    // Horizontal rule
    if (HR_RE.test(line)) {
      blocks.push({ type: "hr" });
      i += 1;
      continue;
    }

    // Heading
    const heading = line.match(HEADING_RE);
    if (heading) {
      const level = heading[1].length as 1 | 2 | 3 | 4 | 5 | 6;
      blocks.push({ type: "heading", level, text: heading[2].trim() });
      i += 1;
      continue;
    }

    // Blockquote (one or more contiguous `> …` lines collapsed into a single
    // block with spaces between lines)
    if (QUOTE_RE.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && QUOTE_RE.test(lines[i])) {
        const m = lines[i].match(QUOTE_RE);
        buf.push(m ? m[1] : "");
        i += 1;
      }
      blocks.push({ type: "quote", text: buf.join(" ") });
      continue;
    }

    // Table (header row + divider + body rows)
    if (
      line.includes("|") &&
      i + 1 < lines.length &&
      TABLE_DIVIDER_RE.test(lines[i + 1])
    ) {
      const header = splitRow(line);
      i += 2; // skip divider
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
        rows.push(splitRow(lines[i]));
        i += 1;
      }
      blocks.push({ type: "table", header, rows });
      continue;
    }

    // List (ordered or unordered)
    if (UL_RE.test(line) || OL_RE.test(line)) {
      const ordered = OL_RE.test(line);
      const re = ordered ? OL_RE : UL_RE;
      const items: string[] = [];
      while (i < lines.length && re.test(lines[i])) {
        const m = lines[i].match(re);
        items.push(m ? m[1] : "");
        i += 1;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    // Paragraph: collect contiguous non-blank, non-special lines
    const buf: string[] = [line];
    i += 1;
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !FENCE_RE.test(lines[i]) &&
      !HR_RE.test(lines[i]) &&
      !HEADING_RE.test(lines[i]) &&
      !QUOTE_RE.test(lines[i]) &&
      !UL_RE.test(lines[i]) &&
      !OL_RE.test(lines[i])
    ) {
      buf.push(lines[i]);
      i += 1;
    }
    blocks.push({ type: "paragraph", text: buf.join(" ") });
  }

  return blocks;
}

// ---------------------------------------------------------------------------
// Renderer
// ---------------------------------------------------------------------------

function renderBlock(block: Block, idx: number): ReactNode {
  const key = `b-${idx}`;
  switch (block.type) {
    case "hr":
      return <hr key={key} className="md-hr" />;
    case "heading": {
      const Tag = (`h${block.level}` as unknown) as keyof React.JSX.IntrinsicElements;
      return (
        <Tag key={key} className={`md-h md-h${block.level}`}>
          {parseInline(block.text, key)}
        </Tag>
      );
    }
    case "paragraph":
      return (
        <p key={key} className="md-p">
          {parseInline(block.text, key)}
        </p>
      );
    case "quote":
      return (
        <blockquote key={key} className="md-quote">
          {parseInline(block.text, key)}
        </blockquote>
      );
    case "code":
      return (
        <pre key={key} className="md-pre">
          <code className={block.language ? `language-${block.language}` : undefined}>
            {block.content}
          </code>
        </pre>
      );
    case "list": {
      const items = block.items.map((it, j) => (
        <li key={`${key}-${j}`}>{parseInline(it, `${key}-${j}`)}</li>
      ));
      return block.ordered ? (
        <ol key={key} className="md-ol">{items}</ol>
      ) : (
        <ul key={key} className="md-ul">{items}</ul>
      );
    }
    case "table":
      return (
        <div key={key} className="md-table-wrap">
          <table className="md-table">
            <thead>
              <tr>
                {block.header.map((cell, j) => (
                  <th key={`${key}-h-${j}`}>{parseInline(cell, `${key}-h-${j}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, r) => (
                <tr key={`${key}-r-${r}`}>
                  {row.map((cell, c) => (
                    <td key={`${key}-r-${r}-c-${c}`}>
                      {parseInline(cell, `${key}-r-${r}-c-${c}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
  }
}

export function renderMarkdown(source: string): ReactNode[] {
  return parseBlocks(source).map(renderBlock);
}
