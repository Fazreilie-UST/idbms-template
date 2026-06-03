import { useRef, useEffect, useState } from "react";
import { uploadDocAsset } from "../services/docsApi";

// Utility: Extract only the content inside <body>...</body> from a full HTML string
function extractBodyContent(html: string): string {
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
  // Insert HTML at the current cursor position in the contentEditable div
  const insertHtmlAtCursor = (html: string) => {
    let sel, range;
    if (window.getSelection && (sel = window.getSelection()) && sel.rangeCount) {
      range = sel.getRangeAt(0);
      range.deleteContents();
      const el = document.createElement("div");
      el.innerHTML = html;
      let frag = document.createDocumentFragment(), node, lastNode;
      while ((node = el.firstChild)) {
        lastNode = frag.appendChild(node);
      }
      range.insertNode(frag);
      // Move the cursor after the inserted node
      if (lastNode) {
        range = range.cloneRange();
        range.setStartAfter(lastNode);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
      }
    }
  };
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const asset = await uploadDocAsset(file);
      // Ensure the image src uses /docs-assets/screenshots/ path
      let imgSrc = asset.url;
      // If asset.url is a full URL, extract the path part
      try {
        const urlObj = new URL(asset.url, window.location.origin);
        imgSrc = urlObj.pathname;
      } catch {}
      // Force path to start with /docs-assets/screenshots/
      if (!imgSrc.startsWith('/docs-assets/screenshots/')) {
        const idx = imgSrc.indexOf('/docs-assets/screenshots/');
        if (idx !== -1) imgSrc = imgSrc.slice(idx);
      }
      insertHtmlAtCursor(`<img src="${imgSrc}" alt="" style="max-width:100%;" />`);
    } catch (err) {
      alert("Image upload failed: " + (err instanceof Error ? err.message : err));
    }
    e.target.value = ""; // Reset file input
  };

interface HtmlEditorProps {
  initialContent: string;
  saving?: boolean;
  onSave: (content: string) => void;
  onCancel: () => void;
}

  const editorRef = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<'edit' | 'preview'>('edit');
  const [previewContent, setPreviewContent] = useState<string>("");

  useEffect(() => {
    if (editorRef.current) {
      // Always set only the body content, never the full HTML doc
      if (/<!DOCTYPE|<html|<body/i.test(initialContent)) {
        editorRef.current.innerHTML = extractBodyContent(initialContent || "");
      } else {
        editorRef.current.innerHTML = initialContent || "";
      }
    }
    setPreviewContent(
      /<!DOCTYPE|<html|<body/i.test(initialContent)
        ? extractBodyContent(initialContent || "")
        : initialContent || ""
    );
  }, [initialContent]);

  // Update preview when switching to preview tab
  useEffect(() => {
    if (tab === 'preview' && editorRef.current) {
      const raw = editorRef.current.innerHTML;
      setPreviewContent(
        /<!DOCTYPE|<html|<body/i.test(raw)
          ? extractBodyContent(raw)
          : raw
      );
    }
  }, [tab]);

  const handleSave = () => {
    if (editorRef.current) {
      // Only save the body content if a full HTML doc was pasted
      const raw = editorRef.current.innerHTML;
      if (/<!DOCTYPE|<html|<body/i.test(raw)) {
        onSave(extractBodyContent(raw));
      } else {
        onSave(raw);
      }
    }
  };

  return (
    <div style={{ width: "100%" }}>
      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #ccc", marginBottom: 8 }}>
        <button
          type="button"
          onClick={() => setTab('edit')}
          style={{
            border: 'none',
            borderBottom: tab === 'edit' ? '2px solid #1976d2' : '2px solid transparent',
            background: 'none',
            padding: '8px 16px',
            cursor: 'pointer',
            color: tab === 'edit' ? '#1976d2' : '#333',
            fontWeight: tab === 'edit' ? 600 : 400,
            fontSize: 16,
          }}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => setTab('preview')}
          style={{
            border: 'none',
            borderBottom: tab === 'preview' ? '2px solid #1976d2' : '2px solid transparent',
            background: 'none',
            padding: '8px 16px',
            cursor: 'pointer',
            color: tab === 'preview' ? '#1976d2' : '#333',
            fontWeight: tab === 'preview' ? 600 : 400,
            fontSize: 16,
          }}
        >
          Preview
        </button>
      </div>
      {/* Editor or Preview */}
      {tab === 'edit' ? (
        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          style={{
            minHeight: 200,
            border: "1px solid #ccc",
            borderRadius: 4,
            padding: 12,
            background: "#fff",
            outline: "none",
            fontSize: 16,
          }}
          aria-label="HTML Editor"
        />
      ) : (
        <div
          style={{
            minHeight: 200,
            border: "1px solid #ccc",
            borderRadius: 4,
            padding: 12,
            background: "#fafbfc",
            fontSize: 16,
            color: "#222",
            wordBreak: "break-word",
          }}
          aria-label="HTML Preview"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: previewContent }}
        />
      )}
      <div style={{ marginTop: 16, display: "flex", gap: 8, alignItems: "center" }}>
        <label style={{ display: "inline-block" }}>
          <input
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={handleImageUpload}
            disabled={saving}
          />
          <span style={{
            display: "inline-block",
            padding: "6px 12px",
            background: "#f0f0f0",
            border: "1px solid #ccc",
            borderRadius: 4,
            cursor: saving ? "not-allowed" : "pointer",
            fontSize: 14,
            marginRight: 8,
          }}>
            Insert Image
          </span>
        </label>
        <button
          type="button"
          disabled={saving}
          onClick={handleSave}
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button type="button" disabled={saving} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}