// hooks/useCurrentUser.ts
// Đọc thông tin người dùng đang đăng nhập từ localStorage
// Backend lưu user info vào key "minerai_user" sau khi login thành công

import { useState, useEffect } from "react";
import { getAuthItem } from "../authStorage";

export interface CurrentUser {
  full_name: string;
  username: string;
  email: string;
  user_id?: string;
}

// Tên user mặc định khi chưa đăng nhập (hard-code từ SettingsTab)
const FALLBACK_USER: CurrentUser = {
  full_name: "Kiên Thị Bé Hai",
  username: "110122218",
  email: "110122218@student.tvu.edu.vn",
};

function readUserFromStorage(): CurrentUser {
  try {
    // Thử đọc từ "minerai_user" (được backend lưu khi login)
    const raw = getAuthItem("minerai_user");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && (parsed.full_name || parsed.username)) {
        return parsed as CurrentUser;
      }
    }
    // Thử đọc từ "minerai_token" rồi decode JWT lấy email
    const token = getAuthItem("minerai_token");
    if (token) {
      // Decode JWT payload (không verify, chỉ đọc claims)
      const parts = token.split(".");
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        if (payload.email) {
          return {
            full_name: payload.full_name || payload.username || payload.email,
            username: payload.username || payload.email,
            email: payload.email,
            user_id: payload.user_id,
          };
        }
      }
    }
  } catch {
    // ignore parse errors
  }
  return FALLBACK_USER;
}

export function useCurrentUser() {
  const [user, setUser] = useState<CurrentUser>(readUserFromStorage);

  useEffect(() => {
    // Lắng nghe sự thay đổi storage (khi tab khác đăng nhập/xuất)
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "minerai_user" || e.key === "minerai_token") {
        setUser(readUserFromStorage());
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return user;
}
