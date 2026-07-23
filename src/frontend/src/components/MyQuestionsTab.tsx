import { useState, useEffect } from "react";
import { FolderHeart, FolderOpen, Plus, RefreshCw, AlertCircle, Save } from "lucide-react";
import { Lang } from "../i18n";
import { getAuthItem } from "../authStorage";

interface MyQuestionsTabProps {
  t: any;
  lang: Lang;
  onStartCustomQuiz: (topic: string) => void;
}

interface Question {
  id: string;
  topic: string;
  question: string;
  correct_answer: string;
  created_at?: string;
}

interface LibraryTopic {
  topic: string;
  questionCount: number;
}

export default function MyQuestionsTab({ t, lang, onStartCustomQuiz }: MyQuestionsTabProps) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [selectedExam, setSelectedExam] = useState<string | null>(null);
  const [isCreateExamModalOpen, setIsCreateExamModalOpen] = useState(false);
  const [newExamName, setNewExamName] = useState("");
  const [libraryTopics, setLibraryTopics] = useState<LibraryTopic[]>([]);
  const [importingTopic, setImportingTopic] = useState<string | null>(null);
  const [selectedBankTopic, setSelectedBankTopic] = useState("");
  const [selectedQuestionCount, setSelectedQuestionCount] = useState(5);
  const [isPresetCreate, setIsPresetCreate] = useState(true);

  // Manual Question State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newQuestion, setNewQuestion] = useState({
    topic: "",
    question: "",
    options: ["", "", "", ""],
    correct_answer: "",
    explanation: ""
  });

  const topics = [
    { id: "apriori", title: "Apriori" },
    { id: "fp_growth", title: "FP-Growth" },
    { id: "kmeans", title: "K-Means" },
    { id: "dbscan", title: "DBSCAN" }
  ];

  const getTopicTitle = (topic: string) => {
    const labels: Record<string, string> = {
      ly_thuyet_25: "Kiểm tra lý thuyết 25%",
      bai_tap_lon_25: "Bài tập lớn 25%",
      cuoi_ky_50: "Trắc nghiệm cuối kỳ 50%",
      apriori: "Apriori",
      fp_growth: "FP-Growth",
      kmeans: "K-Means",
      dbscan: "DBSCAN",
    };
    return labels[topic] || topic.replace(/_/g, " ");
  };

  const getTopicScope = (topic: string) => {
    const scopes: Record<string, string> = {
      ly_thuyet_25: "Lọc nội dung từ Bài 1 đến Bài 3",
      bai_tap_lon_25: "Lọc nội dung từ Bài 2 đến Bài 5",
      cuoi_ky_50: "Lọc nội dung từ Bài 1 đến Bài 5",
      apriori: "Bài 3 - Luật kết hợp",
      fp_growth: "Bài 3 - Luật kết hợp",
      kmeans: "Bài 5 - Phân cụm",
      dbscan: "Bài 5 - Phân cụm",
    };
    return scopes[topic] || "Chủ đề tự tạo";
  };

  const fetchQuestions = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch("/api/user/my-questions", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Không thể tải dữ liệu câu hỏi.");
      const data = await res.json();
      if (data.success) {
        setQuestions(data.questions);
      }
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchLibraryTopics = async () => {
    setErrorMsg("");
    try {
      const res = await fetch("/api/questions/library");
      const data = await res.json();
      if (data.status === "success") {
        const topics = data.topics || [];
        setLibraryTopics(topics);
        if (!selectedBankTopic && topics.length > 0) {
          setSelectedBankTopic(topics[0].topic);
        }
      } else {
        setErrorMsg(data.message || "Không thể tải ngân hàng câu hỏi.");
      }
    } catch (err: any) {
      setErrorMsg("Lỗi khi tải ngân hàng câu hỏi: " + err.message);
    }
  };

  const openCreateExamModal = () => {
    setIsCreateExamModalOpen(true);
    setIsPresetCreate(true);
    fetchLibraryTopics();
  };

  const handleImportTopic = async (topic: string, questionCount: number) => {
    setErrorMsg("");
    setSuccessMsg("");
    setImportingTopic(topic);
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch("/api/user/import-bank-questions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          topic,
          target_topic: getTopicTitle(topic),
          num_questions: questionCount
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || "Không thể nhập câu hỏi.");
      }
      setSuccessMsg(`Đã tạo đề "${data.topic || getTopicTitle(topic)}" với ${data.imported} câu hỏi mới.`);
      await fetchQuestions();
      return true;
    } catch (err: any) {
      setErrorMsg("Lỗi khi nhập câu hỏi: " + err.message);
      return false;
    } finally {
      setImportingTopic(null);
    }
  };

  const handleAddQuestion = async () => {
    setErrorMsg("");
    try {
      const token = getAuthItem("minerai_token");

      // Convert options array to object {"A": "...", "B": "..."}
      const optionsObj: Record<string, string> = {};
      newQuestion.options.forEach((opt, idx) => {
        if (opt.trim() !== "") {
          optionsObj[String.fromCharCode(65 + idx)] = opt;
        }
      });

      const payload = {
        ...newQuestion,
        options: optionsObj
      };

      const res = await fetch("/api/user/my-questions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        // Giữ nguyên topic (đề), chỉ xoá form câu hỏi để tạo tiếp!
        setNewQuestion({
          topic: newQuestion.topic,
          question: "",
          options: ["", "", "", ""],
          correct_answer: "",
          explanation: ""
        });
        alert("Đã lưu thành công 1 câu vào Đề thi này! Tiếp tục nhập câu tiếp theo.");
        fetchQuestions(); // Reload background data
      } else {
        setErrorMsg(`❌ ${data.message || "Lỗi lưu câu hỏi"}`);
      }
    } catch (err: any) {
      setErrorMsg("Lỗi khi kết nối server: " + err.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa câu hỏi này?")) return;
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch(`/api/user/my-questions/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.success) {
        fetchQuestions();
      } else {
        alert(data.message);
      }
    } catch (e: any) {
      alert("Lỗi: " + e.message);
    }
  };

  // Nhóm câu hỏi theo chủ đề để làm bài
  const groupedQuestions = questions.reduce((acc, q) => {
    if (!acc[q.topic]) acc[q.topic] = 0;
    acc[q.topic]++;
    return acc;
  }, {} as Record<string, number>);

  const handleCreateExam = async () => {
    if (isPresetCreate) {
      if (!selectedBankTopic) return;
      const imported = await handleImportTopic(selectedBankTopic, selectedQuestionCount);
      if (!imported) return;
      setIsCreateExamModalOpen(false);
      setNewExamName("");
      setSelectedExam(null);
      return;
    }

    if (!newExamName.trim()) return;
    const topicName = newExamName.trim();
    setSelectedExam(topicName);
    setIsCreateExamModalOpen(false);
    setNewExamName("");
    setNewQuestion({
      topic: topicName,
      question: "",
      options: ["", "", "", ""],
      correct_answer: "",
      explanation: ""
    });
    setIsAddModalOpen(true);
  };

  const questionsInExam = selectedExam
    ? questions.filter(q => q.topic === selectedExam)
    : [];

  const selectedLibraryTopic = libraryTopics.find((item) => item.topic === selectedBankTopic);
  const maxQuestionCount = selectedLibraryTopic?.questionCount || 10;
  const questionCountOptions = Array.from(
    new Set([5, 8, 10, 15, maxQuestionCount].filter((num) => num > 0 && num <= maxQuestionCount))
  ).sort((a, b) => a - b);

  useEffect(() => {
    if (selectedQuestionCount > maxQuestionCount) {
      setSelectedQuestionCount(maxQuestionCount);
    }
  }, [maxQuestionCount, selectedQuestionCount]);

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-4">
      <div className="flex items-center gap-3">

        <div>
          <h2 className="text-xl font-display font-semibold text-slate-800">Đề tự tạo (Cá nhân)</h2>
          <p className="text-sm text-slate-500">Ngân hàng câu hỏi riêng do bạn tự biên soạn</p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 bg-rose-50 border border-rose-100 text-rose-700 rounded-xl flex items-center gap-3">
          <AlertCircle size={20} />
          <span>{errorMsg}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-3.5 bg-green-50 border border-green-100 text-green-700 rounded-xl flex items-center gap-3">
          <span>{successMsg}</span>
          <button className="ml-auto text-green-500 hover:text-green-700" onClick={() => setSuccessMsg("")}>x</button>
        </div>
      )}

      {selectedExam === null ? (
        <>
          {/* Data Table / Danh sách đề thi */}
          {isCreateExamModalOpen && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 space-y-4">
              <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                <FolderOpen size={20} className="text-amber-600" />
                Tạo đề mới
              </h3>

              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setIsPresetCreate(true)}
                  className={`px-4 py-2 rounded-xl border font-semibold transition-colors ${
                    isPresetCreate
                      ? "bg-[#7a1c1c] text-white border-[#7a1c1c]"
                      : "bg-white text-slate-600 border-slate-200 hover:border-rose-200"
                  }`}
                >
                  Chủ đề có sẵn
                </button>
                <button
                  onClick={() => setIsPresetCreate(false)}
                  className={`px-4 py-2 rounded-xl border font-semibold transition-colors ${
                    !isPresetCreate
                      ? "bg-[#7a1c1c] text-white border-[#7a1c1c]"
                      : "bg-white text-slate-600 border-slate-200 hover:border-rose-200"
                  }`}
                >
                  Tự nhập chủ đề
                </button>
              </div>

              {isPresetCreate ? (
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-slate-600">Chọn phạm vi đề / bài</label>
                  {libraryTopics.length > 0 ? (
                    <>
                      <select
                        value={selectedBankTopic}
                        onChange={(e) => setSelectedBankTopic(e.target.value)}
                        className="w-full px-4 py-3 border border-amber-300 rounded-xl outline-none focus:border-[#7a1c1c] bg-white text-slate-800"
                      >
                        {libraryTopics.map((item) => (
                          <option key={item.topic} value={item.topic}>
                            {getTopicTitle(item.topic)} - {getTopicScope(item.topic)}
                          </option>
                        ))}
                      </select>
                      <p className="text-sm text-slate-500">{getTopicScope(selectedBankTopic)}</p>
                      <div className="pt-3 space-y-2">
                        <label className="block text-sm font-semibold text-slate-600">Chọn số câu hỏi</label>
                        <div className="flex flex-wrap gap-2">
                          {questionCountOptions.map((num) => (
                            <button
                              key={num}
                              type="button"
                              onClick={() => setSelectedQuestionCount(num)}
                              className={`px-4 py-2 rounded-xl border font-semibold transition-colors ${
                                selectedQuestionCount === num
                                  ? "bg-[#7a1c1c] text-white border-[#7a1c1c]"
                                  : "bg-white text-slate-600 border-slate-200 hover:border-rose-200"
                              }`}
                            >
                              {num} câu
                            </button>
                          ))}
                        </div>
                        <p className="text-sm text-slate-500">
                          Ngân hàng hiện có {maxQuestionCount} câu cho phạm vi này.
                        </p>
                      </div>
                    </>
                  ) : (
                    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-amber-200 bg-white p-3 text-sm text-amber-700">
                      <span>Chưa tải được ngân hàng câu hỏi.</span>
                      <button
                        onClick={fetchLibraryTopics}
                        className="px-3 py-1.5 rounded-lg bg-amber-100 text-amber-800 font-semibold hover:bg-amber-200"
                      >
                        Tải lại
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-slate-600">Tên đề thi</label>
                  <input
                    type="text"
                    value={newExamName}
                    onChange={(e) => setNewExamName(e.target.value)}
                    placeholder="Ví dụ: Đề ôn tập chương 3..."
                    className="w-full px-4 py-3 border border-amber-300 rounded-xl outline-none focus:border-[#7a1c1c] bg-white text-slate-800"
                  />
                  <p className="text-sm text-slate-500">Sau bước này bạn sẽ nhập câu hỏi thủ công cho đề mới.</p>
                </div>
              )}

              <div className="flex flex-wrap gap-3 pt-1">
                <button
                  onClick={handleCreateExam}
                  disabled={
                    isPresetCreate
                      ? !selectedBankTopic || importingTopic === selectedBankTopic
                      : !newExamName.trim()
                  }
                  className="px-5 py-3 rounded-xl bg-[#7a1c1c] hover:bg-[#5f1515] disabled:opacity-50 text-white font-semibold flex items-center gap-2 shadow-sm"
                >
                  <Plus size={18} />
                  {isPresetCreate
                    ? importingTopic === selectedBankTopic
                      ? "Đang tạo đề..."
                      : "Tạo đề từ ngân hàng"
                    : "Tiếp theo - Thêm câu hỏi"}
                </button>
                <button
                  onClick={() => {
                    setIsCreateExamModalOpen(false);
                    setNewExamName("");
                  }}
                  className="px-5 py-3 rounded-xl bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 font-semibold"
                >
                  Hủy
                </button>
              </div>
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h3 className="text-base font-semibold text-slate-800">Danh sách Đề thi của bạn ({Object.keys(groupedQuestions).length})</h3>
              <div className="flex items-center gap-3">
                <button
                  onClick={openCreateExamModal}
                  className="px-4 py-2 text-sm bg-[#7a1c1c] text-white hover:bg-[#7a1c1c] rounded-lg shadow-sm font-medium flex items-center gap-2"
                >
                  <Plus size={16} /> Tạo Đề thi mới
                </button>
                <button onClick={fetchQuestions} className="p-2 text-slate-500 hover:text-[#7a1c1c] bg-white rounded-lg shadow-sm border border-slate-200">
                  <RefreshCw size={18} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
              {Object.keys(groupedQuestions).length === 0 && !loading ? (
                <div className="col-span-full text-center py-8 text-slate-400">Bạn chưa có đề thi nào. Bấm "Tạo Đề thi mới" để bắt đầu!</div>
              ) : (
                Object.entries(groupedQuestions).map(([topic, count]) => (
                  <div
                    key={topic}
                    onClick={() => setSelectedExam(topic)}
                    className="p-4 border border-slate-200 hover:border-rose-800 rounded-xl cursor-pointer transition-all hover:shadow-md group bg-white"
                  >
                    <div className="w-9 h-9 bg-rose-100 text-[#7a1c1c] rounded-lg flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                      <FolderHeart size={20} />
                    </div>
                    <h4 className="text-lg font-bold text-slate-800 mb-1.5 group-hover:text-[#7a1c1c]">{topic}</h4>
                    <p className="text-sm text-slate-500 font-medium">{count} câu hỏi</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      ) : (
        <>
          {/* Màn hình Chi tiết 1 Đề Thi */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSelectedExam(null)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-200 font-medium rounded-xl transition-colors"
                >
                  ← Quay lại
                </button>
                <h3 className="text-lg font-bold text-slate-800">Đề thi: {selectedExam} ({questionsInExam.length} câu)</h3>
              </div>
              <button
                onClick={() => {
                  setNewQuestion({ ...newQuestion, topic: selectedExam });
                  setIsAddModalOpen(true);
                }}
                className="px-4 py-2 text-sm bg-[#7a1c1c] text-white hover:bg-[#7a1c1c] rounded-lg shadow-sm font-medium flex items-center gap-2"
              >
                <Plus size={16} /> Thêm câu hỏi
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-slate-500 font-medium">
                  <tr>
                    <th className="px-4 py-3">Nội dung câu hỏi</th>
                    <th className="px-4 py-3">Đáp án đúng</th>
                    <th className="px-4 py-3">Hành động</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {questionsInExam.length === 0 ? (
                    <tr><td colSpan={3} className="text-center py-8 text-slate-400">Đề này chưa có câu hỏi nào. Bấm "Thêm câu hỏi" để bắt đầu!</td></tr>
                  ) : (
                    questionsInExam.map((q) => (
                      <tr key={q.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 max-w-md truncate">{q.question}</td>
                        <td className="px-4 py-3 font-bold text-[#7a1c1c]">{q.correct_answer}</td>
                        <td className="px-4 py-3">
                          <button onClick={() => handleDelete(q.id)} className="text-rose-500 hover:text-rose-700 text-xs font-medium">
                            Xóa
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Manual Add Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-lg">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center sticky top-0 bg-white z-10">
              <h3 className="text-lg font-bold text-slate-800">Tạo Đề Thi & Nhập Câu Hỏi</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                ✕
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div className="hidden">
                {/* Ẩn mục chọn Chủ đề vì nó đã được gán cứng theo Đề thi hiện tại */}
                <input
                  type="text"
                  value={newQuestion.topic}
                  readOnly
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Nội dung câu hỏi</label>
                <textarea
                  value={newQuestion.question}
                  onChange={(e) => setNewQuestion({ ...newQuestion, question: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-200 rounded-xl outline-none focus:border-rose-800 min-h-[100px]"
                  placeholder="Nhập nội dung câu hỏi..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Các đáp án</label>
                <div className="space-y-3">
                  {newQuestion.options.map((opt, idx) => (
                    <div key={idx} className="flex gap-3 items-center">
                      <span className="w-8 h-8 flex items-center justify-center bg-slate-100 rounded-lg font-bold text-slate-500">
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <input
                        type="text"
                        value={opt}
                        onChange={(e) => {
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
                          checked={newQuestion.correct_answer === String.fromCharCode(65 + idx)}
                          onChange={() => setNewQuestion({ ...newQuestion, correct_answer: String.fromCharCode(65 + idx) })}
                          className="w-5 h-5 text-[#7a1c1c] focus:ring-rose-800"
                        />
                        <span className="text-sm font-medium text-slate-600">Là đáp án đúng</span>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 flex justify-end gap-2.5 sticky bottom-0 bg-white">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 font-medium rounded-lg transition-colors"
              >
                Đóng
              </button>
              <button
                onClick={handleAddQuestion}
                disabled={!newQuestion.question || !newQuestion.correct_answer}
                className="px-4 py-2 bg-[#7a1c1c] hover:bg-[#7a1c1c] disabled:opacity-50 text-white font-medium rounded-lg flex items-center gap-2 transition-colors"
              >
                <Save size={18} /> Lưu & Thêm câu khác
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
