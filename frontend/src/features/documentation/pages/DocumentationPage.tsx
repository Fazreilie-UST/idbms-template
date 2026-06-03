import { useCallback, useEffect, useMemo, useState } from "react";
// Utility: Extract only the content inside <body>...</body> from a full HTML string
function extractBodyContent(html: string): string {
  // Try to extract <body>...</body> content
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  if (bodyMatch) return bodyMatch[1];
  // Fallback: Remove <html> and <head> if present
  return html
    .replace(/<!DOCTYPE[^>]*>/gi, "")
    .replace(/<html[^>]*>/gi, "")
    .replace(/<head>[\s\S]*?<\/head>/gi, "")
    .replace(/<body[^>]*>/gi, "")
    .replace(/<\/body>/gi, "")
    .replace(/<\/html>/gi, "")
    .trim();
}
import {
  Alert,
  Button,
  Empty,
  Layout,
  Result,
  Skeleton,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { EditOutlined } from "@ant-design/icons";

import DocsSidebar from "../components/DocsSidebar";
import MarkdownView from "../components/MarkdownView";
import MarkdownEditor from "../components/MarkdownEditor";
import HtmlCodeEditor from "../components/HtmlCodeEditor";
import SwaggerEmbed from "../components/SwaggerEmbed";
import {
  fetchDocPage,
  fetchDocTree,
  updateDocPage,
  type DocPageContent,
  type DocTreeNode,
  type DocTreeResponse,
} from "../services/docsApi";

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

const STORAGE_KEY = "docs:lastPath";

function firstLeafPath(nodes: DocTreeNode[]): string | null {
  for (const node of nodes) {
    if (node.path) return node.path;
    if (node.children) {
      const inner = firstLeafPath(node.children);
      if (inner) return inner;
    }
  }
  return null;
}

function findLabelChain(
  nodes: DocTreeNode[],
  path: string,
  trail: string[] = [],
): string[] | null {
  for (const node of nodes) {
    const next = [...trail, node.label];
    if (node.path === path) return next;
    if (node.children) {
      const found = findLabelChain(node.children, path, next);
      if (found) return found;
    }
  }
  return null;
}

export default function DocumentationPage() {
  const [tree, setTree] = useState<DocTreeResponse | null>(null);
  const [treeError, setTreeError] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [page, setPage] = useState<DocPageContent | null>(null);
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  // Load the tree once.
  useEffect(() => {
    let cancelled = false;
    fetchDocTree()
      .then((res) => {
        if (cancelled) return;
        setTree(res);
        const stored = (() => {
          try {
            return localStorage.getItem(STORAGE_KEY);
          } catch {
            return null;
          }
        })();
        const initial = stored ?? firstLeafPath(res.tree);
        if (initial) setSelectedPath(initial);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setTreeError(
          err instanceof Error ? err.message : "Failed to load documentation",
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load the selected page whenever the path changes.
  useEffect(() => {
    if (!selectedPath) return;
    let cancelled = false;
    setPageLoading(true);
    setPageError(null);
    setEditing(false);
    fetchDocPage(selectedPath)
      .then((res) => {
        if (cancelled) return;
        setPage(res);
        try {
          localStorage.setItem(STORAGE_KEY, selectedPath);
        } catch {
          /* ignore */
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPageError(err instanceof Error ? err.message : "Failed to load page");
      })
      .finally(() => {
        if (!cancelled) setPageLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPath]);

  const handleSave = useCallback(
    async (content: string) => {
      if (!selectedPath) return;
      setSaving(true);
      try {
        await updateDocPage(selectedPath, content);
        setEditing(false);
        messageApi.success("Documentation saved");
        // Auto-refresh: re-fetch the page content
        setPageLoading(true);
        setPageError(null);
        fetchDocPage(selectedPath)
          .then((res) => setPage(res))
          .catch((err) => setPageError(err instanceof Error ? err.message : "Failed to load page"))
          .finally(() => setPageLoading(false));
      } catch (err) {
        messageApi.error(
          err instanceof Error ? err.message : "Failed to save documentation",
        );
      } finally {
        setSaving(false);
      }
    },
    [selectedPath, messageApi],
  );

  const breadcrumb = useMemo(() => {
    if (!tree || !selectedPath) return [];
    return findLabelChain(tree.tree, selectedPath) ?? [];
  }, [tree, selectedPath]);

  const canEdit = page?.can_edit ?? tree?.can_edit ?? false;

  return (
    <Layout
      style={{
        background: "#fff",
        minHeight: "calc(100vh - 64px)",
      }}
    >
      {contextHolder}
      <Sider
        width={260}
        theme="light"
        style={{
          background: "#fafbfc",
          borderRight: "1px solid #e5e7eb",
          overflow: "auto",
        }}
      >
        <div
          style={{
            padding: "18px 18px 6px",
            borderBottom: "1px solid #eef2f7",
            marginBottom: 4,
          }}
        >
          <Title
            level={5}
            style={{
              margin: 0,
              fontSize: 13,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#0f172a",
            }}
          >
            Documentation
          </Title>
          {tree?.can_edit && (
            <Tag color="blue" style={{ marginTop: 8, fontSize: 11 }}>
              Admin · edit enabled
            </Tag>
          )}
        </div>
        {treeError ? (
          <Alert type="error" message={treeError} style={{ margin: 16 }} />
        ) : !tree ? (
          <div style={{ padding: 16 }}>
            <Skeleton active paragraph={{ rows: 6 }} />
          </div>
        ) : (
          <DocsSidebar
            tree={tree.tree}
            selectedPath={selectedPath}
            onSelect={(p) => setSelectedPath(p)}
          />
        )}
      </Sider>
      <Content style={{ padding: "28px 36px 48px", overflow: "auto" }}>
        <div style={{ textAlign: "left" }}>
          {!selectedPath && !treeError && (
            <Empty description="Select a documentation page from the sidebar" />
          )}

          {selectedPath && (
            <>
              <Space
                align="center"
                style={{
                  width: "100%",
                  justifyContent: "space-between",
                  marginBottom: 20,
                }}
              >
                <div>
                  {breadcrumb.length > 0 && (
                    <Text
                      type="secondary"
                      style={{
                        fontSize: 11.5,
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                      }}
                    >
                      {breadcrumb.slice(0, -1).join(" / ")}
                    </Text>
                  )}
                  <Title
                    level={2}
                    style={{
                      margin: "2px 0 0",
                      fontSize: 28,
                      color: "#0f172a",
                    }}
                  >
                    {page?.label ?? "Documentation"}
                  </Title>
                  {page?.updated_at && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Last updated {new Date(page.updated_at).toLocaleString()}
                    </Text>
                  )}
                </div>
                {canEdit && !editing && page && (
                  <Button
                    type="primary"
                    icon={<EditOutlined />}
                    onClick={() => setEditing(true)}
                  >
                    Edit
                  </Button>
                )}
              </Space>

              {pageError && (
                <Result
                  status="warning"
                  title="Could not load this page"
                  subTitle={pageError}
                />
              )}

              {pageLoading && !pageError && (
                <Skeleton active paragraph={{ rows: 10 }} />
              )}


              {!pageLoading && !pageError && page && !editing && (
                <>
                  {page.format === "html" ? (
                    <div
                      className="docs-html"
                      style={{ width: "100%" }}
                      dangerouslySetInnerHTML={{
                        __html: extractBodyContent(page.content || "<em>This page is empty.</em>")
                      }}
                    />
                  ) : (
                    <MarkdownView source={page.content} />
                  )}
                  {page.embed === "swagger" && <SwaggerEmbed />}
                </>
              )}

              {!pageLoading && !pageError && page && editing && (
                <HtmlCodeEditor
                  initialContent={page.content}
                  saving={saving}
                  onSave={handleSave}
                  onCancel={() => setEditing(false)}
                />
              )}
            </>
          )}
        </div>
      </Content>
    </Layout>
  );
}
