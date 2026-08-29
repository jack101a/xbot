import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { TargetKOL } from "../types";

export function usePersona(profileId: string) {
  // Persona & Target KOL State
  const [personaData, setPersonaData] = useState<any>(null);
  const [targetKols, setTargetKols] = useState<TargetKOL[]>([]);
  const [newKolHandle, setNewKolHandle] = useState("");
  const [newKolCategory, setNewKolCategory] = useState("tech_ai");
  const [newKolPriority, setNewKolPriority] = useState<"high" | "medium" | "low">("high");
  const [newKolAngle, setNewKolAngle] = useState<"contrarian" | "framework" | "witty" | "data" | "insight">("insight");
  const [savingKols, setSavingKols] = useState(false);
  const [kolActionMsg, setKolActionMsg] = useState<string | null>(null);

  // Load Persona Data
  useEffect(() => {
    async function loadData() {
      if (!profileId) return;
      try {
        const p = await api.getProfilePersona(profileId);
        setPersonaData(p);
        if (p?.target_kols) {
          setTargetKols(p.target_kols);
        }
      } catch (err) {
        console.error("Failed to load persona for growth engine", err);
      }
    }
    loadData();
  }, [profileId]);

  // Handle Add KOL
  const handleAddKol = async () => {
    if (!newKolHandle.trim()) return;
    const cleanHandle = newKolHandle.trim().replace(/^@/, "");
    const updated = [
      ...targetKols.filter(k => k.handle.toLowerCase() !== cleanHandle.toLowerCase()),
      {
        handle: cleanHandle,
        category: newKolCategory,
        priority: newKolPriority,
        preferred_angle: newKolAngle
      }
    ];
    setTargetKols(updated);
    setNewKolHandle("");
    await saveTargetKols(updated);
  };

  // Handle Remove KOL
  const handleRemoveKol = async (handle: string) => {
    const updated = targetKols.filter(k => k.handle.toLowerCase() !== handle.toLowerCase());
    setTargetKols(updated);
    await saveTargetKols(updated);
  };

  // Save KOL list to persona
  const saveTargetKols = async (kols: TargetKOL[]) => {
    setSavingKols(true);
    setKolActionMsg(null);
    try {
      const updatedPersona = {
        ...(personaData || {}),
        target_kols: kols
      };
      await api.updateProfilePersona(profileId, updatedPersona);
      setPersonaData(updatedPersona);
      setKolActionMsg("Target KOL registry updated successfully!");
      setTimeout(() => setKolActionMsg(null), 3500);
    } catch (err: any) {
      alert("Failed to save KOL list: " + err.message);
    } finally {
      setSavingKols(false);
    }
  };


  return {
    personaData, setPersonaData,
    targetKols, setTargetKols,
    newKolHandle, setNewKolHandle,
    newKolCategory, setNewKolCategory,
    newKolPriority, setNewKolPriority,
    newKolAngle, setNewKolAngle,
    savingKols, setSavingKols,
    kolActionMsg, setKolActionMsg,
    handleAddKol,
    handleRemoveKol,
      };
}
