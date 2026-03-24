import { cookies } from "next/headers";

export const LOCALE_COOKIE = "nexus_locale";
export const SUPPORTED_LOCALES = ["en", "zh"] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

type Dictionary = {
  layout: {
    dashboard: string;
    users: string;
    cortex: string;
    audit: string;
    network: string;
    integrations: string;
    roadmap: string;
    language: string;
    searchPlaceholder: string;
    administrator: string;
    guest: string;
    logout: string;
  };
  users: {
    title: string;
    subtitle: string;
    activeUsers: string;
    tableHint: string;
    channelBinding: string;
    channelBindingHint: string;
    id: string;
    username: string;
    role: string;
    apiKey: string;
    language: string;
    telegram: string;
    wechat: string;
    actions: string;
    manage: string;
    bound: string;
    notBound: string;
    pollingActive: string;
    pollingIdle: string;
  };
  languagePage: {
    title: string;
    subtitle: string;
    cardTitle: string;
    cardHint: string;
    english: string;
    chinese: string;
    current: string;
    apply: string;
    success: string;
  };
};

const dictionaries: Record<Locale, Dictionary> = {
  en: {
    layout: {
      dashboard: "Dashboard",
      users: "Users",
      cortex: "Cortex",
      audit: "Audit",
      network: "Network",
      integrations: "Integrations",
      roadmap: "Roadmap",
      language: "Language",
      searchPlaceholder: "Search...",
      administrator: "Administrator",
      guest: "Guest",
      logout: "Logout",
    },
    users: {
      title: "Users & IAM",
      subtitle: "Manage user accounts, roles, and access keys.",
      activeUsers: "Active Users",
      tableHint: "Open a user to edit profile details, review Telegram binding, and manage WeChat connection.",
      channelBinding: "Channel Binding",
      channelBindingHint: "The list now shows Telegram and WeChat binding state directly. Open Manage to reconnect WeChat or review identity details.",
      id: "ID",
      username: "Username",
      role: "Role",
      apiKey: "API Key",
      language: "Language",
      telegram: "Telegram",
      wechat: "WeChat",
      actions: "Actions",
      manage: "Manage",
      bound: "Bound",
      notBound: "Not bound",
      pollingActive: "Polling: active",
      pollingIdle: "Polling: idle",
    },
    languagePage: {
      title: "Language",
      subtitle: "Choose the display language for the admin web UI.",
      cardTitle: "Interface Language",
      cardHint: "This setting is stored in your browser and currently switches the main admin navigation and user management pages.",
      english: "English",
      chinese: "Chinese",
      current: "Current",
      apply: "Apply Language",
      success: "Language updated.",
    },
  },
  zh: {
    layout: {
      dashboard: "仪表盘",
      users: "用户管理",
      cortex: "记忆与技能",
      audit: "审计",
      network: "网络",
      integrations: "集成",
      roadmap: "路线图",
      language: "语言",
      searchPlaceholder: "搜索...",
      administrator: "管理员",
      guest: "访客",
      logout: "退出登录",
    },
    users: {
      title: "用户与权限",
      subtitle: "管理用户账号、角色和访问密钥。",
      activeUsers: "活跃用户",
      tableHint: "打开用户详情，可编辑资料、查看 Telegram 绑定，并管理 WeChat 连接。",
      channelBinding: "渠道绑定",
      channelBindingHint: "列表会直接显示 Telegram 和 WeChat 绑定状态。进入 Manage 可重新连接 WeChat 或查看身份信息。",
      id: "编号",
      username: "用户名",
      role: "角色",
      apiKey: "API Key",
      language: "语言",
      telegram: "Telegram",
      wechat: "WeChat",
      actions: "操作",
      manage: "管理",
      bound: "已绑定",
      notBound: "未绑定",
      pollingActive: "轮询：运行中",
      pollingIdle: "轮询：空闲",
    },
    languagePage: {
      title: "语言",
      subtitle: "选择管理后台页面的显示语言。",
      cardTitle: "界面语言",
      cardHint: "这个设置保存在当前浏览器中，当前会切换主要导航和用户管理相关页面。",
      english: "英文",
      chinese: "中文",
      current: "当前",
      apply: "应用语言",
      success: "语言已更新。",
    },
  },
};

export async function getServerLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const value = cookieStore.get(LOCALE_COOKIE)?.value;
  return value === "zh" ? "zh" : "en";
}

export function getDictionary(locale: Locale): Dictionary {
  return dictionaries[locale];
}
