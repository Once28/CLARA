import { useState, useEffect, useCallback } from "react";
import api from "../services/api";

export function useAudits() {
  const [audits, setAudits] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch all audits on mount
  const fetchAudits = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAudits();
      setAudits(data);
      // Auto-select the first (most recent) audit
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAudits();
  }, [fetchAudits]);

  // Upload a new protocol
  const uploadProtocol = useCallback(async (file, metadata) => {
    setUploading(true);
    setError(null);
    try {
      const newAudit = await api.uploadProtocol(file, metadata);
      setAudits((prev) => [newAudit, ...prev]);
      setSelectedId(newAudit.id);
      return newAudit;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setUploading(false);
    }
  }, []);

  // Delete an audit
  const deleteAudit = useCallback(async (id) => {
    try {
      await api.deleteAudit(id);
      setAudits((prev) => prev.filter((a) => a.id !== id));
      if (selectedId === id) {
        setSelectedId((prev) => {
          const remaining = audits.filter((a) => a.id !== id);
          return remaining.length > 0 ? remaining[0].id : null;
        });
      }
    } catch (err) {
      setError(err.message);
    }
  }, [selectedId, audits]);

  // Clear all audits
  const clearAll = useCallback(() => {
    setAudits([]);
    setSelectedId(null);
  }, []);

  // Derived: currently selected audit object
  const selectedAudit = audits.find((a) => a.id === selectedId) || null;

  // Derived: score history for chart
  const scoreHistory = [...audits]
    .reverse()
    .map((a) => ({ label: a.id, score: a.score, filename: a.filename }));

  return {
    audits,
    selectedId,
    selectedAudit,
    scoreHistory,
    loading,
    uploading,
    error,
    setSelectedId,
    uploadProtocol,
    deleteAudit,
    clearAll,
    refetch: fetchAudits,
  };
}
