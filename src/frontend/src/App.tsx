import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import OverviewTab from "./components/OverviewTab";
import MentorTab from "./components/MentorTab";
import DataLabTab from "./components/DataLabTab";
import LibraryTab from "./components/LibraryTab";
import SettingsTab from "./components/SettingsTab";
import HelpTab from "./components/HelpTab";
import QuizTab from "./components/QuizTab";
import SummaryNotesTab from "./components/SummaryNotesTab";
import AuthScreen from "./components/AuthScreen";
import AdminTab from "./components/AdminTab";
import MyQuestionsTab from "./components/MyQuestionsTab";
import { DatasetFile, ChatMessage, ChatThread } from "./types";
import { i18n, Lang } from "./i18n";
import { clearAuthSession, getAuthItem, hasAuthSession } from "./authStorage";

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(hasAuthSession());
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [lang, setLang] = useState<Lang>("vi");
  const t = i18n[lang];

  const dedupeById = <T extends { id: string }>(items: T[]) => {
    const seen = new Set<string>();
    return items.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
  };

  // State để chuyển thẳng vào Quiz tự tạo
  const [customQuizTopic, setCustomQuizTopic] = useState<string | null>(null);
  const [selectedQuizTopic, setSelectedQuizTopic] = useState<string | null>(null);

  const [labDataset, setLabDataset] = useState<DatasetFile | null>({
    name: "sales_data_2023.csv",
    size: "14.2 MB",
    status: "Sẵn sàng",
    content: "Store,Product,Sales,Date,Rating\nStoreA,Laptop,25000000,2023-01-10,4.8\nStoreB,Smartphone,12000000,2023-01-12,4.5"
  });

  // --- LIFTED CHAT STATE ---
  const initialHistory: { [key: string]: ChatMessage[] } = {
    "thread-1": [
      {
        id: "m1",
        role: "model",
        content: t.mentorGreeting,
        timestamp: "14:23",
      },
      {
        id: "m2",
        role: "user",
        content: lang === "vi"
          ? "Giải thích thuật toán K-means một cách đơn giản, và cho tôi một ví dụ về code Python."
          : "Explain the K-means algorithm simply and give me a Python code example.",
        timestamp: "14:24",
      },
      {
        id: "m3",
        role: "model",
        content: `**K-means** là một thuật toán học máy không giám sát (unsupervised learning) dùng để phân nhóm dữ liệu. Chữ \"K\" đại diện cho số lượng nhóm (clusters) mà bạn muốn tạo ra.\n\n### Cách hoạt động cơ bản:\n1. **Chọn ngẫu nhiên** K điểm làm tâm cụm (centroids).\n2. **Gán** mỗi điểm dữ liệu vào tâm cụm gần nhất dựa vào khoảng cách Euclidean.\n3. **Tính toán lại** vị trí tâm cụm dựa trên trung bình cộng tọa độ các điểm đã gán.\n4. **Lặp lại** bước 2 và 3 cho đến khi tâm cụm không thay đổi hoặc đạt mức lặp cực đại.\n\nDưới đây là ví dụ sử dụng thư viện \`scikit-learn\` trong Python:\n\`\`\`python\nfrom sklearn.cluster import KMeans\nimport numpy as np\n\n# Dữ liệu mẫu (2D)\nX = np.array([[1, 2], [1, 4], [1, 0],\n              [10, 2], [10, 4], [10, 0]])\n\n# Khởi tạo mô hình K-means với K=2\nkmeans = KMeans(n_clusters=2, random_state=0, n_init="auto")\n\n# Huấn luyện mô hình\nkmeans.fit(X)\n\nprint("Labels:", kmeans.labels_)\nprint("Centers:", kmeans.cluster_centers_)\n\`\`\``,
        timestamp: "14:25",
      },
    ],
    "thread-2": [
      {
        id: "m4",
        role: "model",
        content: lang === "vi"
          ? "Chào bạn! Cần trợ giúp gì về xử lý dữ liệu thiếu trong học máy?"
          : "Hello! Need help with missing data handling in machine learning?",
        timestamp: "Thứ Ba",
      },
    ],
    "thread-3": [
      {
        id: "m5",
        role: "model",
        content: lang === "vi"
          ? "Chào bạn! Ở đây phân tích về Trực quan hóa dữ liệu sử dụng PCA."
          : "Hello! Here we analyze Data Visualization using Principal Component Analysis (PCA).",
        timestamp: "Tuần trước",
      },
    ],
  };
  void initialHistory;

  const getUserRole = () => {
    try {
      const user = JSON.parse(getAuthItem("minerai_user") || "{}");
      return user?.role || "user";
    } catch { return "user"; }
  };

  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string>("");
  const [messageHistory, setMessageHistory] = useState<{ [key: string]: ChatMessage[] }>({});

  useEffect(() => {
    Object.keys(localStorage)
      .filter((key) => key.startsWith("minerai_chat_threads_") || key.startsWith("minerai_chat_history_"))
      .forEach((key) => localStorage.removeItem(key));
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;

    const sendHeartbeat = () => {
      const token = getAuthItem("minerai_token");
      if (!token) return;
      fetch("/api/auth/heartbeat", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
      }).catch(() => {
        // Best-effort presence update.
      });
    };

    sendHeartbeat();
    const heartbeatTimer = window.setInterval(sendHeartbeat, 30000);
    return () => window.clearInterval(heartbeatTimer);
  }, [isAuthenticated]);

  // Load threads on mount / login
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const fetchThreads = async () => {
      try {
        const token = getAuthItem("minerai_token");
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        const response = await fetch("/api/conversations", { headers });
        if (response.ok) {
          const data = await response.json();
          if (data.conversations && data.conversations.length > 0) {
            const mappedThreads = dedupeById(data.conversations.map((c: any) => ({
              id: c.conversation_id,
              title: c.title,
              dateGroup: new Date(c.updated_at).toLocaleString(lang === "vi" ? "vi-VN" : "en-US", {
                hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric"
              })
            })));
            setThreads(mappedThreads);
            if (!activeThreadId || !mappedThreads.some((t: any) => t.id === activeThreadId)) {
              setActiveThreadId(mappedThreads[0].id);
            }
          } else {
            handleNewThread();
          }
        }
      } catch (err) {
        console.error("Lỗi khi tải cuộc trò chuyện từ DB:", err);
      }
    };
    
    fetchThreads();
  }, [isAuthenticated]);

  // Load messages for activeThreadId
  useEffect(() => {
    if (!isAuthenticated || !activeThreadId) {
      return;
    }
    
    const isMongoId = /^[0-9a-fA-F]{24}$/.test(activeThreadId);
    if (!isMongoId) {
      return;
    }
    
    if (messageHistory[activeThreadId]?.some((message) => !message.id.startsWith("m-init-"))) {
      return;
    }
    
    const fetchMessages = async () => {
      try {
        const token = getAuthItem("minerai_token");
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        const response = await fetch(`/api/conversations/${activeThreadId}/messages`, { headers });
        if (response.ok) {
          const data = await response.json();
          const mappedMessages = data.messages.map((m: any, idx: number) => ({
            id: `${m.message_id}-${idx}`,
            role: m.role === "assistant" ? "model" : m.role,
            content: m.content,
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            citations: m.metadata?.citations || []
          }));
          
          if (mappedMessages.length > 0) {
            setMessageHistory(prev => ({
              ...prev,
              [activeThreadId]: mappedMessages
            }));
          }
        }
      } catch (err) {
        console.error("Lỗi khi tải tin nhắn từ DB:", err);
      }
    };
    
    fetchMessages();
  }, [activeThreadId, isAuthenticated]);

  const handleNewThread = async () => {
    try {
      const token = getAuthItem("minerai_token");
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      const response = await fetch("/api/conversations", {
        method: "POST",
        headers,
        body: JSON.stringify({ title: t.mentorNewThreadTitle })
      });
      
      if (response.ok) {
        const data = await response.json();
        const newId = data.conversation_id;
        
        const timeString = new Date().toLocaleString(lang === "vi" ? "vi-VN" : "en-US", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric" });
        const newThread: ChatThread = {
          id: newId,
          title: t.mentorNewThreadTitle,
          dateGroup: timeString,
        };
        
        setThreads(prev => [newThread, ...prev]);
        setMessageHistory((prev) => ({
          ...prev,
          [newId]: [{
            id: `m-init-${Date.now()}`,
            role: "model",
            content: t.mentorNewThreadGreet,
            timestamp: lang === "vi" ? "Vừa xong" : "Just now",
          }],
        }));
        setActiveThreadId(newId);
        setActiveTab("mentor");
      }
    } catch (err) {
      console.error("Lỗi khi tạo cuộc trò chuyện mới trên DB:", err);
      const newId = `thread-local-${Date.now()}`;
      const timeString = new Date().toLocaleString(lang === "vi" ? "vi-VN" : "en-US", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric" });
      const newThread: ChatThread = {
        id: newId,
        title: t.mentorNewThreadTitle,
        dateGroup: timeString,
      };
      setThreads(prev => [newThread, ...prev]);
      setMessageHistory((prev) => ({
        ...prev,
        [newId]: [{
          id: `m-init-${Date.now()}`,
          role: "model",
          content: t.mentorNewThreadGreet,
          timestamp: lang === "vi" ? "Vừa xong" : "Just now",
        }],
      }));
      setActiveThreadId(newId);
      setActiveTab("mentor");
    }
  };

  const handleDeleteThread = async (threadId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const confirmMsg = lang === "vi"
      ? "Xóa cuộc trò chuyện này?"
      : "Delete this conversation?";
    if (!window.confirm(confirmMsg)) return;

    setThreads(threads.filter((t) => t.id !== threadId));
    const newHistory = { ...messageHistory };
    delete newHistory[threadId];
    setMessageHistory(newHistory);

    const isMongoId = /^[0-9a-fA-F]{24}$/.test(threadId);
    if (isMongoId) {
      try {
        const token = getAuthItem("minerai_token");
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        await fetch(`/api/conversations/${threadId}`, {
          method: "DELETE",
          headers
        });
      } catch (err) {
        console.error("Lỗi khi xóa cuộc trò chuyện trên DB:", err);
      }
    }

    if (activeThreadId === threadId) {
      if (threads.length > 1) {
        const nextActive = threads.find((t) => t.id !== threadId);
        setActiveThreadId(nextActive ? nextActive.id : "");
      } else {
        handleNewThread();
      }
    }
  };

  const handleRenameThread = async (threadId: string, newTitle: string) => {
    setThreads(prev => prev.map(th => th.id === threadId ? { ...th, title: newTitle } : th));

    const isMongoId = /^[0-9a-fA-F]{24}$/.test(threadId);
    if (isMongoId) {
      try {
        const token = getAuthItem("minerai_token");
        const headers: HeadersInit = { "Content-Type": "application/json" };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        await fetch(`/api/conversations/${threadId}/title`, {
          method: "PUT",
          headers,
          body: JSON.stringify({ title: newTitle })
        });
      } catch (err) {
        console.error("Lỗi khi đổi tên cuộc trò chuyện trên DB:", err);
      }
    }
  };

  const handleSelectThread = (id: string) => {
    setActiveThreadId(id);
    setActiveTab("mentor");
  };
  // -------------------------

  const handleLoadDatasetToLab = (fileName: string, fileSize: string, fileContent: string) => {
    const importedFile: DatasetFile = {
      name: fileName,
      size: fileSize,
      status: "Sẵn sàng",
      content: fileContent
    };
    setLabDataset(importedFile);
    setActiveTab("datalab");
    alert(lang === "vi"
      ? `Đã nạp thành công bộ dữ liệu "${fileName}" vào Phòng thí nghiệm!`
      : `Successfully loaded dataset "${fileName}" into the Data Lab!`);
  };

  const handlePlayLesson = (lessonName: string) => {
    setSelectedQuizTopic(lessonName);
    setCustomQuizTopic(null);
    setActiveTab("quiz");
  };

  const handleNewAnalysisTrigger = () => {
    handleNewThread();
  };

  const handleToggleLang = () => {
    setLang((prev) => (prev === "vi" ? "en" : "vi"));
  };

  const handleStartCustomQuiz = (topic: string) => {
    setCustomQuizTopic(topic);
    setActiveTab("quiz");
  };

  if (!isAuthenticated) {
    return (
      <AuthScreen 
        onLogin={(token, userData) => {
          // Token & user đã được lưu vào localStorage trong AuthScreen trước khi gọi onLogin
          // Reload để useState tái khởi tạo đúng với user key mới
          window.location.reload();
        }} 
      />
    );
  }

  return (
    <div className="h-screen w-full overflow-hidden bg-transparent text-slate-800 flex relative">
      {/* 1. Sidebar */}
      <Sidebar
        currentTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        onNewAnalysis={handleNewAnalysisTrigger}
        t={t}
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onDeleteThread={handleDeleteThread}
        onNewThread={handleNewThread}
        lang={lang}
        userRole={getUserRole()}
        onRenameThread={handleRenameThread}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        onLogout={() => {
          clearAuthSession();
          window.location.reload();
        }}
      />

      {/* 2. Content area */}
      <div className={`flex-1 min-w-0 h-screen flex flex-col transition-[padding] duration-300 ${isSidebarCollapsed ? "pl-20" : "pl-64"} ${activeTab === "mentor" ? "pr-80" : ""}`}>
        {/* Header */}
        <Header
          currentTab={activeTab}
          onTabChange={(tab) => setActiveTab(tab)}
          lang={lang}
          onToggleLang={handleToggleLang}
          t={t}
          onLogout={() => {
            clearAuthSession();
            window.location.reload();
          }}
        />

        {/* Main content switcher */}
        <main className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden bg-transparent relative z-10 flex flex-col [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-slate-200 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-300">
          {activeTab === "overview" && (
            <OverviewTab
              onNavigateToLibrary={() => setActiveTab("library")}
              onNavigateToMentor={() => setActiveTab("mentor")}
              onPlayLesson={handlePlayLesson}
              t={t}
            />
          )}

          {activeTab === "mentor" && (
            <MentorTab 
              t={t} 
              lang={lang} 
              threads={threads}
              setThreads={setThreads}
              activeThreadId={activeThreadId}
              messageHistory={messageHistory}
              setMessageHistory={setMessageHistory}
            />
          )}

          {activeTab === "quiz" && (
            <QuizTab 
              t={t} 
              lang={lang} 
              selectedTopic={selectedQuizTopic}
              customPracticeTopic={customQuizTopic}
              onClearSelectedTopic={() => setSelectedQuizTopic(null)}
              onClearCustomPractice={() => setCustomQuizTopic(null)}
            />
          )}

          {activeTab === "datalab" && (
            <DataLabTab 
              t={t} 
              lang={lang} 
              initialDataset={labDataset} 
              onClearInitialDataset={() => setLabDataset(null)} 
            />
          )}

          {activeTab === "library" && (
            <LibraryTab onLoadDatasetToLab={handleLoadDatasetToLab} t={t} />
          )}

          {activeTab === "summary_notes" && <SummaryNotesTab t={t} lang={lang} />}

          {activeTab === "settings" && <SettingsTab t={t} />}

          {activeTab === "help" && <HelpTab t={t} />}

          {activeTab === "admin" && getUserRole() === "admin" && <AdminTab t={t} lang={lang} />}

          {activeTab === "my_questions" && <MyQuestionsTab t={t} lang={lang} onStartCustomQuiz={handleStartCustomQuiz} />}
        </main>

        {/* Footer */}
        {activeTab !== "mentor" && (
          <footer className="py-2 border-t border-slate-200/80 text-center text-[10px] text-slate-500 font-semibold font-sans">
            <span>&copy; {new Date().getFullYear()} MinerAI — {t.footerText}</span>
          </footer>
        )}
      </div>
    </div>
  );
}
