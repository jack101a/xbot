import { useState, useRef, RefObject } from "react";
import { api, Profile } from "@/lib/api";

export function useQuickComposer(profile: Profile, onRefresh: () => void) {
  const [quickPostText, setQuickPostText] = useState("");
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [publishingQuickPost, setPublishingQuickPost] = useState(false);
  const [quickPostMsg, setQuickPostMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImageFile(file);
      setImagePreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleRemoveImage = () => {
    setSelectedImageFile(null);
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
      setImagePreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleInsertEmoji = (emoji: string) => {
    setQuickPostText((prev) => prev + (prev.endsWith(" ") || prev === "" ? "" : " ") + emoji);
  };

  const handlePublishQuickPost = async () => {
    if (!quickPostText.trim() && !selectedImageFile) return;
    setPublishingQuickPost(true);
    setQuickPostMsg(null);
    try {
      let uploadedMediaPath: string | undefined = undefined;
      if (selectedImageFile) {
        const uploadRes = await api.uploadMedia(profile.id, selectedImageFile);
        uploadedMediaPath = uploadRes.file_path;
      }

      await api.publishLivePost(
        profile.id,
        quickPostText.trim(),
        uploadedMediaPath ? [uploadedMediaPath] : undefined
      );

      setQuickPostMsg({ type: "success", text: "Published live post to X timeline!" });
      setQuickPostText("");
      handleRemoveImage();
      onRefresh();
    } catch (err: any) {
      setQuickPostMsg({ type: "error", text: err.message || "Failed to publish live post." });
    } finally {
      setPublishingQuickPost(false);
    }
  };

  return {
    quickPostText,
    setQuickPostText,
    selectedImageFile,
    imagePreviewUrl,
    publishingQuickPost,
    quickPostMsg,
    fileInputRef,
    handleFileChange,
    handleRemoveImage,
    handleInsertEmoji,
    handlePublishQuickPost
  };
}
