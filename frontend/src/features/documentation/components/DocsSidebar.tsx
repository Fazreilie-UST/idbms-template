import { useEffect, useMemo, useState } from "react";
import { CaretDownOutlined, CaretRightOutlined } from "@ant-design/icons";
import type { DocTreeNode } from "../services/docsApi";
import "./docs-sidebar.css";

export interface DocsSidebarProps {
  tree: DocTreeNode[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

function collectGroupKeys(nodes: DocTreeNode[]): string[] {
  const out: string[] = [];
  for (const n of nodes) {
    if (n.children && n.children.length > 0) {
      out.push(n.key);
      out.push(...collectGroupKeys(n.children));
    }
  }
  return out;
}

function findParentChain(
  nodes: DocTreeNode[],
  path: string,
  trail: string[] = [],
): string[] | null {
  for (const node of nodes) {
    if (node.path === path) return trail;
    if (node.children) {
      const inner = findParentChain(node.children, path, [...trail, node.key]);
      if (inner) return inner;
    }
  }
  return null;
}

interface NodeProps {
  node: DocTreeNode;
  depth: number;
  selectedPath: string | null;
  expanded: Set<string>;
  toggle: (key: string) => void;
  onSelect: (path: string) => void;
}

function DocsNavNode({
  node,
  depth,
  selectedPath,
  expanded,
  toggle,
  onSelect,
}: NodeProps) {
  const hasChildren = !!node.children && node.children.length > 0;
  const isOpen = hasChildren && expanded.has(node.key);
  const isLeaf = !!node.path;
  const isSelected = isLeaf && node.path === selectedPath;

  // Use CSS custom property for indent so each depth lines up neatly with a
  // small visible step.
  const indent = 8 + depth * 14;

  return (
    <li className="docs-nav-item">
      <button
        type="button"
        className={[
          "docs-nav-button",
          hasChildren ? "is-group" : "is-leaf",
          `depth-${depth}`,
          isSelected ? "is-selected" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        style={{ paddingLeft: indent }}
        onClick={() => {
          if (hasChildren) toggle(node.key);
          if (isLeaf && node.path) onSelect(node.path);
        }}
      >
        <span className="docs-nav-caret" aria-hidden>
          {hasChildren ? (
            isOpen ? (
              <CaretDownOutlined />
            ) : (
              <CaretRightOutlined />
            )
          ) : (
            <span className="docs-nav-bullet" />
          )}
        </span>
        <span className="docs-nav-label">{node.label}</span>
      </button>
      {hasChildren && isOpen && (
        <ul className="docs-nav-list">
          {node.children!.map((child) => (
            <DocsNavNode
              key={child.key}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              expanded={expanded}
              toggle={toggle}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function DocsSidebar({
  tree,
  selectedPath,
  onSelect,
}: DocsSidebarProps) {
  // Start with every group open so the user can see the full structure on
  // first render; subsequent toggling is remembered in component state.
<<<<<<< Updated upstream
  const initiallyOpen = useMemo(() => new Set(collectGroupKeys(tree)), [tree]);
  const [expanded, setExpanded] = useState<Set<string>>(initiallyOpen);
=======
  // By default, no nodes are expanded
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
>>>>>>> Stashed changes

  // Whenever the selection changes, make sure its parent groups stay open
  // (e.g. after a deep link / restored session).
  useEffect(() => {
    if (!selectedPath) return;
    const chain = findParentChain(tree, selectedPath);
    if (!chain) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      chain.forEach((k) => next.add(k));
      return next;
    });
  }, [selectedPath, tree]);

  const toggle = (key: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <nav className="docs-sidebar" aria-label="Documentation navigation">
      <ul className="docs-nav-list docs-nav-root">
        {tree.map((node) => (
          <DocsNavNode
            key={node.key}
            node={node}
            depth={0}
            selectedPath={selectedPath}
            expanded={expanded}
            toggle={toggle}
            onSelect={onSelect}
          />
        ))}
      </ul>
    </nav>
  );
}
