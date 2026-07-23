// i18n.ts - Bảng dịch ngôn ngữ Việt / Anh cho toàn bộ giao diện

export type Lang = "vi" | "en";

export const i18n = {
  vi: {
    // Sidebar
    appTagline: "Trợ lý Khai phá Dữ liệu",
    newAnalysis: "Trò chuyện mới",
    nav: {
      overview: "Tổng quan",
      mentor: "Gia sư AI",
      quiz: "Trắc nghiệm",
      datalab: "Phòng thí nghiệm",
      library: "Thư viện",
      settings: "Cài đặt",
      help: "Trợ giúp",
    },
    signOut: "Đăng xuất",

    // Header
    headerTabs: {
      overview: "Tổng quan",
      datalab: "Phòng Lab",
      library: "Thư viện",
    },
    langToggle: "EN",

    // Overview
    overviewTitle: "Tổng quan học tập",
    overviewSubtitle: "Chào mừng trở lại. Tiếp tục hành trình làm chủ Khai phá Dữ liệu.",
    progressLabel: "TIẾN ĐỘ",
    activityLabel: "HOẠT ĐỘNG HỌC TẬP",
    continueLearning: "Tiếp tục học →",
    aiInsightLabel: "Gợi ý từ AI",
    recentLessons: "Bài học gần đây",
    statsTitle: "Thông số Hệ thống RAG (Thời gian thực)",
    statDocs: "Tài liệu đã nạp",
    statVectors: "Vector lập chỉ mục",
    statMessages: "Lượt hỏi đáp",
    statSessions: "Phiên làm việc",
    statUnit: { docs: "tệp", vectors: "vector", messages: "câu hỏi", sessions: "phiên" },

    // Mentor
    mentorHistoryTitle: "Lịch sử trò chuyện",
    mentorNewThread: "Mới +",
    mentorGreeting: `Xin chào! Tôi là **Trợ lý MinerAI** - được xây dựng bằng RAG kết hợp Gemini, chuyên hỗ trợ môn **Khai phá Dữ liệu**.

Bạn có thể hỏi tôi về:
- Nội dung trong đề cương môn học (INT3210 / IT)
- Các thuật toán: K-means, Apriori, Decision Tree, DBSCAN...
- Câu hỏi ôn tập và kiểm tra trắc nghiệm
- Giải thích code Python với scikit-learn`,
    mentorPlaceholder: "Nhập câu hỏi về Khai phá Dữ liệu...",
    mentorLoading: "Trợ lý MinerAI đang tìm kiếm trong tài liệu...",
    mentorLoadingDetail: "Đang truy vấn 5984 vector từ cơ sở tri thức (RAG + Gemini)...",
    mentorWarning: "2026 MinerAI - Kiên Thị Bé Hai - 110122218 - DA22TTA - Hệ thống Trợ lý Học tập Khai phá Dữ liệu - Đồ án Tốt nghiệp 2026",
    mentorNewThreadGreet: "Cuộc trò chuyện mới. Hãy hỏi tôi về bất kỳ chủ đề nào trong môn Khai phá Dữ liệu.",
    mentorAILabel: "Trợ lý MinerAI",
    mentorUserLabel: "Bạn",
    mentorCopyCode: "Sao chép",
    mentorCopied: "Đã sao chép mã vào clipboard!",
    mentorNewThreadTitle: "Cuộc thảo luận mới",
    mentorInProgress: "Đang diễn ra",
    quickQuestions: [
      "K-means hoạt động như thế nào?",
      "Đề cương môn Khai phá dữ liệu gồm các chương nào?",
      "Cho tôi 5 câu hỏi trắc nghiệm về Apriori",
    ],

    // Library
    libraryTitle: "",
    librarySubtitle: "Toàn bộ tài liệu học tập môn Khai phá Dữ liệu đã được nạp vào hệ thống RAG.",

    // Data Lab
    datalabTitle: "Phòng thí nghiệm Dữ liệu",
    datalabSubtitle: "Không gian tương tác để phân tích dữ liệu và mô hình hóa học máy trực quan.",
    
    datalabStep1: "Tải lên bộ dữ liệu",
    datalabUploadHelp: "Kéo thả file CSV/JSON hoặc click để chọn",
    datalabMaxFile: "Tối đa 50MB",
    datalabStep2: "Chọn thuật toán",
    datalabRun: "Chạy phân tích",
    datalabRunning: "Đang chạy phân tích...",
    datalabVisualization: "Trực quan hóa kết quả",
    datalabNoResult: "Chưa có kết quả",
    datalabNoResultHelp: "Tải lên tệp dữ liệu hoạt động và chọn thuật toán phân lớp cụ thể, sau đó nhấn \"Chạy phân tích\" để theo dõi trực quan tại màn hình này.",
    datalabLoadingData: "Đang học bộ dữ liệu hành vi máy...",
    datalabExtracting: "Trích xuất báo cáo thông minh từ AI Engine",
    datalabAlertNoFile: "Vui lòng tải lên một tệp cơ sở dữ liệu (CSV/JSON) trước.",
    datalabPdfSuccess: "Bắt đầu tải báo cáo phân tích định dạng PDF!",
    datalabPdfError: "Hãy chạy phân tích trước khi tải báo cáo.",
    datalabReady: "Sẵn sàng",
    datalabFeatures: "cột",
    datalabInstances: "bản ghi",
    datalabPerformance: "Hiệu năng",
    datalabTargetGroup: "Nhóm VIP mua nhiều",
    datalabStimulate: "Cần kích cầu giảm giá",
    datalabClassA: "Lớp A",
    datalabClassB: "Lớp B",
    datalabSupportVector: "Vector hỗ trợ",

    // Settings
    settingsTitle: "Cài đặt Hệ thống",
    settingsSubtitle: "Quản lý tài khoản và theo dõi thông số môi trường hệ thống RAG.",
    profileSection: "HỒ SƠ SINH VIÊN",
    securitySection: "BẢO MẬT & TRÍ TUỆ NHÂN TẠO",
    systemSection: "THÔNG SỐ HỆ THỐNG",
    studentIdLabel: "Mã số Sinh viên",
    emailLabel: "Địa chỉ Email",

    // Help
    helpTitle: "Trung tâm Trợ giúp",
    helpSubtitle: "Giải đáp thắc mắc về hệ thống RAG, AI Mentor và tính năng hỏi đáp.",
    faqs: [
      {
        q: "MinerAI hỗ trợ những thuật toán khai phá dữ liệu nào?",
        a: "Hệ thống đã nạp đầy đủ 13 bài giảng (PPTX) bao gồm: Giới thiệu, Dữ liệu, Tiền xử lý, OLAP, FP-Growth, Apriori, Phân lớp (Decision Tree, Naive Bayes, SVM, Random Forest), Phân cụm (K-means, DBSCAN, Hierarchical), Phát hiện Outlier và Phân tích xu hướng. Bạn có thể hỏi bất kỳ nội dung nào trong các bài giảng đó.",
      },
      {
        q: "AI Mentor sử dụng công nghệ gì?",
        a: "AI Mentor được xây dựng theo kiến trúc RAG (Retrieval-Augmented Generation): khi bạn đặt câu hỏi, hệ thống tìm kiếm trong cơ sở tri thức gồm 5.984 đoạn văn bản từ slide, sách giáo khoa và đề cương, rồi kết hợp với mô hình Gemini của Google để tạo câu trả lời chính xác, có trích dẫn nguồn.",
      },
      {
        q: "Tôi có thể hỏi về đề cương môn học không?",
        a: "Hoàn toàn được! Hệ thống đã nạp 2 file đề cương (ngành CNTT và ngành AI). Bạn có thể hỏi về số tín chỉ, các chương, mục tiêu môn học, hoặc yêu cầu đầu ra. Ví dụ: 'Đề cương ngành CNTT gồm bao nhiêu chương?'",
      },
      {
        q: "Làm sao để ôn tập và kiểm tra trắc nghiệm?",
        a: "Hỏi AI Mentor trực tiếp: 'Cho tôi 5 câu hỏi trắc nghiệm về K-means' hoặc 'Câu hỏi ôn tập chương Phân cụm'. Hệ thống sẽ tự động tạo câu hỏi từ tài liệu thực tế có trong cơ sở tri thức.",
      },
    ],

    // Footer
    footerText: "Kiên Thị Bé Hai - 110122218 - DA22TTA - Hệ thống Trợ lý Học tập Khai phá Dữ liệu - Đồ án Tốt nghiệp 2026",
  },

  en: {
    appTagline: "Data Mining AI Assistant",
    newAnalysis: "New chat ",
    nav: {
      overview: "Overview",
      mentor: "AI Mentor",
      quiz: "Quiz Context",
      datalab: "Data Lab",
      library: "Library",
      settings: "Settings",
      help: "Help",
    },
    signOut: "Sign Out",

    headerTabs: {
      overview: "Dashboard",
      datalab: "Lab",
      library: "Library",
    },
    langToggle: "VI",

    overviewTitle: "Learning Overview",
    overviewSubtitle: "Welcome back. Continue your Data Mining mastery journey.",
    progressLabel: "PROGRESS",
    activityLabel: "LEARNING ACTIVITY",
    continueLearning: "Continue Learning →",
    aiInsightLabel: "AI Insight",
    recentLessons: "Recent Lessons",
    statsTitle: "RAG System Stats (Real-time)",
    statDocs: "Loaded Documents",
    statVectors: "Indexed Vectors",
    statMessages: "Q&A Sessions",
    statSessions: "Active Sessions",
    statUnit: { docs: "files", vectors: "vectors", messages: "queries", sessions: "sessions" },

    mentorHistoryTitle: "Chat History",
    mentorNewThread: "New +",
    mentorGreeting: `Hello! I'm **MinerAI Assistant** - built with RAG + Gemini, specialized in **Data Mining**.

You can ask me about:
- Course curriculum content (INT3210 / IT)
- Algorithms: K-means, Apriori, Decision Tree, DBSCAN...
- Practice quizzes and multiple-choice questions
- Python code examples with scikit-learn`,
    mentorPlaceholder: "Ask a Data Mining question...",
    mentorLoading: "MinerAI is searching the knowledge base...",
    mentorLoadingDetail: "Querying 5,984 vectors from the RAG knowledge base (Gemini)...",
    mentorWarning: "MinerAI may make mistakes. Please verify important information.",
    mentorNewThreadGreet: "New conversation started. Ask me anything about Data Mining.",
    mentorAILabel: "MinerAI Assistant",
    mentorUserLabel: "You",
    mentorCopyCode: "Copy",
    mentorCopied: "Code copied to clipboard!",
    mentorNewThreadTitle: "New conversation",
    mentorInProgress: "Active",
    quickQuestions: [
      "How does K-means work?",
      "What chapters are in the Data Mining curriculum?",
      "Give me 5 multiple-choice questions about Apriori",
    ],

    libraryTitle: "Document Library",
    librarySubtitle: "All Data Mining study materials loaded into the RAG knowledge base.",

    // Data Lab
    datalabTitle: "Data Science Lab",
    datalabSubtitle: "Interactive workspace for data analysis and visual machine learning modeling.",
    datalabStep1: "Upload Dataset",
    datalabUploadHelp: "Drag & drop CSV/JSON files or click to select",
    datalabMaxFile: "Max 50MB",
    datalabStep2: "Select Algorithm",
    datalabRun: "Run Analysis",
    datalabRunning: "Running analysis...",
    datalabVisualization: "Result Visualization",
    datalabNoResult: "No results yet",
    datalabNoResultHelp: "Upload a dataset, choose a specific classification algorithm, and click 'Run Analysis' to see results here.",
    datalabLoadingData: "Learning dataset patterns...",
    datalabExtracting: "Extracting intelligent report from AI Engine...",
    datalabAlertNoFile: "Please upload a CSV/JSON database file first.",
    datalabPdfSuccess: "Starting PDF analytical report download!",
    datalabPdfError: "Please run analysis before downloading the report.",
    datalabReady: "Ready",
    datalabFeatures: "columns",
    datalabInstances: "rows",
    datalabPerformance: "Performance",
    datalabTargetGroup: "VIP Target Group",
    datalabStimulate: "Discount Target Group",
    datalabClassA: "Class A",
    datalabClassB: "Class B",
    datalabSupportVector: "Support Vector",

    libraryTitle_unused: "Document Library", // prevent conflict
    librarySubtitle_unused: "All Data Mining study materials loaded into the RAG knowledge base.",

    settingsTitle: "System Settings",
    settingsSubtitle: "Manage your student account and monitor RAG system environment.",
    profileSection: "STUDENT PROFILE",
    securitySection: "SECURITY & AI",
    systemSection: "SYSTEM INFO",
    studentIdLabel: "Student ID",
    emailLabel: "Email Address",

    helpTitle: "Help Center",
    helpSubtitle: "Answers to questions about the RAG system, AI Mentor, and Q&A features.",
    faqs: [
      {
        q: "Which Data Mining algorithms does MinerAI support?",
        a: "The system has loaded 13 lecture slides covering: Introduction, Data, Preprocessing, OLAP, FP-Growth, Apriori, Classification (Decision Tree, Naive Bayes, SVM, Random Forest), Clustering (K-means, DBSCAN, Hierarchical), Outlier Detection, and Trend Analysis.",
      },
      {
        q: "What technology powers the AI Mentor?",
        a: "The AI Mentor uses RAG (Retrieval-Augmented Generation): when you ask a question, the system searches 5,984 text chunks from slides, textbooks and curriculum, then combines with Google's Gemini model to generate accurate, cited answers.",
      },
      {
        q: "Can I ask about the course curriculum?",
        a: "Absolutely! The system has loaded 2 curriculum files (IT and AI majors). Ask about credit hours, chapters, learning outcomes, or requirements. Example: 'How many chapters in the IT Data Mining curriculum?'",
      },
      {
        q: "How do I practice with quizzes?",
        a: "Ask the AI Mentor directly: 'Give me 5 multiple-choice questions about K-means' or 'Practice questions for the Clustering chapter'. The system generates questions from actual materials in the knowledge base.",
      },
    ],

    footerText: "Data Mining Learning Assistant System - Graduation Thesis 2026",
  },
} as const;

export type I18nKey = typeof i18n.vi;
