import React from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BookOpen,
  Brain,
  Check,
  Clipboard,
  Download,
  FlaskConical,
  History,
  LoaderCircle,
  Play,
  RefreshCw,
  Settings,
  Sparkles,
} from "lucide-react";
import "./styles/app.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

const emptyTemplate = {
  field: "",
  background: "",
  existing_basis: "",
  extension_points: "",
  core_question: "",
  platforms: "",
  constraints: "",
  target_output: "",
  preferred_direction: "",
  avoid_direction: "",
};

const requiredFields = ["field", "background", "existing_basis"];

const formFields = [
  ["field", "研究领域", "如：肿瘤免疫、单细胞测序、材料催化"],
  ["background", "实验大背景", "当前领域问题、疾病背景、技术背景"],
  ["existing_basis", "已有研究基础", "已有数据、实验结果、模型系统、样本资源"],
  ["extension_points", "初步想法", "你已经想到的延伸点"],
  ["core_question", "核心科学问题", "不清楚可留空，KS 会协助提炼"],
  ["platforms", "可用技术平台", "RNA-seq、动物模型、细胞实验、临床队列等"],
  ["constraints", "资源限制", "时间、经费、样本量、仪器、合作条件"],
  ["target_output", "目标产出", "开题报告、组会讨论、毕业课题、预实验等"],
  ["preferred_direction", "偏好方向", "机制研究、方法开发、转化应用、交叉学科等"],
  ["avoid_direction", "避免方向", "明确不想做的方向"],
];

const agentSlots = [
  ["intake", "入口 Agent", "结构化 briefing"],
  ["novelty", "创新性 Agent", "讨论组"],
  ["mechanism", "机制深挖 Agent", "讨论组"],
  ["feasibility", "可行性 Agent", "讨论组"],
  ["reviewer", "审稿人 Agent", "讨论组"],
  ["moderator", "Moderator", "冲突与遗漏"],
  ["group_summarizer", "结构化 IR", "总结"],
  ["output", "出口 Agent", "最终报告"],
];

const agentRecommendations = {
  intake: "推荐：长上下文、稳健理解模型，例如 GLM-5.1 / Kimi 长上下文 / DeepSeek Pro，用于全文消化模板和文档。",
  novelty: "推荐：创造性强、响应较快的模型，例如 DeepSeek Flash / Qwen Plus，用于提出差异化方向。",
  mechanism: "推荐：推理稳定、机制链条表达强的模型，例如 GLM / DeepSeek Pro / Qwen Max。",
  feasibility: "推荐：成本适中且执行细节可靠的模型，例如 DeepSeek Flash / Qwen Plus，用于压实实验路线。",
  reviewer: "推荐：批判性和长文本能力强的模型，例如 DeepSeek Pro / GLM-5.1，用于模拟审稿质疑。",
  moderator: "推荐：总结和对比能力强的中高质量模型，用于提炼第 1 轮冲突点和第 2 轮问题清单。",
  group_summarizer: "推荐：结构化能力强的模型，用于把多轮讨论压缩成稳定 IR。",
  output: "推荐：质量最高、中文写作稳定的模型，用于生成最终 Markdown 报告。",
};

const apiTypes = [
  ["openai_compatible", "OpenAI Compatible"],
  ["anthropic_messages", "Anthropic Messages"],
  ["openai_responses", "OpenAI Responses"],
];

const providerGroups = [
  ["coding_plan", "CODING PLAN"],
  ["api", "API"],
];

const defaultModelSettings = {
  version: 6,
  providers: [
    {
      id: "kimi-coding",
      name: "Kimi Coding Plan",
      category: "coding_plan",
      api_key: "",
      base_url: "https://api.kimi.com/coding/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "bailian-coding",
      name: "百炼 Coding Plan",
      category: "coding_plan",
      api_key: "",
      base_url: "https://coding.dashscope.aliyuncs.com/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "volcengine-coding",
      name: "火山引擎 Coding Plan",
      category: "coding_plan",
      api_key: "",
      base_url: "https://ark.cn-beijing.volces.com/api/coding/v3",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "deepseek",
      name: "DeepSeek",
      category: "api",
      api_key: "",
      base_url: "https://api.deepseek.com/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "dashscope",
      name: "DashScope (百炼 API)",
      category: "api",
      api_key: "",
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "openai",
      name: "OpenAI",
      category: "api",
      api_key: "",
      base_url: "https://api.openai.com/v1",
      api_type: "openai_responses",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "openrouter",
      name: "OpenRouter",
      category: "api",
      api_key: "",
      base_url: "https://openrouter.ai/api/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "ollama",
      name: "Ollama (Local)",
      category: "api",
      api_key: "ollama",
      base_url: "http://127.0.0.1:11434/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "minimax",
      name: "MiniMax",
      category: "api",
      api_key: "",
      base_url: "https://api.minimax.io/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
    {
      id: "siliconflow",
      name: "SiliconFlow",
      category: "api",
      api_key: "",
      base_url: "https://api.siliconflow.cn/v1",
      api_type: "openai_compatible",
      allow_insecure_tls: false,
      models: [],
    },
  ],
  assignments: {},
};

function loadModelSettings() {
  try {
    return normalizeModelSettings(
      JSON.parse(localStorage.getItem("ks-model-settings-react")) ||
      JSON.parse(JSON.stringify(defaultModelSettings)),
    );
  } catch {
    return normalizeModelSettings(JSON.parse(JSON.stringify(defaultModelSettings)));
  }
}

function normalizeModelSettings(settings) {
  const defaults = JSON.parse(JSON.stringify(defaultModelSettings));
  const existing = settings.providers || [];
  const existingIds = new Set(existing.map((item) => item.id));
  const presetApiIds = new Set(
    defaults.providers.map((item) => item.id),
  );
  const resetPresetModels = settings.version !== defaults.version;
  return {
    ...settings,
    version: defaults.version,
    providers: [
      ...existing
        .filter(
          (item) =>
            item.id !== "chatgpt-plus" &&
            item.api_type !== "chatgpt_codex" &&
            (item.category || "api") !== "oauth",
        )
        .map((item) => ({
          category: "api",
          ...item,
          models:
            resetPresetModels && presetApiIds.has(item.id)
              ? []
              : item.models || [],
        })),
      ...defaults.providers.filter((item) => !existingIds.has(item.id)),
    ],
    assignments: settings.assignments || {},
  };
}

function inferRunRounds(run) {
  const timelineRounds = Math.max(
    0,
    ...(run?.timeline || []).map((step) => {
      const match = String(step?.key || "").match(/^debate_r(\d+)_/);
      return match ? Number.parseInt(match[1], 10) : 0;
    }),
  );
  if (timelineRounds > 0) return timelineRounds;
  return Math.max(1, ...(run?.debate_messages || []).map((message) => message.round || 0));
}

function inferParallelFirstRound(run) {
  return (run?.timeline || []).some(
    (step) => step?.key?.startsWith("debate_r1_") && String(step?.label || "").includes("独立发言"),
  );
}

function baseExportName(run) {
  const raw = `${run?.template_input?.field || "K-Storm-report"}-${run?.run_id || "run"}`;
  return raw
    .replace(/[\\/:*?"<>|]+/g, " ")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80) || "K-Storm-report";
}

function reportFilename(run) {
  return `${baseExportName(run)}.md`;
}

function runJsonFilename(run) {
  return `${baseExportName(run)}.json`;
}

function bundleFilename(run) {
  return `${baseExportName(run)}-bundle.zip`;
}

function normalizeLoadedDocuments(documents = []) {
  return documents.map((document, index) => ({
    ...document,
    id: document.id || `doc-loaded-${Date.now()}-${index}`,
    note: document.note || "",
  }));
}

function downloadTextFile(text, filename, mimeType) {
  const blob = new Blob([text], { type: `${mimeType};charset=utf-8` });
  downloadBlob(blob, filename);
}

function downloadMarkdown(text, filename) {
  downloadTextFile(text, filename, "text/markdown");
}

function downloadJsonFile(value, filename) {
  downloadTextFile(JSON.stringify(value, null, 2), filename, "application/json");
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function bundleEntriesForRun(run) {
  return [
    {
      name: "report.md",
      data: run?.final_report || "",
    },
    {
      name: "structured-ir.md",
      data: run?.group_summary || "",
    },
    {
      name: "metadata.json",
      data: JSON.stringify(
        {
          run_id: run?.run_id,
          status: run?.status,
          exported_at: new Date().toISOString(),
          field: run?.template_input?.field || "",
        },
        null,
        2,
      ),
    },
  ].filter((entry) => entry.data);
}

function buildBundleMD(run) {
  const parts = [];
  parts.push(`# K-Storm 讨论打包`);
  parts.push(``);
  parts.push(`**Run ID**：${run?.run_id || ""}`);
  parts.push(`**领域**：${run?.template_input?.field || ""}`);
  parts.push(`**时间**：${run?.created_at ? new Date(run.created_at).toLocaleString() : ""}`);
  parts.push(``);
  if (run?.final_report) {
    parts.push(`---`);
    parts.push(``);
    parts.push(`## 最终报告`);
    parts.push(``);
    parts.push(run.final_report);
    parts.push(``);
  }
  if (run?.debate_messages?.length) {
    parts.push(`---`);
    parts.push(``);
    parts.push(`## 讨论记录`);
    parts.push(``);
    for (const msg of run.debate_messages) {
      parts.push(`### ${msg.agent} · 第 ${msg.round} 轮`);
      parts.push(``);
      parts.push(msg.content);
      parts.push(``);
    }
  }
  return parts.join("\n");
}

function downloadRunBundle(run) {
  const entries = bundleEntriesForRun(run);
  if (!entries.length) return;
  const blob = createZipBlob(entries);
  downloadBlob(blob, bundleFilename(run));
}

const ZIP_CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let index = 0; index < 256; index += 1) {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
    }
    table[index] = value >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = ZIP_CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function zipTimestampParts(date = new Date()) {
  const year = Math.max(1980, date.getFullYear());
  return {
    time:
      ((date.getHours() & 0x1f) << 11) |
      ((date.getMinutes() & 0x3f) << 5) |
      Math.floor(date.getSeconds() / 2),
    date: (((year - 1980) & 0x7f) << 9) | (((date.getMonth() + 1) & 0x0f) << 5) | (date.getDate() & 0x1f),
  };
}

function createZipBlob(entries) {
  const encoder = new TextEncoder();
  const locals = [];
  const centrals = [];
  let offset = 0;
  const stamp = zipTimestampParts();

  for (const entry of entries) {
    const nameBytes = encoder.encode(entry.name);
    const dataBytes = entry.data instanceof Uint8Array ? entry.data : encoder.encode(String(entry.data));
    const crc = crc32(dataBytes);

    const local = new Uint8Array(30 + nameBytes.length + dataBytes.length);
    const localView = new DataView(local.buffer);
    localView.setUint32(0, 0x04034b50, true);
    localView.setUint16(4, 20, true);
    localView.setUint16(6, 0, true);
    localView.setUint16(8, 0, true);
    localView.setUint16(10, stamp.time, true);
    localView.setUint16(12, stamp.date, true);
    localView.setUint32(14, crc, true);
    localView.setUint32(18, dataBytes.length, true);
    localView.setUint32(22, dataBytes.length, true);
    localView.setUint16(26, nameBytes.length, true);
    localView.setUint16(28, 0, true);
    local.set(nameBytes, 30);
    local.set(dataBytes, 30 + nameBytes.length);
    locals.push(local);

    const central = new Uint8Array(46 + nameBytes.length);
    const centralView = new DataView(central.buffer);
    centralView.setUint32(0, 0x02014b50, true);
    centralView.setUint16(4, 20, true);
    centralView.setUint16(6, 20, true);
    centralView.setUint16(8, 0, true);
    centralView.setUint16(10, 0, true);
    centralView.setUint16(12, stamp.time, true);
    centralView.setUint16(14, stamp.date, true);
    centralView.setUint32(16, crc, true);
    centralView.setUint32(20, dataBytes.length, true);
    centralView.setUint32(24, dataBytes.length, true);
    centralView.setUint16(28, nameBytes.length, true);
    centralView.setUint16(30, 0, true);
    centralView.setUint16(32, 0, true);
    centralView.setUint16(34, 0, true);
    centralView.setUint16(36, 0, true);
    centralView.setUint32(38, 0, true);
    centralView.setUint32(42, offset, true);
    central.set(nameBytes, 46);
    centrals.push(central);

    offset += local.length;
  }

  const centralSize = centrals.reduce((sum, item) => sum + item.length, 0);
  const end = new Uint8Array(22);
  const endView = new DataView(end.buffer);
  endView.setUint32(0, 0x06054b50, true);
  endView.setUint16(4, 0, true);
  endView.setUint16(6, 0, true);
  endView.setUint16(8, entries.length, true);
  endView.setUint16(10, entries.length, true);
  endView.setUint32(12, centralSize, true);
  endView.setUint32(16, offset, true);
  endView.setUint16(20, 0, true);

  return new Blob([...locals, ...centrals, end], { type: "application/zip" });
}


function App() {
  const [template, setTemplate] = React.useState({
    ...emptyTemplate,
    field: "肿瘤免疫与单细胞测序",
    background:
      "课题组关注免疫治疗耐药，希望从肿瘤微环境细胞互作中找到新的机制切入点。",
    existing_basis:
      "已有一批治疗前后样本的单细胞数据，观察到某类髓系细胞亚群在耐药样本中升高，并伴随 T 细胞耗竭评分上升。",
    platforms:
      "单细胞转录组、流式细胞术、细胞共培养、免疫组化、小鼠皮下瘤模型",
    constraints: "3 个月内完成预实验; 样本量有限; 动物实验名额有限",
    target_output: "开题报告和组会讨论材料",
    preferred_direction: "机制研究、转化标志物",
  });
  const [run, setRun] = React.useState(null);
  const [history, setHistory] = React.useState([]);
  const [selectedHistory, setSelectedHistory] = React.useState([]);
  const [historyLocation, setHistoryLocation] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [copied, setCopied] = React.useState(false);
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [modelSettings, setModelSettings] = React.useState(loadModelSettings);
  const [rounds, setRounds] = React.useState(3);
  const [activeRounds, setActiveRounds] = React.useState(3);
  const [parallelFirstRound, setParallelFirstRound] = React.useState(false);
  const [documents, setDocuments] = React.useState([]);
  const pollRef = React.useRef(null);

  React.useEffect(() => {
    loadHistory();
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  const completion = Math.round(
    (requiredFields.filter((field) => template[field].trim()).length /
      requiredFields.length) *
      100,
  );
  const canSubmit = requiredFields.every((field) => template[field].trim());

  async function loadHistory() {
    try {
      const response = await fetch(`${API_BASE}/api/history`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
        setSelectedHistory((current) =>
          current.filter((runId) => data.some((item) => item.run_id === runId)),
        );
      }
    } catch {
      setHistory([]);
    }
  }

  React.useEffect(() => {
    localStorage.setItem("ks-model-settings-react", JSON.stringify(modelSettings));
  }, [modelSettings]);

  async function addDocuments(files) {
    const nextDocuments = [];
    for (const file of files) {
      nextDocuments.push({
        id: `doc-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        name: file.name,
        doc_type: inferDocumentType(file.name),
        content: await file.text(),
        note: "",
      });
    }
    setDocuments((current) => [...current, ...nextDocuments]);
  }

  function updateDocument(id, patch) {
    setDocuments((current) =>
      current.map((document) =>
        document.id === id ? { ...document, ...patch } : document,
      ),
    );
  }

  function removeDocument(id) {
    setDocuments((current) => current.filter((document) => document.id !== id));
  }

  async function createRun(
    templateOverride = template,
    options = {},
  ) {
    const payloadRounds = options.rounds ?? (Number.parseInt(rounds, 10) || 3);
    const payloadParallelFirstRound = options.parallelFirstRound ?? parallelFirstRound;
    const payloadDocuments = options.documents ?? documents;
    const payloadModelSettings = options.modelSettings ?? modelSettings;
    const normalizedDocuments = normalizeLoadedDocuments(payloadDocuments);
    const ready = requiredFields.every((field) => templateOverride[field]?.trim());
    if (!ready || loading) return;
    setLoading(true);
    setError("");
    setCopied(false);
    setActiveRounds(payloadRounds);
    setRounds(payloadRounds);
    try {
      const response = await fetch(`${API_BASE}/api/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_input: templateOverride,
          mode: options.overrideMode || discussionMode,
          rounds: (options.overrideMode === "focused" || discussionMode === "focused") ? Math.min(payloadRounds, 2) : payloadRounds,
          parallel_first_round: payloadParallelFirstRound,
          selected_agents: (options.overrideMode === "focused" || discussionMode === "focused") ? (options.selectedAgents || selectedAgents) : [],
          probe_agent: discussionMode === "quick" ? probeAgent : "",
          probe_question: discussionMode === "quick" ? probeQuestion : "",
          source_run_id: options.sourceRunId || "",
          documents: normalizedDocuments,
          model_settings: payloadModelSettings,
        }),
      });
      if (!response.ok) {
        const detail = await readError(response);
        throw new Error(detail || "运行失败");
      }
      const data = await response.json();
      setRun(data);
      setTemplate({ ...emptyTemplate, ...(data.template_input || templateOverride) });
      setDocuments(normalizedDocuments);
      setParallelFirstRound(payloadParallelFirstRound);
      startPolling(data.run_id);
      await loadHistory();
    } catch (err) {
      setError(err.message || "运行失败，请检查后端服务是否启动。");
      setLoading(false);
    }
  }

  function startPolling(runId) {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/api/runs/${runId}`);
        if (!response.ok) throw new Error(await readError(response));
        const data = await response.json();
        setRun(data);
        if (["COMPLETED", "FAILED"].includes(data.status)) {
          window.clearInterval(pollRef.current);
          pollRef.current = null;
          setLoading(false);
          loadHistory();
        }
      } catch (err) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
        setLoading(false);
        setError(err.message || "读取进度失败");
      }
    }, 900);
  }

  async function fetchRun(runId) {
    const response = await fetch(`${API_BASE}/api/runs/${runId}`);
    if (!response.ok) throw new Error(await readError(response));
    return response.json();
  }

  async function openRun(runId) {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setLoading(true);
    setError("");
    let loadedData = null;
    try {
      const data = await fetchRun(runId);
      loadedData = data;
      setRun(data);
      setTemplate({ ...emptyTemplate, ...(data.template_input || {}) });
      setDocuments(normalizeLoadedDocuments(data.documents || []));
      setParallelFirstRound(inferParallelFirstRound(data));
      setRounds(inferRunRounds(data));
      setActiveRounds(inferRunRounds(data));
      // 如果 run 仍在运行，启动 polling 并保持 loading
      const runningStates = ["RUNNING", "INTAKE_RUNNING", "DEBATE_RUNNING", "GROUP_SUMMARY_RUNNING", "FINAL_REPORT_RUNNING"];
      if (runningStates.includes(data.status)) {
        startPolling(data.run_id);
        return data;
      }
      return data;
    } catch (err) {
      setError(err.message || "无法打开历史记录");
      return null;
    } finally {
      // 只有非运行状态才结束 loading
      const runningStates = ["RUNNING", "INTAKE_RUNNING", "DEBATE_RUNNING", "GROUP_SUMMARY_RUNNING", "FINAL_REPORT_RUNNING"];
      if (!loadedData || !runningStates.includes(loadedData.status)) {
        setLoading(false);
      }
    }
  }

  async function rerunFromRun(sourceRun) {
    if (!sourceRun) return;
    if (sourceRun.status === "FAILED" || sourceRun.status === "CANCELED") {
      // Resume from failure point
      setLoading(true);
      setError("");
      try {
        const response = await fetch(`${API_BASE}/api/runs/${sourceRun.run_id}/resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            rounds: inferRunRounds(sourceRun),
            parallel_first_round: inferParallelFirstRound(sourceRun),
            model_settings: modelSettings,
          }),
        });
        if (!response.ok) {
          const detail = await readError(response);
          throw new Error(detail || "继续失败");
        }
        const data = await response.json();
        setRun(data);
        setActiveRounds(inferRunRounds(sourceRun));
        startPolling(data.run_id);
      } catch (err) {
        setError(err.message || "继续失败");
        setLoading(false);
      }
    } else {
      // Rerun from scratch
      await createRun(sourceRun.template_input, {
        rounds: inferRunRounds(sourceRun),
        parallelFirstRound: inferParallelFirstRound(sourceRun),
        documents: sourceRun.documents || [],
        modelSettings,
      });
    }
  }

  async function rerunCurrent() {
    if (!run) return;
    await rerunFromRun(run);
  }

  async function confirmRerunAndEdit(sourceItem) {
    // 先加载完整 run 数据
    const fullRun = await fetchRun(sourceItem.run_id);
    if (!fullRun?.template_input) return;
    // 预填模板并跳转到新建讨论页
    setTemplate({ ...emptyTemplate, ...fullRun.template_input });
    if (fullRun.mode) setDiscussionMode(fullRun.mode);
    if (fullRun.selected_agents?.length) setSelectedAgents(fullRun.selected_agents);
    setRounds(inferRunRounds(fullRun));
    setParallelFirstRound(inferParallelFirstRound(fullRun));
    setActivePage("create");
  }

  async function cancelCurrent() {
    if (!run?.run_id || !loading) return;
    try {
      const response = await fetch(`${API_BASE}/api/runs/${run.run_id}/cancel`, { method: "POST" });
      if (!response.ok) {
        const detail = await readError(response);
        throw new Error(detail || "停止失败");
      }
      const data = await response.json();
      setRun(data);
      setLoading(false);
    } catch (err) {
      setError(err.message || "停止失败");
    }
  }

  async function downloadRunReport(sourceRun) {
    if (!sourceRun?.final_report) return;
    downloadMarkdown(sourceRun.final_report, reportFilename(sourceRun));
  }

  async function downloadRunJson(sourceRun) {
    if (!sourceRun) return;
    downloadJsonFile(sourceRun, runJsonFilename(sourceRun));
  }

  async function downloadRunBundleFile(sourceRun) {
    if (!sourceRun?.final_report && !sourceRun?.group_summary) return;
    downloadRunBundle(sourceRun);
  }

  async function downloadCurrentReport() {
    if (!run?.final_report) return;
    await downloadRunReport(run);
  }

  async function downloadCurrentJson() {
    if (!run) return;
    await downloadRunJson(run);
  }

  async function downloadCurrentBundle() {
    if (!run?.final_report && !run?.group_summary) return;
    await downloadRunBundleFile(run);
  }

  function exportPDF(content, title) {
    if (!content) return;
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title><style>
      body{font-family:Inter,system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#1a2a28;line-height:1.7;font-size:14px}
      h1{font-size:24px;color:#2f9d89;border-bottom:2px solid #2f9d89;padding-bottom:8px}
      h2{font-size:18px;color:#1a2a28;margin-top:28px}
      h3{font-size:15px;color:#51665f}
      blockquote{border-left:3px solid #2f9d89;padding-left:12px;color:#51665f;margin:12px 0}
      code{background:#f3f7f4;padding:2px 6px;border-radius:4px;font-size:13px}
      pre{background:#f3f7f4;padding:14px;border-radius:8px;overflow-x:auto}
      table{border-collapse:collapse;width:100%;margin:12px 0}
      th,td{border:1px solid #ccd9d2;padding:8px 10px;text-align:left;font-size:13px}
      th{background:#e8efea;font-weight:700}
      ul,ol{padding-left:22px}
      hr{border:0;border-top:1px solid #ccd9d2;margin:20px 0}
      @media print{body{margin:0;padding:20px;max-width:none}}
    </style></head><body>${markdownToHtml(content)}</body></html>`;
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 400);
  }

  async function copyReport() {
    if (!run?.final_report) return;
    await navigator.clipboard.writeText(run.final_report);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  async function deleteSelectedHistory() {
    if (!selectedHistory.length) {
      setError("请先勾选要删除的历史记录。");
      return;
    }
    setError("");
    const response = await fetch(`${API_BASE}/api/history/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_ids: selectedHistory }),
    });
    if (!response.ok) throw new Error(await readError(response));
    if (run && selectedHistory.includes(run.run_id)) setRun(null);
    setSelectedHistory([]);
    await loadHistory();
  }

  async function showHistoryLocation() {
    setError("");
    const response = await fetch(`${API_BASE}/api/history/location`);
    if (!response.ok) throw new Error(await readError(response));
    const location = await response.json();
    setHistoryLocation(`历史记录文件夹：${location.folder}`);
  }

  // ── V2 页面路由 ──
  const [activePage, setActivePage] = React.useState("overview");
  const [discussionMode, setDiscussionMode] = React.useState("full");
  const [selectedAgents, setSelectedAgents] = React.useState(["novelty", "mechanism"]);
  const [probeAgent, setProbeAgent] = React.useState("reviewer");
  const [probeQuestion, setProbeQuestion] = React.useState("");
  const navItems = [
    ["overview", "总览", Sparkles],
    ["create", "新建讨论", Play],
    ["debate", "讨论台", Brain],
    ["report", "报告", Clipboard],
    ["refs", "外部论据", BookOpen],
    ["history", "历史", History],
  ];

  async function handleCreateAndGo(options = {}) {
    await createRun(options.templateOverride || undefined, options);
    setActivePage("debate");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Brain size={24} strokeWidth={2.2} />
          </div>
          <div>
            <h1>K-Storm</h1>
            <p>科研选题多 Agent 头脑风暴工作流</p>
          </div>
        </div>
        <div className="header-actions">
          <button className="icon-button" onClick={() => setSettingsOpen(true)}>
            <Settings size={18} />
            <span>模型设置</span>
          </button>
          <div className="status-pill">
            <Sparkles size={16} />
            {run?.status ?? "READY"}
          </div>
        </div>
      </header>

      {error ? (
        <div className="error-banner">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button className="error-close" onClick={() => setError("")}>
            ×
          </button>
        </div>
      ) : null}

      <section className="workspace">
        <nav className="left-nav">
          {navItems.map(([key, label, Icon]) => (
            <button
              key={key}
              className={`nav-item ${activePage === key ? "active" : ""}`}
              onClick={() => setActivePage(key)}
            >
              <Icon size={18} />
              {label}
              {key === "history" && history.length > 0 ? (
                <span className="nav-badge">{history.length}</span>
              ) : null}
            </button>
          ))}
        </nav>

        <section className="main-stage">
          <div className={`page ${activePage === "overview" ? "active" : ""}`}>
            <OverviewPage
              run={run}
              history={history}
              loading={loading}
              onPageNavigate={setActivePage}
              onOpenRun={openRun}
            />
          </div>
          <div className={`page ${activePage === "create" ? "active" : ""}`}>
            <div style={{ display: "grid", gap: 20 }}>
              <div className="panel">
                <div className="panel-title">
                  <div>
                    <h2>新建讨论</h2>
                    <p>配置模板参数并选择讨论模式</p>
                  </div>
                </div>
              </div>
              <ModeSelector mode={discussionMode} onChange={setDiscussionMode} selectedAgents={selectedAgents} setSelectedAgents={setSelectedAgents} probeAgent={probeAgent} setProbeAgent={setProbeAgent} probeQuestion={probeQuestion} setProbeQuestion={setProbeQuestion} rounds={rounds} setRounds={setRounds} parallelFirstRound={parallelFirstRound} setParallelFirstRound={setParallelFirstRound} />
              {discussionMode === "memory" ? (
                <MemoryQueryPanel history={history} run={run} setRun={setRun} setError={setError} onStartRun={handleCreateAndGo} />
              ) : (
              <TemplatePanel
                template={template}
                setTemplate={setTemplate}
                completion={completion}
                canSubmit={canSubmit}
                loading={loading}
                rounds={rounds}
                setRounds={setRounds}
                parallelFirstRound={parallelFirstRound}
                setParallelFirstRound={setParallelFirstRound}
                documents={documents}
                addDocuments={addDocuments}
                updateDocument={updateDocument}
                removeDocument={removeDocument}
                onSubmit={handleCreateAndGo}
                mode={discussionMode}
              />
              )}
            </div>
          </div>
          <div className={`page ${activePage === "debate" ? "active" : ""}`}>
            <DebatePage
              run={run}
              loading={loading}
              activeRounds={activeRounds}
              onRerun={rerunCurrent}
              onCancel={cancelCurrent}
              onConfirmRerun={confirmRerunAndEdit}
            />
          </div>
          <div className={`page ${activePage === "report" ? "active" : ""}`}>
            <div style={{ display: "grid", gap: 20 }}>
              <div className="panel">
                <div className="panel-title">
                  <div>
                    <h2>报告</h2>
                    <p>查看最终分析报告并导出</p>
                  </div>
                </div>
              </div>
              <ReportView
                run={run}
                copied={copied}
                onCopy={copyReport}
                onDownloadReport={downloadCurrentReport}
                onDownloadJson={downloadCurrentJson}
                onDownloadBundle={downloadCurrentBundle}
                onExportPDF={() => exportPDF(run?.final_report, `K-Storm 报告 ${run?.run_id || ""}`)}
                onNavigate={setActivePage}
              />
            </div>
          </div>
          <div className={`page ${activePage === "refs" ? "active" : ""}`}>
            <ReferencesPage
              run={run}
              setRun={setRun}
              setError={setError}
              onNavigate={setActivePage}
              history={history}
              openRun={(runId) => { openRun(runId); }}
            />
          </div>
          <div className={`page ${activePage === "history" ? "active" : ""}`}>
            <div style={{ display: "grid", gap: 20 }}>
              <div className="panel">
                <div className="panel-title">
                  <div>
                    <h2>历史记录</h2>
                    <p>浏览和管理所有运行记录</p>
                  </div>
                </div>
              </div>
              <HistoryView
              history={history}
              location={historyLocation}
              selected={selectedHistory}
              setSelected={setSelectedHistory}
              onDelete={() =>
                deleteSelectedHistory().catch((err) =>
                  setError(err.message || "删除失败"),
                )
              }
              onLocation={() =>
                showHistoryLocation().catch((err) =>
                  setError(err.message || "读取位置失败"),
                )
              }
              onOpen={async (runId) => {
                const data = await openRun(runId);
                setActivePage("debate");
                return data;
              }}
              onRerunRun={rerunFromRun}
              onDownloadReportRun={downloadRunReport}
              onDownloadJsonRun={downloadRunJson}
              onDownloadBundleRun={downloadRunBundleFile}
              onConfirmRerunRun={confirmRerunAndEdit}
              onExportPDF={(content, title) => exportPDF(content, title)}
              loading={loading}
            />
            </div>
          </div>
        </section>

        <aside className="intel-rail">
          <IntelRail
            run={run}
            loading={loading}
            modelSettings={modelSettings}
            activePage={activePage}
            onNavigate={setActivePage}
            onCopy={copyReport}
            onDownloadReport={downloadCurrentReport}
            onDownloadJson={downloadCurrentJson}
            onDownloadBundle={downloadCurrentBundle}
            onExportPDF={() => exportPDF(run?.final_report, `K-Storm 报告 ${run?.run_id || ""}`)}
          />
        </aside>
      </section>
      {settingsOpen ? (
        <SettingsModal
          settings={modelSettings}
          setSettings={setModelSettings}
          onClose={() => setSettingsOpen(false)}
          setError={setError}
        />
      ) : null}
    </main>
  );
}

function agentKeyFromDisplay(displayName) {
  const map = {
    "Novelty Agent": "novelty",
    "Mechanism Agent": "mechanism",
    "Feasibility Agent": "feasibility",
    "Reviewer Agent": "reviewer",
    "Moderator": "moderator",
    "Intake Agent": "intake",
    "Group Summarizer": "group_summarizer",
    "Output Agent": "output",
  };
  return map[displayName] || displayName.toLowerCase().split(" ")[0];
}

const DEBATE_AGENTS = [
  { key: "novelty", label: "Novelty Agent", role: "创新性" },
  { key: "mechanism", label: "Mechanism Agent", role: "机制深挖" },
  { key: "feasibility", label: "Feasibility Agent", role: "可行性" },
  { key: "reviewer", label: "Reviewer Agent", role: "审稿/评审" },
];

function ModeSelector({ mode, onChange, selectedAgents, setSelectedAgents, probeAgent, setProbeAgent, probeQuestion, setProbeQuestion, rounds, setRounds, parallelFirstRound, setParallelFirstRound }) {
  const modes = [
    { key: "full", label: "完整讨论", desc: "多轮全员辩论 + IR 总结", agents: 8, rounds: "2-5" },
    { key: "focused", label: "聚焦小节", desc: "仅关键 Agent 精准讨论", agents: "2-3", rounds: "1-2" },
    { key: "quick", label: "快速探测", desc: "单 Agent 单次问答", agents: 1, rounds: "1" },
    { key: "memory", label: "记忆查询", desc: "检索历史 Run 的洞察", agents: 0, rounds: "0" },
  ];

  function toggleAgent(key) {
    setSelectedAgents((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  }

  return (
    <div className="mode-selector">
      <div className="mode-selector-title">讨论模式</div>
      <div className="mode-selector-desc">选择适合当前场景的工作流模式</div>
      <div className="mode-options">
        {modes.map((m) => (
          <button
            key={m.key}
            className={`mode-option ${mode === m.key ? "active" : ""}`}
            onClick={() => onChange(m.key)}
          >
            <div className="mode-option-header">
              <strong>{m.label}</strong>
              <span className="mode-option-sub">{m.desc}</span>
            </div>
            <div className="mode-option-meta">
              <span>{m.agents} Agent</span>
              <span>{m.rounds} 轮</span>
            </div>
          </button>
        ))}
      </div>

      {mode === "focused" ? (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)", marginBottom: 8 }}>选择参与的 Agent（2-3 个）</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {DEBATE_AGENTS.map((a) => (
              <button
                key={a.key}
                className={`icon-button ${selectedAgents.includes(a.key) ? "active" : ""}`}
                style={{
                  background: selectedAgents.includes(a.key) ? "var(--accent-soft)" : undefined,
                  borderColor: selectedAgents.includes(a.key) ? "var(--accent)" : undefined,
                  color: selectedAgents.includes(a.key) ? "var(--accent-strong)" : undefined,
                  fontSize: 13,
                }}
                onClick={() => toggleAgent(a.key)}
              >
                {a.role}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {mode === "quick" ? (
        <div style={{ marginTop: 16, display: "grid", gap: 10 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)" }}>选择提问的 Agent</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {DEBATE_AGENTS.map((a) => (
              <button
                key={a.key}
                className={`icon-button ${probeAgent === a.key ? "active" : ""}`}
                style={{
                  background: probeAgent === a.key ? "var(--accent-soft)" : undefined,
                  borderColor: probeAgent === a.key ? "var(--accent)" : undefined,
                  color: probeAgent === a.key ? "var(--accent-strong)" : undefined,
                  fontSize: 13,
                }}
                onClick={() => setProbeAgent(a.key)}
              >
                {a.role}
              </button>
            ))}
          </div>
          <label className="field">
            <span>具体问题</span>
            <textarea
              rows={2}
              value={probeQuestion}
              placeholder="输入你想问的具体问题，留空则基于模板背景自动生成"
              onChange={(e) => setProbeQuestion(e.target.value)}
            />
          </label>
        </div>
      ) : null}

      {mode === "memory" ? (
        <div style={{ marginTop: 16, color: "var(--muted)", fontSize: 13 }}>
          记忆查询模式将检索历史 Run 的结构化结论。此功能需要先有至少一次完整讨论的记录。
        </div>
      ) : null}

      {(mode === "full" || mode === "focused") ? (
        <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>讨论轮次</span>
          <input
            type="text"
            inputMode="numeric"
            value={rounds}
            style={{ width: 56, textAlign: "center", fontSize: 14, fontWeight: 600 }}
            onChange={(event) => {
              const raw = event.target.value.replace(/[^0-9]/g, "");
              if (raw === "") { setRounds(""); return; }
              const value = Number.parseInt(raw, 10);
              const maxR = mode === "focused" ? 2 : 5;
              setRounds(Math.min(maxR, Math.max(1, value)));
            }}
            onBlur={() => {
              const maxR = mode === "focused" ? 2 : 5;
              const r = Number.parseInt(rounds, 10);
              setRounds(Number.isFinite(r) && r >= 1 ? Math.min(maxR, r) : (mode === "focused" ? 1 : 3));
            }}
          />
          <span style={{ fontSize: 12, color: "var(--muted)" }}>轮（{mode === "focused" ? "1-2" : "1-5"}）</span>
        </div>
      ) : null}

      {mode === "full" ? (
        <label className="checkbox-row parallel-option" style={{ marginTop: 8 }}>
          <input
            checked={parallelFirstRound}
            type="checkbox"
            onChange={(event) => setParallelFirstRound(event.target.checked)}
          />
          <span>第 1 轮并行独立发言</span>
        </label>
      ) : null}
    </div>
  );
}

function TemplatePanel({
  template,
  setTemplate,
  completion,
  canSubmit,
  loading,
  rounds,
  setRounds,
  parallelFirstRound,
  setParallelFirstRound,
  documents,
  addDocuments,
  updateDocument,
  removeDocument,
  onSubmit,
  mode = "full",
}) {
  const isQuickOrMemory = mode === "quick" || mode === "memory";
  const submitLabel = mode === "quick" ? "快速探测" : mode === "memory" ? "查询记忆" : mode === "focused" ? "启动专题研讨" : "开始分析";
  return (
    <div className="panel" style={{ display: "grid", gap: 0, overflow: "auto" }}>
      <div className="pane-heading">
        <div>
          <h2>{{full: "头脑风暴", focused: "头脑风暴聚焦版", quick: "头脑风暴快速版"}[mode] || "头脑风暴"}</h2>
          <p>{{full: "完整选题讨论，适合开题方向探索、多方案对比评估、多视角交叉验证的复杂问题。", focused: "精选关键 Agent 定向讨论，适合验证单一方向、深挖机制假设或评估可行性。", quick: "单 Agent 快速问答，适合初步判断一个想法是否值得深入。"}[mode] || ""}</p>
        </div>
        <div
          className="completion"
          aria-label={`模板完成度 ${completion}%`}
          style={{ "--progress": `${completion}%` }}
        >
          <span>{completion}%</span>
        </div>
      </div>

      <div className="form-grid">
        {(() => {
          const topRowKeys = ["field", "background", "existing_basis"];
          const rightColKeys = ["core_question", "platforms", "constraints"];
          const bottomRowKeys = ["extension_points", "target_output", "preferred_direction", "avoid_direction"];
          const filtered = formFields.filter(([key]) => {
            if (mode === "quick") return ["field", "background", "existing_basis", "core_question"].includes(key);
            if (mode === "focused") return ["field", "background", "existing_basis", "core_question", "platforms", "constraints"].includes(key);
            return true;
          });
          const topFields = filtered.filter(([key]) => topRowKeys.includes(key));
          const rightFields = filtered.filter(([key]) => rightColKeys.includes(key));
          const bottomFields = filtered.filter(([key]) => bottomRowKeys.includes(key));
          const fieldFn = (key, label, placeholder, rows) => (
            <label className="field" key={key}>
              <span>
                {label}
                {requiredFields.includes(key) ? <b>*</b> : null}
              </span>
              <textarea
                rows={rows}
                value={template[key]}
                placeholder={placeholder}
                onChange={(event) =>
                  setTemplate((current) => ({ ...current, [key]: event.target.value }))
                }
              />
            </label>
          );
          return (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
              {/* 上排：前3个是大框（跨3行高度），textarea 自动撑满） */}
              {topFields.map(([key, label, placeholder]) => (
                <div key={key} style={{ gridRow: "span 3", display: "flex", flexDirection: "column" }}>
                  <label className="field" style={{ display: "flex", flexDirection: "column", flex: 1, gap: 7 }}>
                    <span>
                      {formFields.find(([k]) => k === key)?.[1] || key}
                      {requiredFields.includes(key) ? <b>*</b> : null}
                    </span>
                    <textarea
                      value={template[key]}
                      placeholder={placeholder}
                      onChange={(event) =>
                        setTemplate((current) => ({ ...current, [key]: event.target.value }))
                      }
                      style={{ flex: 1, minHeight: 0, resize: "none" }}
                    />
                  </label>
                </div>
              ))}
              {rightFields.map(([key, label, placeholder]) => (
                <div key={key}>
                  {fieldFn(key, label, placeholder, 2)}
                </div>
              ))}
              {/* 下排：4个横排一行 */}
              {bottomFields.map(([key, label, placeholder]) => (
                <div key={key} style={{ gridColumn: "span 1" }}>
                  {fieldFn(key, label, placeholder, 2)}
                </div>
              ))}
            </div>
          );
        })()}
      </div>

      <section className="document-upload">
        <div>
          <h3>上传文档</h3>
          <p>支持文本类 design / experiment-data 文档，可添加注释。</p>
        </div>
        <input
          multiple
          type="file"
          onChange={(event) => {
            addDocuments(Array.from(event.target.files || []));
            event.target.value = "";
          }}
        />
        <div className="document-list">
          {documents.length ? (
            documents.map((document) => (
              <div className="document-item" key={document.id}>
                <div className="document-row">
                  <strong>
                    {document.name}
                    <small>{formatChars(document.content?.length || 0)} 字符</small>
                  </strong>
                  <select
                    value={document.doc_type}
                    onChange={(event) =>
                      updateDocument(document.id, { doc_type: event.target.value })
                    }
                  >
                    <option value="design">design</option>
                    <option value="experiment-data">experiment-data</option>
                    <option value="other">other</option>
                  </select>
                  <button
                    className="danger-button"
                    onClick={() => removeDocument(document.id)}
                  >
                    删除
                  </button>
                </div>
                <textarea
                  rows={2}
                  value={document.note}
                  placeholder="为该文档添加注释"
                  onChange={(event) =>
                    updateDocument(document.id, { note: event.target.value })
                  }
                />
              </div>
            ))
          ) : (
            <div className="empty-line">还没有上传文档。</div>
          )}
        </div>
      </section>

      {!isQuickOrMemory ? null : null}
      <button
        className="primary-action"
        disabled={!canSubmit || loading}
        onClick={onSubmit}
      >
        {loading ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}
        {loading ? "分析中" : submitLabel}
      </button>
    </div>
  );
}

function MemoryQueryPanel({ history, run, setRun, setError, onStartRun }) {
  const [selectedRunId, setSelectedRunId] = React.useState("");
  const [loadedRun, setLoadedRun] = React.useState(null);
  const [memoryAgents, setMemoryAgents] = React.useState(["novelty", "mechanism"]);
  const [memoryRounds, setMemoryRounds] = React.useState(1);
  const [memoryParallel, setMemoryParallel] = React.useState(false);
  const [memoryQuestion, setMemoryQuestion] = React.useState("");

  const completedRuns = React.useMemo(
    () => history.filter((h) => h.status === "COMPLETED"),
    [history],
  );

  async function loadMemory() {
    if (!selectedRunId) return;
    try {
      const resp = await fetch(`${API_BASE}/api/runs/${selectedRunId}`);
      if (!resp.ok) throw new Error("加载失败");
      const data = await resp.json();
      setLoadedRun(data);
    } catch (err) {
      setError(err.message);
    }
  }

  function resetSelection() {
    setLoadedRun(null);
    setSelectedRunId("");
    setMemoryQuestion("");
  }

  function toggleAgent(key) {
    setMemoryAgents((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key],
    );
  }

  function handleStart() {
    if (!loadedRun || !memoryQuestion.trim()) return;
    const newTemplate = {
      ...loadedRun.template_input,
      core_question: memoryQuestion,
    };
    onStartRun({
      templateOverride: newTemplate,
      sourceRunId: loadedRun.run_id,
      overrideMode: "memory",
      selectedAgents: memoryAgents,
      rounds: memoryRounds,
      parallelFirstRound: memoryParallel,
    });
  }

  // Build summary from structured_brief
  const brief = loadedRun?.structured_brief;
  const summaryItems = React.useMemo(() => {
    if (!brief) return [];
    const items = [];
    if (brief.known_facts?.length) items.push({ label: "已知事实", values: brief.known_facts.slice(0, 3) });
    if (brief.unknowns?.length) items.push({ label: "未知问题", values: brief.unknowns.slice(0, 3) });
    if (brief.constraints?.length) items.push({ label: "约束条件", values: brief.constraints.slice(0, 2) });
    if (brief.opportunity_points?.length) items.push({ label: "机会点", values: brief.opportunity_points.slice(0, 2) });
    return items;
  }, [brief]);

  return (
    <div className="panel" style={{ display: "grid", gap: 16, overflow: "auto" }}>
      <div className="pane-heading">
        <div>
          <h2>记忆查询</h2>
          <p>选择一次历史完整讨论，读取记忆后基于它提出新问题。</p>
        </div>
      </div>

      {!completedRuns.length ? (
        <div className="empty-state">
          <FlaskConical size={28} />
          <span>还没有已完成的历史讨论。请先运行一次完整讨论模式。</span>
        </div>
      ) : loadedRun ? (
        /* ── 已加载记忆：折叠列表，显示选中项 + 摘要 + 提问 ── */
        <div style={{ display: "grid", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--accent-soft)", border: "1px solid var(--accent)", borderRadius: "var(--radius-sm)", padding: "12px 16px" }}>
            <div>
              <div style={{ color: "var(--accent-strong)", fontWeight: 700, fontSize: 14 }}>已读取记忆：{loadedRun.template_input?.field || loadedRun.run_id}</div>
              <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>{new Date(loadedRun.created_at).toLocaleString()} · {loadedRun.debate_messages?.length || 0} 条发言</div>
            </div>
            <button className="icon-button" onClick={resetSelection} style={{ fontSize: 12, minHeight: 32 }}>
              重新选择
            </button>
          </div>

          {summaryItems.length ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)" }}>记忆摘要</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
                {summaryItems.map(({ label, values }) => (
                  <div key={label} style={{ background: "var(--panel-muted)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "10px 12px", overflow: "hidden" }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-strong)", marginBottom: 4 }}>{label}</div>
                    {values.map((v, i) => (
                      <div key={i} style={{ fontSize: 12, color: "var(--ink-soft)", lineHeight: 1.5, overflowWrap: "break-word", wordBreak: "break-word" }}>· {v}</div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {brief?.intake_synthesis ? (
            <div style={{ background: "var(--panel-muted)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "12px" }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-strong)", marginBottom: 6 }}>入口整合 Briefing</div>
              <div
                className="markdown-rendered"
                style={{ fontSize: 13, lineHeight: 1.6, maxHeight: 160, overflow: "auto" }}
                dangerouslySetInnerHTML={{ __html: markdownToHtml(brief.intake_synthesis.slice(0, 800) + (brief.intake_synthesis.length > 800 ? "..." : "")) }}
              />
            </div>
          ) : null}

          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14, display: "grid", gap: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)" }}>配置讨论参数</div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>选择 Agent</span>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {DEBATE_AGENTS.map((a) => (
                  <button
                    key={a.key}
                    className="icon-button"
                    style={{
                      background: memoryAgents.includes(a.key) ? "var(--accent-soft)" : undefined,
                      borderColor: memoryAgents.includes(a.key) ? "var(--accent)" : undefined,
                      color: memoryAgents.includes(a.key) ? "var(--accent-strong)" : undefined,
                      fontSize: 12, minHeight: 30,
                    }}
                    onClick={() => toggleAgent(a.key)}
                  >{a.role}</button>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>讨论轮次</span>
              <input
                type="text"
                inputMode="numeric"
                value={memoryRounds}
                style={{ width: 48, textAlign: "center", fontSize: 14, fontWeight: 600 }}
                onChange={(e) => {
                  const raw = e.target.value.replace(/[^0-9]/g, "");
                  if (raw === "") { setMemoryRounds(""); return; }
                  setMemoryRounds(Math.min(5, Math.max(1, Number.parseInt(raw, 10))));
                }}
                onBlur={() => {
                  const r = Number.parseInt(memoryRounds, 10);
                  setMemoryRounds(Number.isFinite(r) && r >= 1 ? Math.min(5, r) : 1);
                }}
              />
              <span style={{ fontSize: 12, color: "var(--muted)" }}>轮（1-5）</span>
            </div>

            <label className="checkbox-row parallel-option" style={{ marginTop: 0 }}>
              <input
                checked={memoryParallel}
                type="checkbox"
                onChange={(e) => setMemoryParallel(e.target.checked)}
              />
              <span>第 1 轮并行独立发言</span>
            </label>

            <label className="field">
              <span>新问题</span>
              <textarea
                rows={3}
                value={memoryQuestion}
                placeholder="基于记忆提出新问题，例如：上次讨论提到的 XX 方向，如果从 YY 角度切入会怎样？"
                onChange={(e) => setMemoryQuestion(e.target.value)}
              />
            </label>

            <button
              className="primary-action"
              disabled={!memoryQuestion.trim() || memoryAgents.length < 1}
              onClick={handleStart}
            >
              <Play size={18} />
              启动讨论
            </button>
          </div>
        </div>
      ) : (
        /* ── 未加载记忆：显示历史列表 ── */
        <div style={{ display: "grid", gap: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)" }}>选择历史讨论</div>
          <div className="history-list">
            {completedRuns.map((item) => (
              <button
                key={item.run_id}
                className={`history-item ${selectedRunId === item.run_id ? "active" : ""}`}
                onClick={() => setSelectedRunId(item.run_id)}
                style={{
                  cursor: "pointer",
                  borderLeft: selectedRunId === item.run_id ? "4px solid var(--accent)" : undefined,
                  background: selectedRunId === item.run_id ? "var(--accent-soft)" : undefined,
                }}
              >
                <span>{item.field}</span>
                <small>{new Date(item.created_at).toLocaleString()}</small>
              </button>
            ))}
          </div>
          <button className="primary-action" disabled={!selectedRunId} onClick={loadMemory} style={{ marginTop: 4 }}>
            <Brain size={18} />
            读取记忆
          </button>
        </div>
      )}
    </div>
  );
}
function OverviewPage({ run, history, loading, onPageNavigate, onOpenRun }) {
  const recent = history.slice(0, 5);
  const totalRuns = history.length;
  const completedRuns = history.filter((h) => h.status === "COMPLETED").length;
  const failedRuns = history.filter((h) => h.status === "FAILED").length;
  return (
    <div style={{ display: "grid", gap: 20 }}>
      <div className="panel">
        <div className="panel-title">
          <div>
            <h2>总览</h2>
            <p>最近运行与快速入口</p>
          </div>
        </div>
      </div>

      <div className="metric-row" style={{ marginTop: 0 }}>
        <div className="metric">
          <span>总运行数</span>
          <strong>{totalRuns}</strong>
        </div>
        <div className="metric">
          <span>已完成</span>
          <strong>{completedRuns}</strong>
        </div>
        <div className="metric">
          <span>失败</span>
          <strong>{failedRuns}</strong>
        </div>
        <div className="metric">
          <span>当前状态</span>
          <strong>{loading ? "RUNNING" : run?.status ?? "READY"}</strong>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">
          <div>
            <h3>快速入口</h3>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 14 }}>
          <button className="primary-action" style={{ width: "auto", marginTop: 0 }} onClick={() => onPageNavigate("create")}>
            <Play size={18} />
            新建讨论
          </button>
          {run ? (
            <button className="icon-button" onClick={() => onPageNavigate("debate")}>
              <Brain size={18} />
              查看当前讨论
            </button>
          ) : null}
        </div>
      </div>

      <div className="panel-auto">
        <div className="panel-title">
          <div>
            <h3>最近讨论</h3>
            <p>{recent.length ? `最近 ${recent.length} 条运行记录` : "暂无历史记录"}</p>
          </div>
          {recent.length ? (
            <button className="icon-button" onClick={() => onPageNavigate("history")}>
              查看全部
            </button>
          ) : null}
        </div>
        {recent.length ? (
          <div className="history-list" style={{ marginTop: 16 }}>
            {recent.map((item) => (
              <button
                key={item.run_id}
                className="history-item"
                onClick={() => onOpenRun(item.run_id)}
                style={{ cursor: "pointer" }}
              >
                <span>{item.field}</span>
                <small>{item.status} · {new Date(item.created_at).toLocaleString()}</small>
              </button>
            ))}
          </div>
        ) : (
          <div className="empty-state" style={{ marginTop: 16 }}>
            <FlaskConical size={28} />
            <span>还没有运行记录，点击“新建讨论”开始。</span>
          </div>
        )}
      </div>
    </div>
  );
}

function DebatePage({ run, loading, activeRounds, onRerun, onCancel, onConfirmRerun }) {
  return (
    <div style={{ display: "grid", gap: 20 }}>
      <RunOverview run={run} loading={loading} activeRounds={activeRounds} onRerun={onRerun} onCancel={onCancel} onConfirmRerun={onConfirmRerun} />
      <DebateView run={run} />
    </div>
  );
}

function IntelRail({ run, loading, modelSettings, activePage, onNavigate, onCopy, onDownloadReport, onDownloadJson, onDownloadBundle, onExportPDF }) {
  const brief = run?.structured_brief;
  const assignments = modelSettings.assignments || {};
  const assignmentEntries = Object.entries(assignments);
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="intel-card">
        <h3>当前 Run</h3>
        {run ? (
          <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
            <div className="intel-row"><span>Run ID</span><strong>{run.run_id?.slice(0, 12)}</strong></div>
            <div className="intel-row">
              <span>状态</span>
              <strong>
                <span className={`status-badge ${run.status === "COMPLETED" ? "completed" : run.status === "FAILED" ? "failed" : run.status === "RUNNING" ? "running" : "pending"}`}>
                  {loading ? "RUNNING" : run.status}
                </span>
              </strong>
            </div>
            {run.field ? <div className="intel-row"><span>领域</span><strong style={{fontSize:12}}>{run.field.length > 20 ? run.field.slice(0,20) + "..." : run.field}</strong></div> : null}
          </div>
        ) : (
          <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 8 }}>尚未启动</div>
        )}
      </div>

      <div className="intel-card">
        <h3>快速操作</h3>
        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
          <button className="icon-button" style={{ width: "100%" }} onClick={() => onNavigate("create")}>
            <Play size={16} /> 新建讨论
          </button>
          {run ? (
            <button className="icon-button" style={{ width: "100%" }} onClick={() => onNavigate("debate")}>
              <Brain size={16} /> 查看讨论
            </button>
          ) : null}
          {run?.final_report ? (
            <button className="icon-button" style={{ width: "100%" }} onClick={() => onNavigate("report")}>
              <Clipboard size={16} /> 查看报告
            </button>
          ) : null}
        </div>
      </div>

      {assignmentEntries.length > 0 ? (
        <div className="intel-card">
          <h3>模型分配</h3>
          <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
            {assignmentEntries.map(([agentKey, modelRef]) => (
              <div className="intel-row" key={agentKey}>
                <span>{agentKey}</span>
                <strong>{modelRef.split(":").pop()}</strong>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="intel-card">
        <h3>导出</h3>
        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
          <div><DownloadMenu label="报告" disabled={!run?.final_report} mdContent={run?.final_report} pdfContent={run?.final_report} pdfTitle={`K-Storm 报告 ${run?.run_id || ""}`} /></div>
          <div><DownloadMenu label="打包" disabled={!run?.final_report && !run?.group_summary} mdContent={buildBundleMD(run)} pdfContent={buildBundleMD(run)} pdfTitle={`K-Storm 打包 ${run?.run_id || ""}`} /></div>
          <button className="icon-button" style={{ width: "100%" }} disabled={!run} onClick={onDownloadJson}>
            <Download size={16} /> Run JSON
          </button>
        </div>
      </div>
    </div>
  );
}

function RunOverview({ run, loading, activeRounds, onRerun, onCancel, onConfirmRerun }) {
  const brief = run?.structured_brief;
  const isCompleted = run?.status === "COMPLETED";
  const isFailed = run?.status === "FAILED" || run?.status === "CANCELED";
  const canRerun = (isFailed || isCompleted) && !loading;
  const rerunLabel = isFailed ? "继续分析" : "重新分析";
  return (
    <section className="panel overview">
      <div className="panel-title">
        <div>
          <h2>运行概览</h2>
          <p>{run ? `Run ID：${run.run_id}` : "等待启动一次 KS 工作流"}</p>
        </div>
        <div className="header-actions">
          {loading ? (
            <button className="danger-button" style={{minHeight: 38}} onClick={onCancel}>
              停止分析
            </button>
          ) : null}
          <button className="icon-button" disabled={!canRerun} onClick={() => {
            if (isCompleted) {
              if (window.confirm("当前记录为 COMPLETED 状态，确认重新分析？")) {
                onConfirmRerun(run);
              }
            } else {
              onRerun();
            }
          }}>
            <RefreshCw size={18} />
            <span>{rerunLabel}</span>
          </button>
        </div>
      </div>

      <div className="metric-row">
        <Metric
          label="讨论轮次"
          value={
            run
              ? Math.max(...run.debate_messages.map((message) => message.round), 0)
              : "-"
          }
        />
        <Metric label="Agent 发言" value={run ? run.debate_messages.length : "-"} />
        <Metric label="状态" value={loading ? "RUNNING" : run?.status ?? "READY"} />
      </div>

      <ProgressTimeline run={run} activeRounds={activeRounds} />

      {brief ? (
        <div className="brief-grid">
          <BriefBlock title="已知事实" items={brief.known_facts} />
          <BriefBlock title="未知问题" items={brief.unknowns} />
          <BriefBlock title="约束条件" items={brief.constraints} />
          <BriefBlock title="机会点" items={brief.opportunity_points} />
          {brief.intake_synthesis ? (
            <div className="brief-block brief-wide">
              <CollapsibleMarkdown title="入口整合 Briefing" content={brief.intake_synthesis} />
            </div>
          ) : null}
        </div>
      ) : (
        <div className="empty-state">
          <FlaskConical size={28} />
          <span>提交模板后，这里会显示入口 Agent 生成的结构化 briefing。</span>
        </div>
      )}
    </section>
  );
}

function CollapsibleMarkdown({ title, content }) {
  const [expanded, setExpanded] = React.useState(false);
  const bodyRef = React.useRef(null);
  const scrollTopRef = React.useRef(0);
  React.useLayoutEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = scrollTopRef.current;
  });
  return (
    <div className="briefing-card">
      <div className="briefing-head">
        <h3>{title}</h3>
        <div className="inline-actions">
          <CopyButton text={content} />
          <button className="icon-button progress-toggle" onClick={() => setExpanded(!expanded)}>
            {expanded ? "收起" : "展开"}
          </button>
        </div>
      </div>
      <div
        ref={bodyRef}
        className={`briefing-body markdown-rendered ${expanded ? "expanded" : ""}`}
        onScroll={(event) => {
          scrollTopRef.current = event.currentTarget.scrollTop;
        }}
        dangerouslySetInnerHTML={{ __html: markdownToHtml(content) }}
      />
    </div>
  );
}

function DownloadMenu({ label, icon, mdContent, pdfContent, pdfTitle, disabled }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  function handleMD() {
    setOpen(false);
    if (!mdContent) return;
    downloadMarkdown(mdContent, (pdfTitle || "K-Storm").replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, "_").slice(0, 40));
  }
  function handlePDF() {
    setOpen(false);
    const content = pdfContent || mdContent;
    if (!content) return;
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${pdfTitle || "K-Storm"}</title><style>
      body{font-family:Inter,system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#1a2a28;line-height:1.7;font-size:14px}
      h1{font-size:24px;color:#2f9d89;border-bottom:2px solid #2f9d89;padding-bottom:8px}
      h2{font-size:18px;color:#1a2a28;margin-top:28px}
      h3{font-size:15px;color:#51665f}
      blockquote{border-left:3px solid #2f9d89;padding-left:12px;color:#51665f;margin:12px 0}
      code{background:#f3f7f4;padding:2px 6px;border-radius:4px;font-size:13px}
      pre{background:#f3f7f4;padding:14px;border-radius:8px;overflow-x:auto}
      table{border-collapse:collapse;width:100%;margin:12px 0}
      th,td{border:1px solid #ccd9d2;padding:8px 10px;text-align:left;font-size:13px}
      th{background:#e8efea;font-weight:700}
      ul,ol{padding-left:22px}
      hr{border:0;border-top:1px solid #ccd9d2;margin:20px 0}
      @media print{body{margin:0;padding:20px;max-width:none}}
    </style></head><body>${markdownToHtml(content)}</body></html>`;
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 400);
  }

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <button className="icon-button" disabled={disabled} onClick={() => setOpen(!open)} style={{ whiteSpace: "nowrap" }}>
        {icon || <Download size={16} />}
        <span>{label || "下载"}</span>
      </button>
      {open ? (
        <div style={{ position: "absolute", right: 0, top: "100%", marginTop: 4, background: "var(--panel-strong)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", boxShadow: "0 4px 16px rgba(0,0,0,0.12)", zIndex: 50, minWidth: 140 }}>
          <button onClick={handleMD} style={{ display: "block", width: "100%", border: "none", background: "transparent", padding: "8px 14px", cursor: "pointer", fontSize: 13, color: "var(--ink)", textAlign: "left" }} onMouseEnter={(e) => e.currentTarget.style.background = "var(--panel-muted)"} onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>Markdown (.md)</button>
          <button onClick={handlePDF} style={{ display: "block", width: "100%", border: "none", background: "transparent", padding: "8px 14px", cursor: "pointer", fontSize: 13, color: "var(--ink)", textAlign: "left", borderTop: "1px solid var(--border)" }} onMouseEnter={(e) => e.currentTarget.style.background = "var(--panel-muted)"} onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>PDF (.pdf)</button>
        </div>
      ) : null}
    </div>
  );
}

function CopyButton({ text, className = "" }) {
  const [copied, setCopied] = React.useState(false);
  return (
    <button
      className={`icon-button copy-mini ${className}`}
      disabled={!text}
      onClick={async () => {
        if (!text) return;
        await navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1400);
      }}
    >
      {copied ? "已复制" : "复制"}
    </button>
  );
}

function ProgressTimeline({ run, activeRounds }) {
  const [expanded, setExpanded] = React.useState(false);
  if (!run) return null;
  if (run.timeline?.length) {
    const rows = run.timeline.filter((step) => !step.is_overall);
    const overall = run.timeline.find((step) => step.is_overall);
    const visibleRows = progressRows(rows, overall, expanded);
    return (
      <div className="progress-list">
        <div className="progress-toolbar">
          <small>{expanded ? "完整运行状态" : "当前运行状态"}</small>
          <button className="icon-button progress-toggle" onClick={() => setExpanded(!expanded)}>
            {expanded ? "收起" : "展开"}
          </button>
        </div>
        {visibleRows.map(({ step, overall: isOverall }) => (
          <TimelineStepRow key={step.key} step={step} overall={isOverall} />
        ))}
      </div>
    );
  }
  const totalDebateMessages = activeRounds * 4;
  const debateDone = run.debate_messages.length;
  const status = run.status;
  const steps = [
    [
      "创建运行并校验模板",
      ["INTAKE_RUNNING", "DEBATE_RUNNING", "GROUP_SUMMARY_RUNNING", "FINAL_REPORT_RUNNING", "COMPLETED"].includes(status),
      ["CREATED", "TEMPLATE_VALIDATED"].includes(status),
    ],
    ["入口模型整理模板与上传文档", Boolean(run.structured_brief), status === "INTAKE_RUNNING"],
    ["信息传送到讨论组", Boolean(run.structured_brief), status === "DEBATE_RUNNING" && debateDone === 0],
    ...run.debate_messages.map((message) => [
      `${message.agent} 发言（第 ${message.round} 轮）`,
      true,
      false,
    ]),
  ];
  if (status === "DEBATE_RUNNING" && debateDone < totalDebateMessages) {
    const order = ["Novelty Agent", "Mechanism Agent", "Feasibility Agent", "Reviewer Agent"];
    steps.push([run.current_step || `${order[debateDone % 4]} 发言中`, false, true]);
  }
  steps.push(["结构化 IR", Boolean(run.group_summary), status === "GROUP_SUMMARY_RUNNING"]);
  steps.push(["出口模型生成最终报告", Boolean(run.final_report), status === "FINAL_REPORT_RUNNING"]);
  if (status === "COMPLETED") steps.push(["运行完成", true, false]);
  if (status === "FAILED") {
    steps.push([`运行失败${run.error ? `：${run.error}` : ""}`, false, true]);
  }

  return (
    <div className="progress-list">
      {steps.map(([label, done, active], index) => (
        <div
          className={`progress-step ${done ? "done" : ""} ${active ? "active" : ""}`}
          key={`${label}-${index}`}
        >
          <span className="progress-dot" />
          <span className="progress-label">{label}</span>
          <span className="progress-time" />
        </div>
      ))}
    </div>
  );
}

function progressRows(rows, overall, expanded) {
  if (expanded) {
    return [
      ...rows.map((step) => ({ step, overall: false })),
      ...(overall ? [{ step: overall, overall: true }] : []),
    ];
  }
  const current = rows.find(
    (step) => step.status === "running" || step.status === "failed",
  );
  if (current) return [{ step: current, overall: false }];
  if (overall && ["running", "failed", "completed"].includes(overall.status)) {
    return [{ step: overall, overall: true }];
  }
  const lastDone = [...rows].reverse().find((step) => step.status === "completed");
  return lastDone ? [{ step: lastDone, overall: false }] : rows.slice(0, 1).map((step) => ({ step, overall: false }));
}

function TimelineStepRow({ step, overall = false }) {
  const done = step.status === "completed";
  const active = step.status === "running" || step.status === "failed";
  return (
    <div className={`progress-step ${done ? "done" : ""} ${active ? "active" : ""} ${overall ? "progress-overall" : ""}`}>
      <span className="progress-dot" />
      <span className="progress-label">{step.label}</span>
      <span className="progress-time">{timelineTimeLabel(step)}</span>
    </div>
  );
}

function timelineTimeLabel(step) {
  if (step.status === "completed" && step.finished_at) return `完成 ${formatStepTime(step.finished_at)}`;
  if (step.status === "failed" && step.finished_at) return `失败 ${formatStepTime(step.finished_at)}`;
  if (step.estimated_done_at) return `预计 ${formatStepTime(step.estimated_done_at)}`;
  return "";
}

function formatStepTime(value) {
  try {
    return new Date(value).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function BriefBlock({ title, items }) {
  return (
    <div className="brief-block">
      <h3>{title}</h3>
      <ul>
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function inferDocumentType(name) {
  const lower = name.toLowerCase();
  if (lower.includes("design") || lower.includes("方案") || lower.includes("设计")) {
    return "design";
  }
  if (lower.includes("data") || lower.includes("experiment") || lower.includes("实验")) {
    return "experiment-data";
  }
  return "other";
}

function formatChars(count) {
  return count >= 10000 ? `${(count / 10000).toFixed(1)} 万` : String(count);
}

function DebateView({ run }) {
  const [activeRound, setActiveRound] = React.useState(1);
  const grouped = React.useMemo(() => {
    const map = new Map();
    for (const message of run?.debate_messages ?? []) {
      if (!map.has(message.round)) map.set(message.round, []);
      map.get(message.round).push(message);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a - b);
  }, [run]);
  React.useEffect(() => {
    if (grouped.length && !grouped.some(([round]) => round === activeRound)) {
      setActiveRound(grouped[0][0]);
    }
  }, [grouped, activeRound]);
  const activeMessages =
    grouped.find(([round]) => round === activeRound)?.[1] || [];

  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>讨论过程</h2>
          <p>第 1 轮可并行独立发言，第 2 轮起串行反驳/修正。</p>
        </div>
      </div>
      {grouped.length ? (
        <div className="rounds">
          <div className="round-tabs">
            {grouped.map(([round]) => (
              <button
                className={`icon-button round-tab ${round === activeRound ? "active" : ""}`}
                key={round}
                onClick={() => setActiveRound(round)}
              >
                第 {round} 轮
              </button>
            ))}
          </div>
          <div className="round">
            <div className="round-heading">第 {activeRound} 轮</div>
            <div className="message-grid">
              {activeMessages.map((message) => (
                <article className="agent-card" data-agent={agentKeyFromDisplay(message.agent)} key={`${message.round}-${message.agent}`}>
                  <div className="agent-card-header">
                    <strong>{message.agent}</strong>
                    <span className="agent-model-label">{message.model_label || ""}</span>
                    <span className="content-head">
                      <CopyButton text={message.content} />
                    </span>
                  </div>
                  <div
                    className="agent-card-body markdown-rendered"
                    dangerouslySetInnerHTML={{ __html: markdownToHtml(message.content) }}
                  />
                </article>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="empty-line">还没有讨论记录。</div>
      )}
    </section>
  );
}

function SettingsModal({ settings, setSettings, onClose, setError }) {
  const [activeProviderId, setActiveProviderId] = React.useState(
    settings.providers[0]?.id,
  );
  const [discoveredModels, setDiscoveredModels] = React.useState({});
  const [modelSearch, setModelSearch] = React.useState("");
  const [collapsedCandidates, setCollapsedCandidates] = React.useState({});
  const activeProvider =
    settings.providers.find((provider) => provider.id === activeProviderId) ??
    settings.providers[0];
  const modelOptions = settings.providers.flatMap((provider) =>
    provider.models.map((model) => ({
      value: `${provider.id}:${model.id}`,
      label: `${provider.name} / ${model.name}`,
    })),
  );

  function updateProvider(patch) {
    setSettings((current) => ({
      ...current,
      providers: current.providers.map((provider) =>
        provider.id === activeProvider.id ? { ...provider, ...patch } : provider,
      ),
    }));
  }

  function addProvider() {
    const id = `provider-${Date.now()}`;
    setSettings((current) => ({
      ...current,
      providers: [
        ...current.providers,
        {
          id,
          name: "新供应商",
          category: "api",
          api_key: "",
          base_url: "",
          api_type: "openai_compatible",
          allow_insecure_tls: false,
          models: [],
        },
      ],
    }));
    setActiveProviderId(id);
  }

  function deleteProvider() {
    setSettings((current) => {
      const providers = current.providers.filter(
        (provider) => provider.id !== activeProvider.id,
      );
      const assignments = { ...current.assignments };
      for (const key of Object.keys(assignments)) {
        if (assignments[key].startsWith(`${activeProvider.id}:`)) delete assignments[key];
      }
      return {
        providers: providers.length ? providers : defaultModelSettings.providers,
        assignments,
      };
    });
    setActiveProviderId(settings.providers[0]?.id);
  }

  function addModel() {
    addModelFromCandidate(null);
  }

  function addModelFromCandidate(candidate) {
    const typed = modelSearch.trim();
    const source = candidate || (typed ? { id: typed, name: typed, model: typed } : null);
    if (!source) {
      setError("请先读取模型并选择，或手动输入模型 ID。");
      return;
    }
    const modelId = source.model || source.id;
    if (activeProvider.models.some((model) => model.model === modelId)) {
      setError("该模型已添加。");
      return;
    }
    const next = {
      id: activeProvider.models.some((model) => model.id === source.id)
        ? `${source.id}-${Date.now()}`
        : source.id || `model-${Date.now()}`,
      name: source.name || modelId,
      model: modelId,
      context_window: source.context_window || "",
    };
    updateProvider({ models: [...activeProvider.models, next] });
    setModelSearch("");
    setError("");
  }

  function updateModel(modelId, patch) {
    updateProvider({
      models: activeProvider.models.map((model) =>
        model.id === modelId ? { ...model, ...patch } : model,
      ),
    });
  }

  function removeModel(modelId) {
    updateProvider({
      models: activeProvider.models.filter((model) => model.id !== modelId),
    });
  }

  async function discoverModels() {
    try {
      const response = await fetch(`${API_BASE}/api/models/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(activeProvider),
      });
      if (!response.ok) throw new Error(await readError(response));
      const data = await response.json();
      setDiscoveredModels((current) => ({
        ...current,
        [activeProvider.id]: data.models.map((model) => ({
          id: model.id,
          name: model.name,
          model: model.model,
          context_window: model.context_window || "",
        })),
      }));
      setCollapsedCandidates((current) => ({ ...current, [activeProvider.id]: false }));
      setModelSearch("");
      setError("");
    } catch (err) {
      setError(err.message || "读取模型失败");
    }
  }

  const candidateModels = React.useMemo(() => {
    const added = new Set(activeProvider?.models.map((model) => model.model) || []);
    const query = modelSearch.toLowerCase();
    return (discoveredModels[activeProvider?.id] || [])
      .filter((model) => !added.has(model.model || model.id))
      .filter((model) => {
        const text = `${model.name || ""} ${model.model || ""} ${model.id || ""}`.toLowerCase();
        return !query || text.includes(query);
      });
  }, [activeProvider, discoveredModels, modelSearch]);

  return (
    <section className="settings-backdrop">
      <div className="settings-modal">
        <aside className="settings-sidebar">
          <div className="panel-title">
            <div>
              <h2>供应商</h2>
              <p>API Key 仅保存在本机浏览器。</p>
            </div>
          </div>
          <div className="provider-list">
            {providerGroups.map(([category, label]) => {
              const providers = settings.providers.filter(
                (provider) => (provider.category || "api") === category,
              );
              if (!providers.length) return null;
              return (
                <React.Fragment key={category}>
                  <div className="provider-group">{label}</div>
                  {providers.map((provider) => (
                    <button
                      className={`provider-row ${provider.id === activeProvider?.id ? "active" : ""}`}
                      key={provider.id}
                      onClick={() => setActiveProviderId(provider.id)}
                    >
                      <span>{provider.name}</span>
                      <small>{provider.models.length}</small>
                    </button>
                  ))}
                </React.Fragment>
              );
            })}
          </div>
          <button className="icon-button" onClick={addProvider}>添加供应商</button>
        </aside>

        <section className="settings-content">
          <div className="panel-title">
            <div>
              <h2>{activeProvider?.name || "模型供应商"}</h2>
              <p>支持 OpenAI Compatible、Anthropic Messages、OpenAI Responses。</p>
            </div>
            <button className="danger-button" onClick={deleteProvider}>删除供应商</button>
          </div>

          <div className="settings-form">
            <label className="field">
              <span>名称</span>
              <input
                value={activeProvider?.name || ""}
                onChange={(event) => updateProvider({ name: event.target.value })}
              />
            </label>
            <label className="field">
              <span>API Key</span>
              <input
                type="password"
                value={activeProvider?.api_key || ""}
                onChange={(event) => updateProvider({ api_key: event.target.value })}
              />
            </label>
            <label className="field">
              <span>Base URL</span>
              <input
                value={activeProvider?.base_url || ""}
                placeholder="https://api.deepseek.com/v1"
                onChange={(event) => updateProvider({ base_url: event.target.value })}
              />
            </label>
            <label className="field">
              <span>API 类型</span>
              <select
                value={activeProvider?.api_type || "openai_compatible"}
                onChange={(event) => updateProvider({ api_type: event.target.value })}
              >
                {apiTypes.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>证书校验</span>
              <div className="checkbox-row">
                <input
                  type="checkbox"
                  checked={Boolean(activeProvider?.allow_insecure_tls)}
                  onChange={(event) =>
                    updateProvider({ allow_insecure_tls: event.target.checked })
                  }
                />
                允许不安全证书
              </div>
            </label>
          </div>

          <div className="panel-title">
            <div><h3>已添加的模型 {activeProvider?.models.length || 0}</h3></div>
            <button className="icon-button" onClick={discoverModels}>读取模型</button>
          </div>
          <div className="settings-list">
            {activeProvider?.models.map((model) => (
              <div className="model-row" key={model.id}>
                <input
                  value={model.name}
                  onChange={(event) => updateModel(model.id, { name: event.target.value })}
                />
                <input
                  value={model.model}
                  onChange={(event) => updateModel(model.id, { model: event.target.value })}
                />
                <button className="danger-button" onClick={() => removeModel(model.id)}>
                  删除
                </button>
              </div>
            ))}
          </div>
          <div className="model-picker">
            <div className="model-picker-row">
              <input
                value={modelSearch}
                placeholder="搜索或输入模型 ID"
                onChange={(event) => setModelSearch(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    addModelFromCandidate(candidateModels[0] || null);
                  }
                }}
              />
              <button className="icon-button" onClick={addModel}>添加模型</button>
            </div>
            {(candidateModels.length ||
              modelSearch ||
              discoveredModels[activeProvider?.id]?.length) ? (
              <div className="model-candidate-list open">
                {collapsedCandidates[activeProvider?.id] ? (
                  <div className="model-candidate-head">
                    <span>模型候选已收起</span>
                    <button
                      onClick={() =>
                        setCollapsedCandidates((current) => ({
                          ...current,
                          [activeProvider.id]: false,
                        }))
                      }
                    >
                      展开
                    </button>
                  </div>
                ) : (
                  <>
                    {discoveredModels[activeProvider?.id]?.length ? (
                      <div className="model-candidate-head">
                        <span>候选模型 {candidateModels.length}</span>
                        <button
                          onClick={() =>
                            setCollapsedCandidates((current) => ({
                              ...current,
                              [activeProvider.id]: true,
                            }))
                          }
                        >
                          收起
                        </button>
                      </div>
                    ) : null}
                    {candidateModels.length ? (
                  candidateModels.slice(0, 80).map((model) => (
                    <button
                      className="model-candidate"
                      key={model.id}
                      onClick={() => addModelFromCandidate(model)}
                    >
                      <span>{model.name || model.model || model.id}</span>
                      <small>{model.context_window || ""}</small>
                    </button>
                  ))
                ) : (
                  <div className="empty-line">回车或点击“添加模型”添加输入的模型 ID。</div>
                )}
                  </>
                )}
              </div>
            ) : null}
          </div>

          <div>
            <h3>Agent 模型位置</h3>
            <p>为不同模块分配不同能力侧重的模型。</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            {agentSlots.map(([key, label, group]) => (
              <div key={key} style={{ background: "var(--panel-muted)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "12px", display: "grid", gap: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ fontSize: 13, color: "var(--ink)" }}>{label}</strong>
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>{group}</span>
                </div>
                <select
                  value={settings.assignments[key] || ""}
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      assignments: {
                        ...current.assignments,
                        [key]: event.target.value,
                      },
                    }))
                  }
                  style={{ fontSize: 12, minHeight: 32 }}
                >
                  <option value="">本地 Mock</option>
                  {modelOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <span style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.4 }}>{agentRecommendations[key]}</span>
              </div>
            ))}
          </div>
          <div className="settings-actions">
            <button className="icon-button" onClick={onClose}>关闭</button>
          </div>
        </section>
      </div>
    </section>
  );
}

function markdownToHtml(markdown) {
  const raw = String(markdown || "").trim();
  // If the content looks like raw JSON, render it as a formatted code block
  if (raw.startsWith("{") && raw.includes('"version"')) {
    try {
      const obj = JSON.parse(raw);
      return '<div class="json-fallback-notice"><strong>模型输出为 JSON 格式（Markdown 部分缺失），以下是解析后的内容：</strong></div>'
        + '<pre style="background:var(--panel-muted);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px;overflow-x:auto;font-size:13px;line-height:1.6;white-space:pre-wrap;word-break:break-all">'
        + JSON.stringify(obj, null, 2)
          .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        + '</pre>';
    } catch {
      // Not valid JSON, render as-is
    }
  }
  const lines = String(markdown || "").split(/\r?\n/);
  let html = "";
  let listType = "";
  let inCode = false;
  const closeList = () => {
    if (listType) {
      html += `</${listType}>`;
      listType = "";
    }
  };
  const renderTable = (tableLines) => {
    const rows = tableLines
      .filter(
        (row) =>
          !/^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(row),
      )
      .map((row) =>
        row
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((cell) => cell.trim()),
      );
    if (!rows.length) return "";
    const head = rows[0];
    const body = rows.slice(1);
    return `<div class="markdown-table-wrap"><table><thead><tr>${head
      .map((cell) => `<th>${inlineMarkdown(cell)}</th>`)
      .join("")}</tr></thead><tbody>${body
      .map(
        (row) =>
          `<tr>${head
            .map((_, index) => `<td>${inlineMarkdown(row[index] || "")}</td>`)
            .join("")}</tr>`,
      )
      .join("")}</tbody></table></div>`;
  };
  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index];
    const line = rawLine.trimEnd();
    const trimmed = line.trim();
    if (trimmed.startsWith("```")) {
      closeList();
      if (!inCode) {
        html += "<pre><code>";
        inCode = true;
      } else {
        html += "</code></pre>";
        inCode = false;
      }
      continue;
    }
    if (inCode) {
      html += `${escapeHtml(line)}\n`;
      continue;
    }
    if (!trimmed) {
      closeList();
      continue;
    }
    if (isTableLine(trimmed)) {
      closeList();
      const tableLines = [line];
      while (index + 1 < lines.length && isTableLine(lines[index + 1].trim())) {
        index += 1;
        tableLines.push(lines[index]);
      }
      html += renderTable(tableLines);
      continue;
    }
    if (/^[-*_]{3,}$/.test(trimmed)) {
      closeList();
      html += "<hr />";
    } else if (/^#{1,6}\s*/.test(trimmed)) {
      closeList();
      const match = trimmed.match(/^(#{1,6})\s*(.+)$/);
      const level = Math.min(match?.[1]?.length || 3, 3);
      html += `<h${level}>${inlineMarkdown(match?.[2] || trimmed)}</h${level}>`;
    } else if (/^>\s?/.test(trimmed)) {
      closeList();
      html += `<blockquote>${inlineMarkdown(trimmed.replace(/^>\s?/, ""))}</blockquote>`;
    } else if (/^[-*+]\s+/.test(trimmed)) {
      if (listType !== "ul") {
        closeList();
        html += "<ul>";
        listType = "ul";
      }
      html += `<li>${inlineMarkdown(trimmed.replace(/^[-*+]\s+/, ""))}</li>`;
    } else if (/^\d+[.)]\s+/.test(trimmed)) {
      if (listType !== "ol") {
        closeList();
        html += "<ol>";
        listType = "ol";
      }
      html += `<li>${inlineMarkdown(trimmed.replace(/^\d+[.)]\s+/, ""))}</li>`;
    } else {
      closeList();
      html += `<p>${inlineMarkdown(line)}</p>`;
    }
  }
  closeList();
  if (inCode) html += "</code></pre>";
  return html;
}

function inlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function isTableLine(line) {
  return line.includes("|") && line.split("|").length >= 3;
}

function escapeHtml(value) {
  return String(value).replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
}

async function readError(response) {
  const text = await response.text();
  try {
    const data = JSON.parse(text);
    return data.detail || text;
  } catch {
    return text;
  }
}

function ReportView({
  run,
  copied,
  onCopy,
  onDownloadReport,
  onDownloadJson,
  onDownloadBundle,
  onExportPDF,
  onNavigate,
}) {
  return (
    <section className="panel report-panel">
      <div className="panel-title">
        <div>
          <h2>{{full: "选题建议报告", focused: "聚焦分析报告", memory: "追问分析报告", quick: "快速探测结果"}[run?.mode] || "最终报告"}</h2>
          <p>{{full: "Markdown 格式，可直接复制到开题或组会讨论材料。", focused: "针对特定问题的深度分析报告。", memory: "基于历史讨论的追问分析报告。", quick: "单 Agent 快速问答结果。"}[run?.mode] || "Markdown 格式，可直接复制到开题或组会讨论材料。"}</p>
        </div>
        <div className="inline-actions multi-actions">
          <DownloadMenu label="报告" disabled={!run?.final_report} mdContent={run?.final_report} pdfContent={run?.final_report} pdfTitle={`K-Storm 报告 ${run?.run_id || ""}`} />
          <DownloadMenu label="打包" disabled={!run?.final_report && !run?.group_summary} mdContent={buildBundleMD(run)} pdfContent={buildBundleMD(run)} pdfTitle={`K-Storm 打包 ${run?.run_id || ""}`} />
          <button className="icon-button" disabled={!run} onClick={onDownloadJson}>
            <Download size={18} />
            <span>JSON</span>
          </button>
          <button
            className="icon-button"
            disabled={!run?.final_report}
            onClick={onCopy}
          >
            {copied ? <Check size={18} /> : <Clipboard size={18} />}
            <span>{copied ? "已复制" : "复制"}</span>
          </button>
        </div>
      </div>
      {run?.ir_warnings?.length ? (
        <div style={{ background: "rgba(234, 179, 8, 0.08)", border: "1px solid rgba(234, 179, 8, 0.3)", borderRadius: "var(--radius-sm)", padding: "12px 16px", margin: "4px 0" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#b45309", marginBottom: 6 }}>证据绑定校验发现 {run.ir_warnings.length} 个问题</div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#92400e", lineHeight: 1.6 }}>
            {run.ir_warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      ) : null}
      {run?.external_references?.length ? (
        <div style={{ background: "var(--accent-soft)", border: "1px solid var(--accent)", borderRadius: "var(--radius-sm)", padding: "10px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", margin: "4px 0" }}>
          <div style={{ fontSize: 13, color: "var(--accent-strong)" }}>
            <BookOpen size={16} style={{ verticalAlign: -3, marginRight: 6 }} />
            本次讨论共引用 {run.external_references.length} 条外部论据
          </div>
          <button className="icon-button" style={{ fontSize: 12, minHeight: 30 }} onClick={() => onNavigate("refs")}>前往查看</button>
        </div>
      ) : null}
      {run?.final_report ? (
        <div
          className="markdown-output markdown-rendered"
          dangerouslySetInnerHTML={{ __html: markdownToHtml(run.final_report) }}
        />
      ) : (
        <div className="empty-line">完成一次分析后会生成最终报告。</div>
      )}
    </section>
  );
}

function ReferencesPage({ run, setRun, setError, onNavigate, history, openRun }) {
  const [busy, setBusy] = React.useState(false);
  const allRuns = React.useMemo(
    () => history,
    [history],
  );

  async function fetchRefs(merge) {
    if (!run?.run_id) return;
    setBusy(true);
    try {
      const resp = await fetch(`${API_BASE}/api/runs/${run.run_id}/references`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(merge ? { merge: true } : {}),
      });
      if (!resp.ok) {
        const detail = await readError(resp);
        throw new Error(detail || "操作失败");
      }
      const data = await resp.json();
      setRun(data);
      if (!data.external_references?.length) {
        setError("未提取到外部论据。Agent 在发言中需要包含“### 外部引用”小节才会被收录。旧 run 可能不支持此功能。");
      } else {
        setError("");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function buildRefsMD() {
    if (!refs.length) return "";
    const lines = [`# 外部论据清单`, ``, `来源 Run: ${run.run_id}`, `时间: ${new Date(run.created_at).toLocaleString()}`, ``, ``];
    const grouped = {};
    for (const ref of refs) {
      const t = ref.source_type || "other";
      if (!grouped[t]) grouped[t] = [];
      grouped[t].push(ref);
    }
    for (const [type, items] of Object.entries(grouped)) {
      lines.push(`## ${typeLabel[type] || type}（${items.length} 条）`);
      lines.push("");
      for (const ref of items) {
        lines.push(`### ${ref.title || "未命名"}${ref.year ? ` (${ref.year})` : ""}`);
        if (ref.authors) lines.push(`- **作者**：${ref.authors}`);
        if (ref.url && ref.url !== "待确认") lines.push(`- **链接**：${ref.url}`);
        if (ref.cited_viewpoint) {
          const vp = ref.cited_viewpoint.replace(/^[\s]*支撑观点[：:]/, "").trim();
          if (vp) lines.push(`- **支撑观点**：${vp}`);
        }
        lines.push(`- **引用阶段**：${ref.citing_agent || ""} · 第 ${ref.round || "?"} 轮`);
        lines.push("");
      }
    }
    return lines.join("\n");
  }

  const refs = run?.external_references || [];
  const typeLabel = { paper: "论文", blog: "博客", dataset: "数据集", book: "书籍", other: "其他" };

  const grouped = React.useMemo(() => {
    const groups = {};
    for (const ref of refs) {
      const t = ref.source_type || "other";
      if (!groups[t]) groups[t] = [];
      groups[t].push(ref);
    }
    return groups;
  }, [refs]);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px minmax(0, 1fr)", gap: 16, minHeight: "100%" }}>
      {/* 左侧：历史记录列表 */}
      <div className="panel" style={{ display: "flex", flexDirection: "column", overflow: "auto", maxHeight: "calc(100vh - 120px)", padding: 0 }}>
        <div style={{ padding: "14px 16px 10px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)" }}>历史讨论</div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>{allRuns.length} 条记录</div>
        </div>
        <div style={{ overflow: "auto", flex: 1 }}>
          {allRuns.length === 0 ? (
            <div style={{ padding: "16px", fontSize: 13, color: "var(--muted)" }}>暂无讨论记录</div>
          ) : allRuns.map((item) => (
            <button
              key={item.run_id}
              onClick={() => openRun(item.run_id)}
              style={{
                display: "block",
                width: "100%",
                border: "none",
                borderBottom: "1px solid var(--border)",
                background: run?.run_id === item.run_id ? "var(--accent-soft)" : "transparent",
                borderLeft: run?.run_id === item.run_id ? "4px solid var(--accent)" : "4px solid transparent",
                padding: "12px 14px",
                cursor: "pointer",
                textAlign: "left",
                color: "var(--ink)",
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) => { if (run?.run_id !== item.run_id) e.currentTarget.style.background = "var(--panel-muted)"; }}
              onMouseLeave={(e) => { if (run?.run_id !== item.run_id) e.currentTarget.style.background = "transparent"; }}
            >
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", lineHeight: 1.4, marginBottom: 4 }}>{item.field}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
                <span className={`status-badge ${item.status === "COMPLETED" ? "completed" : item.status === "FAILED" ? "failed" : item.status === "RUNNING" ? "running" : "pending"}`} style={{ fontSize: 10 }}>
                  {item.status}
                </span>
                {item.mode && item.mode !== "full" ? (
                  <span className="status-badge pending" style={{ fontSize: 10 }}>
                    {{focused: "聚焦", quick: "快速", memory: "记忆"}[item.mode] || item.mode}
                  </span>
                ) : null}
                {item.source_run_id ? (
                  <span className="status-badge pending" style={{ fontSize: 10, background: "rgba(111,124,255,0.1)", color: "#6a79d6" }}>
                    源 {item.source_run_id.slice(0, 8)}
                  </span>
                ) : null}
                <span style={{ fontSize: 11, color: "var(--muted)" }}>{new Date(item.created_at).toLocaleDateString()}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 右侧：论据内容 */}
      <div className="panel" style={{ display: "grid", gap: 16, alignContent: "start" }}>
        <div className="pane-heading">
          <div>
            <h2>外部论据清单</h2>
            <p>讨论过程中各 Agent 引用的外部论文、博客、数据集等论据。</p>
          </div>
          {run ? (
            <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
              <button className="icon-button" disabled={busy} onClick={() => fetchRefs(false)} style={{ whiteSpace: "nowrap", fontSize: 12, minHeight: 32 }}>
                <RefreshCw size={14} className={busy ? "spin" : ""} />
                <span>重新提取</span>
              </button>
              <button className="icon-button" disabled={busy} onClick={() => fetchRefs(true)} style={{ whiteSpace: "nowrap", fontSize: 12, minHeight: 32 }}>
                <span>+ 更新论据</span>
              </button>
              <DownloadMenu label="导出" disabled={!refs.length} mdContent={buildRefsMD()} pdfContent={buildRefsMD()} pdfTitle={`K-Storm 外部论据 ${run?.run_id || ""}`} />
            </div>
          ) : null}
        </div>

        {!run ? (
          <div className="empty-state">
            <BookOpen size={28} />
            <span>从左侧选择一条历史讨论，或先启动一次讨论。</span>
          </div>
        ) : refs.length === 0 ? (
          <div className="empty-state">
            <BookOpen size={28} />
            <span>本次讨论暂无外部论据。Agent 在发言中引用了外部论文、博客等资料时会自动收录。</span>
            <button className="icon-button" disabled={busy} onClick={() => fetchRefs(false)} style={{ marginTop: 8 }}>
              <RefreshCw size={16} className={busy ? "spin" : ""} />
              重新提取
            </button>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            <div style={{ fontSize: 13, color: "var(--muted)" }}>共 {refs.length} 条外部论据</div>
            {Object.entries(grouped).map(([type, items]) => (
              <div key={type}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink-soft)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                  <span className="status-badge pending">{typeLabel[type] || type}</span>
                  {items.length} 条
                </div>
                <div style={{ display: "grid", gap: 8 }}>
                  {items.map((ref) => {
                    const vp = ref.cited_viewpoint ? ref.cited_viewpoint.replace(/^[\s]*支撑观点[：:]/, "").trim() : "";
                    const md = [
                      `**${ref.url && ref.url !== "待确认" ? `[${ref.title || "未命名"}](${ref.url})` : (ref.title || "未命名")}${ref.year ? ` (${ref.year})` : ""}**`,
                      ref.authors ? `**作者**：${ref.authors}` : null,
                      vp ? `**支撑观点**：${vp}` : null,
                      `*引用阶段：${ref.citing_agent || ""} · 第 ${ref.round || "?"} 轮*`,
                    ].filter(Boolean).join("\n\n");
                    return (
                      <div key={ref.id} style={{ background: "var(--panel-muted)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "12px 16px" }}>
                        <div
                          className="markdown-rendered"
                          style={{ fontSize: 13, lineHeight: 1.6 }}
                          dangerouslySetInnerHTML={{ __html: markdownToHtml(md) }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function HistoryView({
  history,
  location,
  selected,
  setSelected,
  onDelete,
  onLocation,
  onOpen,
  onRerunRun,
  onDownloadReportRun,
  onDownloadJsonRun,
  onDownloadBundleRun,
  onConfirmRerunRun,
  onExportPDF,
  loading,
}) {
  const [searchQuery, setSearchQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("all");

  function toggle(runId, checked) {
    setSelected((current) =>
      checked ? [...new Set([...current, runId])] : current.filter((id) => id !== runId),
    );
  }

  const filtered = React.useMemo(() => {
    let list = history;
    if (statusFilter !== "all") {
      list = list.filter((h) => h.status === statusFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter(
        (h) =>
          (h.field || "").toLowerCase().includes(q) ||
          (h.run_id || "").toLowerCase().includes(q),
      );
    }
    return list;
  }, [history, statusFilter, searchQuery]);

  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>历史记录</h2>
          <p>本地 SQLite 保存最近运行。</p>
        </div>
        <button className="icon-button" onClick={onLocation}>
          <History size={18} />
          <span>位置</span>
        </button>
      </div>
      <div className="history-toolbar">
        <button className="danger-button" disabled={!selected.length} onClick={onDelete}>
          删除所选
        </button>
      </div>
      <div className="history-filter-bar">
        <input
          type="text"
          placeholder="搜索领域或 Run ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">全部状态</option>
          <option value="COMPLETED">已完成</option>
          <option value="FAILED">失败</option>
          <option value="RUNNING">运行中</option>
        </select>
        <span className="history-count">{filtered.length} / {history.length} 条</span>
      </div>
      {location ? <div className="history-location">{location}</div> : null}
      {filtered.length ? (
        <div className="history-list">
          {filtered.map((item) => {
            const isFailed = item.status === "FAILED";
            const isCompleted = item.status === "COMPLETED";
            const canExport = isCompleted;
            return (
              <div
                className="history-item"
                key={item.run_id}
              >
                <input
                  checked={selected.includes(item.run_id)}
                  type="checkbox"
                  onChange={(event) => toggle(item.run_id, event.target.checked)}
                />
                <button className="history-open" onClick={() => onOpen(item.run_id)}>
                  <span>{item.field}</span>
                  <small>
                    {item.mode && item.mode !== "full" ? (
                      <span className="status-badge pending" style={{marginRight: 4}}>
                        {{focused: "聚焦", quick: "快速", memory: "记忆"}[item.mode] || item.mode}
                      </span>
                    ) : null}
                    {item.source_run_id ? (
                      <span className="status-badge pending" style={{marginRight: 4, background: "rgba(111,124,255,0.1)", color: "#6a79d6"}}>
                        源 {item.source_run_id.slice(0, 8)}
                      </span>
                    ) : null}
                    <span className={`status-badge ${item.status === "COMPLETED" ? "completed" : item.status === "FAILED" ? "failed" : item.status === "RUNNING" ? "running" : "pending"}`}>{item.status}</span>
                    {" \u00b7 "}{new Date(item.created_at).toLocaleString()}
                  </small>
                </button>
                <div className="history-actions-inline">
                  {isFailed ? (
                    <button
                      className="icon-button copy-mini"
                      disabled={loading}
                      onClick={async () => {
                        const opened = await onOpen(item.run_id);
                        if (opened) await onRerunRun(opened);
                      }}
                    >
                      {item.status === "FAILED" ? "继续分析" : "重新分析"}
                    </button>
                  ) : null}
                  {isCompleted ? (
                    <button
                      className="icon-button copy-mini"
                      disabled={loading}
                      onClick={async () => {
                        const opened = await onOpen(item.run_id);
                        if (!opened) return;
                        if (!opened.final_report) return;
                        downloadMarkdown(opened.final_report, `K-Storm 报告 ${opened.run_id}`);
                      }}
                    >
                      <Download size={14} />
                      <span>报告</span>
                    </button>
                  ) : null}
                  {isCompleted ? (
                    <button
                      className="icon-button copy-mini"
                      disabled={loading}
                      onClick={async () => {
                        const opened = await onOpen(item.run_id);
                        if (!opened) return;
                        onExportPDF(opened.final_report, `K-Storm 报告 ${opened.run_id}`);
                      }}
                    >
                      <Download size={14} />
                      <span>PDF</span>
                    </button>
                  ) : null}
                  {isCompleted ? (
                    <button
                      className="icon-button copy-mini"
                      disabled={loading}
                      onClick={() => {
                        if (window.confirm("当前记录为 COMPLETED 状态，确认重新分析？")) {
                          onConfirmRerunRun(item);
                        }
                      }}
                    >
                      <RefreshCw size={14} />
                      <span>重新分析</span>
                    </button>
                  ) : null}
                  {canExport ? (
                    <button
                      className="icon-button copy-mini"
                      disabled={loading}
                      onClick={async () => {
                        const opened = await onOpen(item.run_id);
                        if (opened) await onDownloadBundleRun(opened);
                      }}
                    >
                      <Download size={14} />
                      <span>打包</span>
                    </button>
                  ) : null}
                  {canExport ? (
                    <button
                      className="icon-button copy-mini"
                      disabled={loading}
                      onClick={async () => {
                        const opened = await onOpen(item.run_id);
                        if (opened) await onDownloadJsonRun(opened);
                      }}
                    >
                      <span>JSON</span>
                    </button>
                  ) : null}
                  <small>{item.run_id}</small>
                </div>
              </div>
            );
          })}
        </div>
      ) : history.length ? (
        <div className="empty-line">没有匹配“{searchQuery}”的记录。</div>
      ) : (
        <div className="empty-line">暂无历史记录。</div>
      )}
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
