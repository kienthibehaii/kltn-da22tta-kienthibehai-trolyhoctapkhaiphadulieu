export interface ChatMessage {
  id: string;
  role: "user" | "model";
  content: string;
  timestamp: string;
  citations?: any[];
}

export interface ChatThread {
  id: string;
  title: string;
  dateGroup: string;
}

export interface DatasetFile {
  name: string;
  size: string;
  status: "Sẵn sàng" | "Đang xử lý" | "Lỗi";
  content?: string;
}

export type MachineLearningAlgorithm = "Decision Tree" | "Apriori" | "K-Means" | "DBSCAN" | "Linear Regression";

export interface AnalysisResult {
  summary: string;
  features: string[];
  instances: number;
  metrics: { [key: string]: string | number };
  logs: string[];
  visualizationData: {
    type: "tree" | "scatter" | "bars" | "rules";
    chartData: any[];
  } | null;
}

export interface LibraryItem {
  id: string;
  type: "video" | "pdf" | "dataset";
  title: string;
  description: string;
  duration?: string;
  size?: string;
  rows?: string; // for datasets
  category: "all" | "video" | "pdf" | "dataset";
  linkText: "Bắt đầu" | "Tải xuống" | "Xem chi tiết";
  image?: string;
  filename?: string;
  is_public?: boolean;
}

export interface LearningProgess {
  percent: number;
  courseName: string;
  aiInsight: string;
  activityData: { day: string; hours: number }[];
}
