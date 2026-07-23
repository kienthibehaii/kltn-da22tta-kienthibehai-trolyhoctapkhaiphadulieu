import { ShieldCheck, Cpu, Sparkles, Database, Server } from "lucide-react";
import { I18nKey } from "../i18n";

interface SettingsTabProps {
  t: I18nKey;
}

export default function SettingsTab({ t }: SettingsTabProps) {
  const isVi = t.statUnit.docs === "tệp";

  const systemInfo = [
    {
      label: isVi ? "Trạng thái Hệ thống" : "System Status",
      value: isVi ? "Hoạt động bình thường" : "Running normally",
      color: "text-rose-800"
    },
    {
      label: isVi ? "Mô hình ngôn ngữ" : "Language Model",
      value: "Gemini Flash (Google)",
      color: "text-sky-500 font-bold"
    },
    {
      label: isVi ? "Cơ sở tri thức" : "Knowledge Base",
      value: "5,984 vectors · 17 tài liệu",
      color: "text-purple-600 font-bold"
    },
    {
      label: isVi ? "Quốc gia / Ngôn ngữ" : "Country / Language",
      value: isVi ? "Việt Nam (Tiếng Việt)" : "Vietnam (Vietnamese)",
      color: "text-slate-500"
    },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-[#0b1c3c] tracking-tight font-display">{t.settingsTitle}</h2>
        <p className="text-gray-500 mt-1.5 text-sm font-medium">{t.settingsSubtitle}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Student Profile Card */}
        <div className="bg-white border border-[#e2e8f0] rounded-xl p-6 shadow-sm space-y-5">
          <h3 className="text-xs font-bold text-gray-400 tracking-wider uppercase block border-b border-gray-100 pb-3">
            {t.profileSection}
          </h3>

          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#05113c] to-[#0ea5e9] flex items-center justify-center text-white text-xl font-bold border border-slate-100 shadow-sm overflow-hidden">
              <img
                src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
                alt="Profile Avatar"
                className="w-full h-full object-cover"
                referrerPolicy="no-referrer"
              />
            </div>
            <div>
              <h4 className="text-sm font-bold text-gray-900">
                {isVi ? "Kiên Thị Bé Hai" : "Kien Thi Be Hai"}
              </h4>
              <p className="text-[10px] text-gray-400 font-medium">
                {isVi ? "MSSV: 110122218 · Đại học Trà Vinh" : "Student ID: 110122218 · Tra Vinh University"}
              </p>
            </div>
          </div>

          <div className="space-y-3.5 pt-2">
            <div>
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wide mb-1">{t.studentIdLabel}</label>
              <input
                type="text"
                disabled
                value="110122218"
                className="w-full bg-slate-50 border border-[#cbd5e1] p-2 rounded text-xs text-gray-500 select-all font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wide mb-1">{t.emailLabel}</label>
              <input
                type="text"
                disabled
                value="110122218@student.tvu.edu.vn"
                className="w-full bg-slate-50 border border-[#cbd5e1] p-2 rounded text-xs text-gray-500 select-all font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wide mb-1">
                {isVi ? "Môn học" : "Course"}
              </label>
              <input
                type="text"
                disabled
                value={isVi ? "Khai phá Dữ liệu (INT3210) · 3 tín chỉ" : "Data Mining (INT3210) · 3 Credits"}
                className="w-full bg-slate-50 border border-[#cbd5e1] p-2 rounded text-xs text-gray-500 select-all font-mono"
              />
            </div>
          </div>
        </div>

        {/* AI & Security */}
        <div className="bg-white border border-[#e2e8f0] rounded-xl p-6 shadow-sm space-y-5">
          <h3 className="text-xs font-bold text-gray-400 tracking-wider uppercase block border-b border-gray-100 pb-3">
            {t.securitySection}
          </h3>

          <div className="p-4 bg-sky-50/50 rounded-xl border border-sky-100 space-y-3">
            <div className="flex items-center gap-2 text-sky-700 font-bold text-xs">
              <ShieldCheck size={16} />
              <span>{isVi ? "Bảo mật API Server-side" : "Server-side API Security"}</span>
            </div>
            <p className="text-[11px] text-gray-600/90 leading-relaxed font-sans">
              {isVi
                ? "Toàn bộ yêu cầu đến Gemini API được xử lý và mã hóa tại server. Khóa API không bao giờ lộ ra phía frontend của trình duyệt."
                : "All requests to Gemini API are processed and encrypted server-side. API keys are never exposed to the browser frontend."}
            </p>
          </div>

          <div className="p-4 bg-purple-50/50 rounded-xl border border-purple-100 space-y-2">
            <div className="flex items-center gap-2 text-purple-700 font-bold text-xs">
              <Database size={16} />
              <span>{isVi ? "Cơ sở tri thức RAG" : "RAG Knowledge Base"}</span>
            </div>
            <p className="text-[11px] text-gray-600/90 leading-relaxed">
              {isVi
                ? "5,984 vectors được lập chỉ mục từ 13 bài giảng PPTX, 2 đề cương DOCX và 2 sách giáo khoa PDF. Sử dụng Hybrid Search (Vector + BM25) để tìm kiếm chính xác."
                : "5,984 vectors indexed from 13 PPTX lecture slides, 2 DOCX curriculum files, and 2 PDF textbooks. Uses Hybrid Search (Vector + BM25) for precise retrieval."}
            </p>
          </div>

          <div className="p-4 bg-rose-50/50 rounded-xl border border-rose-100 space-y-2">
            <div className="flex items-center gap-2 text-[#7a1c1c] font-bold text-xs">
              <Cpu size={16} />
              <span>{isVi ? "Mô hình AI" : "AI Model"}</span>
            </div>
            <p className="text-[11px] text-gray-600/90 leading-relaxed">
              {isVi
                ? "Google Gemini Flash · Embedding: sentence-transformers/all-MiniLM-L6-v2 · Vector DB: ChromaDB"
                : "Google Gemini Flash · Embedding: sentence-transformers/all-MiniLM-L6-v2 · Vector DB: ChromaDB"}
            </p>
          </div>
        </div>
      </div>

      {/* System diagnostics */}
      <div className="bg-slate-50 border rounded-xl p-6 shadow-sm font-sans space-y-4">
        <h3 className="text-xs font-bold text-slate-500 tracking-wider uppercase flex items-center gap-1.5">
          <Sparkles size={13} className="text-sky-500" />
          {t.systemSection}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {systemInfo.map((info, idx) => (
            <div key={idx} className="bg-white border border-slate-150 p-4 rounded-lg shadow-sm">
              <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{info.label}</p>
              <p className={`text-xs font-semibold mt-1 truncate ${info.color}`}>{info.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
