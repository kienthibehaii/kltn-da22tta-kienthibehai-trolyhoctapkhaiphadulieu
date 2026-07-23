import { LibraryItem, ChatThread, LearningProgess } from "./types";

export const defaultLibraryItems: LibraryItem[] = [
  {
    id: "lib-1",
    type: "video",
    title: "Nhập môn Data Mining với Python",
    description: "Hướng dẫn cơ bản về các thuật toán khai phá dữ liệu đỉnh cao, tiền xử lý và trực quan hóa dữ liệu sử dụng thư viện Pandas và Scikit-Learn.",
    duration: "45 phút",
    category: "video",
    linkText: "Bắt đầu",
    image: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=400&q=80"
  },
  {
    id: "lib-2",
    type: "pdf",
    title: "Sổ tay Thuật toán Phân cụm (Clustering Manual)",
    description: "Tài liệu tổng hợp toán học, lý thuyết trực quan hóa và ví dụ thực tế về các thuật toán phân cụm cốt lõi như K-Means, DBSCAN và Hierarchical Clustering.",
    size: "2.4 MB",
    category: "pdf",
    linkText: "Tải xuống",
    image: "https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=400&q=80"
  },
  {
    id: "lib-3",
    type: "dataset",
    title: "Dữ liệu Hành vi Khách hàng E-commerce",
    description: "Tập dữ liệu sạch 100% bao gồm thông tin chi dùng, sản phẩm bán chạy nhất, độ tuổi và thói quen mua sắm, thích hợp cho mô hình hóa phân khúc Apriori và SVM.",
    rows: "150K dòng",
    category: "dataset",
    linkText: "Xem chi tiết",
    image: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=400&q=80"
  },
  {
    id: "lib-4",
    type: "video",
    title: "Kỹ thuật Tiền xử lý Dữ liệu (Data Preprocessing)",
    description: "Xử lý triệt để các nan values (missing values), chuẩn hóa thang đo chuẩn z-score, phát hiện và khử trị số ngoại lai lập dị (outliers) hiệu quả.",
    duration: "1h 20m",
    category: "video",
    linkText: "Bắt đầu",
    image: "https://images.unsplash.com/photo-1504868584819-f8e8b4b6d7e3?auto=format&fit=crop&w=400&q=80"
  }
];

export const defaultChatHistory: ChatThread[] = [
  {
    id: "thread-1",
    title: "Phân cụm K-means & Ứng dụng",
    dateGroup: "Hôm qua"
  },
  {
    id: "thread-2",
    title: "Xử lý dữ liệu thiếu trong Pandas",
    dateGroup: "Thứ Ba"
  },
  {
    id: "thread-3",
    title: "Trực quan hóa với PCA",
    dateGroup: "Tuần trước"
  }
];

export const defaultProgress: LearningProgess = {
  percent: 68,
  courseName: "Khóa học Khai phá Dữ liệu Cơ bản",
  aiInsight: "Bạn đang làm rất tốt với các thuật toán phân loại. Hãy xem lại phần Random Forest để củng cố kiến thức trước bài kiểm tra sắp tới.",
  activityData: [
    { day: "T2", hours: 1.5 },
    { day: "T3", hours: 2.8 },
    { day: "T4", hours: 4.5 },
    { day: "T5", hours: 2.0 },
    { day: "T6", hours: 3.5 },
    { day: "T7", hours: 5.2 },
    { day: "CN", hours: 1.0 }
  ]
};
