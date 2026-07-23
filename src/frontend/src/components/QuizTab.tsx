import { useState, useEffect } from "react";
import { Clock, Brain, ArrowLeft, ArrowRight, CheckCircle2, XCircle, RefreshCw, Award, BookOpen, AlertCircle, HelpCircle, Network, Share2, Target, CircleDashed, Library, Download, Flame, Sprout, Leaf, Flower2, TreePine } from "lucide-react";
import { Lang } from "../i18n";
import { getAuthItem, getLocalRecentLessons, saveLocalRecentLesson, StoredRecentLesson } from "../authStorage";

interface QuizTabProps {
  t: any;
  lang: Lang;
  selectedTopic?: string | null;
  customPracticeTopic?: string | null;
  onClearSelectedTopic?: () => void;
  onClearCustomPractice?: () => void;
}

interface Question {
  id: number;
  type: string;
  difficulty: string;
  question: string;
  options?: {
    A: string;
    B: string;
    C: string;
    D: string;
  };
  correct_answer?: string;
  explanation?: string;
  source_reference?: string;
}

interface QuizSource {
  filename: string;
  page: string | number;
  content: string;
}

interface QuizResult {
  is_correct: boolean;
  score: number;
  feedback: string;
  correct_answer: string;
  explanation?: string;
  source_reference?: string;
  missing_points?: string[];
  user_answer: string;
}

const OPTION_KEYS = ["A", "B", "C", "D"] as const;

const shuffleArray = <T,>(items: T[]): T[] => {
  const shuffled = [...items];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
};

const shuffleQuestionOptions = (question: Question): Question => {
  if (!question.options || !question.correct_answer) return question;

  const entries = OPTION_KEYS.map((key) => ({
    originalKey: key,
    value: question.options?.[key],
  })).filter((entry) => entry.value !== undefined);

  const shuffledEntries = shuffleArray(entries);
  const options = {} as NonNullable<Question["options"]>;
  const originalCorrectKey = entries.find((entry) =>
    entry.originalKey === question.correct_answer || entry.value === question.correct_answer
  )?.originalKey;
  let correctAnswer = question.correct_answer;

  shuffledEntries.forEach((entry, index) => {
    const newKey = OPTION_KEYS[index];
    options[newKey] = entry.value || "";
    if (entry.originalKey === originalCorrectKey) {
      correctAnswer = newKey;
    }
  });

  return {
    ...question,
    options,
    correct_answer: correctAnswer,
  };
};

const shuffleQuizQuestions = (questions: Question[]): Question[] =>
  shuffleArray(questions.map(shuffleQuestionOptions));

export default function QuizTab({ t, lang, selectedTopic: selectedTopicFromOverview, customPracticeTopic, onClearSelectedTopic, onClearCustomPractice }: QuizTabProps) {
  // Quiz states
  const [quizState, setQuizState] = useState<"setup" | "loading" | "active" | "completed">("setup");
  const [selectedTopic, setSelectedTopic] = useState<string>("apriori");
  const [numQuestions, setNumQuestions] = useState<number>(5);
  const [quizId, setQuizId] = useState<string>("");
  const [activeQuizTopic, setActiveQuizTopic] = useState<string>("");
  const [activeQuizTopicId, setActiveQuizTopicId] = useState<string>("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [sources, setSources] = useState<QuizSource[]>([]);
  const [currentIdx, setCurrentIdx] = useState<number>(0);
  const [userAnswers, setUserAnswers] = useState<{ [key: number]: string }>({});
  const [evaluations, setEvaluations] = useState<{ [key: number]: QuizResult }>({});
  const [isShuffledRedo, setIsShuffledRedo] = useState<boolean>(false);

  // Timer states
  const [timeLeft, setTimeLeft] = useState<number>(15 * 60);
  const [timerActive, setTimerActive] = useState<boolean>(false);

  // Results state
  const [overallScore, setOverallScore] = useState<any>(null);
  const [loadingResults, setLoadingResults] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Personalization states
  const [weakTopics, setWeakTopics] = useState<string[]>([]);
  const [completedTopics, setCompletedTopics] = useState<string[]>([]);
  const [completedScores, setCompletedScores] = useState<Record<string, StoredRecentLesson>>({});
  const [isCustomTopic, setIsCustomTopic] = useState<boolean>(false);
  const [customTopic, setCustomTopic] = useState<string>("");
  const [isLibraryModalOpen, setIsLibraryModalOpen] = useState<boolean>(false);
  const [libraryTopics, setLibraryTopics] = useState<any[]>([]);
  const [personalTopics, setPersonalTopics] = useState<any[]>([]);

  // Restore downloaded topics from localStorage (icons are stored as string type, resolved on load)
  const resolveIcon = (iconType: string) => {
    if (iconType === 'Network') return Network;
    if (iconType === 'Share2') return Share2;
    if (iconType === 'Target') return Target;
    if (iconType === 'CircleDashed') return CircleDashed;
    return Library;
  };

  const [downloadedTopics, setDownloadedTopics] = useState<any[]>(() => {
    try {
      const saved = localStorage.getItem('minerai_downloaded_topics');
      if (!saved) return [];
      const parsed = JSON.parse(saved);
      return parsed.map((item: any) => ({
        ...item,
        icon: resolveIcon(item.iconType || 'Library'),
      }));
    } catch {
      return [];
    }
  });

  // Persist downloaded topics to localStorage whenever they change
  useEffect(() => {
    try {
      const serializable = downloadedTopics.map(({ icon: _icon, ...rest }) => rest);
      localStorage.setItem('minerai_downloaded_topics', JSON.stringify(serializable));
    } catch {}
  }, [downloadedTopics]);

  useEffect(() => {
    if (isLibraryModalOpen) {
      fetch('/api/questions/library')
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            setLibraryTopics(data.topics);
          }
        })
        .catch(err => console.error('Error fetching library topics:', err));
    }
  }, [isLibraryModalOpen]);

  const topics = [
    {
      id: "apriori",
      icon: Network,
      title: lang === "vi" ? "Thuật toán Apriori" : "Apriori Algorithm",
      desc: lang === "vi" ? "Khai phá luật kết hợp mạnh, tập mục phổ biến và các chỉ số Support, Confidence, Lift." : "Mine association rules, frequent itemsets, and Support, Confidence, Lift metrics.",

    },
    {
      id: "fp_growth",
      icon: Share2,
      title: lang === "vi" ? "Thuật toán FP-Growth" : "FP-Growth Algorithm",
      desc: lang === "vi" ? "Cấu trúc cây FP-Tree nén dữ liệu hiệu quả, không cần sinh ứng viên như Apriori." : "Compress databases into FP-Tree without candidate generation.",

    },
    {
      id: "kmeans",
      icon: Target,
      title: lang === "vi" ? "Thuật toán K-Means" : "K-Means Clustering",
      desc: lang === "vi" ? "Thuật toán phân cụm phân hoạch tối ưu dựa trên khoảng cách Euclidean và centroids." : "Partitioning clustering method based on Euclidean distance and centroids.",

    },
    {
      id: "dbscan",
      icon: CircleDashed,
      title: lang === "vi" ? "Thuật toán DBSCAN" : "DBSCAN Clustering",
      desc: lang === "vi" ? "Phân cụm dựa trên mật độ, tự động phát hiện nhiễu (outliers) và cụm hình dạng bất kỳ." : "Density-based spatial clustering to detect noise and arbitrary shapes.",

    },
    {
      id: "ly_thuyet_25",
      icon: BookOpen,
      title: lang === "vi" ? "Đề kiểm tra lý thuyết (25%)" : "Theory Midterm Exam (25%)",
      desc: lang === "vi" ? "Tạo đề trắc nghiệm khách quan 25% dựa trên Đề cương học phần (Bài 1, 2, 3)." : "Generate a 25% midterm quiz based on Syllabus Lessons 1, 2, and 3.",
    },
    {
      id: "cuoi_ky_50",
      icon: Award,
      title: lang === "vi" ? "Đề thi trắc nghiệm cuối kỳ (50%)" : "Final Theory Exam (50%)",
      desc: lang === "vi" ? "Tạo đề thi kết thúc học phần trắc nghiệm 50% bao quát toàn bộ đề cương (Bài 1 đến Bài 5)." : "Generate a 50% final exam encompassing all Syllabus chapters (Lesson 1 to 5).",
    },
    {
      id: "code_thuc_hanh",
      icon: Brain,
      title: lang === "vi" ? "Thực hành Mã nguồn Python" : "Python Algorithm Coding",
      desc: lang === "vi" ? "Tạo đề kiểm tra thực hành về mã lệnh Python của các thuật toán: kNN, Naive Bayes, Decision Tree, K-Means, Apriori." : "Generate code quizzes focused on Python implementations of kNN, Naive Bayes, Decision Tree, K-Means, and Apriori.",
    }
  ];

  const displayTopics = [...topics, ...downloadedTopics, ...personalTopics];

  const fetchPersonalTopics = async () => {
    const token = getAuthItem("minerai_token");
    if (!token) return;

    try {
      const res = await fetch("/api/user/my-questions", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok || !data.success) return;

      const grouped = (data.questions || []).reduce((acc: Record<string, number>, q: any) => {
        if (!q.topic) return acc;
        acc[q.topic] = (acc[q.topic] || 0) + 1;
        return acc;
      }, {});

      setPersonalTopics(
        Object.entries(grouped).map(([topic, count]) => ({
          id: `personal:${topic}`,
          apiTopic: topic,
          isPersonal: true,
          count,
          icon: BookOpen,
          title: topic,
          desc: lang === "vi"
            ? `Đề tự tạo của tài khoản này, có ${count} câu hỏi.`
            : `Personal quiz for this account with ${count} questions.`,
        }))
      );
    } catch (err) {
      console.error("Error fetching personal quiz topics:", err);
    }
  };

  useEffect(() => {
    fetchPersonalTopics();
  }, [lang]);

  const normalizeTopicKey = (value: string) => value.toLowerCase().trim().replace(/[-\s]+/g, "_");
  const buildScoreMap = (lessons: StoredRecentLesson[]) => {
    const map: Record<string, StoredRecentLesson> = {};
    lessons
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .forEach((lesson) => {
        const keys = [lesson.topic, lesson.title].filter(Boolean).map(normalizeTopicKey);
        keys.forEach((key) => {
          if (!map[key]) map[key] = lesson;
        });
      });
    return map;
  };
  const getLatestScoreForTopic = (topic: any) => {
    const keys = [topic.id, topic.title, topic.apiTopic].filter(Boolean).map(normalizeTopicKey);
    for (const key of keys) {
      if (completedScores[key]) return completedScores[key];
    }
    return null;
  };
  const getDisplayScore = (lesson: StoredRecentLesson) => {
    const score = Number(lesson.score || 0);
    const maxScore = Number(lesson.max_score || lesson.total_questions || 0);
    const rawPercentage = Number(lesson.percentage);
    const percentage = Number.isFinite(rawPercentage)
      ? rawPercentage
      : maxScore > 0
        ? (score / maxScore) * 100
        : 0;

    return {
      score,
      maxScore,
      max_score: maxScore,
      percentage: Number(percentage.toFixed(0)),
      answeredQuestions: Number(lesson.answered_questions || lesson.total_questions || maxScore || 0),
      answered_questions: Number(lesson.answered_questions || lesson.total_questions || maxScore || 0),
      totalQuestions: Number(lesson.total_questions || maxScore || lesson.answered_questions || 0),
      total_questions: Number(lesson.total_questions || maxScore || lesson.answered_questions || 0),
    };
  };

  // Fetch personalization data
  useEffect(() => {
    const fetchPersonalization = async () => {
      const token = getAuthItem("minerai_token");
      setCompletedScores(buildScoreMap(getLocalRecentLessons()));
      if (!token) return;

      const headers = { "Authorization": `Bearer ${token}` };

      try {
        const [weakRes, completedRes, recentRes] = await Promise.all([
          fetch("/api/user/weak-topics", { headers }),
          fetch("/api/user/completed-topics", { headers }),
          fetch("/api/user/recent-lessons?limit=12", { headers })
        ]);

        if (weakRes.ok) {
          const weakData = await weakRes.json();
          setWeakTopics(weakData.weak_topics || []);
        }

        if (completedRes.ok) {
          const completedData = await completedRes.json();
          setCompletedTopics(completedData.completed_topics || []);
        }

        if (recentRes.ok) {
          const recentData = await recentRes.json();
          const serverLessons = Array.isArray(recentData.lessons) ? recentData.lessons : [];
          setCompletedScores(buildScoreMap([...serverLessons, ...getLocalRecentLessons()]));
        }
      } catch (err) {
        console.error("Lỗi khi tải dữ liệu cá nhân hóa", err);
      }
    };

    fetchPersonalization();
  }, []);

  // Timer Effect
  useEffect(() => {
    let interval: any = null;
    if (timerActive && timeLeft > 0 && quizState === "active") {
      interval = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0 && quizState === "active") {
      clearInterval(interval);
      handleAutoSubmit();
    }
    return () => clearInterval(interval);
  }, [timerActive, timeLeft, quizState]);

  // Auto-start custom practice
  useEffect(() => {
    if (customPracticeTopic && quizState === "setup") {
      startQuiz(customPracticeTopic, true);
    }
  }, [customPracticeTopic]);

  useEffect(() => {
    if (selectedTopicFromOverview && quizState === "setup") {
      setSelectedTopic(selectedTopicFromOverview);
      setIsCustomTopic(false);
      setCustomTopic("");
      onClearSelectedTopic?.();
    }
  }, [selectedTopicFromOverview, quizState]);

  const startQuiz = async (overrideTopic?: string, forcePersonalMode: boolean = false) => {
    setQuizState("loading");
    setErrorMsg("");
    setUserAnswers({});
    setEvaluations({});
    setOverallScore(null);
    setCurrentIdx(0);
    setIsShuffledRedo(false);
    setActiveQuizTopic("");
    setActiveQuizTopicId("");

    // Resolve the actual API topic: downloaded cards may have suffixed IDs like "apriori_2"
    // We store the real topic in their `apiTopic` field
    const resolveApiTopic = (topicId: string): string => {
      const topic = displayTopics.find(d => d.id === topicId);
      return topic?.apiTopic || topicId;
    };
    const rawTopic = overrideTopic || (isCustomTopic && customTopic.trim() ? customTopic.trim() : selectedTopic);
    const selectedDisplayTopic = displayTopics.find(d => d.id === rawTopic || d.apiTopic === rawTopic);
    const isCustomMode = forcePersonalMode || Boolean(selectedDisplayTopic?.isPersonal);
    const finalTopic = resolveApiTopic(rawTopic);
    const finalTopicTitle = selectedDisplayTopic?.title || finalTopic;
    const endpoint = isCustomMode ? "/api/quiz/custom-practice" : "/api/quiz";
    const requestedQuestionCount = selectedDisplayTopic?.isPersonal && Number(selectedDisplayTopic.count || 0) > 0
      ? Math.min(numQuestions, Number(selectedDisplayTopic.count))
      : numQuestions;

    try {
      const token = getAuthItem("minerai_token");
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({
          topic: finalTopic,
          num_questions: requestedQuestionCount
        })
      });

      if (!response.ok) throw new Error("Không thể khởi tạo bộ câu hỏi từ máy chủ RAG.");

      const data = await response.json();
      if (!data.questions || data.questions.length === 0) {
        throw new Error("Dữ liệu câu hỏi bị rỗng.");
      }

      setQuizId(data.quiz_id);
      setActiveQuizTopic(finalTopicTitle);
      setActiveQuizTopicId(finalTopic);
      setQuestions(data.questions);
      setIsShuffledRedo(false);
      setSources(data.sources || []);
      setTimeLeft(requestedQuestionCount * 2 * 60);
      setQuizState("active");
      setTimerActive(true);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "Đã xảy ra lỗi khi tạo trắc nghiệm.");
      setQuizState("setup");
    }
  };

  const handleSelectOption = (qId: number, optionKey: string) => {
    setUserAnswers((prev) => ({
      ...prev,
      [qId]: optionKey
    }));
  };

  const recordRecentQuizLesson = (scoreData: any, answeredCount: number) => {
    const totalScore = Number(scoreData?.total_score ?? 0);
    const maxScore = Number(questions.length || scoreData?.max_score || scoreData?.total_questions || answeredCount || 0);
    const percentage = maxScore > 0 ? (totalScore / maxScore) * 100 : 0;
    const title = activeQuizTopic || selectedTopic || (lang === "vi" ? "Trắc nghiệm" : "Quiz");

    const lessonRecord = {
      id: quizId || `${title}-${Date.now()}`,
      title,
      subtitle: lang === "vi" ? "Trắc nghiệm đã hoàn thành" : "Completed quiz",
      topic: activeQuizTopicId || selectedTopic || title,
      score: Number(totalScore.toFixed(2)),
      max_score: Number(maxScore.toFixed(2)),
      percentage: Number(percentage.toFixed(1)),
      grade: scoreData?.grade,
      answered_questions: answeredCount,
      total_questions: questions.length || answeredCount,
      created_at: new Date().toISOString(),
    };

    saveLocalRecentLesson(lessonRecord);
    setCompletedScores((prev) => ({
      ...prev,
      [normalizeTopicKey(lessonRecord.topic)]: lessonRecord,
      [normalizeTopicKey(lessonRecord.title)]: lessonRecord,
    }));
  };

  useEffect(() => {
    if (quizState === "completed" && overallScore) {
      recordRecentQuizLesson(overallScore, Object.keys(userAnswers).length || questions.length);
    }
  }, [quizState, overallScore, quizId]);

  const handleAutoSubmit = () => {
    alert(lang === "vi" ? "Hết thời gian làm bài! Hệ thống tự động nộp bài." : "Time's up! Submitting your answers automatically.");
    submitQuiz();
  };

  const submitQuiz = async () => {
    setTimerActive(false);
    setQuizState("loading");
    setLoadingResults(true);

    try {
      if (isShuffledRedo) {
        const localEvaluations: { [key: number]: QuizResult } = {};
        let correctCount = 0;

        questions.forEach((question, index) => {
          const userAnswer = userAnswers[index] || "";
          const correctAnswer = question.correct_answer || "";
          const isCorrect = userAnswer.trim().toUpperCase() === correctAnswer.trim().toUpperCase();

          if (isCorrect) correctCount += 1;

          localEvaluations[index] = {
            is_correct: isCorrect,
            score: isCorrect ? 1 : 0,
            feedback: isCorrect
              ? "Chính xác! Bạn đã chọn đúng đáp án."
              : `Chưa chính xác. Đáp án đúng là ${correctAnswer}.`,
            correct_answer: correctAnswer,
            explanation: question.explanation,
            source_reference: question.source_reference,
            user_answer: userAnswer,
          };
        });

        setEvaluations(localEvaluations);
        const localScore = {
          total_score: correctCount,
          max_score: questions.length,
          total_questions: questions.length,
          percentage: questions.length > 0 ? (correctCount / questions.length) * 100 : 0,
        };
        setOverallScore(localScore);
        recordRecentQuizLesson(localScore, questions.length);
        setQuizState("completed");
        return;
      }

      const answerPromises = Object.entries(userAnswers).map(async ([qIndexStr, answer]) => {
        const qIndex = parseInt(qIndexStr);
        const token = getAuthItem("minerai_token");
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("/api/quiz/answer", {
          method: "POST",
          headers,
          body: JSON.stringify({
            quiz_id: quizId,
            question_index: qIndex,
            user_answer: answer
          })
        });
        if (res.ok) {
          const resultData = await res.json();
          setEvaluations((prev) => ({
            ...prev,
            [qIndex]: resultData
          }));
        }
      });

      await Promise.all(answerPromises);

      const token = getAuthItem("minerai_token");
      const headers: HeadersInit = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const scoreRes = await fetch(`/api/quiz/${quizId}/results`, { headers });
      if (scoreRes.ok) {
        const scoreData = await scoreRes.json();
        setOverallScore(scoreData.score);
        recordRecentQuizLesson(scoreData.score, scoreData.answered_questions || Object.keys(userAnswers).length);
      }
      setQuizState("completed");
    } catch (err) {
      console.error(err);
      alert("Đã xảy ra lỗi khi chấm điểm. Hiển thị kết quả làm bài của bạn.");
      setQuizState("completed");
    } finally {
      setLoadingResults(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const getTopicTitle = (topicId: string) => {
    const tItem = displayTopics.find((t) => t.id === topicId);
    return tItem ? tItem.title : topicId;
  };

  // Map raw filenames / interaction logs to known topic IDs for weak topic display
  const mapWeakTopicToId = (raw: string): string | null => {
    const s = raw.toLowerCase().replace(/[-_.\s]+/g, ' ');
    if (s.includes('apriori')) return 'apriori';
    if (s.includes('fp') || s.includes('growth')) return 'fp_growth';
    if (s.includes('kmeans') || s.includes('k means') || s.includes('k-means')) return 'kmeans';
    if (s.includes('dbscan')) return 'dbscan';
    // Check against displayTopics ids / titles
    const byId = displayTopics.find(t => t.id && s.includes(t.id.toLowerCase()));
    if (byId) return byId.id;
    const byTitle = displayTopics.find(t => t.title && s.includes(t.title.toLowerCase()));
    if (byTitle) return byTitle.id;
    return null;
  };

  const firstWeakTopicId = mapWeakTopicToId(weakTopics[0] || '');
  const firstWeakTopicTitle = firstWeakTopicId
    ? displayTopics.find(t => t.id === firstWeakTopicId)?.title || (lang === 'vi' ? 'Chủ đề ôn tập' : 'Review Topic')
    : (lang === 'vi' ? 'Chủ đề liên quan' : 'Related Topic');

  const selectedTopicInfo = !isCustomTopic ? displayTopics.find((topic) => topic.id === selectedTopic) : undefined;
  const availableQuestionCounts = (() => {
    const baseCounts = [5, 8, 10];
    if (!selectedTopicInfo?.isPersonal) return baseCounts;

    const personalCount = Number(selectedTopicInfo.count || 0);
    if (!personalCount) return baseCounts;

    const counts = baseCounts.filter((count) => count <= personalCount);
    return counts.length > 0 ? counts : [personalCount];
  })();
  const availableQuestionCountsKey = availableQuestionCounts.join(",");

  useEffect(() => {
    if (quizState !== "setup") return;
    if (availableQuestionCounts.length === 0 || availableQuestionCounts.includes(numQuestions)) return;
    setNumQuestions(availableQuestionCounts[availableQuestionCounts.length - 1]);
  }, [availableQuestionCountsKey, numQuestions, quizState]);

  if (quizState === "setup") {
    return (
      <div className="max-w-5xl mx-auto p-4 space-y-4">
        <div className="text-center space-y-2.5">

          <h2 className="text-3xl font-display font-semibold text-slate-800">
            {lang === "vi" ? "Hãy cùng học nhé!" : "Let's Learn Together"}
          </h2>
          <p className="text-sm text-slate-600 max-w-md mx-auto leading-relaxed">
            {lang === "vi"
              ? "Chọn chủ đề và để MinerAI tạo bộ câu hỏi cá nhân hóa từ tài liệu thật."
              : "Pick a topic and let MinerAI create a personalized quiz from real course materials."}
          </p>
        </div>

        {errorMsg && (
          <div className="p-4 bg-rose-50 border border-rose-100 text-rose-700 rounded-xl flex items-start gap-3">
            <AlertCircle size={24} className="mt-0.5 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-4 space-y-4">
          {/* Topic Selection */}
          <div>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-3 gap-4">
              <h3 className="text-base font-semibold text-slate-700 flex items-center gap-2">
                <span className="text-[#7a1c1c]">1.</span>
                {lang === "vi" ? "Chọn chủ đề bạn muốn ôn" : "Choose what you'd like to practice"}
              </h3>
              <button
                onClick={() => setIsLibraryModalOpen(true)}
                className="px-3.5 py-2 bg-rose-50 text-[#7a1c1c] rounded-lg text-sm font-medium flex items-center gap-2 hover:bg-rose-100 transition-colors"
              >
                <Library size={18} />
                {lang === "vi" ? "Mở Thư viện đề (Admin tạo)" : "Open Quiz Library"}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {displayTopics.map((t) => {
                const storedScore = getLatestScoreForTopic(t);
                const latestScore = storedScore ? getDisplayScore(storedScore) : null;
                const isCompleted = Boolean(storedScore) || completedTopics.includes(t.id);
                const isWeak = weakTopics.includes(t.title) || weakTopics.includes(t.id);

                return (
                  <button
                    key={t.id}
                    onClick={() => {
                      setSelectedTopic(t.id);
                      setIsCustomTopic(false);
                    }}
                    className={`group p-4 border rounded-xl text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md flex flex-col ${!isCustomTopic && selectedTopic === t.id
                      ? "border-rose-800 bg-rose-50 border-rose-200 shadow-sm"
                      : "border-slate-200 hover:border-slate-300"
                      }`}
                  >
                    <div className="flex items-start justify-between mb-2.5 w-full">
                      <div className="w-9 h-9 bg-white rounded-lg flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
                        <t.icon className="w-5 h-5 text-[#7a1c1c]" />
                      </div>
                      <div className="flex flex-col gap-2 items-end">
                        {!isCustomTopic && selectedTopic === t.id && (
                          <div className="w-6 h-6 bg-rose-800 rounded-lg flex items-center justify-center text-white text-sm shadow-sm">
                            ✨
                          </div>
                        )}
                        <div className="flex gap-1.5">
                          {isWeak && (
                            <span className="px-2 py-1 bg-rose-100 text-rose-700 text-[10px] font-bold rounded-lg whitespace-nowrap">
                              🔥 {lang === "vi" ? "Cần ôn tập" : "Needs review"}
                            </span>
                          )}
                          {isCompleted && !isWeak && (
                            <span className="px-2 py-1 bg-violet-100 text-violet-700 text-[10px] font-bold rounded-lg whitespace-nowrap">
                              ✓ {lang === "vi" ? "Đã làm" : "Done"}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <h4 className="font-semibold text-base text-slate-800 mb-1.5">{t.title}</h4>
                    <p className="text-slate-600 text-[13px] leading-relaxed line-clamp-3">{t.desc}</p>
                    {latestScore && (
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] font-bold">
                        <span className="rounded-lg bg-emerald-50 px-2 py-1 text-emerald-700">
                          {latestScore.percentage}%
                        </span>
                        <span className="rounded-lg bg-slate-100 px-2 py-1 text-slate-600">
                          {latestScore.score}/{latestScore.max_score} {lang === "vi" ? "điểm" : "pts"}
                        </span>
                        <span className="rounded-lg bg-slate-100 px-2 py-1 text-slate-600">
                          {latestScore.answered_questions}/{latestScore.total_questions} {lang === "vi" ? "câu" : "questions"}
                        </span>
                      </div>
                    )}
                  </button>
                );
              })}

              {/* Custom Topic Card 
              <div
                onClick={() => setIsCustomTopic(true)}
                className={`group p-5 border-2 rounded-2xl text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-xl flex flex-col cursor-pointer ${isCustomTopic
                  ? "border-rose-800 bg-rose-50 border-rose-200 shadow-sm"
                  : "border-slate-200 hover:border-slate-300"
                  }`}
              >
                <div className="flex items-start justify-between mb-3 w-full">
                  <div className="w-10 h-10 bg-white rounded-2xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                    <BookOpen className="w-8 h-8 text-[#7a1c1c]" />
                  </div>
                  {isCustomTopic && (
                    <div className="w-8 h-8 bg-rose-800 rounded-2xl flex items-center justify-center text-white text-xl shadow-sm">
                      ✨
                    </div>
                  )}
                </div>

                <h4 className="font-semibold text-xl text-slate-800 mb-3">
                  {lang === "vi" ? "Luyện tập câu hỏi cá nhân" : "Custom Topic"}
                </h4>

                {isCustomTopic ? (
                  <input
                    type="text"
                    value={customTopic}
                    onChange={(e) => setCustomTopic(e.target.value)}
                    placeholder={lang === "vi" ? "Nhập chủ đề bạn muốn thi..." : "Enter topic name..."}
                    className="w-full mt-2 px-4 py-3 bg-white border border-rose-200 focus:border-rose-800 rounded-xl outline-none focus:ring-2 focus:ring-rose-100 transition-all text-slate-700"
                    autoFocus
                  />
                ) : (
                  <p className="text-slate-600 text-[15px] leading-relaxed">
                    {lang === "vi"
                      ? "Bạn muốn làm trắc nghiệm về phần nào khác? MinerAI sẽ tìm trong tài liệu."
                      : "Want to quiz on something else? MinerAI will find it."}
                  </p>
                )}
              </div> */}

              {/* Personalized Topic Card */}
              {weakTopics.length > 0 && (
                <div
                  onClick={() => {
                    setIsCustomTopic(false);
                    const targetId = firstWeakTopicId || weakTopics[0];
                    setSelectedTopic(targetId);
                  }}
                  className={`group p-5 border-2 rounded-2xl text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-xl flex flex-col cursor-pointer ${
                    !isCustomTopic && selectedTopic === (firstWeakTopicId || weakTopics[0])
                      ? "border-rose-500 bg-gradient-to-br from-rose-50 to-orange-50 shadow-rose-100"
                      : "border-rose-200 hover:border-rose-300 bg-rose-50/30"
                  }`}
                >
                  <div className="flex items-start justify-between mb-3 w-full">
                    <div className="w-10 h-10 bg-white rounded-2xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                      <Flame className="w-8 h-8 text-[#7a1c1c]" />
                    </div>
                    {!isCustomTopic && selectedTopic === (firstWeakTopicId || weakTopics[0]) && (
                      <div className="w-8 h-8 bg-rose-500 rounded-2xl flex items-center justify-center text-white text-xl shadow-sm">
                        ✨
                      </div>
                    )}
                  </div>

                  <h4 className="font-semibold text-xl text-slate-800 mb-3">
                    {lang === "vi" ? "Các câu mà bạn dùng làm sai" : "Review Weaknesses"}
                  </h4>

                  <p className="text-slate-600 text-[15px] leading-relaxed">
                    {lang === "vi"
                      ? `Hệ thống gợi ý bạn nên ôn tập: ${firstWeakTopicTitle}`
                      : `System suggests reviewing: ${firstWeakTopicTitle}`}
                  </p>
                </div>
              )}
            </div>


          </div>

          {/* Questions Count */}
          <div className="border-t border-slate-100 pt-5">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  {lang === "vi" ? "Số câu hỏi" : "How many questions?"}
                </label>
                <div className="flex gap-2">
                  {availableQuestionCounts.map((num) => (
                    <button
                      key={num}
                      onClick={() => setNumQuestions(num)}
                      className={`px-5 py-2.5 rounded-lg font-semibold text-sm transition-all duration-200 border ${numQuestions === num
                        ? "bg-[#7a1c1c] text-white border-rose-900 shadow-sm shadow-[#7a1c1c]/20"
                        : "border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700"
                        }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={() => startQuiz()}
                className="mt-auto py-3 px-8 bg-[#7a1c1c] hover:bg-[#5a1515] text-white rounded-lg font-semibold text-sm flex items-center gap-2.5 shadow-md shadow-[#7a1c1c]/20 active:scale-[0.97] transition-all duration-200"
              >
                <span>{lang === "vi" ? "Bắt đầu hành trình" : "Start the journey"}</span>
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Library Modal */}
        {isLibraryModalOpen && (
          <div className="fixed inset-0 md:left-80 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl w-full max-w-3xl max-h-[85vh] shadow-2xl flex flex-col overflow-hidden">
              <div className="p-4 border-b border-slate-100 flex justify-between items-start bg-white">
                <div>
                  <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    <Library size={22} className="text-[#7a1c1c]" />
                    {lang === "vi" ? "Lấy đề từ Ngân hàng" : "Load From Question Bank"}
                  </h3>
                  <p className="text-sm text-slate-500 mt-1">
                    {lang === "vi" ? "Chọn một đề có sẵn để tải vào màn trắc nghiệm." : "Choose an existing quiz to load into practice."}
                  </p>
                </div>
                <button onClick={() => setIsLibraryModalOpen(false)} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg transition-colors">
                  <XCircle size={22} />
                </button>
              </div>

              <div className="overflow-y-auto flex-1 divide-y divide-slate-100">
                {libraryTopics.length === 0 ? (
                  <div className="px-6 py-16 text-center text-slate-500 text-base">
                    {lang === "vi" ? "Chưa có đề nào trong thư viện." : "No quizzes found in library."}
                  </div>
                ) : (
                  libraryTopics.map((t, idx) => {
                        const foundTopic = topics.find(p => p.id === t.topic);
                        const defaultTitle = t.topic.split('_').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                        const displayTitle = foundTopic ? foundTopic.title : defaultTitle;

                        return (
                          <div key={idx} className="p-4 flex items-center justify-between gap-4 hover:bg-slate-50 transition-colors group">
                            <div className="min-w-0">
                              <div className="font-semibold text-slate-800 text-base">{displayTitle}</div>
                              <div className="text-sm text-slate-500 mt-1">
                                {t.questionCount} {lang === "vi" ? "câu hỏi" : "questions"} · topic: {t.topic}
                              </div>
                            </div>
                            <div className="flex-shrink-0">
                              <button
                                onClick={() => {
                                  setIsLibraryModalOpen(false);

                                  // Generate a unique ID — if topic already exists, append a counter
                                  setDownloadedTopics(prev => {
                                    const allTopicIds = [...topics.map(tp => tp.id), ...prev.map(p => p.id)];
                                    let uniqueId = t.topic;
                                    let counter = 1;
                                    while (allTopicIds.includes(uniqueId)) {
                                      counter++;
                                      uniqueId = `${t.topic}_${counter}`;
                                    }
                                    const uniqueTitle = counter > 1
                                      ? `${displayTitle} (${counter})`
                                      : displayTitle;

                                    setSelectedTopic(uniqueId);
                                    setIsCustomTopic(false);
                                    setCustomTopic(t.topic); // actual topic for API call

                                    return [...prev, {
                                      id: uniqueId,
                                      apiTopic: t.topic,   // real topic ID for API calls
                                      icon: Library,
                                      title: uniqueTitle,
                                      desc: lang === "vi" ? "Đề thi tải từ thư viện (Admin biên soạn)." : "Quiz loaded from Admin Library.",
                                    }];
                                  });
                                }}
                                className="px-4 py-2 bg-[#7a1c1c] hover:bg-[#5f1515] text-white rounded-lg font-medium transition-all inline-flex items-center gap-2 text-sm shadow-sm shadow-[#7a1c1c]/20 active:scale-95"
                              >
                                <Download size={16} />
                                {lang === "vi" ? "Tải đề" : "Load Quiz"}
                              </button>
                            </div>
                          </div>
                        );
                      })
                )}
              </div>

              <div className="p-4 border-t border-slate-100 flex justify-end bg-slate-50">
                <button
                  onClick={() => setIsLibraryModalOpen(false)}
                  className="px-4 py-2 text-slate-600 hover:bg-slate-100 font-medium rounded-lg transition-colors"
                >
                  {lang === "vi" ? "Đóng" : "Close"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (quizState === "loading") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[420px] space-y-4">
        <div className="relative">
          <div className="w-18 h-18 border-6 border-slate-100 rounded-full"></div>
          <RefreshCw className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 text-rose-800 animate-spin" />
        </div>
        <div className="text-center space-y-3">
          <h3 className="text-xl font-medium text-slate-800">
            {lang === "vi" ? "Đang chuẩn bị cho bạn..." : "Preparing your quiz..."}
          </h3>
          <p className="text-slate-600 max-w-xs">
            {lang === "vi"
              ? "MinerAI đang đọc lại slide và soạn câu hỏi thật hay"
              : "MinerAI is reviewing materials and crafting thoughtful questions"}
          </p>
        </div>
      </div>
    );
  }

  if (quizState === "active" && questions.length > 0) {
    const currentQuestion = questions[currentIdx];
    const isLastQuestion = currentIdx === questions.length - 1;
    const selectedAnswer = userAnswers[currentIdx];

    const activeHint = sources[currentIdx]
      ? `Từ slide: ${sources[currentIdx].filename} • Trang ${sources[currentIdx].page || "?"}`
      : "Hãy nhớ lại những gì bạn đã học nhé.";

    return (
      <div className="max-w-7xl mx-auto p-3 pb-24">
        <div className="flex flex-col xl:flex-row gap-3">
          {/* Main Content */}
          <div className="flex-1 space-y-3 min-w-0">
            {/* Progress Bar - Friendly */}
            <div className="flex items-center gap-3 bg-white rounded-xl px-4 py-2.5 border border-slate-100 shadow-sm">
              <div className="text-[#7a1c1c] font-medium text-sm flex items-center gap-2">
                <BookOpen size={17} />
                <span>{currentIdx + 1} / {questions.length}</span>
              </div>
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#7a1c1c] rounded-full transition-all duration-500"
                  style={{ width: `${((currentIdx + 1) / questions.length) * 100}%` }}
                />
              </div>
            </div>

            {/* Question Card - Soft & Warm */}
            <div className="bg-white border border-slate-100 rounded-xl shadow-sm p-3.5 md:p-4">
              <div className="flex items-center gap-3 mb-2.5">
                <div className="px-3 py-1 bg-rose-100 text-[#7a1c1c] text-xs font-medium rounded-full">
                  {lang === "vi" ? `Câu ${currentIdx + 1}` : `Question ${currentIdx + 1}`}
                </div>
                <div className="h-px flex-1 bg-gradient-to-r from-slate-100 to-transparent" />
              </div>

              <h3 className="text-lg md:text-xl leading-snug font-medium text-slate-800 mb-4">
                {currentQuestion.question}
              </h3>

              {currentQuestion.options ? (
                <div className="space-y-2.5">
                  {Object.entries(currentQuestion.options).map(([key, val]) => {
                    const isChecked = selectedAnswer === key;
                    return (
                      <label
                        key={key}
                        onClick={() => handleSelectOption(currentIdx, key)}
                        className={`block p-3 border rounded-xl cursor-pointer transition-all duration-200 hover:border-rose-200 text-sm ${isChecked
                          ? "border-rose-800 bg-rose-50 shadow-inner"
                          : "border-slate-200 hover:bg-slate-50"
                          }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0 mt-0.5 transition-all ${isChecked ? "bg-rose-800 border-rose-800" : "border-slate-300"
                            }`}>
                            {isChecked && <CheckCircle2 className="text-white" size={13} />}
                          </div>
                          <div className="min-w-0 leading-relaxed">
                            <span className="font-semibold text-[#7a1c1c] mr-2">{key}.</span>
                            <span className="text-slate-700">{val}</span>
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              ) : (
                <textarea
                  value={selectedAnswer || ""}
                  onChange={(e) => handleSelectOption(currentIdx, e.target.value)}
                  placeholder={lang === "vi" ? "Viết câu trả lời của bạn ở đây..." : "Write your answer here..."}
                  className="w-full h-40 p-4 border border-slate-200 focus:border-indigo-300 rounded-xl text-sm resize-none focus:outline-none"
                />
              )}
            </div>

            {/* Navigation */}
            <div className="sticky bottom-3 z-20 flex justify-between items-center gap-3 bg-white/95 backdrop-blur border border-slate-100 shadow-lg rounded-xl p-2">
              <button
                onClick={() => {
                  setQuizState("setup");
                  if (onClearCustomPractice) onClearCustomPractice();
                }}
                className="px-3 py-2 text-slate-500 hover:bg-slate-100 rounded-lg font-medium transition-colors text-sm"
              >
                ← {lang === "vi" ? "Quay lại" : "Back"}
              </button>
              <div className="flex items-center gap-2 text-[#7a1c1c] font-mono font-bold text-base">
                <button
                  onClick={() => setCurrentIdx((prev) => Math.max(0, prev - 1))}
                  disabled={currentIdx === 0}
                  className="flex items-center gap-2 px-3.5 py-2 rounded-lg border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition-all text-slate-600 text-sm"
                >
                  <ArrowLeft size={17} />
                  <span className="font-medium">{lang === "vi" ? "Câu trước" : "Previous"}</span>
                </button>

                {isLastQuestion ? (
                  <button
                    onClick={submitQuiz}
                    className="flex items-center gap-2 px-4 py-2 bg-[#7a1c1c] hover:bg-[#7a1c1c] text-white rounded-lg font-semibold text-sm shadow-md shadow-[#7a1c1c]/20 transition-all active:scale-95"
                  >
                    {lang === "vi" ? "Nộp bài và xem kết quả" : "Submit & See Results"}
                    <Award size={18} />
                  </button>
                ) : (
                  <button
                    onClick={() => setCurrentIdx((prev) => Math.min(questions.length - 1, prev + 1))}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg font-semibold text-sm shadow-md shadow-slate-200 transition-all active:scale-95"
                  >
                    {lang === "vi" ? "Câu tiếp theo" : "Next Question"}
                    <ArrowRight size={18} />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Right Sidebar - Soft & Helpful */}
          <div className="xl:w-72 space-y-3">
            {/* Timer */}
            <div className="bg-white border border-slate-100 rounded-xl p-3 text-center shadow-sm">
              <div className="flex justify-center mb-2">
                <div className="bg-orange-100 text-orange-600 w-8 h-8 rounded-lg flex items-center justify-center">
                  <Clock size={18} />
                </div>
              </div>
              <div className={`text-2xl font-mono font-semibold transition-colors ${timeLeft < 120 ? "text-orange-500" : "text-slate-800"}`}>
                {formatTime(timeLeft)}
              </div>
              <p className="text-xs uppercase tracking-widest text-slate-500 mt-1">Thời gian còn lại</p>
            </div>

            {/* AI Friend Hint */}


            {/* Question Navigator */}
            <div className="bg-white border border-slate-100 rounded-xl p-3">
              <h4 className="uppercase text-xs tracking-widest text-slate-500 font-medium mb-2.5">Câu hỏi</h4>
              <div className="grid grid-cols-5 gap-2">
                {questions.map((_, idx) => {
                  const isCurrent = currentIdx === idx;
                  const isAnswered = userAnswers[idx] !== undefined;
                  return (
                    <button
                      key={idx}
                      onClick={() => setCurrentIdx(idx)}
                      className={`aspect-square rounded-lg font-medium text-sm transition-all flex items-center justify-center border min-h-10 ${isCurrent
                        ? "bg-[#7a1c1c] text-white border-rose-900 shadow-lg"
                        : isAnswered
                          ? "bg-rose-100 border-rose-200 text-[#7a1c1c]"
                          : "border-slate-200 hover:bg-slate-50 text-slate-400"
                        }`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Completed Screen - Warm & Encouraging
  if (quizState === "completed") {
    const totalQuestions = questions.length;
    const answeredCount = Object.keys(userAnswers).length;

    let percentage = 0;
    let totalScore = 0;
    if (overallScore) {
      totalScore = overallScore.total_score || 0;
      percentage = totalQuestions > 0 ? (totalScore / totalQuestions) * 100 : 0;
    } else {
      const evaluatedArray = Object.entries(evaluations);
      if (evaluatedArray.length > 0) {
        const correctCount = evaluatedArray.filter(([_, ev]) => (ev as QuizResult).is_correct).length;
        percentage = (correctCount / totalQuestions) * 100;
        totalScore = correctCount;
      }
    }

    const getGrowthResult = (pct: number) => {
      if (pct >= 90) {
        return {
          label: lang === "vi" ? "Xuất sắc!" : "Outstanding!",
          message: lang === "vi" ? "Bạn nắm bài rất chắc, hãy tiếp tục duy trì phong độ này nhé." : "You have a very strong grasp. Keep this momentum going.",
          Icon: TreePine,
          iconColor: "text-emerald-700",
          iconBg: "from-emerald-100 to-green-50",
          percentColor: "text-emerald-700",
        };
      }
      if (pct >= 80) {
        return {
          label: lang === "vi" ? "Tốt lắm!" : "Great job!",
          message: lang === "vi" ? "Bạn làm bài rất ổn, chỉ cần rà lại vài câu sai để chắc kiến thức hơn." : "You did very well. Review a few missed questions to make it stronger.",
          Icon: TreePine,
          iconColor: "text-green-600",
          iconBg: "from-green-100 to-lime-50",
          percentColor: "text-green-600",
        };
      }
      if (pct >= 60) {
        return {
          label: lang === "vi" ? "Khá lắm!" : "Good effort!",
          message: lang === "vi" ? "Bạn đã hiểu phần chính, hãy luyện thêm các câu sai để tiến bộ nhanh hơn." : "You understand the core ideas. Practice missed questions to improve faster.",
          Icon: Flower2,
          iconColor: "text-lime-600",
          iconBg: "from-lime-100 to-yellow-50",
          percentColor: "text-lime-700",
        };
      }
      if (pct >= 40) {
        return {
          label: lang === "vi" ? "Cố gắng hơn nhé!" : "Keep going!",
          message: lang === "vi" ? "Bạn đã có nền tảng ban đầu, hãy ôn tập thêm và làm lại bài này." : "You have a starting base. Review more and try this quiz again.",
          Icon: Leaf,
          iconColor: "text-amber-600",
          iconBg: "from-amber-100 to-yellow-50",
          percentColor: "text-amber-600",
        };
      }
      return {
        label: lang === "vi" ? "Cố gắng ôn tập nhiều hơn nhé!" : "Review more and keep trying!",
        message: lang === "vi" ? "Chưa sao, hãy xem kỹ giải thích từng câu rồi thử lại lần nữa." : "No worries. Study each explanation carefully, then try again.",
        Icon: Sprout,
        iconColor: "text-rose-700",
        iconBg: "from-rose-100 to-orange-50",
        percentColor: "text-[#8b1e1e]",
      };
    };

    const rank = getGrowthResult(percentage);
    const ResultIcon = rank.Icon;

    return (
      <div className="max-w-4xl mx-auto p-4 space-y-4">
        <div className="bg-white rounded-xl shadow-md shadow-rose-100/50 border border-slate-100 p-6 text-center">
          <div className={`mx-auto w-20 h-20 bg-gradient-to-br ${rank.iconBg} rounded-full flex items-center justify-center mb-4`}>
            <ResultIcon className={`w-11 h-11 ${rank.iconColor}`} />
          </div>

          <h2 className="text-3xl font-semibold text-slate-800 mb-1.5">{rank.label}</h2>
          <p className={`text-5xl font-bold mb-2 ${rank.percentColor}`}>{percentage.toFixed(0)}%</p>
          <p className="max-w-xl mx-auto text-sm md:text-base text-slate-500 leading-relaxed mb-4">{rank.message}</p>

          <div className="inline-flex items-center gap-5 bg-slate-50 rounded-xl px-7 py-4">
            <div className="text-center">
              <div className="text-xl font-semibold text-slate-800">{totalScore}</div>
              <div className="text-xs text-slate-500">Đúng</div>
            </div>
            <div className="h-12 w-px bg-slate-200" />
            <div className="text-center">
              <div className="text-xl font-semibold text-slate-800">{answeredCount}/{totalQuestions}</div>
              <div className="text-xs text-slate-500">Đã trả lời</div>
            </div>
          </div>

          <div className="mt-7 flex flex-col md:flex-row items-center justify-center gap-3">
            <button
              onClick={() => {
                const shuffledQuestions = shuffleQuizQuestions(questions);
                setQuestions(shuffledQuestions);
                setCurrentIdx(0);
                setQuizState("active");
                setUserAnswers({});
                setEvaluations({});
                setOverallScore(null);
                setIsShuffledRedo(true);
                setTimeLeft(numQuestions * 2 * 60);
                setTimerActive(true);
              }}
              className="w-full md:w-auto py-2.5 px-5 bg-white border border-rose-800 text-[#7a1c1c] hover:bg-rose-50 rounded-lg font-medium flex items-center justify-center gap-2 text-sm transition-all"
            >
              <RefreshCw size={20} />
              {lang === "vi" ? "Làm lại bài này" : "Redo this quiz"}
            </button>

            <button
              onClick={() => startQuiz(customPracticeTopic || undefined)}
              className="w-full md:w-auto py-2.5 px-5 bg-[#7a1c1c] hover:bg-[#7a1c1c] text-white rounded-lg font-medium flex items-center justify-center gap-2 text-sm shadow-md shadow-[#7a1c1c]/20 transition-all"
            >
              <Brain size={20} />
              {lang === "vi" ? "Tạo bộ đề mới" : "New questions"}
            </button>

            <button
              onClick={() => {
                setQuizState("setup");
                if (onClearCustomPractice) onClearCustomPractice();
              }}
              className="w-full md:w-auto py-2.5 px-5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium flex items-center justify-center gap-2 text-sm transition-all"
            >
              <ArrowLeft size={20} />
              {lang === "vi" ? "Đổi chủ đề" : "Change topic"}
            </button>
          </div>
        </div>

        {/* Review Section */}
        <div>
          <h3 className="text-xl font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <HelpCircle size={24} className="text-[#7a1c1c]" />
            {lang === "vi" ? "Xem lại chi tiết" : "Review your answers"}
          </h3>

          <div className="space-y-4">
            {questions.map((q, idx) => {
              const userAnswer = userAnswers[idx];
              const evaluation = evaluations[idx];
              const isCorrect = evaluation?.is_correct || false;

              return (
                <div
                  key={idx}
                  className={`rounded-2xl p-4 border transition-all ${!userAnswer
                    ? "border-slate-200 bg-slate-50/50"
                    : isCorrect
                      ? "border-rose-200 bg-rose-50/30"
                      : "border-rose-200 bg-rose-50/30"
                    }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="uppercase text-xs tracking-widest text-slate-500 mb-1">Câu {idx + 1}</div>
                      <h4 className="text-base font-medium leading-tight text-slate-800">{q.question}</h4>
                    </div>
                    {userAnswer && (
                    <div className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 ${isCorrect ? "bg-rose-100 text-[#7a1c1c]" : "bg-rose-100 text-rose-700"}`}>
                        {isCorrect ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                        {isCorrect ? "Đúng" : "Chưa đúng"}
                      </div>
                    )}
                  </div>

                  {/* Options or Answer */}
                  {q.options ? (
                    <div className="grid grid-cols-1 gap-3 text-sm">
                      {Object.entries(q.options).map(([key, val]) => (
                        <div
                          key={key}
                          className={`p-3 rounded-xl border ${evaluation?.correct_answer === key ? "border-indigo-400 bg-rose-50" : userAnswer === key ? "border-rose-300 bg-rose-50" : "border-slate-100"}`}
                        >
                          <strong>{key}.</strong> {val}
                          {evaluation?.correct_answer === key && " ✓ Đáp án đúng"}
                          {userAnswer === key && !isCorrect && " ← Của bạn"}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-white p-4 rounded-xl border text-slate-700">
                      <strong>Bạn trả lời:</strong> {userAnswer || "Chưa trả lời"}
                    </div>
                  )}

                  {evaluation?.explanation && (
                    <div className="mt-8 pt-8 border-t border-slate-100">
                      <div className="font-medium text-[#7a1c1c] mb-3 flex items-center gap-2">
                        <BookOpen size={18} /> Giải thích chi tiết
                      </div>
                      <p className="text-slate-600 leading-relaxed">{evaluation.explanation}</p>
                    </div>
                  )}

                  {evaluation?.source_reference && (
                    <div className="mt-4 text-xs text-slate-500 flex items-center gap-2">
                      📖 {evaluation.source_reference}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
