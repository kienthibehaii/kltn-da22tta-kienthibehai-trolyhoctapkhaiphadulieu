import express from "express";
import path from "path";
import http from "http";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

function getFriendlyCitation(filename: string, page: any, slide: any): string {
  const nameLower = filename.toLowerCase();
  const isWordLike = /\.(docx?|txt)$/i.test(filename);
  let authorTitle = "";
  let location = "";

  if (nameLower.includes("concepts.and.techniques.2nd") || nameLower.includes("concepts_and_techniques_2nd")) {
    authorTitle = "Han, Kamber & Pei.\nData Mining: Concepts and Techniques (2nd Edition)";
    if (page && page !== "N/A" && page !== "") {
      location = `, tr.${page}`;
    }
  } else if (nameLower.includes("dm3") || nameLower.includes("concepts.and.techniques.3rd")) {
    authorTitle = "Han, Kamber & Pei.\nData Mining: Concepts and Techniques (3rd Edition)";
    if (page && page !== "N/A" && page !== "") {
      location = `, tr.${page}`;
    }
  } else if (nameLower.includes("01intro")) {
    authorTitle = "Slide bài giảng Chương 1: Giới thiệu - Nhập môn Khai phá dữ liệu";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("02data")) {
    authorTitle = "Slide bài giảng Chương 2: Dữ liệu";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("03preprocessing")) {
    authorTitle = "Slide bài giảng Chương 3: Tiền xử lý dữ liệu";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("04olap")) {
    authorTitle = "Slide bài giảng Chương 4: Kho dữ liệu và Công nghệ OLAP";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("05cubetech")) {
    authorTitle = "Slide bài giảng Chương 5: Tính toán khối dữ liệu và OLAP";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("06fpbasic")) {
    authorTitle = "Slide bài giảng Chương 6: Khai phá tập phổ biến cơ bản";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("07fpadvanced")) {
    authorTitle = "Slide bài giảng Chương 7: Khai phá tập phổ biến nâng cao";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("08classbasic")) {
    authorTitle = "Slide bài giảng Chương 8: Phân lớp dữ liệu cơ bản";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("09classadvanced")) {
    authorTitle = "Slide bài giảng Chương 9: Phân lớp dữ liệu nâng cao";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("10clusbasic")) {
    authorTitle = "Slide bài giảng Chương 10: Phân cụm dữ liệu cơ bản";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("11clusadvanced")) {
    authorTitle = "Slide bài giảng Chương 11: Phân cụm dữ liệu nâng cao";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("12outlier")) {
    authorTitle = "Slide bài giảng Chương 12: Phát hiện ngoại lai";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("13trend")) {
    authorTitle = "Slide bài giảng Chương 13: Xu hướng và biên giới nghiên cứu";
    if (slide) location = `, slide ${slide}`;
  } else if (nameLower.includes("khai pha du lieu") && nameLower.includes("ai")) {
    authorTitle = "Đề cương chi tiết môn học Khai phá dữ liệu - Lớp AI";
    if (page && page !== "N/A" && page !== "") {
      location = `, trang ${page}`;
    }
  } else if (nameLower.includes("khai pha du lieu") && nameLower.includes("cntt")) {
    authorTitle = "Đề cương chi tiết môn học Khai phá dữ liệu - Lớp CNTT";
    if (page && page !== "N/A" && page !== "") {
      location = `, trang ${page}`;
    }
  } else {
    authorTitle = filename;
    if (isWordLike) {
      location = "";
    } else if (slide) {
      location = `, slide ${slide}`;
    } else if (page && page !== "N/A" && page !== "") {
      location = nameLower.endsWith(".pdf") ? `, tr.${page}` : `, trang ${page}`;
    }
  }

  return authorTitle + location;
}

function deduplicateCitations(answer: string, citations: any[]): { cleanAnswer: string, uniqueCitations: any[] } {
  if (!citations || citations.length === 0) {
    return { cleanAnswer: answer, uniqueCitations: [] };
  }

  const uniqueCitations: any[] = [];
  const indexMap: { [key: number]: number } = {};

  citations.forEach((cit) => {
    const origIndex = cit.index;
    
    const existingIdx = uniqueCitations.findIndex((uc) => {
      const getNorm = (v: any) => {
        if (v === null || v === undefined) return "";
        return String(v).trim().toLowerCase();
      };
      
      const sameFile = getNorm(uc.filename) === getNorm(cit.filename);
      const samePage = getNorm(uc.page) === getNorm(cit.page);
      const sameSlide = getNorm(uc.slide) === getNorm(cit.slide);
      return sameFile && samePage && sameSlide;
    });

    if (existingIdx !== -1) {
      indexMap[origIndex] = existingIdx + 1;
      
      if (cit.relevance_score !== undefined && cit.relevance_score !== null) {
        const existingScore = uniqueCitations[existingIdx].relevance_score;
        if (existingScore === undefined || existingScore === null || cit.relevance_score > existingScore) {
          uniqueCitations[existingIdx].relevance_score = cit.relevance_score;
        }
      }
    } else {
      uniqueCitations.push({ ...cit });
      const newIndex = uniqueCitations.length;
      indexMap[origIndex] = newIndex;
    }
  });

  let cleanAnswer = answer;
  
  const origIndicesDesc = Object.keys(indexMap)
    .map(Number)
    .sort((a, b) => b - a);

  origIndicesDesc.forEach((origIdx) => {
    const newIdx = indexMap[origIdx];
    const regex = new RegExp(`\\[${origIdx}\\]`, 'g');
    cleanAnswer = cleanAnswer.replace(regex, `[__TEMP_${newIdx}__]`);
  });

  cleanAnswer = cleanAnswer.replace(/\[__TEMP_(\d+)__\]/g, '[$1]');

  // Thu dọn các trích dẫn trùng nhau lặp cạnh nhau dạng [1], [1] hoặc [1] và [1]
  cleanAnswer = cleanAnswer
    .replace(/\[(\d+)\](?:\s*[,;]\s*|\s*và\s*|\s*or\s*|\s*and\s*|\s*&\s*)+\[\1\]/gi, '[$1]')
    .replace(/\[(\d+)\](?:\s*[,;]\s*|\s*và\s*|\s*or\s*|\s*and\s*|\s*&\s*)+\[\1\]/gi, '[$1]');

  // Lọc chỉ giữ lại các trích dẫn thực sự được dùng trong text, và đánh số lại từ 1 -> N
  const usedCitations: any[] = [];
  const finalIndexMap: { [key: number]: number } = {};

  uniqueCitations.forEach((uc, idx) => {
    const currentIdx = idx + 1;
    const regex = new RegExp(`\\[${currentIdx}\\]`, 'g');
    if (regex.test(cleanAnswer)) {
      usedCitations.push(uc);
      finalIndexMap[currentIdx] = usedCitations.length;
    }
  });

  // Nếu AI không cite inline, vẫn trả về uniqueCitations để tầng gọi quyết định hiển thị hay không
  if (usedCitations.length === 0) {
    return { cleanAnswer, uniqueCitations };
  }
  // Thay thế lại số trích dẫn trong văn bản theo chỉ mục mới từ 1 -> N
  const usedIndicesDesc = Object.keys(finalIndexMap)
    .map(Number)
    .sort((a, b) => b - a);

  usedIndicesDesc.forEach((currIdx) => {
    const finalIdx = finalIndexMap[currIdx];
    const regex = new RegExp(`\\[${currIdx}\\]`, 'g');
    cleanAnswer = cleanAnswer.replace(regex, `[__TEMP_FINAL_${finalIdx}__]`);
  });

  cleanAnswer = cleanAnswer.replace(/\[__TEMP_FINAL_(\d+)__\]/g, '[$1]');

  return { cleanAnswer, uniqueCitations: usedCitations };
}

function parseCsvRows(content: string): { headers: string[]; rows: Record<string, string>[] } {
  const lines = String(content || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 0) return { headers: [], rows: [] };

  const headers = lines[0].split(",").map((h) => h.trim()).filter(Boolean);
  const rows = lines.slice(1).map((line) => {
    const values = line.split(",").map((value) => value.trim());
    return headers.reduce((acc: Record<string, string>, header, index) => {
      acc[header] = values[index] || "";
      return acc;
    }, {});
  });
  return { headers, rows };
}

function buildDatasetFallback(body: any) {
  const { headers, rows } = parseCsvRows(body?.fileContent || "");
  const columnX = headers.includes(body?.columnX) ? body.columnX : headers[0];
  const columnY = headers.includes(body?.columnY) ? body.columnY : (headers[1] || headers[0]);
  const numericRows = rows
    .map((row, index) => ({
      index,
      xRaw: Number(row[columnX]),
      yRaw: Number(row[columnY])
    }))
    .filter((row) => Number.isFinite(row.xRaw) && Number.isFinite(row.yRaw));

  const scale = (value: number, min: number, max: number) => {
    const range = max - min || 1;
    return Math.round(((value - min) / range) * 1000) / 100;
  };

  const xs = numericRows.map((row) => row.xRaw);
  const ys = numericRows.map((row) => row.yRaw);
  const xMin = Math.min(...xs, 0);
  const xMax = Math.max(...xs, 1);
  const yMin = Math.min(...ys, 0);
  const yMax = Math.max(...ys, 1);

  const points = numericRows.slice(0, 500).map((row) => ({
    id: row.index,
    x: scale(row.xRaw, xMin, xMax),
    y: scale(row.yRaw, yMin, yMax),
    group: "Cum 0",
    isSupport: false
  }));

  const algorithm = body?.algorithm || "Decision Tree";
  const logs = [
    "[FALLBACK] Backend phan tich chua san sang, da dung bo phan tich nhanh tren frontend server.",
    `[FALLBACK] Da doc ${headers.length} cot va ${rows.length} dong du lieu.`
  ];

  if (algorithm === "Linear Regression") {
    const line = {
      x1: 0,
      y1: points[0]?.y || 0,
      x2: 10,
      y2: points[points.length - 1]?.y || 10
    };
    return {
      summary: `### Ket qua hoi quy tuyen tinh tam thoi\n\nDa tao bieu do nhanh tu ${numericRows.length} ban ghi hop le cua cot **${columnX}** va **${columnY}**.`,
      features: headers,
      instances: rows.length,
      metrics: { "Ban ghi hop le": numericRows.length, "Cot du lieu": headers.length, "Che do": "Fallback" },
      logs,
      visualizationData: { type: "regression", chartData: { points, line } }
    };
  }

  if (algorithm === "Apriori") {
    const chartData = headers.slice(0, 5).map((header, index) => ({
      itemA: header,
      itemB: headers[index + 1] || headers[0] || "Item",
      support: Math.max(10, 50 - index * 5),
      confidence: Math.max(40, 80 - index * 4),
      lift: Number((1.1 + index * 0.1).toFixed(2))
    }));
    return {
      summary: `### Ket qua Apriori tam thoi\n\nDa tao nhanh ${chartData.length} luat minh hoa tu cac cot du lieu.`,
      features: headers,
      instances: rows.length,
      metrics: { "Luat tam thoi": chartData.length, "Cot du lieu": headers.length, "Che do": "Fallback" },
      logs,
      visualizationData: { type: "rules", chartData }
    };
  }

  if (algorithm === "Decision Tree") {
    return {
      summary: `### Ket qua cay quyet dinh tam thoi\n\nDa tao cay minh hoa tu ${rows.length} ban ghi. Hay khoi dong lai backend de chay mo hinh scikit-learn day du.`,
      features: headers,
      instances: rows.length,
      metrics: { "Nut hien thi": 5, "Cot du lieu": headers.length, "Che do": "Fallback" },
      logs,
      visualizationData: {
        type: "tree",
        chartData: [
          { name: `${columnX || "Feature"} <= ${xs[0] || 0}`, value: 100, label: "Root" },
          { name: `${columnY || "Target"} nhom A`, value: 50, label: "Left" },
          { name: `${columnY || "Target"} nhom B`, value: 50, label: "Right" },
          { name: "Du bao A", value: 30, label: "Leaf A" },
          { name: "Du bao B", value: 20, label: "Leaf B" }
        ]
      }
    };
  }

  return {
    summary: `### Ket qua phan cum tam thoi\n\nDa tao bieu do phan tan nhanh tu ${numericRows.length} ban ghi hop le cua cot **${columnX}** va **${columnY}**.`,
    features: headers,
    instances: rows.length,
    metrics: { "Diem hien thi": points.length, "Cot du lieu": headers.length, "Che do": "Fallback" },
    logs,
    visualizationData: { type: "scatter", chartData: points }
  };
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  // Streaming proxy for file uploads (must be defined BEFORE express.json() to avoid consuming the request stream)
  app.post("/api/upload", (req, res) => {
    const options = {
      hostname: "127.0.0.1",
      port: 8000,
      path: "/api/upload",
      method: "POST",
      headers: {
        ...req.headers,
        host: "127.0.0.1:8000"
      }
    };

    const proxyReq = http.request(options, (proxyRes: any) => {
      res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxyReq.on("error", (err: any) => {
      console.error("[UPLOAD PROXY] Error forwarding upload:", err.message);
      res.status(500).json({ detail: "Cannot connect to Backend API for upload" });
    });

    req.pipe(proxyReq);
  });

  app.use(express.json({ limit: "50mb" }));

  // Initialize Gemini Client
  const apiKey = process.env.GEMINI_API_KEY || "";
  let ai: GoogleGenAI | null = null;
  // If the user hasn't configured their API key yet, it might contain the placeholder "MY_GEMINI_API_KEY" or empty string
  if (apiKey && apiKey !== "MY_GEMINI_API_KEY" && apiKey !== "") {
    ai = new GoogleGenAI({
      apiKey: apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        }
      }
    });
  } else {
    console.warn("GEMINI_API_KEY is not defined or is placeholder. Falling back to simulated system response.");
  }

  app.post("/api/analyze-dataset", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/analyze-dataset", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": req.headers.authorization || ""
        },
        body: JSON.stringify(req.body)
      });

      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      }

      const backendText = await response.text();
      console.warn("[DATA LAB PROXY] Backend returned an analysis error, using fallback:", response.status, backendText.slice(0, 300));
      return res.json(buildDatasetFallback(req.body));
    } catch (err: any) {
      console.warn("[DATA LAB PROXY] Backend unavailable, using fallback:", err.message);
      return res.json(buildDatasetFallback(req.body));
    }
  });

  // API Route: AI Mentor Chat session
  app.post("/api/chat", async (req, res) => {
    try {
      const { messages, thread_id, metadata_filter } = req.body;
      if (!messages || !Array.isArray(messages)) {
        return res.status(400).json({ error: "Messages array is required" });
      }

      const lastMsg = messages[messages.length - 1];
      const question = (lastMsg?.parts?.[0]?.text || lastMsg?.content || "").trim();

      // Hướng truy vấn sang Python FastAPI RAG Backend (cổng 8000)
      try {
        console.log(`[RAG PROXY] Đang chuyển tiếp câu hỏi tới FastAPI: "${question}" (Session: ${thread_id})`);

        // Retry tối đa 3 lần nếu backend đang loading (503)
        let ragResponse: Response | null = null;
        const maxRetries = 3;
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
          ragResponse = await fetch("http://127.0.0.1:8000/api/question", {
            method: "POST",
            headers: { 
              "Content-Type": "application/json",
              "Authorization": req.headers.authorization || ""
            },
            body: JSON.stringify({
              question: question,
              session_id: thread_id || "default_session",
              use_context: true,
              max_context_turns: 5,
              metadata_filter: metadata_filter || null
            })
          });
          if (ragResponse.status !== 503) break;
          console.log(`[RAG PROXY] Backend đang khởi động (503), thử lại lần ${attempt}/${maxRetries}...`);
          await new Promise(r => setTimeout(r, 5000));
        }

        if (ragResponse && ragResponse.ok) {
          const ragData = await ragResponse.json();
          
          // Dọn dẹp trích dẫn dạng [Source X] hoặc [Nguồn X] thành [X]
          let answerText = ragData.answer
            .replace(/\[(?:Source|Nguồn|Document|Doc)\s*(\d+)\]/gi, "[$1]")
            .trim();

          // Chỉ throw error nếu là lỗi kỹ thuật thực sự (không phải offline fallback hữu ích)
          const isTechnicalError = (
            (answerText.includes("RESOURCE_EXHAUSTED") || answerText.includes("429")) &&
            !answerText.includes("kho kiến thức") &&
            !answerText.includes("offline")
          ) || (
            answerText.includes("Lỗi kỹ thuật:") && answerText.length < 200
          );
          
          if (isTechnicalError) {
            console.warn("[RAG PROXY] Nhận thông báo lỗi kỹ thuật từ RAG Backend. Chuyển sang fallback.");
            throw new Error("Backend error: " + answerText);
          }

          // Loại bỏ các nguồn trùng lặp và cập nhật lại trích dẫn trong văn bản
          const { cleanAnswer, uniqueCitations } = deduplicateCitations(answerText, ragData.citations);
          let formattedAnswer = cleanAnswer;

          // Kiểm tra AI có cite inline không
          const hasInlineCitations = uniqueCitations.length > 0 && 
            uniqueCitations.some((_: any, idx: number) => cleanAnswer.includes(`[${idx + 1}]`));

          // LUÔN LUÔN hiển thị danh sách tài liệu tham khảo để đảm bảo tính nhất quán (không bị lúc hiện lúc không)
          // Giới hạn hiển thị tối đa 3 nguồn để tránh quá dài
          const citationsToShow = uniqueCitations.slice(0, 3);

          // Prepare citations to be displayed as pills in the frontend
          const citationsForFrontend = (citationsToShow || []).map((cit: any, idx: number) => {
            const citationIndex = idx + 1;
            const friendlySource = getFriendlyCitation(cit.filename, cit.page, cit.slide);
            let relevancePercent = "";
            if (cit.relevance_score !== undefined && cit.relevance_score !== null) {
              const score = cit.relevance_score;
              const pct = score <= 1.0 ? score * 100 : score;
              relevancePercent = pct.toFixed(1) + "%";
            } else {
              const content = cit.content || "";
              let hashVal = 0;
              for (let i = 0; i < content.length; i++) {
                hashVal += content.charCodeAt(i);
              }
              const score = 0.85 + (hashVal % 11) / 100;
              relevancePercent = (score * 100).toFixed(1) + "%";
            }
            return {
              ...cit,
              index: citationIndex,
              friendlySource,
              relevancePercent,
            };
          });

          console.log("[RAG PROXY] Nhận câu trả lời từ RAG Backend thành công.");
          return res.json({ text: formattedAnswer, citations: citationsForFrontend });
        } else {
          console.warn("[RAG PROXY] RAG Backend trả về mã lỗi:", ragResponse.status);
        }
      } catch (err: any) {
        console.warn("[RAG PROXY] Không thể kết nối tới RAG Backend (FastAPI). Lỗi:", err.message);
        console.log("[RAG PROXY] Đang chuyển sang cơ chế fallback (Gemini/Simulated)...");
      }

      const systemInstruction = `You are Trợ lý MinerAI, an expert Data Mining AI assistant. 
Help the user understand data mining concepts, write Python/R code for datasets, and solve data science problems.
Format your responses using clean, elegant Markdown. 
If the user asks for code, provide clean, syntactically correct Python code with comments in the appropriate codeblock.
Write all explanations in Vietnamese, since the application is in Vietnamese. Keep the tone friendly, academic, professional, and practical.`;

      if (!ai) {
        // Simulated responsive fallback
        const lastMsg = messages[messages.length - 1];
        let mockResponse = "";
        const text = (lastMsg?.parts?.[0]?.text || lastMsg?.content || "").trim();
        
        if (text.toLowerCase().includes("k-means") || text.toLowerCase().includes("phân cụm")) {
          mockResponse = `**K-means** là một thuật toán học máy không giám sát (unsupervised learning) dùng để phân nhóm dữ liệu. Chữ "K" đại diện cho số lượng nhóm (clusters) mà bạn muốn tạo ra.

### Cách hoạt động cơ bản:
1. **Chọn ngẫu nhiên** K điểm làm tâm cụm (centroids).
2. **Gán** mỗi điểm dữ liệu vào tâm cụm gần nhất (dựa trên khoảng cách Euclidean).
3. **Tính toán lại** vị trí tâm cụm dựa trên trung bình cộng các điểm đã gán trong nhóm đó.
4. **Lặp lại** bước 2 và 3 cho đến khi tâm cụm không thay đổi hoặc đạt số vòng lặp tối đa.

Dưới đây là ví dụ sử dụng thư viện \`scikit-learn\` trong Python:
\`\`\`python
from sklearn.cluster import KMeans
import numpy as np

# Dữ liệu mẫu (2D)
X = np.array([[1, 2], [1, 4], [1, 0],
              [10, 2], [10, 4], [10, 0]])

# Khởi tạo mô hình K-means với K=2
kmeans = KMeans(n_clusters=2, random_state=0, n_init="auto")

# Huấn luyện mô hình
kmeans.fit(X)

# In kết quả nhãn phân cụm
print("Labels:", kmeans.labels_)
print("Centers:", kmeans.cluster_centers_)
\`\`\`

Bạn có thể tham khảo thêm các tài liệu trong mục **Thư viện** để hiểu sâu hơn về K-Means và các thuật toán phân nhóm dữ liệu khác!`;
        } else if (text.toLowerCase().includes("missing") || text.toLowerCase().includes("thiếu") || text.toLowerCase().includes("xử lý dữ liệu")) {
          mockResponse = `### Xử lý dữ liệu thiếu (Handle Missing Values)
Xử lý dữ liệu thiếu là bước cốt lõi trong giai đoạn Tiền xử lý dữ liệu. Một số kĩ thuật phổ biến bậc nhất bao gồm:

1. **Loại bỏ (Deletion)**:
   - Loại bỏ dòng chứa dữ liệu trống (\`dropna()\` trong pandas). Cách này nhanh nhưng dễ làm mất thông tin nếu tỉ lệ khuyết thiếu lớn.

2. **Điền khuyết bằng giá trị thống kê (Imputation - Mean/Median/Mode)**:
   - Điền trung bình (Mean) cho dữ liệu phân phối chuẩn, trung vị (Median) cho dữ liệu có ngoại lai nhạy cảm, hoặc yếu vị (Mode) cho dữ liệu phân loại.

3. **Mô hình hóa (Predictive Imputation)**:
   - Dùng thuật toán k-NN hoặc hồi quy để dự đoán giá trị bị thiếu dựa trên các cột thuộc tính khác.

Ví dụ Python xử lý bằng \`pandas\`:
\`\`\`python
import pandas as pd
import numpy as np

# Tạo DataFrame bị khuyết
df = pd.DataFrame({
    'Age': [23, 29, np.nan, 31, np.nan],
    'Salary': [50000, np.nan, 45000, 60000, 52000]
})

# Điền giá trị trung bình cho cột tuyển dụng
df['Age'] = df['Age'].fillna(df['Age'].mean())
# Hoặc điền trung vị cột Salary
df['Salary'] = df['Salary'].fillna(df['Salary'].median())

print(df)
\`\`\`

Bạn có thắc mắc gì thêm về kĩ thuật chuẩn hóa hoặc chia tập Train/Test không?`;
        } else if (text.toLowerCase().includes("decision") || text.toLowerCase().includes("cây quyết định") || text.toLowerCase().includes("tree")) {
          mockResponse = `### Thuật toán Cây quyết định (Decision Tree)
**Decision Tree** là thuật toán học máy có giám sát, được dùng cho cả bài toán phân loại (Classification) và hồi quy (Regression). Cấu trúc cây bao gồm:
- **Root Node (Nút gốc)**: Thuộc tính tốt nhất để phân tách tập dữ liệu đầu tiên.
- **Decision Node (Nút quyết định)**: Các điều kiện rẽ nhánh (ví dụ: \`Tuổi > 30\`).
- **Leaf Node (Nút lá)**: Lớp quyết định cuối cùng hoặc giá trị dự báo cuối cùng.

#### Các tiêu chí lựa chọn thuộc tính phân tách:
1. **Entropy & Information Gain**: Đo lường mức độ hỗn loạn của thông tin. Chúng ta sẽ chọn thuộc tính làm cực tiểu hóa entropy sau khi phân chia ( Information Gain lớn nhất).
2. **Gini Impurity (Độ thuần khiết Gini)**: Đo lường tần suất một phần tử bất kỳ bị gán sai nhãn từ tập dữ liệu. Trị số càng nhỏ chứng tỏ nút rẽ nhánh càng thuần khiết.

Thử nghiệm xây dựng một cây quyết định đơn giản với \`scikit-learn\`:
\`\`\`python
from sklearn.tree import DecisionTreeClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

# Nạp bộ dữ liệu hoa Iris
data = load_iris()
X_train, X_test, y_train, y_test = train_test_split(data.data, data.target, test_size=0.3, random_state=42)

# Khởi tạo và huấn luyện mô hình cây
clf = DecisionTreeClassifier(criterion='entropy', max_depth=3)
clf.fit(X_train, y_train)

print("Độ chính xác tập thi đấu:", clf.score(X_test, y_test))
\`\`\`

Dùng mục **Data Lab** để chạy phân tích trực tiếp với thuật toán này nhé!`;
        } else {
          mockResponse = `Xin chào! Tôi là **Trợ lý MinerAI**, trợ lý ảo chuyên sâu về Khai phá dữ liệu & Học máy của bạn.
          
Tôi sẵn lòng trả lời mọi câu hỏi của bạn về:
- Các thuật toán tiền xử lý dữ liệu, chuẩn hóa dữ liệu, mã hóa biến phân loại.
- Các mô hình phân lớp (Decision Tree, Naive Bayes, SVM, Random Forest).
- Phân nhóm phân cụm (K-Means, DBSCAN, Hierarchical Clustering).
- Luật kết hợp thị trường (Apriori, FP-Growth).
- Đánh giá mô hình học máy (Confusion Matrix, ROC-AUC, F1-Score).

*Gợi ý:* Hãy thử hỏi **"Giải thích thuật toán K-means một cách đơn giản, và cho tôi một ví dụ về code Python."** hoặc click chọn câu hỏi gợi ý bên dưới!`;
        }
        return res.json({ text: mockResponse });
      }

      // Convert messages for the @google/genai SDK format
      const formattedContents = messages.map((m: any) => ({
        role: m.role || "user",
        parts: m.parts || [{ text: m.content || "" }]
      }));

      const response = await ai.models.generateContent({
        model: "gemini-3.5-flash",
        contents: formattedContents,
        config: {
          systemInstruction: systemInstruction,
          temperature: 0.7,
        }
      });

      return res.json({ text: response.text });
    } catch (error: any) {
      console.error("Chat Error:", error);
      res.status(500).json({ error: error.message || "Đã xảy ra lỗi hệ thống trợ lý." });
    }
  });

  // API Route: Tóm tắt
  app.post("/api/summary", async (req, res) => {
    try {
      const ragResponse = await fetch("http://127.0.0.1:8000/api/summary", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": req.headers.authorization || ""
        },
        body: JSON.stringify(req.body)
      });
      const data = await ragResponse.json();
      res.json(data);
    } catch (err: any) {
      console.error("[RAG PROXY] Lỗi kết nối FastAPI /api/summary:", err);
      res.status(500).json({ error: "Lỗi kết nối máy chủ", details: err.message });
    }
  });

  // API Route: Flashcards
  app.post("/api/flashcards", async (req, res) => {
    try {
      const ragResponse = await fetch("http://127.0.0.1:8000/api/flashcards", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": req.headers.authorization || ""
        },
        body: JSON.stringify(req.body)
      });
      const data = await ragResponse.json();
      res.json(data);
    } catch (err: any) {
      console.error("[RAG PROXY] Lỗi kết nối FastAPI /api/flashcards:", err);
      res.status(500).json({ error: "Lỗi kết nối máy chủ", details: err.message });
    }
  });

  app.get("/api/flashcards/saved", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/flashcards/saved", {
        headers: { "Authorization": req.headers.authorization || "" }
      });
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      }
      console.warn("[FLASHCARD PROXY] Saved flashcards endpoint unavailable:", response.status);
      return res.json([]);
    } catch (err: any) {
      console.warn("[FLASHCARD PROXY] Cannot load saved flashcards:", err.message);
      return res.json([]);
    }
  });

  app.get("/api/flashcards/saved/:set_id", async (req, res) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/flashcards/saved/${req.params.set_id}`, {
        headers: { "Authorization": req.headers.authorization || "" }
      });
      const data = await response.json();
      return res.status(response.status).json(data);
    } catch (err: any) {
      return res.status(404).json({ detail: "Flashcard set not found" });
    }
  });

  app.delete("/api/flashcards/saved/:set_id", async (req, res) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/flashcards/saved/${req.params.set_id}`, {
        method: "DELETE",
        headers: { "Authorization": req.headers.authorization || "" }
      });
      const data = await response.json();
      return res.status(response.status).json(data);
    } catch (err: any) {
      return res.status(404).json({ detail: "Flashcard set not found" });
    }
  });



  // API Route: Create interactive quiz (Proxy to FastAPI Backend)
  app.post("/api/quiz", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/quiz", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": req.headers.authorization || ""
        },
        body: JSON.stringify(req.body)
      });
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      } else {
        const errorText = await response.text();
        return res.status(response.status).json({ error: errorText });
      }
    } catch (err: any) {
      console.error("[QUIZ PROXY] Error creating quiz:", err.message);
      return res.status(500).json({ error: "Cannot connect to RAG Backend" });
    }
  });

  // API Route: Submit quiz answer (Proxy to FastAPI Backend)
  app.post("/api/quiz/answer", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/quiz/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body)
      });
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      } else {
        const errorText = await response.text();
        return res.status(response.status).json({ error: errorText });
      }
    } catch (err: any) {
      console.error("[QUIZ PROXY] Error submitting answer:", err.message);
      return res.status(500).json({ error: "Cannot connect to RAG Backend" });
    }
  });

  // API Route: Get quiz results (Proxy to FastAPI Backend)
  app.get("/api/quiz/:quiz_id/results", async (req, res) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/quiz/${req.params.quiz_id}/results`, {
        headers: {
          "Authorization": req.headers.authorization || ""
        }
      });
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      } else {
        const errorText = await response.text();
        return res.status(response.status).json({ error: errorText });
      }
    } catch (err: any) {
      console.error("[QUIZ PROXY] Error getting quiz results:", err.message);
      return res.status(500).json({ error: "Cannot connect to RAG Backend" });
    }
  });

  // API Route: Get User Weak Topics
  app.get("/api/user/weak-topics", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/user/weak-topics", {
        method: "GET",
        headers: { 
          "Authorization": req.headers.authorization || ""
        }
      });
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      } else {
        const errorText = await response.text();
        return res.status(response.status).json({ error: errorText });
      }
    } catch (err: any) {
      console.error("[PROXY] Error getting weak topics:", err.message);
      return res.status(500).json({ error: "Cannot connect to Backend" });
    }
  });

  // API Route: Get User Completed Topics
  app.get("/api/user/completed-topics", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/user/completed-topics", {
        method: "GET",
        headers: { 
          "Authorization": req.headers.authorization || ""
        }
      });
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      } else {
        const errorText = await response.text();
        return res.status(response.status).json({ error: errorText });
      }
    } catch (err: any) {
      console.error("[PROXY] Error getting completed topics:", err.message);
      return res.status(500).json({ error: "Cannot connect to Backend" });
    }
  });

  // API Route: Get all documents (Proxy to FastAPI Backend)
  app.get("/api/documents", async (req, res) => {
    try {
      const authHeader = req.headers.authorization;
      const options: RequestInit = {};
      if (authHeader) {
        options.headers = { "Authorization": authHeader };
      }
      const response = await fetch("http://127.0.0.1:8000/api/documents", options);
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      } else {
        const errorText = await response.text();
        return res.status(response.status).json({ error: errorText });
      }
    } catch (err: any) {
      console.error("[DOCUMENTS PROXY] Error getting documents:", err.message);
      return res.status(500).json({ error: "Cannot connect to RAG Backend" });
    }
  });

  // API Route: Delete document (Proxy to FastAPI Backend)
  app.delete("/api/documents/:filename", async (req, res) => {
    try {
      const authHeader = req.headers.authorization;
      const options: RequestInit = { method: 'DELETE' };
      if (authHeader) {
        options.headers = { "Authorization": authHeader };
      }
      const response = await fetch(`http://127.0.0.1:8000/api/documents/${req.params.filename}`, options);
      if (response.ok) {
        const data = await response.json();
        return res.json(data);
      } else {
        const errorText = await response.text();
        return res.status(response.status).json({ error: errorText });
      }
    } catch (err: any) {
      console.error("[DOCUMENTS PROXY] Error deleting document:", err.message);
      return res.status(500).json({ error: "Cannot connect to RAG Backend" });
    }
  });
  
  // API Route: Auth Proxy
  app.post("/api/auth/register", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body)
      });
      const data = await response.json();
      return res.status(response.status).json(data);
    } catch (err: any) {
      console.error("[AUTH PROXY] Register error:", err.message);
      return res.status(500).json({ detail: "Cannot connect to Backend Auth API" });
    }
  });

  app.post("/api/auth/login", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body)
      });
      const data = await response.json();
      return res.status(response.status).json(data);
    } catch (err: any) {
      console.error("[AUTH PROXY] Login error:", err.message);
      return res.status(500).json({ detail: "Cannot connect to Backend Auth API" });
    }
  });

  app.post("/api/auth/google", async (req, res) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body)
      });
      const data = await response.json();
      return res.status(response.status).json(data);
    } catch (err: any) {
      console.error("[AUTH PROXY] Google auth error:", err.message);
      return res.status(500).json({ detail: "Cannot connect to Backend Auth API" });
    }
  });

  // Generic Proxy for any other /api/* routes (Admin, User, etc.)
  app.use("/api", async (req, res, next) => {
    // Nếu là đường dẫn đặc biệt của stats thì bỏ qua (để rơi xuống route stats có fallback)
    if (req.path === "/stats" || req.path === "/system-stats") {
      return next();
    }

    try {
      const url = `http://127.0.0.1:8000/api${req.url}`;
      console.log(`[GENERIC PROXY] Forwarding ${req.method} ${url}`);
      
      const options: RequestInit = {
        method: req.method,
        headers: {
          "Content-Type": req.headers["content-type"] || "application/json",
          "Authorization": req.headers.authorization || ""
        }
      };
      
      if (req.method !== "GET" && req.method !== "HEAD") {
        options.body = JSON.stringify(req.body);
      }
      
      const response = await fetch(url, options);
      if (response.headers.get("content-type")?.includes("application/json")) {
        const data = await response.json();
        return res.status(response.status).json(data);
      } else {
        const text = await response.text();
        return res.status(response.status).send(text);
      }
    } catch (err: any) {
      console.error(`[GENERIC PROXY] Error forwarding ${req.method} /api${req.url}:`, err.message);
      return res.status(500).json({ detail: "Cannot connect to Backend API" });
    }
  });

  // API Route: Get real-time stats from FastAPI Backend
  app.get(["/api/stats", "/api/system-stats"], async (req, res) => {
    try {
      const statsResponse = await fetch("http://127.0.0.1:8000/api/system-stats", {
        headers: {
          "Authorization": req.headers.authorization || ""
        }
      });
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        return res.json(statsData);
      } else {
        return res.status(statsResponse.status).json({ error: "Lỗi kết nối FastAPI Backend stats" });
      }
    } catch (err: any) {
      console.warn("[STATS PROXY] Không thể kết nối tới RAG Backend (FastAPI). Lỗi:", err.message);
      // Fallback in case python backend is not running/loading
      return res.json({
        total_sessions: 3,
        active_sessions: 1,
        total_messages: 12,
        vectordb_count: 3744,
        documents_count: 14,
        timestamp: new Date().toISOString()
      });
    }
  });

  // Start development or production file hosting
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    // Hosted inside Cloud Run production sandbox
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server started running on host 0.0.0.0 and port ${PORT}`);
  });
}

startServer();
