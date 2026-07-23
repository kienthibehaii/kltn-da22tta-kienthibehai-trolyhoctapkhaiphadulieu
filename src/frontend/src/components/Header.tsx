import { useState, useRef, useEffect } from "react";
import { Globe, User, HelpCircle, LogOut } from "lucide-react";
import logo from "../assets/logo.png";
import { Lang, I18nKey } from "../i18n";
import { useCurrentUser } from "../hooks/useCurrentUser";

interface HeaderProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  lang: Lang;
  onToggleLang: () => void;
  t: I18nKey;
  onLogout: () => void;
}

export default function Header({ currentTab, onTabChange, lang, onToggleLang, t, onLogout }: HeaderProps) {
  const currentUser = useCurrentUser();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getTabTitle = () => {
    switch (currentTab) {
      case "overview": return t.nav.overview;
      case "mentor": return t.nav.mentor;
      case "quiz": return t.nav.quiz;
      case "datalab": return t.datalabTitle;
      case "library": return lang === "vi" ? "Th\u01b0 vi\u1ec7n T\u00e0i li\u1ec7u" : "Document Library";
      case "summary_notes": return lang === "vi" ? "T\u00f3m t\u1eaft ch\u01b0\u01a1ng & Flashcard" : "Chapter Summary & Flashcards";
      case "settings": return t.nav.settings;
      case "help": return t.nav.help;
      case "admin": return lang === "vi" ? "Ng\u00e2n h\u00e0ng C\u00e2u h\u1ecfi" : "Question Bank";
      case "my_questions": return lang === "vi" ? "C\u00e2u h\u1ecfi c\u1ee7a t\u00f4i" : "My Questions";
      default: return "MinerAI";
    }
  };

  return (
    <header className="h-14 glass-header flex items-center justify-between px-5 sticky top-0 z-40 transition-all">
      {/* Left Side - Dynamic Tab Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="hidden sm:block">
            <h1 className="font-display font-bold text-lg text-slate-900 leading-tight">{getTabTitle()}</h1>
          </div>
        </div>
      </div>

      {/* Right Side - Utilities */}
      <div className="flex items-center gap-2">
        {/* Language Toggle */}
        <button
          onClick={onToggleLang}
          title={lang === "vi" ? "Chuy\u1ec3n sang ti\u1ebfng Anh" : "Switch to Vietnamese"}
          className="flex items-center gap-1.5 px-2 py-1 bg-white border border-slate-200 hover:border-rose-200 rounded-lg text-[11px] font-medium text-slate-700 hover:text-[#7a1c1c] transition-all active:scale-95"
        >
          <Globe size={14} className="text-[#7a1c1c]" />
          <span>{lang === "vi" ? "EN" : "VI"}</span>
        </button>

        {/* User Profile & Dropdown */}
        <div className="relative pl-4 border-l border-slate-200" ref={dropdownRef}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 text-left hover:opacity-80 transition-opacity"
          >
            <div className="text-right hidden md:block">
              <p className="text-xs font-semibold text-slate-800 leading-tight">{currentUser.full_name}</p>
              <p className="text-[10px] text-slate-500 truncate max-w-[140px] leading-tight mt-0.5" title={currentUser.email}>
                {currentUser.email}
              </p>
            </div>

            <div className="w-7 h-7 bg-gradient-to-br from-slate-100 to-slate-200 rounded-lg flex items-center justify-center border border-slate-200 text-slate-600 hover:shadow-sm transition-shadow">
              <User size={15} />
            </div>
          </button>

          {/* Dropdown Menu */}
          {showDropdown && (
            <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-lg border border-slate-100 py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
              <button
                onClick={() => {
                  setShowDropdown(false);
                  onTabChange("help");
                }}
                className={`w-full px-4 py-2.5 text-left text-sm font-medium flex items-center gap-2.5 transition-colors ${currentTab === "help" ? "bg-rose-50 text-[#7a1c1c]" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
              >
                <HelpCircle size={18} className={currentTab === "help" ? "text-[#7a1c1c]" : "text-slate-400"} />
                {t.nav.help}
              </button>

              <div className="h-px bg-slate-100 my-1 mx-3" />

              <button
                onClick={() => {
                  setShowDropdown(false);
                  onLogout();
                }}
                className="w-full px-4 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-rose-50 hover:text-rose-600 flex items-center gap-2.5 transition-colors"
              >
                <LogOut size={18} className="text-slate-400" />
                {t.signOut}
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
