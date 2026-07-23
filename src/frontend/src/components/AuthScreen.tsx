import React, { useState, useEffect, useRef } from "react";
import { Mail, Lock, User, UserCircle } from "lucide-react";
import logo from "../assets/logo.png";
import { recordLoginEvent, saveAuthSession } from "../authStorage";

interface AuthScreenProps {
  onLogin: (token: string, userData: any) => void;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (
            element: HTMLElement | null,
            options: { theme: string; size: string; text: string; shape: string; width?: string }
          ) => void;
        };
      };
    };
  }
}

export default function AuthScreen({ onLogin }: AuthScreenProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [rememberLogin, setRememberLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const googleButtonRef = useRef<HTMLDivElement>(null);

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

  useEffect(() => {
    if (!clientId) return;

    const initGoogle = () => {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: handleGoogleCredential,
        });
        if (googleButtonRef.current) {
          window.google.accounts.id.renderButton(googleButtonRef.current, {
            theme: "outline",
            size: "large",
            text: "signin_with",
            shape: "rectangular",
            width: "360",
          });
        }
      }
    };

    if (window.google?.accounts?.id) {
      initGoogle();
    } else if (!document.querySelector('script[src="https://accounts.google.com/gsi/client"]')) {
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = initGoogle;
      document.body.appendChild(script);
    }
  }, [clientId]);

  const handleGoogleCredential = async (response: { credential: string }) => {
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Đăng nhập Google thất bại");
      }

      saveAuthSession(data.token, data.user, rememberLogin);
      recordLoginEvent(data.user);
      onLogin(data.token, data.user);
    } catch (err: any) {
      setError(err.message || "Đã xảy ra lỗi xác thực Google");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const endpoint = isLogin
        ? "/api/auth/login"
        : "/api/auth/register";

      const payload = isLogin
        ? { email, password }
        : { email, username, password, full_name: fullName };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const text = await res.text();
      let data: any = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (e) {
        console.error("Lỗi parse JSON:", text);
      }

      if (!res.ok) {
        let errorMsg = "Xác thực thất bại";
        if (Array.isArray(data?.detail)) {
          errorMsg = data.detail.map((e: any) => `${e.loc?.join('.')} : ${e.msg}`).join(', ');
        } else if (data?.detail) {
          errorMsg = data.detail;
        } else if (data?.message) {
          errorMsg = data.message;
        } else {
          errorMsg = text || "Lỗi server";
        }
        throw new Error(errorMsg);
      }

      if (isLogin) {
        saveAuthSession(data.token, data.user, rememberLogin);
        recordLoginEvent(data.user);
        onLogin(data.token, data.user);
      } else {
        setIsLogin(true);
        setError("Đăng ký thành công! Vui lòng đăng nhập.");
      }
    } catch (err: any) {
      setError(err.message || "Đã xảy ra lỗi hệ thống.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-rose-50 to-rose-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        {/* Branding */}
        <div className="flex flex-col items-center mb-8">
          <img src={logo} alt="MinerAI Logo" className="w-16 h-16 object-contain mb-4" />
          <h1 className="text-2xl font-display font-semibold text-slate-900 tracking-tighter">MinerAI</h1>
          <p className="text-[#7a1c1c] mt-1.5 text-base font-medium">Học cùng bạn</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-slate-800">
              {isLogin ? "Chào mừng trở lại" : "Tạo tài khoản mới"}
            </h2>
            <p className="text-slate-500 mt-2">
              {isLogin
                ? "Hãy tiếp tục hành trình học tập của bạn"
                : "Bắt đầu hành trình khai phá tri thức cùng MinerAI"}
            </p>
          </div>

          {error && (
            <div className={`p-4 rounded-2xl text-sm mb-6 flex items-start gap-3 ${error.includes("thành công")
                ? "bg-rose-50 text-[#7a1c1c] border border-rose-100"
                : "bg-rose-50 text-rose-700 border border-rose-100"
              }`}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {!isLogin && (
              <>
                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-1.5">Họ và tên</label>
                  <div className="relative">
                    <UserCircle className="absolute left-3.5 top-2.5 text-slate-400" size={18} />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-rose-100 transition-all text-sm placeholder:text-slate-400"
                      placeholder="Nguyễn Văn A"
                      required={!isLogin}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-600 mb-1.5">Tên đăng nhập</label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-2.5 text-slate-400" size={18} />
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-rose-100 transition-all text-sm placeholder:text-slate-400"
                      placeholder="nguyenvana"
                      required={!isLogin}
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Email sinh viên</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-2.5 text-slate-400" size={18} />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-rose-100 transition-all text-sm placeholder:text-slate-400"
                  placeholder="sv@tvu.edu.vn"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Mật khẩu</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-2.5 text-slate-400" size={18} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-rose-100 transition-all text-sm placeholder:text-slate-400"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 bg-rose-900 hover:bg-[#4d2f2f] disabled:bg-slate-300 text-white rounded-xl font-medium text-base shadow-md shadow-[#7a1c1c]/20 transition-all active:scale-[0.98] flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Đang xử lý...
                </div>
              ) : isLogin ? (
                "Đăng nhập"
              ) : (
                "Tạo tài khoản"
              )}
            </button>
          </form>

          {/* Google Sign-In */}
          {clientId && (
            <div className="mt-6">
              <div className="relative mb-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200"></div>
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-white px-4 text-slate-400">hoặc tiếp tục với</span>
                </div>
              </div>
              <div ref={googleButtonRef} className="flex justify-center min-h-[44px]"></div>
            </div>
          )}

          <div className="mt-8 text-center">
            <button
              onClick={() => {
                setIsLogin(!isLogin);
                setError("");
              }}
              className="text-[#7a1c1c] hover:text-[#7a1c1c] font-medium transition-colors"
            >
              {isLogin
                ? "Chưa có tài khoản? Đăng ký ngay"
                : "Đã có tài khoản? Đăng nhập"}
            </button>
          </div>
        </div>

        <div className="text-center text-xs text-slate-400 mt-8">
          &copy; 2026 MinerAI &bull; Trợ lý học tập thông minh
        </div>
      </div>
    </div>
  );
}
