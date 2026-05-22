import { useRef, useState } from "react";
import {
  Button,
  Input,
  Space,
  Tabs,
  Upload,
  message,
  Popconfirm,
  Modal,
  List,
  Image as AntImage,
  Typography,
} from "antd";
import type { UploadProps } from "antd";
import {
  CloseOutlined,
  PictureOutlined,
  SaveOutlined,
  UploadOutlined,
  DeleteOutlined,
  CopyOutlined,
} from "@ant-design/icons";
import MarkdownView from "./MarkdownView";
import {
  deleteDocAsset,
  fetchDocAssets,
  uploadDocAsset,
  type DocAsset,
} from "../services/docsApi";
import { resolveBackendUrl } from "@/config";

const { TextArea } = Input;

export interface MarkdownEditorProps {
  initialContent: string;
  onSave: (content: string) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

export default function MarkdownEditor({
  initialContent,
  onSave,
  onCancel,
  saving,
}: MarkdownEditorProps) {
  const [value, setValue] = useState(initialContent);
  const [assetModalOpen, setAssetModalOpen] = useState(false);
  const [assets, setAssets] = useState<DocAsset[]>([]);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const textareaRef = useRef<{
    resizableTextArea?: { textArea: HTMLTextAreaElement };
  } | null>(null);
  const [messageApi, contextHolder] = message.useMessage();

  const insertAtCursor = (snippet: string) => {
    const el = textareaRef.current?.resizableTextArea?.textArea;
    if (!el) {
      setValue((v) => v + snippet);
      return;
    }
    const start = el.selectionStart ?? value.length;
    const end = el.selectionEnd ?? value.length;
    const next = value.slice(0, start) + snippet + value.slice(end);
    setValue(next);
    // Restore caret after the inserted snippet on the next tick.
    requestAnimationFrame(() => {
      el.focus();
      const caret = start + snippet.length;
      el.setSelectionRange(caret, caret);
    });
  };

  const openAssetPicker = async () => {
    setAssetModalOpen(true);
    setLoadingAssets(true);
    try {
      const res = await fetchDocAssets();
      setAssets(res.assets);
    } catch (err) {
      messageApi.error(
        err instanceof Error ? err.message : "Could not load assets",
      );
    } finally {
      setLoadingAssets(false);
    }
  };

  const uploadProps: UploadProps = {
    accept: "image/png,image/jpeg,image/webp,image/gif,image/svg+xml",
    showUploadList: false,
    customRequest: async (options) => {
      try {
        const file = options.file as File;
        const asset = await uploadDocAsset(file);
        setAssets((prev) => [asset, ...prev]);
        messageApi.success(`Uploaded ${asset.filename}`);
        options.onSuccess?.(asset);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        messageApi.error(msg);
        options.onError?.(new Error(msg));
      }
    },
  };

  const handleInsertAsset = (asset: DocAsset) => {
    const snippet = `\n\n![${asset.filename}](${asset.url})\n\n`;
    insertAtCursor(snippet);
    messageApi.success("Image markdown inserted");
    setAssetModalOpen(false);
  };

  const handleCopyUrl = async (asset: DocAsset) => {
    try {
      await navigator.clipboard.writeText(asset.url);
      messageApi.success("URL copied");
    } catch {
      messageApi.warning("Clipboard unavailable");
    }
  };

  const handleDeleteAsset = async (asset: DocAsset) => {
    try {
      await deleteDocAsset(asset.filename);
      setAssets((prev) => prev.filter((a) => a.filename !== asset.filename));
      messageApi.success("Asset deleted");
    } catch (err) {
      messageApi.error(
        err instanceof Error ? err.message : "Could not delete asset",
      );
    }
  };

  return (
    <div>
      {contextHolder}
      <Space style={{ marginBottom: 12 }} wrap>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          loading={saving}
          onClick={() => void onSave(value)}
        >
          Save
        </Button>
        <Popconfirm
          title="Discard unsaved changes?"
          okText="Discard"
          okButtonProps={{ danger: true }}
          onConfirm={onCancel}
          disabled={value === initialContent}
        >
          <Button
            icon={<CloseOutlined />}
            onClick={() => {
              if (value === initialContent) onCancel();
            }}
          >
            Cancel
          </Button>
        </Popconfirm>
        <Button icon={<PictureOutlined />} onClick={() => void openAssetPicker()}>
          Insert image
        </Button>
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />}>Upload new image</Button>
        </Upload>
      </Space>

      <Tabs
        defaultActiveKey="edit"
        items={[
          {
            key: "edit",
            label: "Edit",
            children: (
              <TextArea
                ref={textareaRef as never}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                autoSize={{ minRows: 20, maxRows: 40 }}
                style={{
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                  fontSize: 13,
                }}
              />
            ),
          },
          {
            key: "preview",
            label: "Preview",
            children: (
              <div
                style={{
                  border: "1px solid #f0f0f0",
                  borderRadius: 4,
                  padding: 16,
                  minHeight: 400,
                  background: "#fff",
                }}
              >
                <MarkdownView source={value} />
              </div>
            ),
          },
        ]}
      />

      <Modal
        open={assetModalOpen}
        onCancel={() => setAssetModalOpen(false)}
        footer={null}
        title="Documentation assets"
        width={720}
      >
        <Space style={{ marginBottom: 12 }}>
          <Upload {...uploadProps}>
            <Button type="primary" icon={<UploadOutlined />}>
              Upload image
            </Button>
          </Upload>
          <Typography.Text type="secondary">
            Click an image to insert it at the current cursor position.
          </Typography.Text>
        </Space>
        <List
          loading={loadingAssets}
          dataSource={assets}
          locale={{ emptyText: "No assets uploaded yet" }}
          renderItem={(asset) => (
            <List.Item
              actions={[
                <Button
                  key="insert"
                  type="link"
                  onClick={() => handleInsertAsset(asset)}
                >
                  Insert
                </Button>,
                <Button
                  key="copy"
                  type="link"
                  icon={<CopyOutlined />}
                  onClick={() => void handleCopyUrl(asset)}
                >
                  Copy URL
                </Button>,
                <Popconfirm
                  key="delete"
                  title={`Delete ${asset.filename}?`}
                  okText="Delete"
                  okButtonProps={{ danger: true }}
                  onConfirm={() => void handleDeleteAsset(asset)}
                >
                  <Button danger type="link" icon={<DeleteOutlined />}>
                    Delete
                  </Button>
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={
                  <AntImage
                    src={resolveBackendUrl(asset.url) ?? asset.url}
                    width={64}
                    height={64}
                    style={{ objectFit: "cover", borderRadius: 4 }}
                    preview={{ src: resolveBackendUrl(asset.url) ?? asset.url }}
                  />
                }
                title={asset.filename}
                description={
                  <span>
                    {(asset.size_bytes / 1024).toFixed(1)} KB ·{" "}
                    {new Date(asset.uploaded_at).toLocaleString()}
                  </span>
                }
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
}
