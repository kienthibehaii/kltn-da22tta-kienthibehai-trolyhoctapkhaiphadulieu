import React, { useState, useRef, useEffect } from "react";
import {
  LayoutGrid,
  BotMessageSquare,
  FileQuestion,
  FlaskConical,
  BookOpen,
  ClipboardList,
  Database,
  Plus,
  Trash2,
  Calendar,
  NotebookPen,
  MoreHorizontal,
  Pencil,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { I18nKey, Lang } from "../i18n";
import { ChatThread } from "../types";
import logo from "../assets/logo.png";

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  onNewAnalysis: () => void;
  t: I18nKey;
  threads: ChatThread[];
  activeThreadId: string;
  onSelectThread: (id: string) => void;
  onDeleteThread: (id: string, e: React.MouseEvent) => void;
  onNewThread: () => void;
  lang: Lang;
  onLogout?: () => void;
  userRole?: string;
  onRenameThread: (id: string, newTitle: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export default function Sidebar({
  currentTab,
  onTabChange,
  onNewAnalysis,
  t,
  threads,
  activeThreadId,
  onSelectThread,
  onDeleteThread,
  onNewThread,
  lang,
  userRole,
  onRenameThread,
  isCollapsed,
  onToggleCollapse,
}: SidebarProps) {
  const [openDropdownId, setOpenDropdownId] = useState<string | null>(null);
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdownId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleEditClick = (thread: ChatThread, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingThreadId(thread.id);
    setEditTitle(thread.title);
    setOpenDropdownId(null);
  };

  const handleSaveEdit = (id: string) => {
    if (editTitle.trim()) {
      onRenameThread(id, editTitle.trim());
    }
    setEditingThreadId(null);
  };

  const menuItems = [
    { id: "overview", label: t.nav.overview, icon: LayoutGrid },
    { id: "mentor", label: t.nav.mentor, icon: BotMessageSquare },
    { id: "quiz", label: t.nav.quiz, icon: FileQuestion },
    { id: "my_questions", label: lang === "vi" ? "Đề tự tạo" : "My Bank", icon: ClipboardList },
    { id: "summary_notes", label: lang === "vi" ? "Tóm tắt & Ghi chú" : "Summary & Notes", icon: NotebookPen },
    { id: "datalab", label: t.nav.datalab, icon: FlaskConical },
    { id: "library", label: t.nav.library, icon: BookOpen },
  ];

  if (userRole === "admin") {
    menuItems.push({ id: "admin", label: "Ngân hàng Câu hỏi", icon: Database });
  }

  const historyPanel = (
    <aside className="w-80 glass-panel !rounded-none !border-y-0 !border-r-0 border-l border-white/60 flex flex-col h-screen fixed right-0 top-0 text-slate-800 select-none z-40 overflow-hidden shadow-sm">
      <div className="px-5 pb-6 flex-1 min-h-0 flex flex-col">
        <div className="flex items-center justify-between mb-4 pt-6 px-2">
          <div className="uppercase text-[11px] font-semibold tracking-widest text-slate-600">
            {t.mentorHistoryTitle || "Lịch sử trò chuyện"}
          </div>
          <button
            onClick={onNewThread}
            className="text-[#7a1c1c] hover:text-[#7a1c1c] p-1.5 -mr-1.5 rounded-xl hover:bg-rose-50 transition-all"
            title={lang === "vi" ? "Cuộc trò chuyện mới" : "New conversation"}
          >
            <Plus size={16} />
          </button>
        </div>

        <div className="space-y-1.5 pr-1 flex-1 min-h-0 overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-slate-200 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-300">
          {threads.map((thread) => (
            <div key={thread.id} className="group relative">
              <button
                onClick={() => onSelectThread(thread.id)}
                className={`w-full text-left p-3 pr-10 rounded-2xl transition-all border ${
                  activeThreadId === thread.id && currentTab === "mentor"
                    ? "bg-white/60 border-white shadow-sm"
                    : "border-transparent hover:bg-white/40"
                }`}
              >
                {editingThreadId === thread.id ? (
                  <input
                    type="text"
                    autoFocus
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => handleSaveEdit(thread.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveEdit(thread.id);
                      if (e.key === "Escape") setEditingThreadId(null);
                    }}
                    className="w-full bg-white border border-rose-200 rounded-lg px-2 py-1 text-[13px] text-slate-800 outline-none focus:ring-1 focus:ring-rose-800"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="font-semibold text-[13px] truncate leading-tight text-slate-900" title={thread.title}>
                    {thread.title}
                  </div>
                )}
                <div className="flex items-center gap-1.5 text-[11px] font-medium text-slate-600 mt-2">
                  <Calendar size={12} />
                  <span>{thread.dateGroup}</span>
                </div>
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setOpenDropdownId(openDropdownId === thread.id ? null : thread.id);
                }}
                className={`absolute top-4 right-3 p-1.5 rounded-xl transition-all ${
                  openDropdownId === thread.id
                    ? "text-[#7a1c1c] bg-rose-50 opacity-100"
                    : "text-slate-400 hover:text-[#7a1c1c] hover:bg-rose-50 opacity-0 group-hover:opacity-100"
                }`}
                title={lang === "vi" ? "Tùy chọn" : "Options"}
              >
                <MoreHorizontal size={16} />
              </button>

              {openDropdownId === thread.id && (
                <div
                  ref={dropdownRef}
                  className="absolute top-8 right-3 w-36 bg-white rounded-xl shadow-[0_10px_25px_-5px_rgba(79,70,229,0.15)] border border-rose-50 py-1 z-50"
                >
                  <button
                    onClick={(e) => handleEditClick(thread, e)}
                    className="w-full text-left px-3 py-2 text-[13px] text-slate-700 hover:bg-rose-50 hover:text-[#7a1c1c] flex items-center gap-2"
                  >
                    <Pencil size={14} /> Đổi tên
                  </button>
                  <button
                    onClick={(e) => {
                      setOpenDropdownId(null);
                      onDeleteThread(thread.id, e);
                    }}
                    className="w-full text-left px-3 py-2 text-[13px] text-rose-600 hover:bg-rose-50 flex items-center gap-2"
                  >
                    <Trash2 size={14} /> Xóa
                  </button>
                </div>
              )}
            </div>
          ))}

          {threads.length === 0 && (
            <div className="text-center py-12 text-slate-400 text-sm">
              Chưa có cuộc trò chuyện nào.<br />
              Hãy bắt đầu một cuộc chat mới!
            </div>
          )}
        </div>
      </div>
    </aside>
  );

  return (
    <>
      <aside
        className={`${
          isCollapsed ? "w-20" : "w-64"
        } glass-panel !rounded-none !border-y-0 !border-l-0 border-r border-white/60 flex flex-col h-screen fixed left-0 top-0 text-slate-800 select-none z-50 overflow-hidden shadow-sm transition-[width] duration-300`}
      >
        <div className={isCollapsed ? "p-3.5" : "p-4"}>
          <div className={`flex items-center ${isCollapsed ? "justify-center mb-4" : "gap-3 mb-5 px-1"}`}>
            <img src={logo} alt="MinerAI Logo" className={`${isCollapsed ? "w-9 h-9" : "w-10 h-10"} object-contain`} />
            <div className={isCollapsed ? "hidden" : ""}>
              <h1 className="font-display font-bold text-lg text-slate-900">MinerAI</h1>
              <p className="text-[10px] text-[#7a1c1c]/70 font-medium tracking-widest uppercase">Học cùng bạn</p>
            </div>
          </div>

          <button
            onClick={onToggleCollapse}
            className={`absolute p-1.5 rounded-lg text-slate-500 hover:text-[#7a1c1c] hover:bg-rose-50 transition-all ${
              isCollapsed ? "top-14 left-1/2 -translate-x-1/2" : "top-4 right-3"
            }`}
            title={isCollapsed ? (lang === "vi" ? "Mở menu" : "Expand menu") : (lang === "vi" ? "Cất gọn menu" : "Collapse menu")}
          >
            {isCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>

          <button
            onClick={onNewAnalysis}
            className={`w-full ${isCollapsed ? "mt-10" : "mt-4"} py-2 px-3 bg-[#7a1c1c] hover:bg-[#5f1515] text-white rounded-lg font-medium flex items-center justify-center gap-2 shadow-sm shadow-[#7a1c1c]/20 active:scale-[0.97] transition-all duration-200 ${
              isCollapsed ? "aspect-square px-0" : ""
            }`}
            title={t.newAnalysis}
          >
            <Plus size={16} />
            {!isCollapsed && <span className="text-[12px]">{t.newAnalysis}</span>}
          </button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-slate-200 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-300">
          <div className={`${isCollapsed ? "px-3" : "px-4"} py-5`}>
            <div className={`uppercase text-[10px] font-semibold tracking-widest text-slate-600 mb-2 px-2 ${isCollapsed ? "hidden" : ""}`}>
              Khám phá
            </div>
            <nav className="flex flex-col gap-1">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onTabChange(item.id)}
                    className={`w-full py-2 rounded-lg text-left font-semibold flex items-center transition-all duration-200 group ${
                      isCollapsed ? "justify-center px-0" : "gap-2.5 px-3"
                    } ${
                      isActive
                        ? "bg-rose-50 text-[#7a1c1c] shadow-sm"
                        : "text-slate-700 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                    title={item.label}
                  >
                    <div className={`p-1 rounded-lg transition-colors ${isActive ? "bg-white shadow-sm" : "bg-transparent group-hover:bg-white"}`}>
                      <Icon size={15} className={isActive ? "text-[#7a1c1c]" : "text-slate-400 group-hover:text-rose-700"} />
                    </div>
                    {!isCollapsed && <span className="text-[12px] truncate">{item.label}</span>}
                    {isActive && !isCollapsed && <div className="ml-auto w-2 h-2 bg-rose-800 rounded-full" />}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </aside>

      {currentTab === "mentor" && historyPanel}
    </>
  );
}
