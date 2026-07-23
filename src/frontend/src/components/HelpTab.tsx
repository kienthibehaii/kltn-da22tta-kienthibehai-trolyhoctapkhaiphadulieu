import { HelpCircle, BookOpen, MessageSquare, Terminal, Database, Sparkles } from "lucide-react";
import { I18nKey } from "../i18n";

interface HelpTabProps {
  t: I18nKey;
}

export default function HelpTab({ t }: HelpTabProps) {
  const icons = [Database, MessageSquare, Terminal, BookOpen];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto w-20 h-20 bg-gradient-to-br from-rose-100 to-violet-100 rounded-2xl flex items-center justify-center mb-6">
          <HelpCircle className="text-[#7a1c1c]" size={48} />
        </div>
        <h2 className="text-4xl font-display font-semibold tracking-tight text-slate-900">
          {t.helpTitle}
        </h2>
        <p className="text-lg text-slate-600 mt-3 max-w-md mx-auto">
          {t.helpSubtitle}
        </p>
      </div>

      {/* FAQ Section */}
      <div>
        <h3 className="text-xl font-semibold text-slate-800 mb-8 flex items-center gap-3">
          <Sparkles className="text-[#7a1c1c]" size={24} />
          Câu hỏi thường gặp
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {t.faqs.map((faq, idx) => {
            const Icon = icons[idx % icons.length] || HelpCircle;
            return (
              <div 
                key={idx} 
                className="bg-white border border-slate-100 rounded-2xl p-6 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group"
              >
                <div className="flex items-start gap-5">
                  <div className="w-10 h-10 rounded-2xl bg-rose-50 flex items-center justify-center text-[#7a1c1c] flex-shrink-0 group-hover:scale-110 transition-transform">
                    <Icon size={26} />
                  </div>
                  <div className="space-y-3">
                    <h4 className="text-lg font-semibold text-slate-800 leading-tight">
                      {faq.q}
                    </h4>
                    <p className="text-slate-600 leading-relaxed text-[15px]">
                      {faq.a}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Tips & Guidance */}
      <div className="bg-gradient-to-br from-rose-50 to-rose-50 border border-rose-100 rounded-2xl p-8">
        <div className="flex items-center gap-4 mb-8">
          <div className="p-3 bg-white rounded-2xl shadow-sm">
            <BookOpen className="text-[#7a1c1c]" size={28} />
          </div>
          <div>
            <h3 className="text-2xl font-semibold text-slate-800">Mẹo sử dụng nhanh</h3>
            <p className="text-[#7a1c1c] text-sm">Hãy thử gõ những câu sau với Mentor AI</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {t.statUnit.docs === "tệp" ? (
            <>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                💬 <strong>Hỏi đề cương:</strong><br />
                <span className="text-[#7a1c1c]">"Đề cương môn Data Mining có những chương nào?"</span>
              </div>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                📝 <strong>Tạo bài kiểm tra:</strong><br />
                <span className="text-[#7a1c1c]">"Tạo 8 câu hỏi trắc nghiệm về K-Means"</span>
              </div>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                🔍 <strong>Giải thích thuật toán:</strong><br />
                <span className="text-[#7a1c1c]">"Giải thích FP-Growth với ví dụ dễ hiểu"</span>
              </div>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                🐍 <strong>Yêu cầu code:</strong><br />
                <span className="text-[#7a1c1c]">"Viết code Python cho DBSCAN"</span>
              </div>
            </>
          ) : (
            <>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                💬 <strong>Ask about curriculum:</strong><br />
                <span className="text-[#7a1c1c]">"What chapters are in the Data Mining course?"</span>
              </div>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                📝 <strong>Generate quiz:</strong><br />
                <span className="text-[#7a1c1c]">"Create 8 quiz questions about K-Means"</span>
              </div>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                🔍 <strong>Explain algorithm:</strong><br />
                <span className="text-[#7a1c1c]">"Explain FP-Growth with a simple example"</span>
              </div>
              <div className="bg-white/70 rounded-2xl p-6 text-sm">
                🐍 <strong>Ask for code:</strong><br />
                <span className="text-[#7a1c1c]">"Write Python code for DBSCAN"</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Support Note */}
      <div className="text-center text-slate-500 text-sm">
        Bạn vẫn còn thắc mắc? <span className="text-[#7a1c1c] font-medium">Hãy hỏi trực tiếp Mentor AI</span> — họ luôn sẵn sàng hỗ trợ bạn 24/7.
      </div>
    </div>
  );
}