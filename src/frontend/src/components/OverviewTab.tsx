import { useEffect, useState } from "react";
import {
  ArrowRight,
  Play,
  Sparkles,
  MessageSquare,
  Clock,
  MousePointerClick,
  LogIn,
  Users,
  UserCheck,
  ShieldCheck,
  Activity,
  RefreshCw,
} from "lucide-react";
import { defaultProgress } from "../data";
import { I18nKey } from "../i18n";
import { getAuthItem, getLocalLoginEvents, getLocalRecentLessons } from "../authStorage";
interface OverviewTabProps {
  onNavigateToLibrary: () => void;
  onNavigateToMentor: () => void;
  onPlayLesson: (lessonName: string) => void;
  t: I18nKey;
}

type MetricId = "online" | "active" | "login";
type PeriodId = "week" | "month" | "year";
type ChartPoint = { day: string; val: number };
type RecentLesson = {
  id: string;
  title: string;
  subtitle: string;
  topic: string;
  score: number;
  max_score: number;
  percentage: number;
  grade?: string;
  answered_questions: number;
  total_questions: number;
  created_at?: string;
};
type AdminUserSummary = {
  total_users: number;
  online_count: number;
  active_count: number;
  admin_count: number;
  regular_count: number;
};

const courseProgressTopics = [
  { id: "apriori", title: "Apriori" },
  { id: "fp_growth", title: "FP-Growth" },
  { id: "kmeans", title: "K-Means" },
  { id: "dbscan", title: "DBSCAN" },
  { id: "ly_thuyet_25", title: "Giữa kỳ lý thuyết" },
  { id: "cuoi_ky_50", title: "Cuối kỳ lý thuyết" },
  { id: "code_thuc_hanh", title: "Thực hành Python" },
];

const emptyWeek: ChartPoint[] = [
  { day: "T2", val: 0 },
  { day: "T3", val: 0 },
  { day: "T4", val: 0 },
  { day: "T5", val: 0 },
  { day: "T6", val: 0 },
  { day: "T7", val: 0 },
  { day: "CN", val: 0 },
];
const emptyMonth: ChartPoint[] = [
  { day: "Tuần 1", val: 0 },
  { day: "Tuần 2", val: 0 },
  { day: "Tuần 3", val: 0 },
  { day: "Tuần 4", val: 0 },
];
const emptyYear: ChartPoint[] = [
  { day: "Th1", val: 0 },
  { day: "Th2", val: 0 },
  { day: "Th3", val: 0 },
  { day: "Th4", val: 0 },
  { day: "Th5", val: 0 },
  { day: "Th6", val: 0 },
  { day: "Th7", val: 0 },
  { day: "Th8", val: 0 },
  { day: "Th9", val: 0 },
  { day: "Th10", val: 0 },
  { day: "Th11", val: 0 },
  { day: "Th12", val: 0 },
];

export default function OverviewTab({ onNavigateToLibrary, onNavigateToMentor, onPlayLesson, t }: OverviewTabProps) {
  const [stats, setStats] = useState<any>(null);
  const [weakTopics, setWeakTopics] = useState<string[]>([]);
  const [completedTopics, setCompletedTopics] = useState<string[]>([]);
  const [recentLessons, setRecentLessons] = useState<RecentLesson[]>([]);
  const [adminUserSummary, setAdminUserSummary] = useState<AdminUserSummary | null>(null);
  const [isAdminUser, setIsAdminUser] = useState(false);
  const [activeMetric, setActiveMetric] = useState<MetricId>("online");
  const [activePeriod, setActivePeriod] = useState<PeriodId>("week");
  const [recentUsers, setRecentUsers] = useState<any[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);

  const fetchUserSummary = async () => {
    const token = getAuthItem("minerai_token");
    if (!token) return;
    setLoadingUsers(true);
    try {
      const res = await fetch("/api/admin/users/summary", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setAdminUserSummary(data.summary);
        setRecentUsers(data.recent_users || []);
      }
    } catch (err) {
      console.error("Error fetching users summary:", err);
    } finally {
      setLoadingUsers(false);
    }
  };

  const formatUserDate = (value?: string) => {
    if (!value) return "Chưa có";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Chưa có";
    return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
  };

  useEffect(() => {
    const token = getAuthItem("minerai_token");
    let currentUser: any = null;
    try {
      const rawUser = getAuthItem("minerai_user");
      currentUser = rawUser ? JSON.parse(rawUser) : null;
    } catch {
      currentUser = null;
    }
    const isAdmin = currentUser?.role === "admin";
    setIsAdminUser(isAdmin);
    const headers: HeadersInit = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const mergeRecentLessons = (serverLessons: RecentLesson[] = []) => {
      const merged = [...serverLessons, ...getLocalRecentLessons()];
      const seen = new Set<string>();
      return merged
        .filter((lesson) => {
          const key = lesson.id || `${lesson.title}-${lesson.created_at}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .sort((a, b) => new Date(b.created_at || "").getTime() - new Date(a.created_at || "").getTime())
        .slice(0, 4);
    };

    setRecentLessons(mergeRecentLessons());

    fetch("/api/system-stats", { headers })
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch((err) => console.error("Lỗi khi tải thông số stats:", err));

    if (token) {
      fetch("/api/user/weak-topics", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.weak_topics) {
            setWeakTopics(data.weak_topics);
          }
        })
        .catch((err) => console.error("Lỗi khi tải weak topics:", err));
      fetch("/api/user/completed-topics", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.completed_topics) {
            setCompletedTopics(data.completed_topics);
          }
        })
        .catch((err) => console.error("Error loading completed topics:", err));
      fetch("/api/user/recent-lessons?limit=4", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          if (Array.isArray(data.lessons)) {
            setRecentLessons(mergeRecentLessons(data.lessons));
          }
      })
        .catch((err) => console.error("Error loading recent lessons:", err));
      if (isAdmin) {
        fetchUserSummary();
        const summaryTimer = window.setInterval(fetchUserSummary, 30000);
        return () => window.clearInterval(summaryTimer);
      }
    }
  }, []);

  const normalizeTopic = (value: string) => value.toLowerCase().replace(/[-\s]+/g, "_");
  const completedTopicSet = new Set(completedTopics.map(normalizeTopic));
  const completedCourseTopics = courseProgressTopics.filter((topic) => {
    const normalizedId = normalizeTopic(topic.id);
    const normalizedTitle = normalizeTopic(topic.title);
    return completedTopicSet.has(normalizedId) || completedTopicSet.has(normalizedTitle);
  });
  const courseProgressPercent = Math.round((completedCourseTopics.length / courseProgressTopics.length) * 100);
  const nextCourseTopic = courseProgressTopics.find((topic) => !completedCourseTopics.some((done) => done.id === topic.id));
  const emptyByPeriod = { week: emptyWeek, month: emptyMonth, year: emptyYear };
  const dataKey = {
    online: {
      week: "online_hours_week",
      month: "online_hours_month",
      year: "online_hours_year",
    },
    active: {
      week: "active_ops_week",
      month: "active_ops_month",
      year: "active_ops_year",
    },
    login: {
      week: "login_counts_week",
      month: "login_counts_month",
      year: "login_counts_year",
    },
  }[activeMetric][activePeriod];
  const backendChartData: ChartPoint[] = stats?.[dataKey] || emptyByPeriod[activePeriod];
  const buildLocalLoginChartData = (): ChartPoint[] => {
    const base = emptyByPeriod[activePeriod].map((item) => ({ ...item }));
    const now = new Date();
    const weekStart = new Date(now);
    weekStart.setHours(0, 0, 0, 0);
    weekStart.setDate(now.getDate() - ((now.getDay() + 6) % 7));
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const yearStart = new Date(now.getFullYear(), 0, 1);

    getLocalLoginEvents().forEach((raw) => {
      const date = new Date(raw);
      if (Number.isNaN(date.getTime())) return;
      let index = -1;
      if (activePeriod === "week" && date >= weekStart) {
        index = (date.getDay() + 6) % 7;
      } else if (activePeriod === "month" && date >= monthStart) {
        index = Math.min(3, Math.floor((date.getDate() - 1) / 7));
      } else if (activePeriod === "year" && date >= yearStart) {
        index = date.getMonth();
      }
      if (index >= 0 && base[index]) {
        base[index].val += 1;
      }
    });
    return base;
  };
  const mergeChartDataByMax = (primary: ChartPoint[], fallback: ChartPoint[]) =>
    primary.map((item, index) => ({
      ...item,
      val: Math.max(Number(item.val || 0), Number(fallback[index]?.val || 0)),
    }));
  const currentChartData: ChartPoint[] = activeMetric === "login"
    ? mergeChartDataByMax(backendChartData, buildLocalLoginChartData())
    : backendChartData;

  const maxChartVal = Math.max(...currentChartData.map((d) => Number(d.val || 0)), 1);
  const weeklyTotal = currentChartData.reduce((sum, d) => sum + Number(d.val || 0), 0);
  const bestDay = currentChartData.reduce(
    (best, d) => (Number(d.val || 0) > Number(best.val || 0) ? d : best),
    currentChartData[0] || emptyWeek[0],
  );
  const activeDays = currentChartData.filter((d) => Number(d.val || 0) > 0).length;
  const weekRangeLabel = stats?.week_start && stats?.week_end
    ? `${new Date(stats.week_start).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })} - ${new Date(stats.week_end).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })}`
    : "Tuần này";
  const metricMeta = {
    online: {
      label: "Thời gian online",
      shortLabel: "Online",
      unit: "giờ",
      goal: 10,
      goals: { week: 10, month: 40, year: 520 },
      icon: Clock,
      color: "bg-[#7a1c1c]",
      text: "text-[#7a1c1c]",
      border: "border-rose-100",
      soft: "bg-rose-50 text-[#7a1c1c]",
    },
    active: {
      label: "Số lần hoạt động",
      shortLabel: "Hoạt động",
      unit: "lần",
      goal: 20,
      goals: { week: 20, month: 80, year: 1040 },
      icon: MousePointerClick,
      color: "bg-indigo-600",
      text: "text-indigo-700",
      border: "border-indigo-100",
      soft: "bg-indigo-50 text-indigo-700",
    },
    login: {
      label: "Số lần đăng nhập",
      shortLabel: "Đăng nhập",
      unit: "lần",
      goal: 7,
      goals: { week: 7, month: 28, year: 365 },
      icon: LogIn,
      color: "bg-emerald-600",
      text: "text-emerald-700",
      border: "border-emerald-100",
      soft: "bg-emerald-50 text-emerald-700",
    },
  }[activeMetric];
  const periodMeta = {
    week: {
      label: "Tuần",
      title: "trong tuần này",
      range: weekRangeLabel,
      detail: "7 ngày trong tuần hiện tại",
      activeCountLabel: "ngày",
    },
    month: {
      label: "Tháng",
      title: "trong tháng này",
      range: new Date().toLocaleDateString("vi-VN", { month: "long", year: "numeric" }),
      detail: "4 nhóm tuần trong tháng hiện tại",
      activeCountLabel: "tuần",
    },
    year: {
      label: "Năm",
      title: "trong năm nay",
      range: `${new Date().getFullYear()}`,
      detail: "12 tháng trong năm hiện tại",
      activeCountLabel: "tháng",
    },
  }[activePeriod];
  const MetricIcon = metricMeta.icon;
  const periodGoal = metricMeta.goals[activePeriod];
  const goalPercent = Math.min(100, Math.round((weeklyTotal / periodGoal) * 100));
  const averagePerActiveDay = activeDays > 0 ? weeklyTotal / activeDays : 0;
  const formatMetricValue = (value: number) =>
    activeMetric === "online" ? value.toFixed(value % 1 === 0 ? 0 : 1) : Math.round(value).toString();
  const trendLabel =
    weeklyTotal === 0
      ? "Chưa có dữ liệu"
      : goalPercent >= 100
        ? "Đã đạt mục tiêu"
        : goalPercent >= 50
          ? "Đang tiến triển tốt"
          : "Cần thêm hoạt động";
  const chartScaleLabels = [maxChartVal, maxChartVal / 2, 0];
  const scoreTone = (percentage: number) => {
    if (percentage >= 80) return "bg-emerald-50 text-emerald-700";
    if (percentage >= 60) return "bg-amber-50 text-amber-700";
    return "bg-rose-50 text-[#7a1c1c]";
  };
  const quizTopicLabels: Record<string, string> = {
    apriori: "Thuật toán Apriori",
    fp_growth: "Thuật toán FP-Growth",
    kmeans: "Thuật toán K-Means",
    dbscan: "Thuật toán DBSCAN",
    ly_thuyet_25: "Đề kiểm tra lý thuyết (25%)",
    cuoi_ky_50: "Đề thi trắc nghiệm cuối kỳ (50%)",
    code_thuc_hanh: "Thực hành mã nguồn Python",
  };
  const getQuizTopicId = (lesson: RecentLesson) => {
    const raw = (lesson.topic || lesson.title || "").trim();
    if (Object.prototype.hasOwnProperty.call(quizTopicLabels, raw)) return raw;
    const matched = Object.entries(quizTopicLabels).find(([, label]) => label === raw);
    return matched?.[0] || raw;
  };
  const getQuizTopicTitle = (lesson: RecentLesson) => {
    const rawTopic = (lesson.topic || "").trim();
    const rawTitle = (lesson.title || rawTopic).trim();
    return quizTopicLabels[rawTopic] || quizTopicLabels[rawTitle] || rawTitle || "Trắc nghiệm";
  };

  return (
    <div className="p-4 max-w-[1440px] mx-auto space-y-4">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#7a1c1c] rounded-xl flex items-center justify-center text-white">
            <Sparkles size={21} />
          </div>
          <div>
            <h2 className="text-2xl font-display font-semibold text-slate-900 leading-tight">
              Chào mừng trở lại!
            </h2>
            <p className="text-base text-slate-600 mt-1">Hôm nay chúng ta học gì nào?</p>
          </div>
        </div>

        <button
          onClick={onNavigateToMentor}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 hover:border-rose-300 rounded-lg font-medium text-[13px] text-slate-700 hover:text-[#7a1c1c] transition-all shadow-sm"
        >
          <MessageSquare size={16} />
          Hỏi Mentor AI
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4 items-start">
        <div className="xl:col-span-4 bg-white rounded-xl border border-slate-100 shadow-sm p-4 flex flex-col self-start">
          <div className="flex-1">
            <span className="uppercase tracking-widest text-[10px] font-semibold text-[#7a1c1c]">Tiến độ khóa học</span>

            <div className="mt-3 flex items-baseline gap-1.5">
              <span className="text-4xl font-display font-semibold text-slate-900 tabular-nums">{courseProgressPercent}</span>
              <span className="text-xl text-slate-400 font-light">%</span>
            </div>

            <p className="text-slate-600 mt-1.5 text-sm">Data Mining - INT3210</p>
            <p className="mt-1 text-[11px] font-medium text-slate-500">
              Hoàn thành {completedCourseTopics.length}/{courseProgressTopics.length} chủ đề qua bài luyện tập
            </p>

            <div className="mt-5">
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#7a1c1c] rounded-full transition-all duration-700"
                  style={{ width: `${courseProgressPercent}%` }}
                />
              </div>
            </div>

            <div className="mt-3 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {nextCourseTopic ? "Chủ đề tiếp theo" : "Trạng thái"}
              </div>
              <div className="mt-0.5 text-xs font-semibold text-slate-700">
                {nextCourseTopic ? nextCourseTopic.title : "Đã hoàn thành toàn bộ mốc luyện tập"}
              </div>
            </div>
          </div>

          <button
            onClick={onNavigateToLibrary}
            className="mt-5 w-full py-2.5 bg-slate-900 hover:bg-black text-white rounded-lg text-[13px] font-semibold flex items-center justify-center gap-2 transition-all active:scale-[0.97]"
          >
            Tiếp tục học <ArrowRight size={18} />
          </button>
        </div>

        <div className="xl:col-span-8 bg-white rounded-xl border border-slate-100 shadow-sm p-4 flex flex-col gap-3">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col 2xl:flex-row 2xl:items-start justify-between gap-3">
              <div className="min-w-0 max-w-2xl">
                <span className="uppercase tracking-widest text-[10px] font-semibold text-[#7a1c1c]">
                  Nhật ký & hoạt động cá nhân
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-1 leading-snug">
                  Theo dõi nhịp học tập {periodMeta.title}
                </h3>
                <p className="mt-1.5 text-sm text-slate-500">
                  Dữ liệu được tính từ hoạt động thật của bạn trong khoảng {periodMeta.range}.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row 2xl:flex-col gap-2 2xl:min-w-[340px]">
                <div className="grid grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1 text-[11px] font-semibold">
                  {(["week", "month", "year"] as PeriodId[]).map((id) => {
                    const isActive = activePeriod === id;
                    const label = { week: "Tuần", month: "Tháng", year: "Năm" }[id];
                    return (
                      <button
                        key={id}
                        onClick={() => setActivePeriod(id)}
                        className={`min-h-8 rounded-lg px-2.5 transition-all ${
                          isActive
                            ? "bg-white shadow-sm text-slate-900 ring-1 ring-slate-200"
                            : "text-slate-500 hover:text-slate-700"
                        }`}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>

                <div className="grid grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1 text-[11px] font-semibold">
                  {(["online", "active", "login"] as MetricId[]).map((id) => {
                    const itemMeta = {
                      online: { label: "Online", icon: Clock },
                      active: { label: "Hoạt động", icon: MousePointerClick },
                      login: { label: "Đăng nhập", icon: LogIn },
                    }[id];
                    const ItemIcon = itemMeta.icon;
                    const isActive = activeMetric === id;
                    return (
                      <button
                        key={id}
                        onClick={() => setActiveMetric(id)}
                        className={`min-h-8 rounded-lg px-2 transition-all flex items-center justify-center gap-1.5 ${
                          isActive
                            ? "bg-white shadow-sm text-slate-900 ring-1 ring-slate-200"
                            : "text-slate-500 hover:text-slate-700"
                        }`}
                      >
                        <ItemIcon size={15} />
                        <span className="truncate">{itemMeta.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch">
              <div className="lg:col-span-8 rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">{metricMeta.label}</div>
                    <div className="text-[11px] text-slate-400">{periodMeta.detail}</div>
                  </div>
                  <div className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${metricMeta.soft}`}>{trendLabel}</div>
                </div>

                <div className="relative h-40 pl-9 pr-2 pt-1 pb-7">
                  <div className="absolute left-0 top-1 bottom-8 flex flex-col justify-between text-[10px] font-semibold text-slate-400 tabular-nums">
                    {chartScaleLabels.map((value, idx) => (
                      <span key={idx}>{formatMetricValue(value)}</span>
                    ))}
                  </div>

                  <div className="absolute left-9 right-2 top-2 bottom-7 flex flex-col justify-between pointer-events-none">
                    {[0, 1, 2].map((line) => (
                      <div key={line} className="border-t border-dashed border-slate-200" />
                    ))}
                  </div>

                  <div
                    className="relative z-10 grid h-full gap-2 items-end"
                    style={{ gridTemplateColumns: `repeat(${currentChartData.length}, minmax(0, 1fr))` }}
                  >
                    {currentChartData.map((d, i) => {
                      const value = Number(d.val || 0);
                      const height = value === 0 ? 0 : Math.max(10, (value / maxChartVal) * 100);
                      const isBest = weeklyTotal > 0 && d.day === bestDay.day;
                      return (
                        <div key={i} className="flex h-full min-w-0 flex-col justify-end items-center group">
                          <div className={`mb-2 rounded-full px-2 py-0.5 text-[10px] font-bold opacity-0 shadow-sm transition-opacity group-hover:opacity-100 ${metricMeta.soft}`}>
                            {formatMetricValue(value)} {metricMeta.unit}
                          </div>
                          <div className="flex h-[96px] w-full items-end justify-center">
                            <div
                              className={`w-full max-w-10 rounded-t-lg transition-all duration-500 ${value > 0 ? metricMeta.color : "bg-slate-200/70"} ${isBest ? "ring-2 ring-white shadow-md" : "shadow-sm"}`}
                              style={{ height: `${height}%` }}
                            />
                          </div>
                          <span className={`mt-2 text-[11px] font-bold ${value > 0 ? "text-slate-700" : "text-slate-400"}`}>{d.day}</span>
                        </div>
                      );
                    })}
                  </div>

                  {weeklyTotal === 0 && (
                    <div className="absolute left-9 right-2 top-16 text-center text-sm font-medium text-slate-400">
                      Chưa ghi nhận dữ liệu {periodMeta.title}
                    </div>
                  )}
                </div>
              </div>

              <div className={`lg:col-span-4 rounded-xl border ${metricMeta.border} bg-white p-3.5 flex flex-col justify-between shadow-sm`}>
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${metricMeta.soft}`}>
                      <MetricIcon size={17} />
                    </div>
                    <span className="text-[11px] font-semibold text-slate-400">Mục tiêu {periodMeta.label.toLowerCase()}</span>
                  </div>

                  <div className="mt-4">
                    <div className="flex items-end gap-1.5">
                      <span className="text-4xl font-display font-semibold text-slate-900 tabular-nums leading-none">
                        {formatMetricValue(weeklyTotal)}
                      </span>
                      <span className="pb-1 text-sm font-bold text-slate-500">{metricMeta.unit}</span>
                    </div>
                    <div className="mt-2 text-sm text-slate-500">
                      {goalPercent}% của mục tiêu {periodGoal} {metricMeta.unit}
                    </div>
                  </div>
                </div>

                <div className="mt-4 space-y-2.5">
                  <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${metricMeta.color} transition-all duration-1000`}
                      style={{ width: `${goalPercent}%` }}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="rounded-lg bg-slate-50 p-2.5">
                      <div className="font-semibold text-slate-400">Cao nhất</div>
                      <div className="mt-1 font-bold text-slate-800">
                        {weeklyTotal > 0 ? `${bestDay.day} · ${formatMetricValue(Number(bestDay.val || 0))}` : "Chưa có"}
                      </div>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-2.5">
                      <div className="font-semibold text-slate-400">Có dữ liệu</div>
                      <div className="mt-1 font-bold text-slate-800">{activeDays}/{currentChartData.length} {periodMeta.activeCountLabel}</div>
                    </div>
                  </div>

                  <div className="rounded-lg bg-slate-50 p-2.5 text-[11px]">
                    <div className="font-semibold text-slate-400">Trung bình/{periodMeta.activeCountLabel} có dữ liệu</div>
                    <div className={`mt-1 text-sm font-bold ${metricMeta.text}`}>
                      {formatMetricValue(averagePerActiveDay)} {metricMeta.unit}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {false && isAdminUser && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-4 flex items-center justify-between gap-4">
            <div>
              <div className="uppercase tracking-widest text-[10px] font-semibold text-[#7a1c1c]">Quản lý người dùng</div>
              <div className="mt-2 text-sm font-medium text-slate-500">Tổng số tài khoản trong hệ thống</div>
              <div className="mt-3 text-4xl font-display font-semibold text-slate-900 tabular-nums">
                {adminUserSummary?.total_users ?? 0}
              </div>
            </div>
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-[#7a1c1c] flex items-center justify-center">
              <Users size={24} />
            </div>
          </div>

          <div className="bg-white rounded-xl border border-emerald-100 shadow-sm p-4 flex items-center justify-between gap-4">
            <div>
              <div className="uppercase tracking-widest text-[10px] font-semibold text-emerald-700">Đang truy cập</div>
              <div className="mt-2 text-sm font-medium text-slate-500">Người dùng đăng nhập trong 15 phút gần nhất</div>
              <div className="mt-3 text-4xl font-display font-semibold text-emerald-800 tabular-nums">
                {adminUserSummary?.online_count ?? 0}
              </div>
            </div>
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
              <UserCheck size={24} />
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 bg-gradient-to-br from-rose-50 to-rose-50 border border-rose-100 rounded-xl p-4 flex flex-col">
          <Sparkles className="text-[#7a1c1c] mb-3" size={24} />

          <h3 className="text-lg font-semibold text-slate-800">Lời khuyên từ AI</h3>
          <div className="text-slate-600 mt-3 text-sm leading-relaxed flex-1">
            {weakTopics.length > 0 ? (
              <>
                <p className="mb-1.5">Bạn đang học rất chăm chỉ! Phân tích nhật ký học tập cho thấy bạn đang gặp khó khăn ở các chủ đề sau:</p>
                <ul className="list-disc pl-4 font-semibold text-[#7a1c1c] space-y-0.5">
                  {weakTopics.map((topic, i) => <li key={i}>{topic}</li>)}
                </ul>
                <p className="mt-1.5 text-xs text-slate-500">Hãy hỏi Mentor hoặc tạo Flashcard cho các chủ đề này nhé!</p>
              </>
            ) : (
              <p>
                {t.statUnit.docs === "tệp"
                  ? "Bạn đang tiến bộ rất tốt! Hãy tiếp tục duy trì đà học tập này nhé."
                  : "You're doing great! Keep up the good work."}
              </p>
            )}
          </div>

          <button
            onClick={onNavigateToMentor}
            className="mt-5 w-full py-2 bg-white text-[#7a1c1c] border border-rose-200 hover:bg-rose-50 rounded-lg font-medium text-xs flex items-center justify-center gap-1.5 transition-all"
          >
            Hỏi thêm Mentor AI →
          </button>
        </div>

        <div className="lg:col-span-8">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Bài học gần đây</h3>

          {recentLessons.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {recentLessons.map((lesson) => (
                <div
                  key={lesson.id}
                  className="bg-white border border-slate-100 rounded-xl p-4 hover:shadow-md hover:-translate-y-0.5 transition-all group cursor-pointer"
                  onClick={() => onPlayLesson(getQuizTopicId(lesson))}
                >
                  <div className={`inline-flex px-2.5 py-1 text-[11px] font-bold rounded-full ${scoreTone(lesson.percentage)} mb-3`}>
                    {lesson.subtitle}
                  </div>
                  <h4 className="text-base font-semibold text-slate-800 group-hover:text-[#7a1c1c] transition-colors line-clamp-2">{getQuizTopicTitle(lesson)}</h4>
                  <div className="mt-3 flex items-end justify-between gap-3">
                    <div>
                      <div className="text-2xl font-bold text-slate-900 tabular-nums">{lesson.percentage}%</div>
                      <div className="text-xs font-medium text-slate-500">
                        {lesson.score}/{lesson.max_score} điểm · {lesson.answered_questions}/{lesson.total_questions} câu
                      </div>
                    </div>
                    <div className="w-8 h-8 bg-slate-100 group-hover:bg-rose-100 rounded-lg flex items-center justify-center transition-colors">
                      <Play size={16} className="text-[#7a1c1c]" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white border border-dashed border-slate-200 rounded-xl p-6 text-sm text-slate-500">
              Chưa có dữ liệu làm bài trắc nghiệm. Khi bạn hoàn thành quiz, điểm số thật sẽ hiển thị ở đây.
            </div>
          )}
        </div>
      </div>

      {isAdminUser && (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm mt-6">
          <div className="p-5 border-b border-slate-100 bg-slate-50 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-semibold text-slate-800 flex items-center gap-2">
                <Users size={18} className="text-[#7a1c1c]" /> Quản lý người dùng
              </h3>
              <p className="text-sm text-slate-500 mt-1">Tổng quan tài khoản thật trong hệ thống</p>
            </div>
            <button
              onClick={fetchUserSummary}
              disabled={loadingUsers}
              className="p-2 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
              title="Làm mới dữ liệu người dùng"
            >
              <RefreshCw size={16} className={loadingUsers ? "animate-spin" : ""} />
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-5">
            <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
              <div className="flex items-center justify-between text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wide">Tổng người dùng</span>
                <Users size={16} />
              </div>
              <div className="mt-3 text-3xl font-bold text-slate-900">{adminUserSummary?.total_users ?? 0}</div>
            </div>
            <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
              <div className="flex items-center justify-between text-emerald-700">
                <span className="text-xs font-bold uppercase tracking-wide">Đang hoạt động</span>
                <UserCheck size={16} />
              </div>
              <div className="mt-3 text-3xl font-bold text-emerald-800">{adminUserSummary?.active_count ?? 0}</div>
            </div>
            <div className="rounded-xl border border-rose-100 bg-rose-50 p-4">
              <div className="flex items-center justify-between text-rose-700">
                <span className="text-xs font-bold uppercase tracking-wide">Quản trị viên</span>
                <ShieldCheck size={16} />
              </div>
              <div className="mt-3 text-3xl font-bold text-rose-800">{adminUserSummary?.admin_count ?? 0}</div>
            </div>
            <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
              <div className="flex items-center justify-between text-indigo-700">
                <span className="text-xs font-bold uppercase tracking-wide">Người học</span>
                <Activity size={16} />
              </div>
              <div className="mt-3 text-3xl font-bold text-indigo-800">{adminUserSummary?.regular_count ?? 0}</div>
            </div>
          </div>

          <div className="border-t border-slate-100">
            <div className="px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span>Người dùng mới gần đây</span>
              {adminUserSummary?.online_count !== undefined && (
                <span className="normal-case text-emerald-600 flex items-center gap-1.5 font-semibold text-xs">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  {adminUserSummary.online_count} đang truy cập (2 phút qua)
                </span>
              )}
            </div>
            {loadingUsers ? (
              <div className="px-5 py-8 text-center text-slate-400">Đang tải dữ liệu người dùng...</div>
            ) : recentUsers.length === 0 ? (
              <div className="px-5 py-8 text-center text-slate-400">Chưa có dữ liệu người dùng.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {recentUsers.map((user) => {
                  const displayName = user.full_name || user.username || user.email || "Người dùng";
                  return (
                    <div key={user.user_id || user.email} className="px-5 py-4 flex items-center justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <div className="font-semibold text-slate-800 truncate">{displayName}</div>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${user.role === "admin" ? "bg-rose-50 text-[#7a1c1c]" : "bg-slate-100 text-slate-600"}`}>
                            {user.role === "admin" ? "Admin" : "Người học"}
                          </span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${user.is_active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                            {user.is_active ? "Hoạt động" : "Tạm khóa"}
                          </span>
                        </div>
                        <div className="text-sm text-slate-500 truncate">{user.email || "Chưa có email"}</div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-sm font-semibold text-slate-700">{user.login_count || 0} lần đăng nhập</div>
                        <div className="text-xs text-slate-400">Tạo: {formatUserDate(user.created_at)}</div>
                        <div className="text-xs text-slate-400">Lần cuối: {formatUserDate(user.last_login)}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


