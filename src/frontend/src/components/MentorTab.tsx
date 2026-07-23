import React, { useState, useRef, useEffect } from "react";
import { Send, Copy, AlertCircle, RefreshCw, Book } from "lucide-react";
import { ChatMessage, ChatThread } from "../types";
import { I18nKey, Lang } from "../i18n";
import logo from "../assets/logo.png";
import { getAuthItem } from "../authStorage";

interface MentorTabProps {
  t: I18nKey;
  lang: Lang;
  threads: ChatThread[];
  setThreads: React.Dispatch<React.SetStateAction<ChatThread[]>>;
  activeThreadId: string;
  messageHistory: { [key: string]: ChatMessage[] };
  setMessageHistory: React.Dispatch<React.SetStateAction<{ [key: string]: ChatMessage[] }>>;
}

const availableDocuments = [
  { id: "all", name: "Tất cả tài liệu" },
  { id: "DM3.pdf", name: "Data Mining: Concepts and Techniques (3rd Edition)" },
  { id: "01intro.pdf", name: "Chương 1: Giới thiệu" },
  { id: "02data.pdf", name: "Chương 2: Dữ liệu" },
  { id: "03preprocessing.pdf", name: "Chương 3: Tiền xử lý dữ liệu" },
  { id: "06fpbasic.pdf", name: "Chương 6: Khai phá tập phổ biến cơ bản" },
  { id: "08classbasic.pdf", name: "Chương 8: Phân lớp dữ liệu cơ bản" },
  { id: "10clusbasic.pdf", name: "Chương 10: Phân cụm dữ liệu cơ bản" },
];

export default function MentorTab({
  t, lang,
  threads, setThreads, activeThreadId,
  messageHistory, setMessageHistory
}: MentorTabProps) {
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState("all");

  const activeMessages = messageHistory[activeThreadId] || [];
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const formatCitationChip = (cit: any) => {
    const raw = String(cit?.friendlySource || cit?.filename || cit?.source || "");
    const firstLine = raw.split("\n")[0];
    const fileName = String(cit?.filename || firstLine);
    const page = cit?.page;
    const slide = cit?.slide;
    if (/\.(docx?|txt)\b/i.test(fileName) || /\.(docx?|txt)\b/i.test(firstLine)) {
      return firstLine.replace(/\s*,\s*(?:p\.?|trang|page)\s*\d+\s*$/i, "");
    }
    const withoutOldPage = firstLine.replace(/\s*,\s*(?:p\.?|tr\.?|trang|page)\s*\d+\s*$/i, "");
    if ((/\.pdf\b/i.test(fileName) || /\.pdf\b/i.test(firstLine)) && page && page !== "N/A") {
      return `${withoutOldPage}, tr.${page}`;
    }
    if (slide) {
      return `${withoutOldPage}, slide ${slide}`;
    }
    if (page && page !== "N/A") {
      return `${withoutOldPage}, trang ${page}`;
    }
    return withoutOldPage;
  };

  useEffect(() => {
    const el = messagesContainerRef.current;
    if (el) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [activeMessages.length, loading]);

  const handleSendMessage = async (customText?: string) => {
    const textToSend = (customText || inputText).trim();
    if (!textToSend || loading) return;

    if (!customText) setInputText("");

    const userMessage: ChatMessage = {
      id: Math.random().toString(),
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const updatedMessages = [...activeMessages, userMessage];
    setMessageHistory((prev) => ({ ...prev, [activeThreadId]: updatedMessages }));
    setLoading(true);

    const timeString = new Date().toLocaleString(lang === "vi" ? "vi-VN" : "en-US", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric" });
    const isNewTitle = threads.find(th => th.id === activeThreadId)?.title === t.mentorNewThreadTitle || 
                       threads.find(th => th.id === activeThreadId)?.title === "New conversation";
    const newTitle = isNewTitle ? textToSend.slice(0, 36) + (textToSend.length > 36 ? "..." : "") : "";

    setThreads((prev) =>
      prev.map((th) => {
        if (th.id === activeThreadId) {
          return {
            ...th,
            dateGroup: timeString,
            title: isNewTitle ? newTitle : th.title
          };
        }
        return th;
      })
    );

    try {
      const token = getAuthItem("minerai_token");
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const isMongoId = /^[0-9a-fA-F]{24}$/.test(activeThreadId);
      if (isMongoId) {
        try {
          await fetch(`/api/conversations/${activeThreadId}/messages`, {
            method: "POST",
            headers,
            body: JSON.stringify({
              conversation_id: activeThreadId,
              role: "user",
              content: textToSend
            })
          });
        } catch (dbErr) {
          console.error("Lỗi khi lưu tin nhắn user lên DB:", dbErr);
        }

        // Sync new title if first message
        if (isNewTitle && newTitle) {
          try {
            await fetch(`/api/conversations/${activeThreadId}/title`, {
              method: "PUT",
              headers,
              body: JSON.stringify({ title: newTitle })
            });
          } catch (dbErr) {
            console.error("Lỗi khi đồng bộ tiêu đề lên DB:", dbErr);
          }
        }
      }

      // 2. Query LLM via backend chat bridge
      const response = await fetch("/api/chat", {
        method: "POST",
        headers,
        body: JSON.stringify({
          thread_id: activeThreadId,
          messages: updatedMessages.map((m) => ({
            role: m.role,
            parts: [{ text: m.content }],
          })),
          metadata_filter: selectedFilter === "all" ? null : { source: selectedFilter }
        }),
      });

      if (!response.ok) throw new Error("Lỗi mạng khi kết nối máy chủ");

      const data = await response.json();
      const aiMessage: ChatMessage = {
        id: Math.random().toString(),
        role: "model",
        content: data.text || (lang === "vi"
          ? "Xin lỗi, tôi gặp sự cố khi xử lý phản hồi."
          : "Sorry, I encountered an issue processing the response."),
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        citations: data.citations || [],
      };
      setMessageHistory((prev) => ({ ...prev, [activeThreadId]: [...updatedMessages, aiMessage] }));

      // 3. Sync Assistant Message to MongoDB Atlas
      if (isMongoId) {
        try {
          await fetch(`/api/conversations/${activeThreadId}/messages`, {
            method: "POST",
            headers,
            body: JSON.stringify({
              conversation_id: activeThreadId,
              role: "assistant",
              content: aiMessage.content,
              metadata: {
                citations: aiMessage.citations || []
              }
            })
          });
        } catch (dbErr) {
          console.error("Lỗi khi lưu tin nhắn AI lên DB:", dbErr);
        }
      }
    } catch (err: any) {
      const errorMessage: ChatMessage = {
        id: Math.random().toString(),
        role: "model",
        content: lang === "vi"
          ? `❌ Trục trặc kỹ thuật: Không thể kết nối máy chủ. Vui lòng thử lại.\n\nLỗi: ${err.message}`
          : `❌ Technical error: Cannot connect to server. Please try again.\n\nError: ${err.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessageHistory((prev) => ({ ...prev, [activeThreadId]: [...updatedMessages, errorMessage] }));
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    alert(t.mentorCopied);
  };

  const handleClearCurrentChat = async () => {
    const confirmMsg = lang === "vi"
      ? "Xóa toàn bộ tin nhắn trong cuộc trò chuyện này?"
      : "Clear all messages in this conversation?";
    if (!window.confirm(confirmMsg)) return;

    setMessageHistory((prev) => ({
      ...prev,
      [activeThreadId]: [{
        id: `m-clear-${Date.now()}`,
        role: "model",
        content: t.mentorNewThreadGreet,
        timestamp: lang === "vi" ? "Vừa xong" : "Just now",
      }],
    }));

    const isMongoId = /^[0-9a-fA-F]{24}$/.test(activeThreadId);
    if (isMongoId) {
      try {
        const token = getAuthItem("minerai_token");
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        await fetch(`/api/conversations/${activeThreadId}/messages`, {
          method: "DELETE",
          headers
        });
      } catch (err) {
        console.error("Lỗi khi reset lịch sử trên server:", err);
      }
    }
  };

  const quickQuestions = t.quickQuestions;

  const renderMessageContent = (msg: ChatMessage) => {
    const text = msg.content;
    const parts = text.split("```");

    return (
      <div className="space-y-4">
        {parts.map((part, index) => {
          if (index % 2 !== 0) {
            const lines = part.split("\n");
            const language = lines[0]?.trim();
            const code = lines.slice(1).join("\n").trim();
            return (
              <div key={index} className="my-4 rounded-xl overflow-hidden border border-slate-200 shadow-md font-mono text-sm">
                <div className="bg-slate-900 text-slate-200 px-4 py-2 flex justify-between items-center text-xs font-medium">
                  <span>{language || "Code"}</span>
                  <button
                    onClick={() => handleCopyCode(code)}
                    className="flex items-center gap-1.5 hover:text-white transition-colors cursor-pointer"
                  >
                    <Copy size={14} /> Copy
                  </button>
                </div>
                <pre className="bg-[#0b1220] text-slate-100 p-4 overflow-x-auto leading-relaxed text-sm">
                  <code>{code}</code>
                </pre>
              </div>
            );
          }

          const paragraphLines = part.split("\n");
          return (
            <div key={index} className="space-y-3 leading-relaxed">
              {paragraphLines.map((line, lIdx) => {
                let processedLine = line.trim();
                if (!processedLine) return <div key={lIdx} className="h-2" />;

                if (processedLine.startsWith("###")) {
                  return (
                    <h4 key={lIdx} className="text-[15px] font-semibold text-slate-800 pt-3">
                      {processedLine.replace(/^###\s*/, "")}
                    </h4>
                  );
                }
                if (processedLine.startsWith("##")) {
                  return (
                    <h3 key={lIdx} className="text-[16px] font-semibold text-slate-800 pt-3">
                      {processedLine.replace(/^##\s*/, "")}
                    </h3>
                  );
                }
                if (/^─+$/.test(processedLine) || processedLine === "---") {
                  return <hr key={lIdx} className="my-4 border-slate-200" />;
                }

                if (processedLine === "Tài liệu tham khảo") {
                  return (
                    <div key={lIdx} className="text-xs font-semibold text-[#7a1c1c] uppercase tracking-widest mt-6 mb-2 flex items-center gap-2">
                      <Book size={14} /> {processedLine}
                    </div>
                  );
                }

                const isBlockquote = processedLine.startsWith(">") || processedLine.startsWith("&gt;");
                let cleanLine = processedLine.replace(/^>\s*/, "").replace(/^&gt;\s*/, "");

                const isBullet = /^[\*\-]\s/.test(processedLine);
                if (isBullet) cleanLine = processedLine.replace(/^[\*\-]\s*/, "");

                const isNumbered = /^\d+\.\s/.test(processedLine);

                const boldRegex = /\*\*(.*?)\*\*/g;
                const parts = cleanLine.split(boldRegex);

                if (isBlockquote) {
                  return (
                    <blockquote key={lIdx} className="border-l-4 border-rose-200 bg-rose-50/60 pl-4 py-2 text-slate-600 italic my-2 rounded-r-lg">
                      {parts.map((p, i) => i % 2 === 1 ? <strong key={i}>{p}</strong> : p)}
                    </blockquote>
                  );
                }
                if (isBullet) {
                  return (
                    <li key={lIdx} className="list-disc ml-6 text-slate-700">
                      {parts.map((p, i) => i % 2 === 1 ? <strong key={i}>{p}</strong> : p)}
                    </li>
                  );
                }
                if (isNumbered) {
                  return (
                    <div key={lIdx} className="pl-6 text-slate-700">
                      {parts.map((p, i) => i % 2 === 1 ? <strong key={i}>{p}</strong> : p)}
                    </div>
                  );
                }

                return (
                  <p key={lIdx} className="text-slate-700 text-[15px] leading-relaxed">
                    {parts.map((p, i) => i % 2 === 1 ? <strong key={i} className="font-semibold text-slate-900">{p}</strong> : p)}
                  </p>
                );
              })}
            </div>
          );
        })}
        {msg.citations && msg.citations.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap gap-2">
            {msg.citations.map((cit, idx) => (
              <div key={idx} className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-[#7a1c1c] border border-rose-100 rounded-full text-xs font-medium shadow-sm cursor-help transition-transform hover:scale-105" title={formatCitationChip(cit)}>
                {cit.index && <span className="font-bold">[{cit.index}]</span>}
                <span className="truncate max-w-[220px]">{formatCitationChip(cit)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-1 h-full overflow-hidden bg-transparent">
      <section className="flex-1 flex flex-col min-h-0 overflow-hidden">

        {/* Messages Area */}
        <div
          ref={messagesContainerRef}
          className="flex-1 min-h-0 overflow-y-auto px-4 md:px-10 lg:px-20 py-5 space-y-5"
        >
          {activeMessages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div key={msg.id} className={`flex w-full ${isUser ? "justify-end" : "justify-start"} animate-fade-in`}>
                <div className={`w-full max-w-[86%] lg:max-w-[78%] flex ${isUser ? "flex-row-reverse gap-3" : "gap-4"}`}>
                  {!isUser && (
                    <div className="w-10 h-10 rounded-2xl bg-white border border-slate-100 flex items-center justify-center flex-shrink-0 shadow-lg ring-2 ring-white">
                      <img src={logo} alt="MinerAI" className="w-8 h-8 object-contain" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <div className={`px-6 py-4 rounded-2xl shadow-sm text-[15px] leading-relaxed break-words transition-all ${isUser
                        ? "bg-gradient-to-r from-slate-800 to-slate-700 text-white rounded-br-xl shadow-md"
                        : "bg-white border border-slate-100 text-slate-800 rounded-bl-xl"
                      }`}>
                      {isUser ? (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        renderMessageContent(msg)
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-2 px-2 font-medium flex items-center gap-2">
                      <span>{msg.timestamp}</span>
                      {!isUser && msg.citations && msg.citations.length > 0 && (
                        <span className="bg-rose-50 text-[#7a1c1c] px-2 py-0.5 rounded-full text-xs font-medium">Nguồn {msg.citations.length}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex w-full justify-start">
              <div className="flex gap-4 w-full max-w-[86%] lg:max-w-[78%]">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-rose-800 to-rose-900 flex items-center justify-center text-white flex-shrink-0 animate-pulse shadow-lg">
                  <RefreshCw size={16} />
                </div>
                <div className="bg-white/90 border border-slate-100 px-5 py-3 rounded-2xl shadow-sm">
                  <div className="flex gap-2">
                    <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full animate-bounce" />
                    <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full animate-bounce delay-150" />
                    <div className="w-2.5 h-2.5 bg-indigo-400 rounded-full animate-bounce delay-300" />
                  </div>
                  <p className="text-sm text-slate-500 mt-2 font-medium">Đang suy nghĩ...</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="flex-shrink-0 p-2.5 bg-white/70 backdrop-blur-sm border-t border-slate-100">
          <div className="w-full max-w-[92%] lg:max-w-[78%] mx-auto">
            {/* Main Input */}
            <div className="flex gap-2 items-end bg-white border border-slate-100 rounded-xl p-1.5 shadow-sm">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={t.mentorPlaceholder}
                className="flex-1 resize-none bg-transparent border-none px-2 py-1.5 text-[13px] leading-relaxed min-h-[32px] max-h-28 focus:outline-none focus:ring-0 text-slate-700 placeholder-slate-400"
                disabled={loading}
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={loading || !inputText.trim()}
                className="w-8.5 h-8.5 bg-[#7a1c1c] hover:bg-[#5a1515] disabled:from-slate-200 disabled:to-slate-300 disabled:text-slate-400 text-white rounded-full flex items-center justify-center transition-all flex-shrink-0 shadow-sm hover:shadow-md"
              >
                <Send size={14} className="ml-0.5" />
              </button>
            </div>

            <div className="text-center mt-1.5 text-[10px] text-slate-500 flex items-center justify-center gap-1.5 leading-snug">
              <AlertCircle size={11} />
              <span>{t.mentorWarning}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
