"""
QA Test Suite — 30 câu hỏi kiểm thử dựa trên DOCX thực tế.
Ground truth lấy trực tiếp từ:
  - 220269_ Khai pha du lieu - AI.docx  (Table 5,6,10 + paragraphs)
  - thuattoanpython.docx

Kết quả mỗi câu:
  PASS      — hệ thống trả lời đúng, có citation
  FAIL      — đáp án có trong tài liệu nhưng hệ thống không tìm thấy
  HALLUCINATION — đáp án KHÔNG có trong tài liệu nhưng hệ thống vẫn 