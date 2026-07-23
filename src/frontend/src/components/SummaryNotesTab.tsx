import React, { useEffect, useState } from "react";
import { BookOpen, Layers, Printer, ChevronRight, CheckCircle2, RotateCcw, Loader2, History, Trash2 } from "lucide-react";
import { I18nKey } from "../i18n";
import { getAuthItem } from "../authStorage";

interface SummaryNotesTabProps {
  t: I18nKey;
  lang: string;
}

interface Flashcard {
  front: string;
  back: string;
  category: string;
}

interface SavedFlashcardSet {
  id: string;
  topic: string;
  count: number;
  created_at: string;
  updated_at: string;
}

interface SavedSummary {
  id: string;
  topic: string;
  summary: string;
  sources: any[];
  created_at: string;
  updated_at: string;
}

export default function SummaryNotesTab({ t, lang }: SummaryNotesTabProps) {
  const [activeSubTab, setActiveSubTab] = useState<"summary" | "flashcards">("summary");
  
  // Summary State
  const [summaryTopic, setSummaryTopic] = useState("");
  const [summaryResult, setSummaryResult] = useState<string>("");
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);
  const [summarySources, setSummarySources] = useState<any[]>([]);
  const [savedSummaries, setSavedSummaries] = useState<SavedSummary[]>([]);
  const [activeSavedSummaryId, setActiveSavedSummaryId] = useState<string | null>(null);

  // Flashcards State
  const [flashcardTopic, setFlashcardTopic] = useState("");
  const [flashcardCount, setFlashcardCount] = useState(5);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [isGeneratingFlashcards, setIsGeneratingFlashcards] = useState(false);
  const [flippedCards, setFlippedCards] = useState<Record<number, boolean>>({});
  const [learnedCards, setLearnedCards] = useState<Record<number, boolean>>({});
  const [savedFlashcardSets, setSavedFlashcardSets] = useState<SavedFlashcardSet[]>([]);
  const [isLoadingSavedFlashcards, setIsLoadingSavedFlashcards] = useState(false);
  const [activeSavedSetId, setActiveSavedSetId] = useState<string | null>(null);

  const isVi = lang === "vi";

  // --- Handlers ---
  const getAuthHeaders = () => {
    const token = getAuthItem("minerai_token");
    const headers: HeadersInit = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  };

  const getErrorMessage = (data: any, fallback: string) => data?.detail || data?.error || fallback;

  const getSavedSummariesKey = () => {
    try {
      const user = JSON.parse(getAuthItem("minerai_user") || "{}");
      return `minerai_saved_summaries_${user?.user_id || user?.email || "guest"}`;
    } catch {
      return "minerai_saved_summaries_guest";
    }
  };

  const normalizeSourceItem = (src: any) => {
    const metadata = src?.metadata || {};
    const filename =
      src?.friendlySource ||
      src?.filename ||
      src?.source ||
      metadata?.source ||
      metadata?.source_file ||
      "Nguồn tài liệu";
    const page = src?.page || metadata?.page || "";
    const slide = src?.slide || metadata?.slide || "";

    return {
      ...src,
      filename,
      page: page === "N/A" ? "" : page,
      slide,
      content: src?.content || src?.page_content || "",
      source: filename,
    };
  };

  const normalizeSummarySources = (data: any) => {
    const sourceList = Array.isArray(data?.sources) ? data.sources : [];
    if (sourceList.length > 0) return sourceList.map(normalizeSourceItem);

    const citations = Array.isArray(data?.citations) ? data.citations : [];
    return citations.map(normalizeSourceItem);
  };

  const loadSavedSummaries = () => {
    try {
      const raw = localStorage.getItem(getSavedSummariesKey());
      setSavedSummaries(raw ? JSON.parse(raw) : []);
    } catch (err) {
      console.error("Không thể tải tóm tắt đã lưu:", err);
      setSavedSummaries([]);
    }
  };

  const persistSavedSummaries = (items: SavedSummary[]) => {
    setSavedSummaries(items);
    localStorage.setItem(getSavedSummariesKey(), JSON.stringify(items.slice(0, 50)));
  };

  const saveSummaryLocally = (topic: string, summary: string, sources: any[]) => {
    const now = new Date().toISOString();
    const item: SavedSummary = {
      id: `summary-${Date.now()}`,
      topic: topic.trim() || (isVi ? "Tóm tắt chưa đặt tên" : "Untitled summary"),
      summary,
      sources,
      created_at: now,
      updated_at: now
    };
    persistSavedSummaries([item, ...savedSummaries.filter((saved) => saved.summary !== summary)]);
    setActiveSavedSummaryId(item.id);
  };

  const openSavedSummary = (item: SavedSummary) => {
    setSummaryTopic(item.topic);
    setSummaryResult(item.summary);
    setSummarySources(item.sources || []);
    setActiveSavedSummaryId(item.id);
  };

  const deleteSavedSummary = (id: string) => {
    persistSavedSummaries(savedSummaries.filter((item) => item.id !== id));
    if (activeSavedSummaryId === id) {
      setActiveSavedSummaryId(null);
    }
  };

  const loadSavedFlashcardSets = async () => {
    const token = getAuthItem("minerai_token");
    if (!token) return;

    setIsLoadingSavedFlashcards(true);
    try {
      const res = await fetch("/api/flashcards/saved", { headers: getAuthHeaders() });
      const data = await res.json();
      if (res.ok) {
        setSavedFlashcardSets(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error("Không thể tải flashcard đã lưu:", err);
    } finally {
      setIsLoadingSavedFlashcards(false);
    }
  };

  useEffect(() => {
    if (activeSubTab === "flashcards") {
      loadSavedFlashcardSets();
    } else {
      loadSavedSummaries();
    }
  }, [activeSubTab]);

  const handleGenerateSummary = async () => {
    if (!summaryTopic.trim()) return;
    setIsGeneratingSummary(true);
    setSummaryResult("");
    setSummarySources([]);
    
    try {
      const res = await fetch("/api/summary", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ topic: summaryTopic })
      });
      const data = await res.json();
      if (res.ok) {
        const summary = data.summary || "";
        const sources = normalizeSummarySources(data);
        setSummaryResult(summary);
        setSummarySources(sources);
        if (summary) {
          saveSummaryLocally(summaryTopic, summary, sources);
        }
      } else {
        alert(data.error || "Có lỗi xảy ra khi tạo tóm tắt.");
      }
    } catch (err: any) {
      alert("Lỗi mạng: " + err.message);
    } finally {
      setIsGeneratingSummary(false);
    }
  };

  const handleGenerateFlashcards = async () => {
    if (!flashcardTopic.trim()) return;
    setIsGeneratingFlashcards(true);
    setFlashcards([]);
    setFlippedCards({});
    setLearnedCards({});
    
    try {
      const res = await fetch("/api/flashcards", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ topic: flashcardTopic, count: flashcardCount })
      });
      const data = await res.json();
      if (res.ok) {
        setFlashcards(data.flashcards || []);
        setActiveSavedSetId(data.saved_set?.id || null);
        await loadSavedFlashcardSets();
      } else {
        alert(data.error || "Có lỗi xảy ra khi tạo flashcards.");
      }
    } catch (err: any) {
      alert("Lỗi mạng: " + err.message);
    } finally {
      setIsGeneratingFlashcards(false);
    }
  };

  const handleOpenSavedFlashcards = async (setId: string) => {
    try {
      const res = await fetch(`/api/flashcards/saved/${setId}`, { headers: getAuthHeaders() });
      const data = await res.json();
      if (!res.ok) {
        alert(getErrorMessage(data, "Không thể mở bộ flashcard đã lưu."));
        return;
      }

      setFlashcardTopic(data.topic || "");
      setFlashcards(data.flashcards || []);
      setFlashcardCount(Math.max(1, data.flashcards?.length || 5));
      setFlippedCards({});
      setLearnedCards({});
      setActiveSavedSetId(setId);
    } catch (err: any) {
      alert("Lỗi mạng: " + err.message);
    }
  };

  const handleDeleteSavedFlashcards = async (setId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/flashcards/saved/${setId}`, {
        method: "DELETE",
        headers: getAuthHeaders()
      });
      if (!res.ok) {
        const data = await res.json();
        alert(getErrorMessage(data, "Không thể xóa bộ flashcard."));
        return;
      }

      setSavedFlashcardSets(prev => prev.filter(item => item.id !== setId));
      if (activeSavedSetId === setId) {
        setActiveSavedSetId(null);
        setFlashcards([]);
      }
    } catch (err: any) {
      alert("Lỗi mạng: " + err.message);
    }
  };

  const toggleFlip = (index: number) => {
    setFlippedCards(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const markLearned = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setLearnedCards(prev => ({ ...prev, [index]: true }));
  };

  const resetLearned = () => {
    setLearnedCards({});
    setFlippedCards({});
  };

  const formatSavedDate = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString(isVi ? "vi-VN" : "en-US", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const formatSourceLabel = (src: any) => {
    const normalized = normalizeSourceItem(src);
    const filename = normalized.filename || "Nguồn tài liệu";
    const location = normalized.page ? `trang ${normalized.page}` : (normalized.slide ? `slide ${normalized.slide}` : "");
    return location ? `${filename} (${location})` : filename;
  };

  const formatSourceExcerpt = (src: any) => {
    const content = String(src?.content || "").replace(/\s+/g, " ").trim();
    return content.length > 160 ? `${content.slice(0, 160)}...` : content;
  };

  const handlePrint = () => {
    window.print();
  };

  const prepareSummaryMarkdown = (text: string) => {
    return text
      .replace(/\\n/g, "\n")
      .replace(/\s+---\s+/g, "\n\n")
      .replace(/\s+(#{1,6}\s+)/g, "\n\n$1")
      .replace(/\s+(\*\s+)/g, "\n$1")
      .replace(/\s+(\d+\.\s+)/g, "\n$1")
      .replace(/([.!?])\s+(?=(?:Định nghĩa|Thuật toán|Ví dụ|Cấu trúc|Điều kiện|Đầu ra|Mục tiêu|Quá trình):)/g, "$1\n\n")
      .trim();
  };

  const renderInlineMarkdown = (line: string) => {
    const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return parts.map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={index} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={index} className="rounded bg-slate-100 px-1.5 py-0.5 text-[0.92em] text-slate-700">{part.slice(1, -1)}</code>;
      }
      return <span key={index}>{part}</span>;
    });
  };

  const renderMarkdown = (text: string) => {
    return prepareSummaryMarkdown(text).split(/\r?\n/).map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={idx} className="h-2" />;

      if (line.startsWith('### ')) {
        return <h3 key={idx} className="mt-6 border-l-4 border-[#7a1c1c] pl-3 text-xl font-semibold text-slate-900">{renderInlineMarkdown(line.replace('### ', ''))}</h3>;
      }
      if (line.startsWith('#### ')) {
        return <h4 key={idx} className="mt-5 text-base font-semibold uppercase tracking-wide text-[#7a1c1c]">{renderInlineMarkdown(line.replace('#### ', ''))}</h4>;
      }
      if (line.startsWith('## ')) {
        return <h2 key={idx} className="mt-6 text-2xl font-semibold text-slate-900">{renderInlineMarkdown(line.replace('## ', ''))}</h2>;
      }
      if (line.startsWith('# ')) {
        return <h1 key={idx} className="mt-6 text-3xl font-semibold text-slate-900">{renderInlineMarkdown(line.replace('# ', ''))}</h1>;
      }
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        return (
          <div key={idx} className="my-2 flex gap-3 rounded-lg bg-slate-50 px-3 py-2 text-slate-700">
            <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-[#7a1c1c]" />
            <span>{renderInlineMarkdown(trimmed.substring(2))}</span>
          </div>
        );
      }
      const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
      if (numberedMatch) {
        return (
          <div key={idx} className="my-2 flex gap-3">
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-rose-50 text-sm font-semibold text-[#7a1c1c]">{numberedMatch[1]}</span>
            <p className="pt-1 text-slate-700">{renderInlineMarkdown(numberedMatch[2])}</p>
          </div>
        );
      }

      return <p key={idx} className="mb-3 text-[15px] leading-7 text-slate-700">{renderInlineMarkdown(trimmed)}</p>;
    });
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 relative">
      {/* CSS for PDF Printing */}
      <style dangerouslySetInnerHTML={{__html: `
        @media print {
          body * {
            visibility: hidden;
          }
          .print-area, .print-area * {
            visibility: visible;
          }
          .print-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            padding: 20px;
            background: white;
          }
          .no-print {
            display: none !important;
          }
        }
      `}} />

      {/* Sub-navigation */}
      <div className="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center no-print shadow-sm z-10">
        <div className="flex space-x-6">
          <button
            onClick={() => setActiveSubTab("summary")}
            className={`flex items-center gap-2 pb-2 font-medium border-b-2 transition-colors ${
              activeSubTab === "summary"
                ? "border-[#7a1c1c] text-[#7a1c1c]"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <BookOpen size={18} />
            {isVi ? "Tóm tắt chương" : "Chapter Summary"}
          </button>
          
          <button
            onClick={() => setActiveSubTab("flashcards")}
            className={`flex items-center gap-2 pb-2 font-medium border-b-2 transition-colors ${
              activeSubTab === "flashcards"
                ? "border-[#7a1c1c] text-[#7a1c1c]"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            <Layers size={18} />
            {isVi ? "Flashcard tự động" : "Auto Flashcards"}
          </button>
        </div>

        <button
          onClick={handlePrint}
          className="flex items-center gap-2 px-4 py-2 bg-rose-50 text-[#7a1c1c] font-semibold rounded-lg hover:bg-rose-100 transition-colors border border-rose-200 shadow-sm"
        >
          <Printer size={16} />
          {isVi ? "Xuất PDF" : "Export PDF"}
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6 print-area">
        <div className="max-w-4xl mx-auto">

          {/* TAB 1: SUMMARY */}
          {activeSubTab === "summary" && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 no-print">
                <h2 className="text-xl font-bold text-gray-800 mb-4">
                  {isVi ? "Tạo tóm tắt có cấu trúc" : "Generate Structured Summary"}
                </h2>
                <div className="flex gap-4">
                  <input
                    type="text"
                    value={summaryTopic}
                    onChange={(e) => setSummaryTopic(e.target.value)}
                    placeholder={isVi ? "Nhập chương hoặc chủ đề (vd: Thuật toán K-Means)" : "Enter chapter or topic..."}
                    className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#7a1c1c] outline-none"
                    onKeyDown={(e) => e.key === "Enter" && handleGenerateSummary()}
                  />
                  <button
                    onClick={handleGenerateSummary}
                    disabled={isGeneratingSummary || !summaryTopic.trim()}
                    className="px-6 py-3 bg-[#7a1c1c] hover:bg-[#5f1515] text-white font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isGeneratingSummary ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <ChevronRight size={18} />
                    )}
                    {isVi ? "Tạo tóm tắt" : "Generate"}
                  </button>
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 no-print">
                <div className="flex items-center justify-between gap-3 mb-4">
                  <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2">
                    <History size={17} className="text-[#7a1c1c]" />
                    {isVi ? "Tóm tắt đã lưu" : "Saved summaries"}
                  </h3>
                  <button
                    onClick={loadSavedSummaries}
                    className="text-xs font-semibold text-[#7a1c1c] hover:text-[#5f1515]"
                  >
                    {isVi ? "Làm mới" : "Refresh"}
                  </button>
                </div>

                {savedSummaries.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    {isVi ? "Chưa có tóm tắt nào. Tóm tắt mới sẽ tự lưu sau khi tạo." : "No saved summaries yet. New summaries are saved automatically."}
                  </p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {savedSummaries.map((item) => (
                      <div
                        key={item.id}
                        className={`border rounded-xl p-4 transition-all hover:shadow-sm ${
                          activeSavedSummaryId === item.id
                            ? "border-rose-300 bg-rose-50"
                            : "border-gray-100 bg-slate-50 hover:bg-white"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <button
                            type="button"
                            onClick={() => openSavedSummary(item)}
                            className="min-w-0 flex-1 text-left"
                          >
                            <p className="font-semibold text-sm text-gray-800 truncate">{item.topic}</p>
                            <p className="text-xs text-gray-500 mt-1">
                              {formatSavedDate(item.updated_at)} • {item.sources?.length || 0} {isVi ? "nguồn" : "sources"}
                            </p>
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteSavedSummary(item.id)}
                            className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                            aria-label={isVi ? "Xóa tóm tắt" : "Delete summary"}
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {summaryResult && (
                <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-gray-100">
                  <div className="mb-6 border-b border-gray-100 pb-5">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-[#7a1c1c]">
                      {isVi ? "Tóm tắt chương" : "Chapter summary"}
                    </p>
                    <h1 className="text-2xl md:text-3xl font-semibold text-gray-900">
                      {summaryTopic}
                    </h1>
                  </div>
                  <div className="max-w-none space-y-1 text-gray-800 font-sans">
                    {renderMarkdown(summaryResult)}
                  </div>
                  
                  <div className="mt-8 pt-6 border-t border-gray-100 text-sm text-gray-500">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <p className="font-semibold text-gray-800">{isVi ? "Nguồn tài liệu tham khảo" : "Reference Sources"}</p>
                      {summarySources.length > 0 && (
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                          {summarySources.length} {isVi ? "nguồn" : "sources"}
                        </span>
                      )}
                    </div>
                    {summarySources.length > 0 ? (
                      <ul className="grid gap-2 md:grid-cols-2">
                        {summarySources.map((src, i) => {
                          const excerpt = formatSourceExcerpt(src);
                          return (
                            <li key={`${formatSourceLabel(src)}-${i}`} className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2.5">
                              <div className="flex items-start gap-2">
                                <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-[#7a1c1c]">{i + 1}</span>
                                <div className="min-w-0">
                                  <div className="font-medium text-gray-700">{formatSourceLabel(src)}</div>
                                  {excerpt && <div className="mt-1 line-clamp-2 text-xs leading-relaxed text-gray-500">{excerpt}</div>}
                                </div>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    ) : (
                      <p className="text-gray-400">
                        {isVi ? "Chưa nhận được nguồn từ máy chủ cho tóm tắt này." : "No sources were returned for this summary."}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: FLASHCARDS */}
          {activeSubTab === "flashcards" && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 no-print">
                <h2 className="text-xl font-bold text-gray-800 mb-4">
                  {isVi ? "Sinh Flashcard thông minh" : "Generate Smart Flashcards"}
                </h2>
                <div className="flex flex-col md:flex-row gap-4">
                  <input
                    type="text"
                    value={flashcardTopic}
                    onChange={(e) => setFlashcardTopic(e.target.value)}
                    placeholder={isVi ? "Chủ đề (vd: Phân loại dữ liệu)" : "Topic..."}
                    className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#7a1c1c] outline-none"
                    onKeyDown={(e) => e.key === "Enter" && handleGenerateFlashcards()}
                  />
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium text-gray-600 whitespace-nowrap">
                      {isVi ? "Số lượng:" : "Count:"}
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={flashcardCount}
                      onChange={(e) => setFlashcardCount(parseInt(e.target.value) || 5)}
                      className="w-20 p-3 border border-gray-300 rounded-xl text-center focus:ring-2 focus:ring-[#7a1c1c] outline-none"
                    />
                  </div>
                  <button
                    onClick={handleGenerateFlashcards}
                    disabled={isGeneratingFlashcards || !flashcardTopic.trim()}
                    className="px-6 py-3 bg-[#7a1c1c] hover:bg-[#5f1515] text-white font-medium rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {isGeneratingFlashcards ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Layers size={18} />
                    )}
                    {isVi ? "Tạo Flashcard" : "Generate"}
                  </button>
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 no-print">
                <div className="flex items-center justify-between gap-3 mb-4">
                  <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2">
                    <History size={17} className="text-[#7a1c1c]" />
                    {isVi ? "Bộ flashcard đã lưu" : "Saved flashcard sets"}
                  </h3>
                  <button
                    onClick={loadSavedFlashcardSets}
                    disabled={isLoadingSavedFlashcards}
                    className="text-xs font-semibold text-[#7a1c1c] hover:text-[#5f1515] disabled:text-gray-400 flex items-center gap-1"
                  >
                    {isLoadingSavedFlashcards && <Loader2 size={13} className="animate-spin" />}
                    {isVi ? "Làm mới" : "Refresh"}
                  </button>
                </div>

                {savedFlashcardSets.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    {isLoadingSavedFlashcards
                      ? (isVi ? "Đang tải..." : "Loading...")
                      : (isVi ? "Chưa có bộ flashcard nào. Bộ mới sẽ tự lưu sau khi tạo." : "No saved sets yet. New flashcards are saved automatically.")}
                  </p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {savedFlashcardSets.map((set) => (
                      <div
                        key={set.id}
                        className={`border rounded-xl p-4 transition-all hover:shadow-sm ${
                          activeSavedSetId === set.id
                            ? "border-rose-300 bg-rose-50"
                            : "border-gray-100 bg-slate-50 hover:bg-white"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <button
                            type="button"
                            onClick={() => handleOpenSavedFlashcards(set.id)}
                            className="min-w-0 flex-1 text-left"
                          >
                            <p className="font-semibold text-sm text-gray-800 truncate">{set.topic}</p>
                            <p className="text-xs text-gray-500 mt-1">
                              {set.count} {isVi ? "thẻ" : "cards"} • {formatSavedDate(set.updated_at)}
                            </p>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleDeleteSavedFlashcards(set.id, e)}
                            className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                            aria-label={isVi ? "Xóa bộ flashcard" : "Delete flashcard set"}
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {flashcards.length > 0 && (
                <div>
                  <div className="flex justify-between items-end mb-6">
                    <div>
                      <h3 className="text-lg font-bold text-gray-800">
                        {flashcardTopic}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {Object.keys(learnedCards).length} / {flashcards.length} {isVi ? "đã thuộc" : "learned"}
                      </p>
                    </div>
                    {Object.keys(learnedCards).length > 0 && (
                      <button 
                        onClick={resetLearned}
                        className="text-sm text-[#7a1c1c] hover:text-[#5f1515] flex items-center gap-1 no-print"
                      >
                        <RotateCcw size={14} /> {isVi ? "Học lại từ đầu" : "Reset progress"}
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {flashcards.map((card, idx) => {
                      const isFlipped = flippedCards[idx];
                      const isLearned = learnedCards[idx];

                      if (isLearned) return null; // Hide learned cards

                      return (
                        <div 
                          key={idx}
                          className="relative h-64 w-full perspective-1000 cursor-pointer group"
                          onClick={() => toggleFlip(idx)}
                        >
                          <div className={`w-full h-full transition-transform duration-500 transform-style-3d shadow-md hover:shadow-lg rounded-2xl ${isFlipped ? "rotate-y-180" : ""}`}>
                            
                            {/* Front of card */}
                            <div className="absolute w-full h-full backface-hidden bg-white border-2 border-rose-100 rounded-2xl p-6 flex flex-col items-center justify-center text-center">
                              <span className="absolute top-4 left-4 text-[10px] font-bold tracking-wider uppercase bg-rose-50 text-[#7a1c1c] px-2 py-1 rounded-full">
                                {card.category}
                              </span>
                              <h4 className="text-lg font-semibold text-gray-800">
                                {card.front}
                              </h4>
                              <p className="absolute bottom-4 text-xs text-gray-400 font-medium no-print group-hover:text-[#7a1c1c] transition-colors">
                                {isVi ? "Bấm để lật thẻ" : "Click to flip"}
                              </p>
                            </div>

                            {/* Back of card */}
                            <div className="absolute w-full h-full backface-hidden bg-gradient-to-br from-slate-900 to-rose-900 text-white rounded-2xl p-6 flex flex-col items-center justify-center text-center rotate-y-180">
                              <div className="overflow-y-auto w-full h-full flex items-center justify-center pb-8">
                                <p className="text-base font-medium leading-relaxed">{card.back}</p>
                              </div>
                              <button
                                onClick={(e) => markLearned(idx, e)}
                                className="absolute bottom-4 left-1/2 transform -translate-x-1/2 px-4 py-2 bg-white/20 hover:bg-white/30 text-white rounded-full text-sm font-semibold flex items-center gap-2 transition-colors no-print backdrop-blur-sm"
                              >
                                <CheckCircle2 size={16} />
                                {isVi ? "Đã thuộc" : "Learned"}
                              </button>
                            </div>

                          </div>
                        </div>
                      );
                    })}
                  </div>
                  
                  {Object.keys(learnedCards).length === flashcards.length && flashcards.length > 0 && (
                    <div className="py-12 flex flex-col items-center justify-center bg-green-50 rounded-2xl border border-green-100">
                      <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-4">
                        <CheckCircle2 size={32} />
                      </div>
                      <h3 className="text-xl font-bold text-green-800 mb-2">
                        {isVi ? "Tuyệt vời! Bạn đã học xong tất cả thẻ." : "Awesome! You learned all cards."}
                      </h3>
                      <button 
                        onClick={resetLearned}
                        className="mt-4 px-6 py-2 bg-white border border-green-200 text-green-700 rounded-lg hover:bg-green-50 transition-colors font-medium shadow-sm"
                      >
                        {isVi ? "Ôn tập lại" : "Review again"}
                      </button>
                    </div>
                  )}

                </div>
              )}
            </div>
          )}
          
        </div>
      </div>
      
      {/* 3D Utilities for tailwind */}
      <style dangerouslySetInnerHTML={{__html: `
        .perspective-1000 { perspective: 1000px; }
        .transform-style-3d { transform-style: preserve-3d; }
        .backface-hidden { backface-visibility: hidden; }
        .rotate-y-180 { transform: rotateY(180deg); }
      `}} />
    </div>
  );
}
