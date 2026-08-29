import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { PersonaState, LearnedState, DiaryEntry, MsgState } from "../types";

export function usePersonaMemory(profileId: string, onRefresh: () => void) {
  const [subSection, setSubSection] = useState<"identity" | "topics" | "diary" | "learned">("identity");

  const [persona, setPersona] = useState<PersonaState | null>(null);
  const [learnedState, setLearnedState] = useState<LearnedState | null>(null);
  const [diaryList, setDiaryList] = useState<DiaryEntry[]>([]);
  const [selectedDiaryDate, setSelectedDiaryDate] = useState<string | null>(null);
  const [diaryContent, setDiaryContent] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reflecting, setReflecting] = useState(false);
  const [msg, setMsg] = useState<MsgState | null>(null);

  const [showCardModal, setShowCardModal] = useState(false);
  const [cardJson, setCardJson] = useState("");
  const [importingCard, setImportingCard] = useState(false);

  const [newPrimaryTopic, setNewPrimaryTopic] = useState("");
  const [newAntiTopic, setNewAntiTopic] = useState("");

  const loadData = async () => {
    if (!profileId) return;
    setLoading(true);
    try {
      const [pData, lData, dData] = await Promise.all([
        api.getProfilePersona(profileId),
        api.getProfileLearnedState(profileId),
        api.getProfileDiary(profileId, 20)
      ]);
      setPersona(pData || {});
      setLearnedState(lData || {});
      setDiaryList(dData || []);
      if (dData && dData.length > 0 && !selectedDiaryDate) {
        setSelectedDiaryDate(dData[0].date);
        setDiaryContent(dData[0].content || "");
      }
    } catch (err: any) {
      console.error("Failed to load persona/memory data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [profileId]);

  const handleSavePersona = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await api.updateProfilePersona(profileId, persona);
      setMsg({ type: "success", text: "Persona identity & rules saved successfully!" });
      onRefresh();
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to save persona." });
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerReflection = async () => {
    setReflecting(true);
    setMsg(null);
    try {
      await api.triggerProfileReflection(profileId);
      setMsg({ type: "success", text: "Cognitive reflection triggered! Reviewing recent posts and updating learned habits." });
      await loadData();
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to trigger reflection." });
    } finally {
      setReflecting(false);
    }
  };

  const handleImportCard = async () => {
    if (!cardJson.trim()) return;
    setImportingCard(true);
    setMsg(null);
    try {
      await api.importProfileCard(profileId, cardJson, true);
      setMsg({ type: "success", text: "Character card imported and merged into persona!" });
      setShowCardModal(false);
      setCardJson("");
      await loadData();
      onRefresh();
    } catch (err: any) {
      setMsg({ type: "error", text: err.message || "Failed to import character card." });
    } finally {
      setImportingCard(false);
    }
  };

  const handleAddPrimaryTopic = () => {
    if (!newPrimaryTopic.trim()) return;
    const current = persona?.interests?.primary || [];
    setPersona({ ...persona, interests: { ...persona?.interests, primary: [...current, newPrimaryTopic.trim()] } });
    setNewPrimaryTopic("");
  };

  const handleRemovePrimaryTopic = (idx: number) => {
    const current = [...(persona?.interests?.primary || [])];
    current.splice(idx, 1);
    setPersona({ ...persona, interests: { ...persona?.interests, primary: current } });
  };

  const handleAddAntiTopic = () => {
    if (!newAntiTopic.trim()) return;
    const current = persona?.interests?.will_not_discuss || [];
    setPersona({ ...persona, interests: { ...persona?.interests, will_not_discuss: [...current, newAntiTopic.trim()] } });
    setNewAntiTopic("");
  };

  const handleRemoveAntiTopic = (idx: number) => {
    const current = [...(persona?.interests?.will_not_discuss || [])];
    current.splice(idx, 1);
    setPersona({ ...persona, interests: { ...persona?.interests, will_not_discuss: current } });
  };

  return {
    subSection, setSubSection,
    persona, setPersona,
    learnedState,
    diaryList,
    selectedDiaryDate, setSelectedDiaryDate,
    diaryContent, setDiaryContent,
    loading, saving, reflecting, msg, setMsg,
    showCardModal, setShowCardModal,
    cardJson, setCardJson,
    importingCard, handleImportCard,
    handleSavePersona, handleTriggerReflection,
    newPrimaryTopic, setNewPrimaryTopic,
    newAntiTopic, setNewAntiTopic,
    handleAddPrimaryTopic, handleRemovePrimaryTopic,
    handleAddAntiTopic, handleRemoveAntiTopic
  };
}
