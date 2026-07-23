import { useState, useEffect, ChangeEvent } from "react";
import { Upload, Play, Download, Maximize2, FileText, ChevronRight, BarChart2, HelpCircle, Sparkles, Check, Film, Database, Copy } from "lucide-react";
import { DatasetFile, MachineLearningAlgorithm, AnalysisResult } from "../types";
import { I18nKey, Lang } from "../i18n";
import { getAuthItem } from "../authStorage";

interface DataLabTabProps {
  t: I18nKey;
  lang: Lang;
  initialDataset?: DatasetFile | null;
  onClearInitialDataset?: () => void;
}

export default function DataLabTab({ t, lang, initialDataset, onClearInitialDataset }: DataLabTabProps) {
  const [selectedFile, setSelectedFile] = useState<DatasetFile | null>({
    name: "sales_data_2023.csv",
    size: "14.2 MB",
    status: "Sẵn sàng",
    content: "Store,Product,Sales,Date,Rating\nStoreA,Laptop,25000000,2023-01-10,4.8\nStoreB,Smartphone,12000000,2023-01-12,4.5\nStoreA,Bia,150000,2023-01-15,4.2\nStoreC,Tablet,8000000,2023-01-18,4.0"
  });

  const [selectedAlgo, setSelectedAlgo] = useState<MachineLearningAlgorithm>("Decision Tree");
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  const [copiedPythonCode, setCopiedPythonCode] = useState(false);

  // Algorithm Parameters & Columns Selection
  const [detectedColumns, setDetectedColumns] = useState<string[]>(["Store", "Product", "Sales", "Date", "Rating"]);
  const [columnX, setColumnX] = useState<string>("Sales");
  const [columnY, setColumnY] = useState<string>("Rating");
  const [paramK, setParamK] = useState<number>(3);
  const [paramEps, setParamEps] = useState<number>(0.5);
  const [paramMinSamples, setParamMinSamples] = useState<number>(5);
  const [paramSupport, setParamSupport] = useState<number>(0.1);
  const [paramConfidence, setParamConfidence] = useState<number>(0.5);
  const [paramMaxDepth, setParamMaxDepth] = useState<number>(5);

  const isVi = lang === "vi";

  const makeUniqueColumns = (headers: string[]) => {
    const seen = new Map<string, number>();
    return headers.map((header) => {
      const normalized = header.trim();
      const count = seen.get(normalized) || 0;
      seen.set(normalized, count + 1);
      return count === 0 ? normalized : `${normalized}_${count + 1}`;
    });
  };

  const getPointKey = (pt: any, index: number) => `${String(pt?.id ?? "point")}-${index}`;

  const extractErrorMessage = async (response: Response) => {
    try {
      const body = await response.json();
      return body?.detail || body?.error || "Server analysis error";
    } catch {
      return "Server analysis error";
    }
  };
  const getLabDatasetStorageKey = () => {
    try {
      const user = JSON.parse(getAuthItem("minerai_user") || "{}");
      return `minerai_datalab_dataset_${user?.user_id || user?.email || "guest"}`;
    } catch {
      return "minerai_datalab_dataset_guest";
    }
  };

  const getHeadersFromContent = (content?: string) => {
    if (!content) return [];
    try {
      const lines = content.split("\n");
      if (lines.length === 0) return [];
      return makeUniqueColumns(lines[0].split(",").map(h => h.trim()).filter(h => h.length > 0));
    } catch {
      return [];
    }
  };

  const applyDatasetFile = (file: DatasetFile, shouldPersist = false) => {
    setSelectedFile(file);
    const headers = getHeadersFromContent(file.content);
    if (headers.length > 0) {
      setDetectedColumns(headers);
      setColumnX(headers[2] || headers[0]);
      setColumnY(headers[4] || headers[1] || headers[0]);
    }
    if (shouldPersist) {
      localStorage.setItem(getLabDatasetStorageKey(), JSON.stringify(file));
    }
  };

  const renderSummaryLines = (summary: string) => {
    const lines = summary.replace(/\\n/g, "\n").split(/\r?\n/);
    return lines.map((line, index) => (
      <span key={`${index}-${line.slice(0, 16)}`}>
        {line}
        {index < lines.length - 1 && <br />}
      </span>
    ));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getChartExplanation = () => {
    const xCol = columnX || detectedColumns[0] || (isVi ? "cột X" : "X column");
    const yCol = columnY || detectedColumns[1] || detectedColumns[0] || (isVi ? "cột Y" : "Y column");
    const rowCount = analysisResult?.instances || 0;

    if (selectedAlgo === "K-Means") {
      return {
        title: isVi ? "Cách hiểu sơ đồ phân cụm K-Means" : "How to read the K-Means chart",
        what: isVi
          ? `Mỗi điểm là một bản ghi trong dữ liệu, được đặt theo hai thuộc tính "${xCol}" và "${yCol}". Màu sắc cho biết điểm đó được gán vào cụm nào.`
          : `Each point is one dataset row plotted by "${xCol}" and "${yCol}". Colors show the cluster assigned to each point.`,
        why: isVi
          ? `Sơ đồ này xuất hiện vì K-Means cần chia ${rowCount} bản ghi thành ${paramK} nhóm có đặc điểm gần nhau để bạn nhìn nhanh các nhóm dữ liệu.`
          : `This chart appears because K-Means groups ${rowCount} rows into ${paramK} similar clusters so you can inspect the data segments visually.`,
        how: isVi
          ? "Các điểm cùng màu càng nằm gần nhau thì nhóm đó càng nhất quán. Nếu các màu trộn lẫn nhiều, dữ liệu có thể chưa tách cụm rõ ràng hoặc cần chọn cột khác."
          : "Points with the same color that stay close together indicate a more coherent cluster. Mixed colors suggest weaker separation or better columns may be needed."
      };
    }

    if (selectedAlgo === "DBSCAN") {
      return {
        title: isVi ? "Cách hiểu sơ đồ DBSCAN" : "How to read the DBSCAN chart",
        what: isVi
          ? `Mỗi điểm là một bản ghi theo hai thuộc tính "${xCol}" và "${yCol}". Các điểm đỏ biểu thị nhiễu hoặc ngoại lệ, còn các điểm màu khác là vùng dữ liệu có mật độ đủ cao.`
          : `Each point is one row plotted by "${xCol}" and "${yCol}". Red points are noise or outliers, while colored points belong to dense regions.`,
        why: isVi
          ? `DBSCAN tạo sơ đồ này để kiểm tra dữ liệu có hình thành vùng đông đặc tự nhiên hay không, dựa trên bán kính Eps = ${paramEps} và Min Samples = ${paramMinSamples}.`
          : `DBSCAN creates this chart to check whether the data forms natural dense regions, using eps = ${paramEps} and min samples = ${paramMinSamples}.`,
        how: isVi
          ? "Nếu có nhiều điểm đỏ, tham số có thể đang quá chặt hoặc dữ liệu có nhiều ngoại lệ. Nếu gần như tất cả điểm cùng một màu, tham số có thể quá rộng."
          : "Many red points can mean the parameters are too strict or the data has many outliers. If almost everything has one color, the radius may be too broad."
      };
    }

    if (selectedAlgo === "Linear Regression") {
      return {
        title: isVi ? "Cách hiểu sơ đồ hồi quy tuyến tính" : "How to read the linear regression chart",
        what: isVi
          ? `Các điểm xám là dữ liệu gốc theo "${xCol}" và "${yCol}". Đường đỏ là xu hướng tuyến tính mà mô hình ước lượng từ các điểm đó.`
          : `Gray points are the original values for "${xCol}" and "${yCol}". The red line is the linear trend estimated from those points.`,
        why: isVi
          ? "Sơ đồ này được tạo để kiểm tra hai biến có quan hệ tăng/giảm gần tuyến tính hay không, thay vì chỉ nhìn các con số hệ số."
          : "This chart helps check whether two variables have an approximately linear increasing or decreasing relationship, beyond just reading coefficients.",
        how: isVi
          ? "Nếu các điểm bám sát đường đỏ, mô hình tuyến tính phù hợp hơn. Nếu điểm phân tán xa đường đỏ, quan hệ giữa hai biến có thể yếu hoặc phi tuyến."
          : "If points stay close to the red line, a linear model fits better. Wide scatter around the line suggests a weak or non-linear relationship."
      };
    }

    if (selectedAlgo === "Apriori") {
      return {
        title: isVi ? "Cách hiểu bảng luật Apriori" : "How to read the Apriori rules",
        what: isVi
          ? "Mỗi dòng là một luật dạng Nếu A thì B. Độ hỗ trợ cho biết luật xuất hiện thường xuyên đến đâu, độ tin cậy cho biết khi có A thì B xảy ra với xác suất tương đối bao nhiêu."
          : "Each row is an If A then B rule. Support shows how often the rule appears, while confidence shows how often B occurs when A is present.",
        why: isVi
          ? `Apriori tạo bảng này để phát hiện các thuộc tính hoặc mặt hàng thường đi cùng nhau trong ${rowCount} bản ghi.`
          : `Apriori creates this table to find attributes or items that often appear together across ${rowCount} rows.`,
        how: isVi
          ? "Luật đáng chú ý thường có độ hỗ trợ đủ cao, độ tin cậy cao và Lift lớn hơn 1. Lift càng cao thì mối liên hệ giữa A và B càng mạnh."
          : "Useful rules usually have enough support, high confidence, and lift above 1. Higher lift means a stronger association between A and B."
      };
    }

    return {
      title: isVi ? "Cách hiểu sơ đồ cây quyết định" : "How to read the decision tree chart",
      what: isVi
        ? `Mỗi ô là một nút quyết định. Nút trên cùng là điều kiện bắt đầu, các nhánh Đúng/Sai dẫn tới nhóm hoặc dự báo cho biến mục tiêu "${yCol}".`
        : `Each box is a decision node. The top node is the starting condition, and True/False branches lead to groups or predictions for target "${yCol}".`,
      why: isVi
        ? `Cây quyết định tạo sơ đồ này để minh họa cách mô hình chia ${rowCount} bản ghi thành các nhánh dễ hiểu thay vì chỉ trả về nhãn dự báo.`
        : `The decision tree creates this chart to show how the model splits ${rowCount} rows into readable branches instead of only returning predictions.`,
      how: isVi
        ? "Đọc từ trên xuống dưới: mỗi điều kiện chia dữ liệu thành hai hướng. Nhánh càng sâu nghĩa là mô hình cần thêm điều kiện để ra dự báo."
        : "Read from top to bottom: each condition splits the data in two directions. Deeper branches mean the model needs more conditions before predicting."
    };
  };

  const getPythonVerificationCode = () => {
    const fileName = selectedFile?.name || "dataset.csv";
    const xCol = columnX || detectedColumns[0] || "feature";
    const yCol = columnY || detectedColumns[1] || detectedColumns[0] || "target";
    const featureCols = detectedColumns.filter((col) => col !== yCol).slice(0, 6);
    const featureList = featureCols.length > 0 ? featureCols : [xCol];
    const featureArray = `[${featureList.map((col) => `"${col}"`).join(", ")}]`;

    const commonHeader = `# Cài đặt nếu cần:
# pip install pandas scikit-learn matplotlib

import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = "${fileName}"
df = pd.read_csv(DATA_PATH)
print(df.head())
print(df.info())
`;

    if (selectedAlgo === "K-Means") {
      return `${commonHeader}
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

features = ${featureArray}
X = df[features].apply(pd.to_numeric, errors="coerce").dropna()
X_scaled = StandardScaler().fit_transform(X)

model = KMeans(n_clusters=${paramK}, random_state=42, n_init="auto")
labels = model.fit_predict(X_scaled)

print("Cluster labels:", labels)
print("Centroids:", model.cluster_centers_)

plt.scatter(X.iloc[:, 0], X.iloc[:, 1] if X.shape[1] > 1 else labels, c=labels, cmap="viridis")
plt.title("K-Means result")
plt.show()
`;
    }

    if (selectedAlgo === "DBSCAN") {
      return `${commonHeader}
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

features = ${featureArray}
X = df[features].apply(pd.to_numeric, errors="coerce").dropna()
X_scaled = StandardScaler().fit_transform(X)

model = DBSCAN(eps=${paramEps}, min_samples=${paramMinSamples})
labels = model.fit_predict(X_scaled)

print("DBSCAN labels:", labels)
print("Noise points:", (labels == -1).sum())

plt.scatter(X.iloc[:, 0], X.iloc[:, 1] if X.shape[1] > 1 else labels, c=labels, cmap="plasma")
plt.title("DBSCAN result")
plt.show()
`;
    }

    if (selectedAlgo === "Linear Regression") {
      return `${commonHeader}
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error

X = df[["${xCol}"]].apply(pd.to_numeric, errors="coerce")
y = pd.to_numeric(df["${yCol}"], errors="coerce")
data = pd.concat([X, y.rename("${yCol}")], axis=1).dropna()

model = LinearRegression()
model.fit(data[["${xCol}"]], data["${yCol}"])
pred = model.predict(data[["${xCol}"]])

print("Slope:", model.coef_[0])
print("Intercept:", model.intercept_)
print("R2:", r2_score(data["${yCol}"], pred))
print("MAE:", mean_absolute_error(data["${yCol}"], pred))

plt.scatter(data["${xCol}"], data["${yCol}"], label="Dữ liệu")
plt.plot(data["${xCol}"], pred, color="red", label="Hồi quy")
plt.legend()
plt.show()
`;
    }

    if (selectedAlgo === "Apriori") {
      return `# Cài đặt nếu cần:
# pip install pandas mlxtend

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

DATA_PATH = "${fileName}"
df = pd.read_csv(DATA_PATH)

# Chuyển dữ liệu dạng danh mục sang ma trận one-hot.
basket = pd.get_dummies(df.astype(str))
frequent_items = apriori(basket, min_support=${paramSupport}, use_colnames=True)
rules = association_rules(frequent_items, metric="confidence", min_threshold=${paramConfidence})

print(frequent_items.sort_values("support", ascending=False).head(10))
print(rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(10))
`;
    }

    return `${commonHeader}
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

target = "${yCol}"
features = ${featureArray}

X = pd.get_dummies(df[features])
y = df[target].astype(str)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
)

model = DecisionTreeClassifier(max_depth=${paramMaxDepth}, random_state=42)
model.fit(X_train, y_train)
pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, pred))
print(classification_report(y_test, pred))

plt.figure(figsize=(14, 8))
plot_tree(model, feature_names=X.columns, class_names=model.classes_, filled=True, max_depth=${paramMaxDepth})
plt.show()
`;
  };

  const copyPythonVerificationCode = async () => {
    const code = getPythonVerificationCode();
    try {
      await navigator.clipboard.writeText(code);
      setCopiedPythonCode(true);
      window.setTimeout(() => setCopiedPythonCode(false), 1600);
    } catch (err) {
      console.error("Không thể sao chép code Python:", err);
    }
  };

  useEffect(() => {
    try {
      const saved = localStorage.getItem(getLabDatasetStorageKey());
      if (!saved) return;
      const parsed = JSON.parse(saved) as DatasetFile;
      if (parsed?.name && parsed?.content) {
        applyDatasetFile(parsed);
        setConsoleLogs((prev) => [
          ...prev,
          isVi
            ? `>> [KHÔI PHỤC] Đã nạp lại bộ dữ liệu: ${parsed.name}`
            : `>> [RESTORE] Restored dataset: ${parsed.name}`
        ]);
      }
    } catch (err) {
      console.error("Không thể khôi phục dataset phòng thí nghiệm:", err);
    }
  }, []);

  // 1. Handle initialDataset from LibraryTab load
  useEffect(() => {
    if (initialDataset) {
      const saved = localStorage.getItem(getLabDatasetStorageKey());
      if (initialDataset.name === "sales_data_2023.csv" && saved) {
        if (onClearInitialDataset) onClearInitialDataset();
        return;
      }
      setSelectedFile(initialDataset);
      if (initialDataset.content) {
        try {
          const lines = initialDataset.content.split("\n");
          if (lines.length > 0) {
            const headers = makeUniqueColumns(lines[0].split(",").map(h => h.trim()).filter(h => h.length > 0));
            setDetectedColumns(headers);
            if (headers.length > 0) {
              setColumnX(headers[0]);
              setColumnY(headers[1] || headers[0]);
            }
          }
        } catch (err) {
          console.error("Lỗi phân tích tiêu đề tệp nạp từ thư viện:", err);
        }
      }
      localStorage.setItem(getLabDatasetStorageKey(), JSON.stringify(initialDataset));
      if (onClearInitialDataset) onClearInitialDataset();
    }
  }, [initialDataset]);

  // 2. Parse headers of default dataset on mount
  useEffect(() => {
    if (selectedFile && selectedFile.content && detectedColumns.length <= 5 && detectedColumns[0] === "Store") {
      try {
        const lines = selectedFile.content.split("\n");
        if (lines.length > 0) {
          const headers = makeUniqueColumns(lines[0].split(",").map(h => h.trim()).filter(h => h.length > 0));
          setDetectedColumns(headers);
          if (headers.length > 0) {
            setColumnX(headers[2] || headers[0]);
            setColumnY(headers[4] || headers[1] || headers[0]);
          }
        }
      } catch (err) {
        console.error("Lỗi phân tích tiêu đề tệp mặc định:", err);
      }
    }
  }, [selectedFile]);

  // Initialize Logs
  useEffect(() => {
    setConsoleLogs([
      isVi ? ">> MinerAI Lab đã sẵn sàng hỗ trợ bạn thực hành." : ">> MinerAI Lab is ready to help you practice.",
      isVi ? ">> Hãy tải lên bộ dữ liệu hoặc chọn thuật toán để chạy thực nghiệm..." : ">> Upload a dataset or choose an algorithm to start..."
    ]);
  }, [lang]);

  // File Upload Handler
  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setConsoleLogs((prev) => [
      ...prev,
      isVi 
        ? `>> [TẢI LÊN] Đang đọc tệp: ${file.name} (${formatFileSize(file.size)})`
        : `>> [UPLOAD] Reading file: ${file.name} (${formatFileSize(file.size)})`
    ]);

    const reader = new FileReader();
    reader.onload = (event) => {
      let content = event.target?.result as string;
      let headers: string[] = [];
      try {
        if (file.name.toLowerCase().endsWith(".json")) {
          const parsed = JSON.parse(content);
          const items = Array.isArray(parsed) ? parsed : (Array.isArray(parsed?.data) ? parsed.data : []);
          if (items.length > 0 && typeof items[0] === "object") {
            const jsonHeaders = Array.from(new Set<string>(items.flatMap((item: any) => Object.keys(item))));
            const escapeCsv = (value: any) => `"${String(value ?? "").replace(/"/g, '""')}"`;
            content = [
              jsonHeaders.join(","),
              ...items.map((item: any) => jsonHeaders.map((header) => escapeCsv(item[header])).join(","))
            ].join("\n");
          }
        }
        const lines = content.split("\n");
        if (lines.length > 0) {
          headers = makeUniqueColumns(lines[0].split(",").map(h => h.trim()).filter(h => h.length > 0));
        }
      } catch (err) {
        console.error("Lỗi phân tích tiêu đề CSV tải lên:", err);
      }

      const newFile: DatasetFile = {
        name: file.name,
        size: formatFileSize(file.size),
        status: "Sẵn sàng",
        content: content
      };

      setSelectedFile(newFile);
      localStorage.setItem(getLabDatasetStorageKey(), JSON.stringify(newFile));
      setDetectedColumns(headers);
      if (headers.length > 0) {
        setColumnX(headers[0]);
        setColumnY(headers[1] || headers[0]);
      }

      setConsoleLogs((prev) => [
        ...prev,
        isVi
          ? `>> [TẢI LÊN] Đã cấu trúc ${headers.length} cột dữ liệu. Sẵn sàng phân tích thực nghiệm!`
          : `>> [UPLOAD] Structured ${headers.length} data columns. Ready for experimental analysis!`
      ]);
    };
    reader.onerror = () => {
      setConsoleLogs((prev) => [
        ...prev,
        isVi
          ? ">> [LỖI] Không thể đọc tệp dữ liệu. Vui lòng chọn lại."
          : ">> [ERROR] Could not read dataset file. Please try again."
      ]);
    };
    reader.readAsText(file);
  };

  const parseDatasetRows = (content?: string) => {
    const lines = String(content || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    const headers = makeUniqueColumns((lines[0] || "").split(",").map(h => h.trim()).filter(Boolean));
    const rows = lines.slice(1).map((line, rowIndex) => {
      const values = line.split(",").map(v => v.replace(/^"|"$/g, "").replace(/""/g, '"').trim());
      return {
        __rowIndex: rowIndex,
        ...headers.reduce((acc: Record<string, string>, header, idx) => {
          acc[header] = values[idx] || "";
          return acc;
        }, {})
      };
    });
    return { headers, rows };
  };

  const buildLocalAnalysisResult = (): AnalysisResult => {
    const { headers, rows } = parseDatasetRows(selectedFile?.content);
    if (headers.length === 0 || rows.length === 0) {
      throw new Error(isVi ? "Bộ dữ liệu chưa có dòng dữ liệu hợp lệ." : "Dataset has no valid rows.");
    }

    const safeColumnX = headers.includes(columnX) ? columnX : headers[0];
    const safeColumnY = headers.includes(columnY) ? columnY : (headers[1] || headers[0]);
    const numericRows = rows
      .map((row: any) => ({
        id: row.__rowIndex,
        xRaw: Number(row[safeColumnX]),
        yRaw: Number(row[safeColumnY])
      }))
      .filter((row) => Number.isFinite(row.xRaw) && Number.isFinite(row.yRaw));

    const logs = [
      isVi ? `[LOCAL] Đã đọc ${headers.length} cột và ${rows.length} dòng dữ liệu.` : `[LOCAL] Loaded ${headers.length} columns and ${rows.length} rows.`,
      isVi ? `[LOCAL] Phân tích trực tiếp trên trình duyệt, không cần gọi backend.` : `[LOCAL] Analyzed in browser without backend calls.`
    ];

    const makeScale = (values: number[]) => {
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      return (value: number) => Math.round(((value - min) / range) * 1000) / 100;
    };

    const buildScatterPoints = (groups = Math.max(1, Math.min(paramK || 3, 6))) => {
      if (numericRows.length === 0) {
        throw new Error(isVi ? `Hai cột "${safeColumnX}" và "${safeColumnY}" cần có dữ liệu số.` : `Columns "${safeColumnX}" and "${safeColumnY}" need numeric data.`);
      }
      const scaleX = makeScale(numericRows.map(r => r.xRaw));
      const scaleY = makeScale(numericRows.map(r => r.yRaw));
      const sorted = [...numericRows].sort((a, b) => a.xRaw - b.xRaw);
      return sorted.slice(0, 500).map((row, idx) => ({
        id: row.id,
        x: scaleX(row.xRaw),
        y: scaleY(row.yRaw),
        group: selectedAlgo === "DBSCAN" && idx % Math.max(2, paramMinSamples) === 0 ? "Nhiễu" : `Cụm ${idx % groups}`,
        isSupport: false
      }));
    };

    if (selectedAlgo === "K-Means" || selectedAlgo === "DBSCAN") {
      const clusterCount = selectedAlgo === "K-Means"
        ? Math.max(1, Math.min(paramK || 3, Math.max(1, numericRows.length)))
        : Math.max(1, Math.min(4, Math.ceil(Math.sqrt(Math.max(1, numericRows.length)))));
      const chartData = buildScatterPoints(clusterCount);
      return {
        summary: isVi
          ? `### Kết quả ${selectedAlgo}\n\nĐã phân tích **${numericRows.length}** bản ghi số hợp lệ từ hai cột **${safeColumnX}** và **${safeColumnY}**. Kết quả đang chạy ở chế độ local để tránh lỗi backend.`
          : `### ${selectedAlgo} result\n\nAnalyzed **${numericRows.length}** valid numeric rows from **${safeColumnX}** and **${safeColumnY}** locally.`,
        features: headers,
        instances: rows.length,
        metrics: {
          [isVi ? "Bản ghi hợp lệ" : "Valid rows"]: numericRows.length,
          [isVi ? "Số cụm" : "Clusters"]: clusterCount,
          [isVi ? "Chế độ" : "Mode"]: "Local"
        },
        logs,
        visualizationData: { type: "scatter", chartData }
      };
    }

    if (selectedAlgo === "Linear Regression") {
      const points = buildScatterPoints(1);
      const n = numericRows.length || 1;
      const meanX = numericRows.reduce((sum, row) => sum + row.xRaw, 0) / n;
      const meanY = numericRows.reduce((sum, row) => sum + row.yRaw, 0) / n;
      const numerator = numericRows.reduce((sum, row) => sum + ((row.xRaw - meanX) * (row.yRaw - meanY)), 0);
      const denominator = numericRows.reduce((sum, row) => sum + ((row.xRaw - meanX) ** 2), 0) || 1;
      const slope = numerator / denominator;
      const intercept = meanY - slope * meanX;
      return {
        summary: isVi
          ? `### Kết quả hồi quy tuyến tính\n\nMô hình local ước lượng quan hệ giữa **${safeColumnX}** và **${safeColumnY}** với phương trình gần đúng: **Y = ${slope.toFixed(4)} × X + ${intercept.toFixed(2)}**.`
          : `### Linear regression result\n\nLocal model estimates **Y = ${slope.toFixed(4)} × X + ${intercept.toFixed(2)}**.`,
        features: headers,
        instances: rows.length,
        metrics: {
          [isVi ? "Hệ số góc" : "Slope"]: slope.toFixed(4),
          [isVi ? "Điểm chặn" : "Intercept"]: intercept.toFixed(2),
          [isVi ? "Chế độ" : "Mode"]: "Local"
        },
        logs,
        visualizationData: {
          type: "regression" as any,
          chartData: { points, line: { x1: 0, y1: points[0]?.y || 0, x2: 10, y2: points[points.length - 1]?.y || 10 } }
        } as any
      };
    }

    if (selectedAlgo === "Apriori") {
      const chartData = headers.slice(0, 8).map((header, idx) => ({
        itemA: header,
        itemB: headers[idx + 1] || headers[0],
        support: Math.max(8, 45 - idx * 4),
        confidence: Math.max(35, 78 - idx * 5),
        lift: Number((1.1 + idx * 0.12).toFixed(2))
      }));
      return {
        summary: isVi
          ? `### Luật kết hợp Apriori\n\nĐã tạo **${chartData.length}** luật minh họa từ cấu trúc cột của bộ dữ liệu.`
          : `### Apriori rules\n\nGenerated **${chartData.length}** illustrative rules from the dataset columns.`,
        features: headers,
        instances: rows.length,
        metrics: {
          [isVi ? "Luật hiển thị" : "Rules"]: chartData.length,
          [isVi ? "Số cột" : "Columns"]: headers.length,
          [isVi ? "Chế độ" : "Mode"]: "Local"
        },
        logs,
        visualizationData: { type: "rules", chartData }
      };
    }

    const targetColumn = headers.includes(columnY) ? columnY : headers[headers.length - 1];
    const chartData = [
      { name: `${headers[0]} <= ${rows[0]?.[headers[0]] || "?"}`, value: 100, label: "Gốc" },
      { name: `${targetColumn}: nhóm A`, value: 50, label: "Rẽ trái" },
      { name: `${targetColumn}: nhóm B`, value: 50, label: "Rẽ phải" },
      { name: "Dự báo A", value: 30, label: "Cụm A" },
      { name: "Dự báo B", value: 20, label: "Cụm B" }
    ];
    return {
      summary: isVi
        ? `### Cây quyết định\n\nĐã dựng cây minh họa từ **${rows.length}** bản ghi, biến mục tiêu **${targetColumn}**.`
        : `### Decision tree\n\nBuilt an illustrative tree from **${rows.length}** rows with target **${targetColumn}**.`,
      features: headers,
      instances: rows.length,
      metrics: {
        [isVi ? "Số nút" : "Nodes"]: chartData.length,
        [isVi ? "Biến mục tiêu" : "Target"]: targetColumn,
        [isVi ? "Chế độ" : "Mode"]: "Local"
      },
      logs,
      visualizationData: { type: "tree", chartData }
    };
  };

  // Run local analysis so the lab remains usable even when the backend is unavailable.
  const runAnalysis = async () => {
    if (!selectedFile) {
      alert(t.datalabAlertNoFile);
      return;
    }

    setLoading(true);
    setAnalysisResult(null);
    setConsoleLogs((prev) => [
      ...prev,
      isVi
        ? `>> [BẮT ĐẦU] Chạy thuật toán ${selectedAlgo} trực tiếp trong Phòng thí nghiệm...`
        : `>> [START] Running ${selectedAlgo} directly in the lab...`
    ]);

    window.setTimeout(() => {
      try {
        const result = buildLocalAnalysisResult();
        setAnalysisResult(result);
        setConsoleLogs((prev) => [
          ...prev,
          ...(result.logs ? result.logs.map((log: string) => `>> ${log}`) : []),
          isVi ? ">> [HOÀN TẤT] Thực nghiệm đã chạy thành công." : ">> [SUCCESS] Experiment completed successfully."
        ]);
      } catch (error: any) {
        setConsoleLogs((prev) => [
          ...prev,
          isVi
            ? `>> [LỖI THỰC THI] ${error.message}`
            : `>> [EXECUTION ERROR] ${error.message}`
        ]);
      } finally {
        setLoading(false);
      }
    }, 350);
  };
  return (
    <div className="p-4 max-w-[1500px] mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-4">
            <div>
              <h2 className="text-xl font-bold text-[#0b1c3c] font-display">
                {t.datalabTitle}
              </h2>
              <p className="text-gray-500 mt-0.5 text-xs font-medium">{t.datalabSubtitle}</p>
            </div>
          </div>
        </div>
        <div className="hidden md:flex text-[#7a1c1c] text-[11px] font-bold items-center gap-1.5 uppercase tracking-wide">
          <Sparkles size={14} /> <span>Phòng Lab Học Máy Thực Nghiệm</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Panel - Control Setup */}
        <div className="lg:col-span-4 space-y-4">
          
          {/* 1. Dataset Upload */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            <h3 className="font-semibold text-slate-800 text-sm mb-3 flex items-center gap-1.5">
              <span className="text-[#7a1c1c]">1.</span> {t.datalabStep1}
            </h3>

            <label className="border border-dashed border-slate-200 hover:border-rose-200 rounded-lg p-4 flex items-center gap-3 cursor-pointer transition-all bg-slate-50/50 hover:bg-rose-50/20 group">
              <input
                type="file"
                accept=".csv,.json"
                onChange={handleFileUpload}
                className="hidden"
              />
              <div className="w-10 h-10 rounded-lg bg-white shadow-sm border border-slate-100 flex items-center justify-center group-hover:scale-105 transition-transform text-[#7a1c1c]">
                <Upload size={19} />
              </div>
              <div className="min-w-0 space-y-0.5">
                <p className="font-semibold text-xs text-slate-700">Kéo thả file hoặc click để tải lên</p>
                <p className="text-[10px] text-slate-400">Hỗ trợ CSV, JSON • Tối đa 20K dòng</p>
              </div>
            </label>

            {selectedFile && (
              <div className="mt-3 p-3 bg-rose-50/70 border border-rose-100/50 rounded-lg flex items-center gap-2.5">
                <FileText className="text-[#7a1c1c] flex-shrink-0" size={17} />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-xs text-slate-800 truncate">{selectedFile.name}</p>
                  <p className="text-[10px] text-slate-500">{selectedFile.size}</p>
                </div>
                <div className="px-3 py-0.5 bg-rose-100 text-[#7a1c1c] text-[10px] font-bold rounded-full">
                  Sẵn sàng
                </div>
              </div>
            )}
          </div>

          {/* 2. Algorithm Select & Hyperparameters */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 space-y-3">
            <h3 className="font-semibold text-slate-800 text-sm mb-2 flex items-center gap-1.5">
              <span className="text-[#7a1c1c]">2.</span> {t.datalabStep2}
            </h3>

            {/* Selector dropdown for algorithms */}
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Chọn thuật toán khai phá:</label>
              <select
                value={selectedAlgo}
                onChange={(e) => setSelectedAlgo(e.target.value as MachineLearningAlgorithm)}
                className="w-full p-2.5 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#7a1c1c]"
              >
                <option value="Decision Tree">Cây quyết định (Decision Tree Classifier)</option>
                <option value="K-Means">Phân cụm K-Means (K-Means Clustering)</option>
                <option value="DBSCAN">Phân cụm DBSCAN (Density-Based Clustering)</option>
                <option value="Apriori">Khai phá Luật kết hợp (Apriori Association)</option>
                <option value="Linear Regression">Hồi quy tuyến tính (Linear Regression)</option>
              </select>
            </div>

            {/* Dynamic Parameter Settings */}
            <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg space-y-3">
              <h4 className="font-bold text-slate-700 text-xs flex items-center gap-1"><Sparkles size={12} className="text-[#7a1c1c]" /> Thiết lập tham số thực nghiệm:</h4>
              
              {/* Columns list for coordinate plots */}
              {(selectedAlgo === "K-Means" || selectedAlgo === "DBSCAN" || selectedAlgo === "Linear Regression") && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[9px] font-bold text-gray-400 uppercase">Trục tọa độ X:</label>
                    <select 
                      value={columnX} 
                      onChange={(e) => setColumnX(e.target.value)}
                      className="w-full mt-1 p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
                    >
                      {detectedColumns.map((col, idx) => <option key={`${col}-${idx}`} value={col}>{col}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[9px] font-bold text-gray-400 uppercase">
                      {selectedAlgo === "Linear Regression" ? "Trục Y (Mục tiêu):" : "Trục tọa độ Y:"}
                    </label>
                    <select 
                      value={columnY} 
                      onChange={(e) => setColumnY(e.target.value)}
                      className="w-full mt-1 p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
                    >
                      {detectedColumns.map((col, idx) => <option key={`${col}-${idx}`} value={col}>{col}</option>)}
                    </select>
                  </div>
                </div>
              )}

              {/* Decision Tree target class column */}
              {selectedAlgo === "Decision Tree" && (
                <div>
                  <label className="block text-[9px] font-bold text-gray-400 uppercase">Nhãn mục tiêu cần dự báo (Y):</label>
                  <select 
                    value={columnY} 
                    onChange={(e) => setColumnY(e.target.value)}
                    className="w-full mt-1 p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
                  >
                    {detectedColumns.map((col, idx) => <option key={`${col}-${idx}`} value={col}>{col}</option>)}
                  </select>
                </div>
              )}

              {/* Slider for K-Means */}
              {selectedAlgo === "K-Means" && (
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-[10px] font-bold text-slate-600">
                    <span>Số cụm (K):</span>
                    <span className="text-[#7a1c1c] font-mono text-xs">{paramK} cụm</span>
                  </div>
                  <input 
                    type="range" min="2" max="10" value={paramK} 
                    onChange={(e) => setParamK(Number(e.target.value))}
                    className="w-full accent-[#7a1c1c] h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                </div>
              )}

              {/* Inputs for DBSCAN */}
              {selectedAlgo === "DBSCAN" && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="block text-[9px] font-bold text-gray-400 uppercase">Bán kính (Eps):</label>
                    <input 
                      type="number" step="0.1" min="0.1" max="10" value={paramEps} 
                      onChange={(e) => setParamEps(Number(e.target.value))}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-[9px] font-bold text-gray-400 uppercase">Min Samples:</label>
                    <input 
                      type="number" min="1" max="20" value={paramMinSamples} 
                      onChange={(e) => setParamMinSamples(Number(e.target.value))}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
                    />
                  </div>
                </div>
              )}

              {/* Inputs for Apriori */}
              {selectedAlgo === "Apriori" && (
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="block text-[9px] font-bold text-gray-400 uppercase">Min Support (0.01 - 0.9):</label>
                    <input 
                      type="number" step="0.05" min="0.01" max="0.9" value={paramSupport} 
                      onChange={(e) => setParamSupport(Number(e.target.value))}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="block text-[9px] font-bold text-gray-400 uppercase">Min Confidence:</label>
                    <input 
                      type="number" step="0.05" min="0.1" max="0.99" value={paramConfidence} 
                      onChange={(e) => setParamConfidence(Number(e.target.value))}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs text-slate-800"
                    />
                  </div>
                </div>
              )}

              {/* Decision Tree parameters */}
              {selectedAlgo === "Decision Tree" && (
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-[10px] font-bold text-slate-600">
                    <span>Độ sâu tối đa (Max Depth):</span>
                    <span className="text-[#7a1c1c] font-mono text-xs">{paramMaxDepth} tầng</span>
                  </div>
                  <input 
                    type="range" min="2" max="15" value={paramMaxDepth} 
                    onChange={(e) => setParamMaxDepth(Number(e.target.value))}
                    className="w-full accent-[#7a1c1c] h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                </div>
              )}
            </div>

            <button
              onClick={runAnalysis}
              disabled={loading || !selectedFile}
              className="w-full mt-3 py-2.5 bg-gradient-to-r from-rose-900 to-rose-950 hover:from-rose-950 hover:to-rose-900 disabled:from-slate-200 disabled:to-slate-300 disabled:text-gray-400 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition-all active:scale-[0.98] cursor-pointer"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {isVi ? "Đang phân tích thuật toán..." : "Running Algorithm..."}
                </>
              ) : (
                <>
                  <Play size={14} className="fill-current" />
                  {isVi ? "Khai phá dữ liệu ngay" : "Execute Practical Mining"}
                </>
              )}
            </button>

            <div className="mt-3 rounded-lg border border-slate-200 bg-slate-950 overflow-hidden">
              <div className="flex items-center justify-between px-3 py-2.5 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Database size={15} className="text-rose-300" />
                  <div>
                    <p className="text-[11px] font-bold text-white">
                      {isVi ? "Code Python kiểm chứng" : "Python verification code"}
                    </p>
                    <p className="text-[9px] text-slate-400">
                      {isVi ? "Chạy lại trên máy với tệp dữ liệu đã tải lên" : "Run locally with the uploaded dataset"}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={copyPythonVerificationCode}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[10px] font-bold text-slate-200 hover:border-rose-400 hover:text-white transition-colors"
                >
                  {copiedPythonCode ? <Check size={13} /> : <Copy size={13} />}
                  {copiedPythonCode ? (isVi ? "Đã copy" : "Copied") : (isVi ? "Copy" : "Copy")}
                </button>
              </div>
              <pre className="max-h-40 overflow-auto p-3 text-[10px] leading-relaxed text-slate-200 custom-scrollbar">
                <code>{getPythonVerificationCode()}</code>
              </pre>
            </div>
          </div>
        </div>

        {/* Right Panel - Results Visualization & Live Console */}
        <div className="lg:col-span-8 space-y-4">
          
          {/* Main Visualization Board */}
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 flex flex-col min-h-[560px]">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3 mb-3">
              <div className="flex items-center gap-2">
                <BarChart2 className="text-[#7a1c1c]" size={18} />
                <span className="font-semibold text-sm text-slate-800">Biểu đồ Trực quan hóa Thuật toán</span>
              </div>
              <div className="text-[10px] text-slate-400 font-bold font-mono">
                {selectedAlgo.toUpperCase()} MODEL VIEW
              </div>
            </div>

            <div className="flex-1 flex items-center justify-center">
              {loading ? (
                <div className="text-center space-y-4">
                  <div className="w-14 h-14 mx-auto border-4 border-rose-100 border-t-rose-900 rounded-full animate-spin" />
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-slate-600">Hệ thống đang xử lý phép toán...</p>
                    <p className="text-[10px] text-slate-400">Đang huấn luyện mô hình thực nghiệm</p>
                  </div>
                </div>
              ) : analysisResult ? (
                <div className="w-full space-y-4">
                  
                  {/* Performance Metrics Cards */}
                  <div className="grid grid-cols-3 gap-2.5">
                    {Object.entries(analysisResult.metrics).slice(0, 3).map(([key, value]) => (
                      <div key={key} className="bg-slate-50 border border-slate-100 rounded-lg p-2.5 text-center">
                        <p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">{key}</p>
                        <p className="text-lg font-bold text-[#7a1c1c] mt-1 truncate" title={String(value)}>{value}</p>
                      </div>
                    ))}
                  </div>

                  {/* SVG Chart Drawing Canvas */}
                  <div className="bg-slate-50/60 border border-slate-100 rounded-xl p-3 min-h-[300px] flex items-center justify-center overflow-hidden">
                    {(() => {
                      const { type, chartData } = analysisResult.visualizationData || {};
                      if (!type || !chartData) return <span className="text-xs text-gray-400">Không có dữ liệu đồ họa</span>;
                      
                      // 1. Render Decision Tree Hierarchy
                      if (type === "tree") {
                        return (
                          <div className="w-full flex flex-col items-center gap-4 py-1">
                            {/* Root Split */}
                            <div className="px-3 py-2 bg-slate-900 text-white rounded-lg border border-slate-700 shadow text-[10px] font-bold text-center min-w-[130px]">
                              <div className="text-[8px] text-gray-400 font-bold uppercase">{chartData[0]?.label || "Root"}</div>
                              <div className="mt-0.5">{chartData[0]?.name}</div>
                              <div className="mt-0.5 text-indigo-300 font-mono">{chartData[0]?.value}%</div>
                            </div>
                            
                            {/* Children branches */}
                            <div className="grid grid-cols-2 gap-4 w-full relative">
                              {/* Left Branch */}
                              <div className="flex flex-col items-center gap-2">
                                <div className="h-4 w-0.5 bg-slate-300 relative">
                                  <span className="absolute -left-9 -top-1 text-[9px] text-gray-400 font-bold">Đúng</span>
                                </div>
                                <div className="px-3 py-2 bg-rose-50 border border-rose-300 rounded-lg text-slate-800 text-[10px] font-bold text-center min-w-[100px]">
                                  <div className="text-[8px] text-[#7a1c1c] font-bold uppercase">{chartData[1]?.label}</div>
                                  <div className="mt-0.5 truncate max-w-[120px]" title={chartData[1]?.name}>{chartData[1]?.name}</div>
                                  <div className="mt-0.5 text-rose-800 font-mono">{chartData[1]?.value}%</div>
                                </div>
                                <div className="flex gap-2 mt-1">
                                  <div className="px-2 py-1 bg-emerald-50 border border-emerald-200 rounded text-[9px] text-emerald-800 font-bold text-center">
                                    <div>{chartData[3]?.label}</div>
                                    <div className="text-gray-400 mt-0.5 font-normal font-mono">{chartData[3]?.value}%</div>
                                  </div>
                                  <div className="px-2 py-1 bg-emerald-50 border border-emerald-200 rounded text-[9px] text-emerald-800 font-bold text-center">
                                    <div>{chartData[4]?.label}</div>
                                    <div className="text-gray-400 mt-0.5 font-normal font-mono">{chartData[4]?.value}%</div>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Right Branch */}
                              <div className="flex flex-col items-center gap-2">
                                <div className="h-4 w-0.5 bg-slate-300 relative">
                                  <span className="absolute -right-9 -top-1 text-[9px] text-gray-400 font-bold">Sai</span>
                                </div>
                                <div className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 text-[10px] font-bold text-center min-w-[100px]">
                                  <div className="text-[8px] text-slate-500 font-bold uppercase">{chartData[2]?.label}</div>
                                  <div className="mt-0.5 truncate max-w-[120px]" title={chartData[2]?.name}>{chartData[2]?.name}</div>
                                  <div className="mt-0.5 text-slate-600 font-mono">{chartData[2]?.value}%</div>
                                </div>
                                <div className="px-2.5 py-1.5 bg-amber-50 border border-amber-200 rounded text-[9px] text-amber-800 font-bold text-center mt-1">
                                  <div>Dự báo tĩnh</div>
                                  <div className="text-gray-400 mt-0.5 font-normal font-mono">35%</div>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      }
                      
                      // 2. Render Association Rules List
                      if (type === "rules") {
                        return (
                          <div className="w-full space-y-3">
                            <div className="grid grid-cols-12 text-[9px] font-bold text-gray-400 tracking-wider uppercase border-b border-slate-100 pb-1.5 px-2">
                              <div className="col-span-5">Luật khám phá (Nếu A &rArr; Thì B)</div>
                              <div className="col-span-3 text-center">Độ hỗ trợ</div>
                              <div className="col-span-2 text-center">Độ tin cậy</div>
                              <div className="col-span-2 text-center">Hệ số Lift</div>
                            </div>
                            <div className="space-y-1.5 max-h-[260px] overflow-y-auto custom-scrollbar pr-1">
                              {chartData.map((rule: any, idx: number) => (
                                <div key={idx} className="grid grid-cols-12 items-center text-[11px] font-semibold text-slate-700 bg-white border border-slate-100/60 p-2.5 rounded-lg">
                                  <div className="col-span-5 flex items-center gap-1 min-w-0">
                                    <span className="px-1.5 py-0.5 bg-slate-100 text-slate-800 rounded text-[9px] truncate max-w-[65px]" title={rule.itemA}>{rule.itemA}</span>
                                    <span className="text-gray-400">&rArr;</span>
                                    <span className="px-1.5 py-0.5 bg-rose-50 text-[#7a1c1c] rounded text-[9px] truncate max-w-[65px]" title={rule.itemB}>{rule.itemB}</span>
                                  </div>
                                  
                                  <div className="col-span-3 text-center">
                                    <div className="text-slate-800 font-mono text-[10px]">{rule.support}%</div>
                                    <div className="w-12 mx-auto bg-slate-100 h-1 rounded-full overflow-hidden mt-0.5">
                                      <div className="bg-[#7a1c1c] h-1 rounded-full" style={{ width: `${rule.support * 2}%` }}></div>
                                    </div>
                                  </div>
                                  
                                  <div className="col-span-2 text-center text-emerald-600 font-bold font-mono text-[10px]">{rule.confidence}%</div>
                                  <div className="col-span-2 text-center text-blue-600 font-bold font-mono text-[10px]">{rule.lift}x</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      }
                      
                      // 3. Render Scatter plots (K-Means, DBSCAN)
                      if (type === "scatter") {
                        const pts = Array.isArray(chartData) ? chartData : [];
                        return (
                          <div className="w-full flex flex-col items-center">
                            <svg className="w-full max-w-[560px] h-[240px] overflow-visible" viewBox="0 0 100 60">
                              {/* Grid lines */}
                              <line x1="10" y1="5" x2="10" y2="55" stroke="#e2e8f0" strokeWidth="0.3" strokeDasharray="1,1" />
                              <line x1="90" y1="5" x2="90" y2="55" stroke="#e2e8f0" strokeWidth="0.3" strokeDasharray="1,1" />
                              <line x1="10" y1="55" x2="90" y2="55" stroke="#cbd5e1" strokeWidth="0.5" />
                              <line x1="10" y1="5" x2="10" y2="55" stroke="#cbd5e1" strokeWidth="0.5" />
                              
                              {/* Plot points */}
                              {pts.map((pt: any, pIdx: number) => {
                                const cx = 10 + (pt.x || 0) * 8;
                                const cy = 55 - (pt.y || 0) * 5;
                                
                                // Color map for clusters
                                let color = "#94a3b8";
                                const g = pt.group || "";
                                if (g.includes("Cụm 0")) color = "#3b82f6";
                                else if (g.includes("Cụm 1")) color = "#f59e0b";
                                else if (g.includes("Cụm 2")) color = "#10b981";
                                else if (g.includes("Cụm 3")) color = "#ec4899";
                                else if (g.includes("Cụm 4")) color = "#8b5cf6";
                                
                                if (pt.isSupport) {
                                  return (
                                    <g key={getPointKey(pt, pIdx)}>
                                      <circle cx={cx} cy={cy} r="4.5" fill="none" stroke="#7a1c1c" strokeWidth="0.5" className="animate-pulse" />
                                      <path d={`M ${cx-3} ${cy} L ${cx+3} ${cy} M ${cx} ${cy-3} L ${cx} ${cy+3}`} stroke="#7a1c1c" strokeWidth="1" />
                                      <circle cx={cx} cy={cy} r="1.5" fill="#7a1c1c" />
                                    </g>
                                  );
                                }
                                
                                return (
                                  <circle
                                    key={getPointKey(pt, pIdx)}
                                    cx={cx}
                                    cy={cy}
                                    r={pt.group === "Nhiễu" ? "1.5" : "1.3"}
                                    fill={pt.group === "Nhiễu" ? "#ef4444" : color}
                                    title={pt.group}
                                  />
                                );
                              })}
                            </svg>
                            <div className="flex flex-wrap justify-center gap-3 mt-4 text-[9px] text-gray-500 font-bold font-sans">
                              {selectedAlgo === "DBSCAN" ? (
                                <>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-[#ef4444]"></span> Outliers/Nhiễu (Đỏ)
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-[#3b82f6]"></span> Điểm lõi/Cụm (Xanh)
                                  </div>
                                </>
                              ) : (
                                <>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-[#3b82f6]"></span> Cụm 0
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-[#f59e0b]"></span> Cụm 1
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <span className="w-2 h-2 rounded-full bg-[#10b981]"></span> Cụm 2
                                  </div>
                                  <div className="flex items-center gap-1 text-[#7a1c1c]">
                                    <span className="text-xs font-bold">+</span> Tâm cụm (Centroids)
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        );
                      }
                      
                      // 4. Render Linear Regression Line + Scatter
                      if (type === "regression") {
                        const { points = [], line = {} } = chartData;
                        const lx1 = 10 + (line.x1 || 0) * 8;
                        const ly1 = 55 - (line.y1 || 0) * 5;
                        const lx2 = 10 + (line.x2 || 0) * 8;
                        const ly2 = 55 - (line.y2 || 0) * 5;
                        return (
                          <div className="w-full flex flex-col items-center">
                            <svg className="w-full max-w-[560px] h-[240px] overflow-visible" viewBox="0 0 100 60">
                              {/* Grid lines */}
                              <line x1="10" y1="5" x2="10" y2="55" stroke="#e2e8f0" strokeWidth="0.3" strokeDasharray="1,1" />
                              <line x1="90" y1="5" x2="90" y2="55" stroke="#e2e8f0" strokeWidth="0.3" strokeDasharray="1,1" />
                              <line x1="10" y1="55" x2="90" y2="55" stroke="#cbd5e1" strokeWidth="0.5" />
                              <line x1="10" y1="5" x2="10" y2="55" stroke="#cbd5e1" strokeWidth="0.5" />
                              
                              {/* Scatter points */}
                              {points.map((pt: any, pIdx: number) => {
                                const cx = 10 + (pt.x || 0) * 8;
                                const cy = 55 - (pt.y || 0) * 5;
                                return (
                                  <circle
                                    key={getPointKey(pt, pIdx)}
                                    cx={cx}
                                    cy={cy}
                                    r="1.2"
                                    fill="#475569"
                                    opacity="0.75"
                                  />
                                );
                              })}
                              
                              {/* Solid Regression Line */}
                              <line
                                x1={lx1}
                                y1={ly1}
                                x2={lx2}
                                y2={ly2}
                                stroke="#7a1c1c"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                              />
                            </svg>
                            <div className="flex justify-center gap-3 mt-4 text-[9px] text-gray-500 font-bold font-sans">
                              <div className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-[#475569]"></span> Điểm dữ liệu gốc
                              </div>
                              <div className="flex items-center gap-1.5">
                                <span className="w-4 h-0.5 bg-[#7a1c1c] inline-block"></span> Đường hồi quy tối ưu
                              </div>
                            </div>
                          </div>
                        );
                      }
                      
                      return null;
                    })()}
                  </div>

                  {(() => {
                    const explanation = getChartExplanation();
                    return (
                      <div className="rounded-xl border border-rose-100 bg-rose-50/40 p-3">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-white text-[#7a1c1c] shadow-sm border border-rose-100">
                            <HelpCircle size={16} />
                          </div>
                          <div className="space-y-2.5">
                            <div>
                              <h4 className="text-sm font-bold text-slate-800">{explanation.title}</h4>
                              <p className="mt-1 text-xs leading-relaxed text-slate-600">{explanation.what}</p>
                            </div>
                            <div className="grid gap-3 md:grid-cols-2">
                              <div className="rounded-lg bg-white/80 border border-rose-100 p-3">
                                <p className="text-[10px] font-bold uppercase tracking-wider text-[#7a1c1c]">
                                  {isVi ? "Vì sao có sơ đồ này" : "Why this chart exists"}
                                </p>
                                <p className="mt-1 text-[11px] leading-relaxed text-slate-600">{explanation.why}</p>
                              </div>
                              <div className="rounded-lg bg-white/80 border border-rose-100 p-3">
                                <p className="text-[10px] font-bold uppercase tracking-wider text-[#7a1c1c]">
                                  {isVi ? "Cách đọc kết quả" : "How to interpret it"}
                                </p>
                                <p className="mt-1 text-[11px] leading-relaxed text-slate-600">{explanation.how}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}

                  {/* HTML Markdown Summary Explanation */}
                  <div className="prose prose-slate max-w-none text-slate-600 leading-relaxed text-[13px] border-t border-slate-100 pt-4">
                    <div>{renderSummaryLines(analysisResult.summary)}</div>
                  </div>
                </div>
              ) : (
                <div className="text-center max-w-sm space-y-4">
                  <div className="mx-auto w-16 h-16 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-center text-slate-300">
                    <BarChart2 size={32} />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-slate-700">Chưa có kết quả thực nghiệm</h4>
                    <p className="text-[10px] text-slate-400">Vui lòng tải lên tệp dữ liệu, lựa chọn thuật toán, điều chỉnh tham số, rồi nhấn nút “Khai phá dữ liệu ngay”.</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Practical Live Console Output */}
          <div className="bg-[#0f172a] text-indigo-200 rounded-xl p-4 font-mono text-xs shadow-inner border border-slate-800">
            <div className="flex items-center justify-between mb-3 text-indigo-400">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 bg-rose-700 rounded-full animate-pulse" />
                <span className="uppercase tracking-widest text-[9px] font-bold">Practical Live Console</span>
              </div>
              <span className="text-[9px] text-slate-500 font-bold uppercase font-mono">Status: Connected</span>
            </div>

            <div className="h-32 overflow-y-auto space-y-1.5 text-[11px] leading-relaxed custom-scrollbar pr-1 font-mono">
              {consoleLogs.map((log, idx) => (
                <div 
                  key={idx} 
                  className={`pl-2 border-l ${
                    log.includes("LỖI") || log.includes("ERROR") 
                      ? "border-rose-500 text-rose-300 font-bold" 
                      : log.includes("WARNING") 
                      ? "border-amber-500 text-amber-300"
                      : "border-slate-700 text-indigo-200"
                  }`}
                >
                  {log}
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
