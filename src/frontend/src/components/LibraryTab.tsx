import React, { useState, useEffect } from "react";
import { Search, Play, Download, FileText, Database, ArrowRight, ExternalLink, X, Film, Check, UploadCloud, Loader2, Trash2 } from "lucide-react";
import { LibraryItem } from "../types";
import { defaultLibraryItems } from "../data";
import { I18nKey } from "../i18n";
import { getAuthItem } from "../authStorage";

interface LibraryTabProps {
  onLoadDatasetToLab: (fileName: string, fileSize: string, fileContent: string) => void;
  t: I18nKey;
}

export default function LibraryTab({ onLoadDatasetToLab, t }: LibraryTabProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<"all" | "video" | "pdf" | "dataset">("all");
  const [selectedItem, setSelectedItem] = useState<LibraryItem | null>(null);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [downloadSuccessItem, setDownloadSuccessItem] = useState<string | null>(null);
  const [libraryItems, setLibraryItems] = useState<LibraryItem[]>([]);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  
  // Upload States
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState("");

  // Fetch library documents
  const fetchDocuments = async () => {
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch("/api/documents", {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        if (data.documents) {
          setLibraryItems(data.documents);
        }
      }
    } catch (err) {
      console.error("Failed to fetch documents", err);
    }
  };

  const handleDeleteDocument = async (filename: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering card clicks
    if (!confirm(isVi ? `Bạn có chắc muốn xóa tệp "${filename}" khỏi hệ thống không? Dữ liệu AI tương ứng cũng sẽ bị xóa.` : `Are you sure you want to delete "${filename}"? AI data will also be deleted.`)) {
      return;
    }
    
    setIsDeleting(filename);
    try {
      const token = getAuthItem("minerai_token");
      const res = await fetch(`/api/documents/${encodeURIComponent(filename)}`, { 
        method: 'DELETE',
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });
      if (res.ok) {
        fetchDocuments(); // Reload list after delete
      } else {
        alert(isVi ? "Lỗi khi xóa tệp!" : "Error deleting file!");
      }
    } catch (err) {
      console.error("Error deleting document", err);
      alert(isVi ? "Lỗi kết nối khi xóa tệp!" : "Connection error when deleting file!");
    } finally {
      setIsDeleting(null);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Group counts
  const totalCount = libraryItems.length;
  const videoCount = libraryItems.filter((i) => i.type === "video").length;
  const pdfCount = libraryItems.filter((i) => i.type === "pdf").length;
  const datasetCount = libraryItems.filter((i) => i.type === "dataset").length;

  const isVi = t.statUnit.docs === "tệp";
  const categories = [
    { id: "all",     label: isVi ? "Tất cả" : "All",              count: totalCount },
    { id: "video",   label: isVi ? "Video bài giảng" : "Lecture Videos", count: videoCount },
    { id: "pdf",     label: isVi ? "Tài liệu PDF" : "PDF Documents", count: pdfCount },
    { id: "dataset", label: isVi ? "Bộ dữ liệu thực hành" : "Practice Datasets", count: datasetCount }
  ];

  // Perform search and category filtering
  const filteredItems = libraryItems.filter((item) => {
    const matchesSearch =
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = activeCategory === "all" || item.type === activeCategory;
    return matchesSearch && matchesCategory;
  });

  const handleActionClick = (item: LibraryItem) => {
    setSelectedItem(item);
    if (item.type === "video") {
      setShowVideoModal(true);
    } else if (item.type === "pdf") {
      // PDF download effect
      setDownloadSuccessItem(item.id);
      setTimeout(() => setDownloadSuccessItem(null), 3000);
    }
  };

  const handleLoadToLabAndRedirect = (item: LibraryItem) => {
    // Inject mock content matching the dataset selected
    let content = "Column1,Column2,Column3\nVal1,Val2,Val3";
    if (item.title.includes("E-commerce")) {
      content = "Mã_Hóa_Đơn,Bỉm,Sữa,Bia,Bánh_Mì,Bơ\nINV001,1,0,1,0,1\nINV002,0,1,0,1,1\nINV003,1,1,1,1,0";
    }

    onLoadDatasetToLab(
      item.title + ".csv",
      item.rows || "150K rows",
      content
    );
    setSelectedItem(null);
  };

  // Upload Handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processFileUpload(e.dataTransfer.files[0]);
    }
  };
  
  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      e.target.value = ""; // Clear value to allow re-upload of same deleted file
      await processFileUpload(file);
    }
  };
  
  const processFileUpload = async (file: File) => {
    const validTypes = [".pdf", ".pptx", ".docx", ".txt"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    
    if (!validTypes.includes(ext)) {
      alert(isVi ? "Chỉ hỗ trợ file PDF, PPTX, DOCX, TXT!" : "Only PDF, PPTX, DOCX, TXT supported!");
      return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
      alert(isVi ? "Kích thước file vượt quá 50MB!" : "File size exceeds 50MB!");
      return;
    }
    
    setIsUploading(true);
    setUploadProgress(10);
    setUploadStatus(isVi ? "Đang tải lên server..." : "Uploading to server...");
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      // Simulate progress while waiting for real response
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            setUploadStatus(isVi ? "Đang xử lý tài liệu & nhúng Vector..." : "Processing document & embedding...");
            return 90;
          }
          return prev + 10;
        });
      }, 500);
      const token = getAuthItem("minerai_token");
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      const response = await fetch("/api/upload", {
        method: "POST",
        headers,
        body: formData,
      });
      
      clearInterval(interval);
      setUploadProgress(100);
      
      if (!response.ok) {
        let message = isVi ? "Không thể xử lý tài liệu." : "Unable to process document.";
        try {
          const errorData = await response.json();
          message = errorData.detail || errorData.message || message;
        } catch {
          message = await response.text();
        }
        throw new Error(message);
      }
      
      const data = await response.json();
      if (!data.chunks_added || data.chunks_added <= 0) {
        throw new Error(
          isVi
            ? "Tài liệu đã tải lên nhưng không tạo được chunk nào. Vui lòng kiểm tra nội dung file."
            : "The document uploaded but no chunks were created. Please check the file content."
        );
      }
      setUploadStatus(isVi ? `Thành công! Đã tạo ${data.chunks_added} chunks.` : `Success! Created ${data.chunks_added} chunks.`);
      
      // Load lại danh sách ngay lập tức sau khi upload thành công để hiển thị lên đầu
      fetchDocuments();
      
      // Khôi phục UI sau 3s
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setUploadStatus("");
      }, 3000);
      
    } catch (error) {
      console.error("Upload error:", error);
      setUploadStatus(isVi ? "Lỗi khi tải lên hoặc xử lý tài liệu!" : "Error uploading or processing document!");
      if (error instanceof Error && error.message) {
        setUploadStatus(error.message);
      }
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setUploadStatus("");
      }, 3000);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 animate-fade-in">
      {/* Title block & Search banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[#0b1c3c] tracking-tight font-display">{t.libraryTitle}</h2>
          <p className="text-gray-500 mt-1.5 text-sm font-medium">{t.librarySubtitle}</p>
        </div>

        {/* Big Search box matching layout */}
        <div className="relative w-full max-w-md">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={isVi ? "Tìm kiếm tài liệu..." : "Search documents..."}
            className="w-full pl-10 pr-4 py-3 border border-[#cbd5e1] rounded-xl text-xs bg-white text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-[#0ea5e9] shadow-sm font-sans"
          />
          <Search size={16} className="absolute left-3.5 top-3.5 text-gray-400" />
        </div>
      </div>

      {/* Upload Zone */}
      <div 
        className={`w-full border-2 border-dashed rounded-xl p-6 text-center transition-all duration-300 ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50/50'} ${isUploading ? 'pointer-events-none' : 'cursor-pointer hover:bg-gray-50'}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById("file-upload")?.click()}
      >
        <input type="file" id="file-upload" className="hidden" accept=".pdf,.pptx,.docx,.txt" onChange={handleFileInput} />
        
        {isUploading ? (
          <div className="space-y-4">
            <div className="flex justify-center">
              <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
            </div>
            <h3 className="text-lg font-semibold text-gray-800 font-display">{uploadStatus}</h3>
            <div className="w-full max-w-md mx-auto bg-gray-200 rounded-full h-2 overflow-hidden">
              <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto transition-transform hover:scale-110 duration-300">
              <UploadCloud size={32} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-[#0b1c3c] font-display">
                {isVi ? "Thêm tài liệu mới vào cơ sở tri thức (RAG)" : "Add new document to knowledge base (RAG)"}
              </h3>
              <p className="text-sm text-gray-500 mt-1">
                {isVi ? "Kéo thả tài liệu vào đây (Hỗ trợ PDF, PPTX, DOCX, TXT. Tối đa 50MB)." : "Drag and drop here (Supports PDF, PPTX, DOCX, TXT. Max 50MB)."}
              </p>
            </div>
            <button className="px-5 py-2.5 bg-white border border-gray-300 shadow-sm rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors">
              {isVi ? "Chọn tập tin" : "Browse files"}
            </button>
          </div>
        )}
      </div>

      {/* Grid divided Category sidebar (1/4) + Resource cards (3/4) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        
        {/* Category Menu side list */}
        <aside className="md:col-span-3 space-y-4">
          <h3 className="text-[10px] font-bold text-[#94a3b8] tracking-wider uppercase pl-2">DANH MỤC</h3>
          <nav className="flex flex-col gap-1">
            {categories.map((cat) => {
              const isActive = activeCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id as any)}
                  className={`w-full py-2.5 px-3 rounded-lg text-left font-sans text-xs font-semibold flex items-center justify-between transition-all cursor-pointer ${
                    isActive
                      ? "bg-[#dbeafe] text-[#0b1c3c]"
                      : "text-gray-500 hover:bg-slate-100 hover:text-gray-800"
                  }`}
                >
                  <span>{cat.label}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    isActive ? "bg-white text-[#0b1c3c] border border-blue-100" : "bg-gray-100 text-gray-400"
                  }`}>
                    {cat.count}
                  </span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Resources Grid Column */}
        <main className="md:col-span-9">
          <div className="flex flex-col gap-4">
            {[...filteredItems]
              .sort((a, b) => {
                // Group by user files first (is_public: false comes first)
                if (a.is_public !== b.is_public) {
                  return a.is_public ? 1 : -1;
                }
                // Then sort by mtime descending (newest first)
                return (b.mtime || 0) - (a.mtime || 0);
              })
              .map((item) => (
              <div
                key={item.id}
                className="bg-white rounded-xl border border-[#e2e8f0] p-4 hover:border-gray-300 transition-all shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {/* Icon badge based on file type */}
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 bg-slate-50 border border-slate-100 text-slate-600">
                    {item.type === "video" && <Film className="w-5 h-5 text-blue-600" />}
                    {item.type === "pdf" && <FileText className="w-5 h-5 text-emerald-600" />}
                    {item.type === "dataset" && <Database className="w-5 h-5 text-amber-600" />}
                  </div>

                  {/* Title & Description */}
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-sm font-bold text-gray-900 group-hover:text-blue-900 transition-colors leading-snug">
                        {item.title}
                      </h4>
                      <span className="text-[10px] text-gray-400 font-bold font-mono">
                        {item.duration && `• ${item.duration}`}
                        {item.size && `• ${item.size}`}
                        {item.rows && `• CSV • ${item.rows}`}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 leading-normal line-clamp-1">
                      {item.description}
                    </p>
                  </div>
                </div>

                {/* Actions & Delete Button */}
                <div className="flex items-center justify-end gap-2.5 flex-shrink-0 pl-16 sm:pl-0">
                  {item.type === "dataset" && (
                    <button
                      onClick={() => setSelectedItem(item)}
                      className="px-4 py-2 bg-[#7a1c1c] hover:bg-[#601414] text-white rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-sm active:scale-95"
                    >
                      {isVi ? "Nạp Lab" : "Load Lab"}
                    </button>
                  )}
                  
                  {item.type === "video" && (
                    <button
                      onClick={() => handleActionClick(item)}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer shadow-sm flex items-center gap-1.5 active:scale-95"
                    >
                      <Play size={12} className="fill-current" /> {isVi ? "Mở video" : "Open Video"}
                    </button>
                  )}

                  {/* Delete Button (Chỉ dành cho tài liệu do người dùng tải lên, tức là không phải is_public) */}
                  {!item.is_public && (
                    <button
                      onClick={(e) => handleDeleteDocument(item.filename || item.title, e)}
                      disabled={isDeleting === (item.filename || item.title)}
                      className="p-2 hover:bg-red-50 text-gray-400 hover:text-red-600 border border-slate-100 hover:border-red-150 rounded-lg shadow-sm transition-all"
                      title={isVi ? "Xóa tài liệu" : "Delete document"}
                    >
                      {isDeleting === (item.filename || item.title) ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {filteredItems.length === 0 && (
            <div className="text-center py-20 bg-slate-50 border rounded-xl border-[#e2e8f0] p-6 text-gray-400">
              {isVi ? "Không tìm thấy tài liệu phù hợp." : "No documents found matching your search."}
            </div>
          )}
        </main>
      </div>

      {/* Video Lecture Modal simulating tutorial play */}
      {showVideoModal && selectedItem && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-[99] animate-fade-in">
          <div className="bg-slate-950 text-white rounded-2xl overflow-hidden border border-slate-800 w-full max-w-2xl shadow-2xl relative animate-scale-up">
            <button
              onClick={() => {
                setShowVideoModal(false);
                setSelectedItem(null);
              }}
              className="absolute top-4 right-4 p-1.5 bg-black/40 hover:bg-white/10 rounded-full text-[#94a3b8] hover:text-white transition-colors cursor-pointer z-[100]"
            >
              <X size={18} />
            </button>

            {/* Video container simulating custom class */}
            <div className="relative aspect-video bg-black flex items-center justify-center">
              <div className="p-6 text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-blue-600/20 border-2 border-blue-500/80 flex items-center justify-center text-blue-500 mx-auto animate-pulse">
                  <Play size={24} className="fill-current ml-1" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Đang tải luồng Video Học Tập chất lượng cao...</h3>
                  <p className="text-[10px] text-gray-400 mt-1">Bài giảng: {selectedItem.title}</p>
                </div>
              </div>
            </div>

            {/* Title description inside Video frame */}
            <div className="p-6 bg-[#0f172a] space-y-2">
              <span className="px-2 py-0.5 bg-blue-900/60 text-blue-300 rounded text-[9px] font-bold uppercase tracking-wider">
                Video Lesson • {selectedItem.duration}
              </span>
              <h4 className="text-sm font-semibold">{selectedItem.title}</h4>
              <p className="text-xs text-gray-400/90 leading-relaxed font-sans">{selectedItem.description}</p>
            </div>
          </div>
        </div>
      )}

      {/* Dataset info details modal offering direct loading into Lab */}
      {selectedItem && selectedItem.type === "dataset" && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-[99] animate-fade-in">
          <div className="bg-white text-gray-800 rounded-2xl overflow-hidden border border-gray-150 w-full max-w-md shadow-2xl animate-scale-up">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/40">
              <h3 className="font-bold text-sm text-[#0b1c3c] font-display">Chi tiết tệp dữ liệu</h3>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-full cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="p-4 bg-rose-50 text-indigo-800 rounded-xl flex items-center gap-3">
                <Database className="text-[#7a1c1c] flex-shrink-0" size={20} />
                <div>
                  <p className="text-xs font-bold leading-none">{selectedItem.title}</p>
                  <p className="text-[9px] text-[#7a1c1c] font-semibold font-mono mt-1">Sẵn sàng để đưa vào thực nghiệm</p>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <p className="text-[11px] text-gray-400 font-medium">Mô tả tập tin:</p>
                <p className="text-xs text-slate-800 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                  {selectedItem.description}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 font-mono text-[11px] bg-slate-50/50 p-2.5 rounded-lg text-gray-500">
                <div>Định dạng: <strong className="text-slate-800 font-sans">CSV Standard</strong></div>
                <div>Kích thước: <strong className="text-slate-800 font-sans">{selectedItem.rows}</strong></div>
              </div>
            </div>

            <div className="p-4 bg-slate-50/60 border-t border-gray-100 flex gap-2 justify-end">
              <button
                onClick={() => setSelectedItem(null)}
                className="px-4 py-2 text-xs underline font-semibold text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                Đóng
              </button>

              <button
                onClick={() => handleLoadToLabAndRedirect(selectedItem)}
                className="px-4 py-2 bg-[#7a1c1c] hover:bg-[#7a1c1c] text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer shadow"
              >
                Nạp tệp vào Data Lab <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
