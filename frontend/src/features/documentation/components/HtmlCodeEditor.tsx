
import { useState, useEffect, useRef } from "react";
import { uploadDocAsset } from "../services/docsApi";
import DocAssetsModal from "./DocAssetsModal";

interface HtmlCodeEditorProps {
  initialContent: string;
  saving?: boolean;
  onSave: (content: string) => void;
  onCancel: () => void;
}

export default function HtmlCodeEditor({ initialContent, saving, onSave, onCancel }: HtmlCodeEditorProps) {
  const [value, setValue] = useState(initialContent || "");
  const [tab, setTab] = useState<'code' | 'preview'>('code');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setValue(initialContent || "");
  }, [initialContent]);

  // Insert <img> tag at the current cursor position in the textarea
  const insertAtCursor = (text: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = value.slice(0, start);
    const after = value.slice(end);
    const newValue = before + text + after;
    setValue(newValue);
    // Move cursor after inserted text
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + text.length;
      textarea.focus();
    }, 0);
  };

  // Asset modal state
  const [assetModalOpen, setAssetModalOpen] = useState(false);
  const handleInsertAsset = (asset: { url: string; filename: string }) => {
    insertAtCursor(`<img src="http://localhost:8000${asset.url}" alt="" style="max-width:100%;" />`);
    setAssetModalOpen(false);
  };

  return (
    <div style={{ width: "100%" }}>
      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #ccc", marginBottom: 8 }}>
        <button
          type="button"
          onClick={() => setTab('code')}
          style={{
            border: 'none',
            borderBottom: tab === 'code' ? '2px solid #1976d2' : '2px solid transparent',
            background: 'none',
            padding: '8px 16px',
            cursor: 'pointer',
            color: tab === 'code' ? '#1976d2' : '#333',
            fontWeight: tab === 'code' ? 600 : 400,
            fontSize: 16,
          }}
        >
          Code
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
      {tab === 'code' ? (
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          style={{
            width: "100%",
            minHeight: 300,
            fontFamily: "monospace",
            fontSize: 15,
            border: "1px solid #ccc",
            borderRadius: 4,
            padding: 12,
            background: "#fff",
            outline: "none",
            resize: "vertical",
          }}
          aria-label="HTML Code Editor"
          disabled={saving}
        />
      ) : (
        <div
          style={{
            minHeight: 300,
            border: "1px solid #ccc",
            borderRadius: 4,
            padding: 12,
            background: "#fafbfc",
            fontSize: 15,
            color: "#222",
            wordBreak: "break-word",
          }}
          aria-label="HTML Preview"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: value }}
        />
      )}
      <div style={{ marginTop: 16, display: "flex", gap: 8, alignItems: "center" }}>
        <button
          type="button"
          disabled={saving}
          onClick={() => setAssetModalOpen(true)}
          style={{
            padding: "6px 12px",
            background: "#f0f0f0",
            border: "1px solid #ccc",
            borderRadius: 4,
            cursor: saving ? "not-allowed" : "pointer",
            fontSize: 14,
            marginRight: 8,
          }}
        >
          Insert Image
        </button>
        <button
          type="button"
          disabled={saving}
          onClick={() => onSave(value)}
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button type="button" disabled={saving} onClick={onCancel}>
          Cancel
        </button>
        <DocAssetsModal
          open={assetModalOpen}
          onClose={() => setAssetModalOpen(false)}
          onSelect={handleInsertAsset}
        />
      </div>
    </div>
  );
}
