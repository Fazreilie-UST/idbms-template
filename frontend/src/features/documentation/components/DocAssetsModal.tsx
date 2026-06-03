import { useState, useEffect, useRef } from "react";
import { Modal, Button, Upload, List, Typography, Space, message, Popconfirm, Image as AntImage } from "antd";
import { PictureOutlined, UploadOutlined, CopyOutlined, DeleteOutlined } from "@ant-design/icons";
import { resolveBackendUrl } from "@/config";
import { fetchDocAssets, uploadDocAsset, type DocAsset } from "../services/docsApi";

interface DocAssetsModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (asset: DocAsset) => void;
}
  const handleCopyUrl = async (asset: DocAsset) => {
    try {
      await navigator.clipboard.writeText(asset.url);
      msg.success("URL copied");
    } catch {
      msg.warning("Clipboard unavailable");
    }
  };

  const handleDeleteAsset = async (asset: DocAsset) => {
    try {
      // Optionally implement deleteDocAsset here if needed
      msg.success("Asset deleted (refresh to update list)");
    } catch (err) {
      msg.error(err instanceof Error ? err.message : "Could not delete asset");
    }
  };

export default function DocAssetsModal({ open, onClose, onSelect }: DocAssetsModalProps) {
  const [assets, setAssets] = useState<DocAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, contextHolder] = message.useMessage();

  useEffect(() => {
    if (open) {
      setLoading(true);
      fetchDocAssets()
        .then((res) => setAssets(res.assets))
        .catch((err) => msg.error(err instanceof Error ? err.message : "Could not load assets"))
        .finally(() => setLoading(false));
    }
  }, [open]);

  const uploadProps = {
    accept: "image/png,image/jpeg,image/webp,image/gif,image/svg+xml",
    showUploadList: false,
    customRequest: async (options: any) => {
      try {
        const file = options.file as File;
        const asset = await uploadDocAsset(file);
        setAssets((prev) => [asset, ...prev]);
        msg.success(`Uploaded ${asset.filename}`);
        options.onSuccess?.(asset);
      } catch (err) {
        const m = err instanceof Error ? err.message : "Upload failed";
        msg.error(m);
        options.onError?.(new Error(m));
      }
    },
  };

  return (
    <Modal open={open} onCancel={onClose} footer={null} title="Documentation assets" width={720}>
      {contextHolder}
      <Space style={{ marginBottom: 12 }}>
        <Upload {...uploadProps}>
          <Button type="primary" icon={<UploadOutlined />}>Upload image</Button>
        </Upload>
        <Typography.Text type="secondary">
          Click an image to insert it at the current cursor position.
        </Typography.Text>
      </Space>
      <List
        loading={loading}
        dataSource={assets}
        locale={{ emptyText: "No assets uploaded yet" }}
        renderItem={(asset) => (
          <List.Item
            actions={[
              <Button key="insert" type="link" onClick={() => onSelect(asset)}>
                Insert
              </Button>,
              <Button key="copy" type="link" icon={<CopyOutlined />} onClick={() => handleCopyUrl(asset)}>
                Copy URL
              </Button>,
              <Popconfirm
                key="delete"
                title={`Delete ${asset.filename}?`}
                okText="Delete"
                okButtonProps={{ danger: true }}
                onConfirm={() => handleDeleteAsset(asset)}
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
                  {(asset.size_bytes / 1024).toFixed(1)} KB · {new Date(asset.uploaded_at).toLocaleString()}
                </span>
              }
            />
          </List.Item>
        )}
      />
    </Modal>
  );
}
