import { useState, useEffect } from "react";
import { Database, Plus, RefreshCw, AlertCircle, Bot, FolderOpen, ChevronRight, ArrowLeft, Trash2, Edit3, BookOpen } from "lucide-react";
import { Lang } from "../i18n";
import { getAuthItem } from "../authStorage";

interface AdminTabProps {
  t: any;
  lang: Lang;
}

interface Question {
  id: string;
  topic: string;
  question: string;
  correct_answer: string;
  options?: string[];
  explanation?: string;
  created_by?: string;
  created_at?: string;
}

interface TopicGroup {
  topic: string;
  questionCount: number;
}

const PRESET_TOPICS = [
  {
    id: "ly_thuyet_25",
    title: "Kiểm tra lý thuyết 25%",
    scope: "Lọc nội dung từ Bài 1 đến Bài 3",
  },
  {
    id: "bai_tap_lon_25",
    title: "Bài tập lớn 25%",
    scope: "Lọc nội dung từ Bài 2 đến Bài 5",
  },
  {
    id: "cuoi_ky_50",
    title: "Trắc nghiệm cuối kỳ 50%",
    scope: "Lọc nội dung từ Bài 1 đến Bài 5",
  },
  { id: "apriori", title: "Thuật toán Apriori", scope: "Bài 3 - Luật kết hợp" },
  { id: "fp_growth", title: "FP-Growth", scope: "Bài 3 - Luật kết hợp" },
  { id: "kmeans", title: "K-Means Clustering", scope: "Bài 5 - Phân cụm" },
  { id: "dbscan", title: "DBSCAN", scope: "Bài 5 - Phân cụm" },
  { id: "decision_tree", title: "Cây Quyết Định", scope: "Bài 4 - Phân lớp" },
  { id: "naive_bayes", title: "Naive Bayes", scope: "Bài 4 - Phân lớp" },
];

const getPresetFromTopic = (topic: string) => {
  return PRESET_TOPICS.find(p => topic === p.id || topic.startsWith(`${p.id}_de_`));
};

const getTopicMeta = (topic: string) => {
  const preset = getPresetFromTopic(topic);
  if (preset) {
    const variantMatch = topic.match(new RegExp(`^${preset.id}_de_(\\d+)$`));
    return {
      ...preset,
      id: topic,
      title: variantMatch ? `${preset.title} (${variantMatch[1]})` : preset.title,
    };
  }
  return {
    id: topic,
    title: topic.replace(/_/g, " "),
    scope: "Chủ đề tự tạo",
  };
};

const getGenerationSourceTopic = (topic: string) => getPresetFromTopic(topic)?.id || topic;

export default function AdminTab({ t, lang }: AdminTabProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [selectedTopicGroup, setSelectedTopicGroup] = useState<TopicGroup | null>(null);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [topicGroups, setTopicGroups] = useState<TopicGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [isCreatingTopic, setIsCreatingTopic] = useState(false);
  const [newTopicId, setNewTopicId] = useState("");
  const [newTopicTitle, setNewTopicTitle] = useState("");
  const [isPreset, setIsPreset] = useState(true);
  const [selectedPreset, setSelectedPreset] = useState(PRESET_TOPICS[0].id);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newQuestion, setNewQuestion] = useState({
    topic: "",
    question: "",
    options: ["", "", "", ""],
    correct_answer: "",
    explanation: ""
  });

  const [genCount, setGenCount] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [genResult, setGenResult] = useState("");

  const fetchTopicGroups = async () => {
    try {
      const res = await fetch("/api/questions/library");
      const data = await res.json();
      if (data.status === "success") {
        const presetOrder = new Map(PRESET_TOPICS.map((p, idx) => [p.id, idx]));
        const sortedTopics = [...data.topics].sort((a: TopicGroup, b: TopicGroup) => {
          const aOrder = presetOrder.get(a.topic) ?? 999;
          const bOrder = presetOrder.get(b.topic) ?? 999;
          if (aOrder !== bOrder) return aOrder - bOrder;
          return a.topic.localeCompare(b.topic);
        });
        setTopicGroups(sortedTopics);
      }
    } catch (err) {
      console.error("Error fetching topics:", err);
    }
  };

  const fetchQuestionsForTopic = async (topicId: string) => {
    setLoading(true);
    setErrorMsg("");
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch("/api/admin/questions", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Không thể tải dữ liệu câu hỏi (Cần MongoDB)");
      const data = await res.json();
      if (data.success) {
        setQuestions(data.questions.filter((q: Question) => q.topic === topicId));
      }
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopicGroups();
  }, []);

  const handleSelectTopic = (group: TopicGroup) => {
    setSelectedTopicGroup(group);
    setStep(2);
    setGenResult("");
    setErrorMsg("");
    setSuccessMsg("");
    setNewQuestion({ topic: group.topic, question: "", options: ["", "", "", ""], correct_answer: "", explanation: "" });
    fetchQuestionsForTopic(group.topic);
  };

  const handleCreateTopic = () => {
    const existingPresetIds = topicGroups
      .map((group) => group.topic)
      .filter((topic) => topic === selectedPreset || topic.startsWith(`${selectedPreset}_de_`));
    const nextPresetIndex = existingPresetIds.filter((topic) => topic.startsWith(`${selectedPreset}_de_`)).length + 1;
    const topicId = isPreset ? `${selectedPreset}_de_${nextPresetIndex}` : newTopicId.trim().toLowerCase().replace(/\s+/g, "_");
    const topicTitle = isPreset ? (getTopicMeta(selectedPreset).title || selectedPreset) : newTopicTitle.trim();
    if (!topicId || !topicTitle) {
      setErrorMsg("Vui lòng nhập đầy đủ thông tin đề");
      return;
    }
    const newGroup: TopicGroup = { topic: topicId, questionCount: 0 };
    setTopicGroups(prev => {
      const exists = prev.find(g => g.topic === topicId);
      return exists ? prev : [...prev, newGroup];
    });
    setSelectedTopicGroup(newGroup);
    setStep(2);
    setIsCreatingTopic(false);
    setNewTopicId("");
    setNewTopicTitle("");
    setQuestions([]);
    setNewQuestion({ topic: topicId, question: "", options: ["", "", "", ""], correct_answer: "", explanation: "" });
    setGenResult("");
    setErrorMsg("");
    setSuccessMsg("");
  };

  const handleGenerateAI = async () => {
    if (!selectedTopicGroup) return;
    setIsGenerating(true);
    setGenResult("");
    setErrorMsg("");
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch("/api/admin/generate-questions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          topic: getGenerationSourceTopic(selectedTopicGroup.topic),
          folder_topic: selectedTopicGroup.topic,
          num_questions: genCount
        })
      });
      const data = await res.json();
      if (data.success) {
        setGenResult(`Đã sinh thành công ${data.questions_added} câu hỏi!`);
        setSuccessMsg(`Đã thêm ${data.questions_added} câu hỏi vào đề "${getTopicMeta(selectedTopicGroup.topic).title}"`);
        fetchQuestionsForTopic(selectedTopicGroup.topic);
        fetchTopicGroups();
      } else {
        setErrorMsg(`${data.detail || data.message || "Lỗi sinh câu hỏi"}`);
      }
    } catch (err: any) {
      setErrorMsg("Lỗi khi kết nối server: " + err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAddQuestion = async () => {
    setErrorMsg("");
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch("/api/admin/questions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(newQuestion)
      });
      const data = await res.json();
      if (data.success) {
        setIsAddModalOpen(false);
        setNewQuestion({ topic: selectedTopicGroup?.topic || "", question: "", options: ["", "", "", ""], correct_answer: "", explanation: "" });
        setSuccessMsg("Đã thêm câu hỏi thành công!");
        fetchQuestionsForTopic(selectedTopicGroup?.topic || "");
        fetchTopicGroups();
      } else {
        setErrorMsg(`${data.message || "Lỗi lưu câu hỏi"}`);
      }
    } catch (err: any) {
      setErrorMsg("Lỗi khi kết nối server: " + err.message);
    }
  };

  const handleDeleteQuestion = async (qId: string) => {
    if (!confirm("Bạn có chắc chắn muốn xoá câu hỏi này không?")) return;
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch(`/api/admin/questions/${qId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        setSuccessMsg("Đã xoá câu hỏi.");
        fetchQuestionsForTopic(selectedTopicGroup?.topic || "");
        fetchTopicGroups();
      }
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  // STEP 1: DANH SACH DE
  if (step === 1) {
    return (
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">

            <div>
              <p className="text-slate-500">Quản lý dữ liệu ngân hàng câu hỏi</p>
            </div>
          </div>
          <button
            onClick={() => { setIsCreatingTopic(true); setErrorMsg(""); }}
            className="px-5 py-2.5 bg-[#7a1c1c] text-white rounded-xl font-medium flex items-center gap-2 hover:bg-[#5e1515] transition-colors shadow-sm"
          >
            <Plus size={18} /> Tạo đề mới
          </button>
        </div>

        {errorMsg && (
          <div className="p-4 bg-rose-50 border border-rose-100 text-rose-700 rounded-2xl flex items-center gap-3">
            <AlertCircle size={20} /><span>{errorMsg}</span>
          </div>
        )}

        {isCreatingTopic && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 space-y-4">
            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <FolderOpen size={20} className="text-amber-600" /> Tạo đề mới
            </h3>
            <div className="flex gap-3 mb-2">
              <button
                onClick={() => setIsPreset(true)}
                className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${isPreset ? "bg-[#7a1c1c] text-white border-[#7a1c1c]" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}
              >
                Chủ đề có sẵn
              </button>
              <button
                onClick={() => setIsPreset(false)}
                className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${!isPreset ? "bg-[#7a1c1c] text-white border-[#7a1c1c]" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}
              >
                Tự nhập chủ đề
              </button>
            </div>
            {isPreset ? (
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-2">Chọn phạm vi đề / bài</label>
                <select
                  value={selectedPreset}
                  onChange={e => setSelectedPreset(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-amber-200 bg-white outline-none"
                >
                  {PRESET_TOPICS.map(p => (
                    <option key={p.id} value={p.id}>{p.title} - {p.scope}</option>
                  ))}
                </select>
                <p className="mt-2 text-sm text-slate-500">{getTopicMeta(selectedPreset).scope}</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-2">Tên hiển thị đề</label>
                  <input
                    type="text"
                    value={newTopicTitle}
                    onChange={e => setNewTopicTitle(e.target.value)}
                    placeholder="Ví dụ: Khai phá dữ liệu nâng cao"
                    className="w-full px-4 py-3 rounded-xl border border-amber-200 bg-white outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-2">ID đề (slug)</label>
                  <input
                    type="text"
                    value={newTopicId}
                    onChange={e => setNewTopicId(e.target.value)}
                    placeholder="Ví dụ: khai_pha_nang_cao"
                    className="w-full px-4 py-3 rounded-xl border border-amber-200 bg-white outline-none"
                  />
                </div>
              </div>
            )}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-600">Chọn số câu sinh thêm</label>
              <div className="flex flex-wrap gap-2">
                {[3, 5, 10, 15].map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setGenCount(num)}
                    className={`px-4 py-2 rounded-xl border text-sm font-semibold transition-colors ${
                      genCount === num
                        ? "bg-[#7a1c1c] text-white border-[#7a1c1c]"
                        : "bg-white text-slate-600 border-slate-200 hover:border-rose-200"
                    }`}
                  >
                    {num} câu
                  </button>
                ))}
              </div>
              <p className="text-sm text-slate-500">
                {isPreset
                  ? `Hệ thống sẽ tạo một đề mới riêng với đúng ${genCount} câu, không cộng vào đề đã có.`
                  : `Số câu này sẽ được dùng ở bước sinh câu hỏi bằng AI.`}
              </p>
            </div>
            <div className="flex gap-3 pt-1">
              <button
                onClick={handleCreateTopic}
                className="px-5 py-2.5 bg-[#7a1c1c] text-white rounded-xl font-medium hover:bg-[#5e1515] transition-colors"
              >
                Tiếp theo - Thêm câu hỏi
              </button>
              <button
                onClick={() => { setIsCreatingTopic(false); setErrorMsg(""); }}
                className="px-5 py-2.5 bg-white text-slate-600 border border-slate-200 rounded-xl font-medium hover:bg-slate-50 transition-colors"
              >
                Huỷ
              </button>
            </div>
          </div>
        )}



        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
          <div className="p-5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <h3 className="text-base font-semibold text-slate-800">Đề thi hiện có ({topicGroups.length})</h3>
            <button onClick={fetchTopicGroups} className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors">
              <RefreshCw size={16} />
            </button>
          </div>
          {topicGroups.length === 0 ? (
            <div className="p-12 text-center">
              <BookOpen className="mx-auto text-slate-300 mb-3" size={48} />
              <p className="text-slate-400 font-medium">Chưa có đề nào. Bấm "Tạo đề mới" để bắt đầu.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {topicGroups.map((group, idx) => (
                (() => {
                  const meta = getTopicMeta(group.topic);
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSelectTopic(group)}
                      className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-colors text-left group"
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-rose-50 text-[#7a1c1c] rounded-xl flex items-center justify-center font-bold text-sm">
                          {group.topic.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-semibold text-slate-800">{meta.title}</div>
                          <div className="text-sm text-slate-400">{meta.scope} · {group.questionCount} câu hỏi</div>
                        </div>
                      </div>
                      <ChevronRight size={18} className="text-slate-300 group-hover:text-[#7a1c1c] group-hover:translate-x-1 transition-all" />
                    </button>
                  );
                })()
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // STEP 2: CAU HOI CUA DE
  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => { setStep(1); setQuestions([]); setGenResult(""); setErrorMsg(""); setSuccessMsg(""); }}
          className="flex items-center gap-2 text-slate-500 hover:text-[#7a1c1c] font-medium transition-colors"
        >
          <ArrowLeft size={18} /> Danh sách đề
        </button>
        <span className="text-slate-300">/</span>
        <div>
          <div className="text-slate-800 font-semibold">
            {getTopicMeta(selectedTopicGroup?.topic || "").title}
          </div>
          <div className="text-xs text-slate-400">
            {getTopicMeta(selectedTopicGroup?.topic || "").scope}
          </div>
        </div>
        <span className="ml-2 px-2.5 py-0.5 bg-rose-50 text-[#7a1c1c] text-xs font-bold rounded-full">
          {questions.length} câu
        </span>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-100 text-rose-700 rounded-2xl flex items-center gap-3">
          <AlertCircle size={20} /><span>{errorMsg}</span>
          <button className="ml-auto text-rose-400 hover:text-rose-600" onClick={() => setErrorMsg("")}>x</button>
        </div>
      )}
      {successMsg && (
        <div className="p-4 bg-green-50 border border-green-100 text-green-700 rounded-2xl flex items-center gap-3">
          <span>{successMsg}</span>
          <button className="ml-auto text-green-400 hover:text-green-600" onClick={() => setSuccessMsg("")}>x</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gradient-to-br from-rose-50 to-pink-50 border border-rose-100 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Bot className="text-[#7a1c1c]" size={20} />
            <h3 className="font-semibold text-slate-800">Tự động sinh câu hỏi bằng AI</h3>
          </div>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-500 mb-1">Số câu sinh thêm</label>
              <select
                value={genCount}
                onChange={e => setGenCount(Number(e.target.value))}
                className="w-full px-3 py-2.5 rounded-xl border border-rose-200 bg-white outline-none text-sm"
              >
                <option value={3}>3 câu</option>
                <option value={5}>5 câu</option>
                <option value={10}>10 câu</option>
                <option value={15}>15 câu</option>
              </select>
            </div>
            <button
              onClick={handleGenerateAI}
              disabled={isGenerating}
              className="px-4 py-2.5 bg-[#7a1c1c] text-white rounded-xl font-medium flex items-center gap-2 hover:bg-[#5e1515] transition-colors disabled:opacity-50 text-sm whitespace-nowrap"
            >
              {isGenerating ? <RefreshCw size={16} className="animate-spin" /> : <Bot size={16} />}
              {isGenerating ? "Đang sinh..." : "Sinh & Lưu"}
            </button>
          </div>
          {genResult && <p className="mt-3 text-sm text-green-700 font-medium">{genResult}</p>}
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Edit3 className="text-slate-600" size={20} />
            <h3 className="font-semibold text-slate-800">Tự tạo câu hỏi thủ công</h3>
          </div>
          <p className="text-sm text-slate-500 mb-4">Nhập từng câu hỏi, các đáp án và chọn đáp án đúng.</p>
          <button
            onClick={() => {
              setNewQuestion({ topic: selectedTopicGroup?.topic || "", question: "", options: ["", "", "", ""], correct_answer: "", explanation: "" });
              setIsAddModalOpen(true);
            }}
            className="w-full px-4 py-2.5 bg-slate-800 text-white rounded-xl font-medium flex items-center justify-center gap-2 hover:bg-slate-700 transition-colors text-sm"
          >
            <Plus size={16} /> Thêm câu hỏi mới
          </button>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Danh sách câu hỏi ({questions.length})</h3>
          <button onClick={() => fetchQuestionsForTopic(selectedTopicGroup?.topic || "")} className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>
        {loading ? (
          <div className="p-12 text-center text-slate-400">Đang tải...</div>
        ) : questions.length === 0 ? (
          <div className="p-12 text-center">
            <BookOpen className="mx-auto text-slate-200 mb-3" size={40} />
            <p className="text-slate-400">Chưa có câu hỏi nào cho đề này. Hãy sinh bằng AI hoặc thêm thủ công!</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {questions.map((q, idx) => (
              <div key={q.id} className="px-6 py-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold text-slate-400">#{idx + 1}</span>
                      {q.created_by === 'gemini_ai' && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-50 text-purple-600 text-xs font-medium rounded-full">
                          <Bot size={10} /> AI
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-800 font-medium mb-2">{q.question}</p>
                    <p className="text-xs text-green-700 font-medium">Đáp án đúng: {q.correct_answer}</p>
                  </div>
                  <button
                    onClick={() => handleDeleteQuestion(q.id)}
                    className="p-2 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {isAddModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-xl">
            <div className="p-6 border-b border-slate-100 flex justify-between items-center sticky top-0 bg-white z-10">
              <h3 className="text-xl font-bold text-slate-800">Tự tạo câu hỏi thủ công</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600">x</button>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Đề / Chủ đề</label>
                <input
                  type="text"
                  value={newQuestion.topic}
                  readOnly
                  className="w-full px-4 py-2 border border-slate-200 rounded-xl bg-slate-50 text-slate-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nội dung câu hỏi</label>
                <textarea
                  value={newQuestion.question}
                  onChange={e => setNewQuestion({ ...newQuestion, question: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl outline-none focus:border-rose-800 min-h-[100px]"
                  placeholder="Nhập nội dung câu hỏi..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Các đáp án (chọn đáp án đúng)</label>
                <div className="space-y-3">
                  {newQuestion.options.map((opt, idx) => (
                    <div key={idx} className="flex gap-3 items-center">
                      <span className="w-8 h-8 flex items-center justify-center bg-slate-100 rounded-lg font-bold text-slate-500">
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <input
                        type="text"
                        value={opt}
                        onChange={e => {
                          const newOpts = [...newQuestion.options];
                          newOpts[idx] = e.target.value;
                          setNewQuestion({ ...newQuestion, options: newOpts });
                        }}
                        className="flex-1 px-4 py-2 border border-slate-200 rounded-xl outline-none focus:border-rose-800"
                        placeholder={`Nội dung đáp án ${String.fromCharCode(65 + idx)}...`}
                      />
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="correct_answer"
                          checked={newQuestion.correct_answer === opt && opt !== ""}
                          onChange={() => setNewQuestion({ ...newQuestion, correct_answer: opt })}
                          className="w-5 h-5 text-[#7a1c1c] focus:ring-rose-800"
                        />
                        <span className="text-sm font-medium text-slate-600">Đúng</span>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Giải thích (tuỳ chọn)</label>
                <textarea
                  value={newQuestion.explanation}
                  onChange={e => setNewQuestion({ ...newQuestion, explanation: e.target.value })}
                  className="w-full px-4 py-2 border border-slate-200 rounded-xl outline-none focus:border-rose-800"
                  placeholder="Giải thích đáp án..."
                  rows={3}
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleAddQuestion}
                  disabled={!newQuestion.question || !newQuestion.correct_answer}
                  className="flex-1 px-5 py-3 bg-[#7a1c1c] text-white rounded-xl font-semibold hover:bg-[#5e1515] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  Lưu câu hỏi
                </button>
                <button
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-5 py-3 bg-slate-100 text-slate-700 rounded-xl font-medium hover:bg-slate-200 transition-colors"
                >
                  Huỷ
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
