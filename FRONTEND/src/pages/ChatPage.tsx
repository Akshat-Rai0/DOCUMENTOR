import { useCallback, useEffect, useRef, useState } from "react";
import {
  Plus,
  ArrowRight,
  Search,
  Home,
  Library,
  Menu,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  FileText,
} from "lucide-react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { openDB, type IDBPDatabase } from "idb";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/*  IndexedDB helpers  (Issue #1)                                     */
/* ------------------------------------------------------------------ */

const DB_NAME = "documentor_db";
const DB_VERSION = 1;
const STORE_NAME = "sessions";

async function getDB(): Promise<IDBPDatabase> {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    },
  });
}

async function idbGetSession(url: string): Promise<Message[] | undefined> {
  const db = await getDB();
  return db.get(STORE_NAME, url);
}

async function idbSaveSession(url: string, messages: Message[]) {
  const db = await getDB();
  await db.put(STORE_NAME, messages, url);
}

async function idbDeleteSession(url: string) {
  const db = await getDB();
  await db.delete(STORE_NAME, url);
}

async function idbGetAllSessions(): Promise<{ url: string; messages: Message[] }[]> {
  const db = await getDB();
  const keys = await db.getAllKeys(STORE_NAME);
  const results: { url: string; messages: Message[] }[] = [];
  for (const key of keys) {
    const msgs = await db.get(STORE_NAME, key);
    if (Array.isArray(msgs)) {
      results.push({ url: String(key), messages: msgs });
    }
  }
  return results;
}

/** One-time migration from localStorage → IndexedDB */
async function migrateFromLocalStorage() {
  const HISTORY_PREFIX = "documentor_history";
  const migrated = localStorage.getItem("documentor_idb_migrated");
  if (migrated) return;

  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith(HISTORY_PREFIX)) continue;

      if (key === HISTORY_PREFIX) {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        const data = JSON.parse(raw);
        if (data && typeof data === "object" && !Array.isArray(data)) {
          for (const [u, msgs] of Object.entries(data)) {
            if (Array.isArray(msgs)) {
              await idbSaveSession(u, msgs as Message[]);
            }
          }
        }
      } else if (key.startsWith(`${HISTORY_PREFIX}_`)) {
        const raw = localStorage.getItem(key);
        if (!raw) continue;
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) continue;
        const encoded = key.slice(HISTORY_PREFIX.length + 1);
        const u = decodeURIComponent(encoded);
        await idbSaveSession(u, parsed as Message[]);
      }
    }
    localStorage.setItem("documentor_idb_migrated", "1");
  } catch {
    /* ignore migration errors */
  }
}

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

type Intent = "function_search" | "error_fix" | "concept_explain";

type RetrievedChunk = {
  chunk_id: string;
  score: number;
  text: string;
  source_url?: string;
  function_name?: string;
  rank?: number;
};

type ProcessResponse = {
  status: string;
  intent: Intent;
  processed_content: string;
  recommended_functions: string[];
  use_when: string[];
  avoid_when: string[];
  code_snippet: string;
  source_url?: string;
  confidence: number;
  explanation: string;
  fixes: string[];
  retrieved_chunks: RetrievedChunk[];
};

type Message = {
  role: "user" | "assistant";
  content?: string;
  response?: ProcessResponse;
};

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const intentLabel: Record<Intent, string> = {
  function_search: "Function search",
  error_fix: "Error fix",
  concept_explain: "Concept explain",
};

const intentBadgeClass: Record<Intent, string> = {
  function_search: "text-indigo-300 border-indigo-500/30 bg-indigo-500/10",
  error_fix: "text-emerald-300 border-emerald-500/30 bg-emerald-500/10",
  concept_explain: "text-amber-300 border-amber-500/30 bg-amber-500/10",
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function formatLastMessagePreview(messages: Message[]): string {
  if (!messages.length) return "No messages yet";
  const last = messages[messages.length - 1];
  if (last.role === "user") {
    const t = (last.content || "").trim();
    if (!t) return "Empty message";
    return t.length > 90 ? `${t.slice(0, 90)}…` : t;
  }
  const text = (
    last.response?.explanation ||
    last.response?.processed_content ||
    last.content ||
    ""
  ).trim();
  if (!text) return "…";
  return text.length > 90 ? `${text.slice(0, 90)}…` : text;
}

function shortUrlLabel(docUrl: string): string {
  try {
    const u = new URL(docUrl);
    const path =
      u.pathname.length > 1 ? u.pathname.replace(/\/$/, "") : "";
    const tail = path.length > 24 ? `${path.slice(0, 22)}…` : path;
    return `${u.hostname}${tail}`;
  } catch {
    return docUrl.length > 48 ? `${docUrl.slice(0, 46)}…` : docUrl;
  }
}

/* ------------------------------------------------------------------ */
/*  CodeBlock component  (Issue #12)                                  */
/* ------------------------------------------------------------------ */

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard API may fail in insecure contexts */
    }
  };

  return (
    <div className="relative group">
      <button
        type="button"
        onClick={handleCopy}
        className="absolute right-2 top-2 p-1.5 rounded-md bg-[#222222] border border-[#333333] text-[#888888] hover:text-[#EEEEEE] hover:bg-[#333333] transition-all opacity-0 group-hover:opacity-100 focus:opacity-100 z-10"
        title="Copy to clipboard"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5 text-emerald-400" />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </button>
      <pre className="bg-[#111111] border border-[#2A2A2A] rounded-xl p-3 pr-10 text-xs overflow-x-auto whitespace-pre-wrap">
        {code}
      </pre>
      {copied && (
        <span className="absolute right-2 top-10 text-[10px] text-emerald-400 font-medium">
          Copied!
        </span>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  SourcesSection component  (Issue #13)                             */
/* ------------------------------------------------------------------ */

function SourcesSection({ chunks }: { chunks: RetrievedChunk[] }) {
  const [open, setOpen] = useState(false);

  if (!chunks || chunks.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-[#888888] hover:text-[#CCCCCC] transition-colors"
      >
        <FileText className="w-3 h-3" />
        <span>Sources ({chunks.length})</span>
        {open ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
      </button>

      {open && (
        <div className="mt-2 space-y-2 animate-in fade-in slide-in-from-top-1 duration-200">
          {chunks.map((chunk, idx) => (
            <div
              key={chunk.chunk_id || idx}
              className="bg-[#0D0D0D] border border-[#222222] rounded-lg p-3 text-xs"
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className="px-1.5 py-0.5 rounded bg-[#1A1A1A] text-[#888888] font-mono text-[10px]">
                  #{chunk.rank ?? idx + 1}
                </span>
                {chunk.function_name && (
                  <span className="text-indigo-300 font-medium truncate">
                    {chunk.function_name}
                  </span>
                )}
                <span className="ml-auto text-[#555555] text-[10px]">
                  score {(chunk.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-[#999999] leading-relaxed line-clamp-3">
                {chunk.text.slice(0, 200)}
                {chunk.text.length > 200 ? "…" : ""}
              </p>
              {chunk.source_url && (
                <a
                  href={chunk.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block mt-1.5 text-indigo-400/70 hover:text-indigo-300 text-[10px] truncate max-w-full"
                >
                  {chunk.source_url}
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ResponseSkeleton component  (Issue #11)                           */
/* ------------------------------------------------------------------ */

function ResponseSkeleton() {
  return (
    <div className="self-start w-full max-w-[95%]">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
          <Search className="w-3.5 h-3.5 animate-pulse" />
        </div>
        <span className="text-xs font-medium text-[#888888]">
          DocuMentor is thinking…
        </span>
      </div>
      <div className="bg-[#151515] border border-[#2A2A2A] rounded-2xl p-5 space-y-4 animate-pulse">
        {/* Intent badge + confidence skeleton */}
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-24 rounded-full bg-[#222222]" />
          <Skeleton className="h-4 w-16 rounded bg-[#222222]" />
        </div>
        {/* Explanation lines */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-full rounded bg-[#1A1A1A]" />
          <Skeleton className="h-4 w-[90%] rounded bg-[#1A1A1A]" />
          <Skeleton className="h-4 w-[75%] rounded bg-[#1A1A1A]" />
        </div>
        {/* Function pills */}
        <div className="flex gap-2">
          <Skeleton className="h-6 w-28 rounded-md bg-[#1A1A1A]" />
          <Skeleton className="h-6 w-20 rounded-md bg-[#1A1A1A]" />
        </div>
        {/* Code block */}
        <Skeleton className="h-20 w-full rounded-xl bg-[#111111]" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sidebar content (shared between desktop + mobile Sheet) (#14)     */
/* ------------------------------------------------------------------ */

function SidebarContent({
  domainName,
  goSwitchLibrary,
  pastSessions,
  url,
  restoreSession,
  startNewConversation,
}: {
  domainName: string;
  goSwitchLibrary: () => void;
  pastSessions: { url: string; preview: string }[];
  url: string;
  restoreSession: (u: string) => void;
  startNewConversation: () => void;
}) {
  return (
    <>
      <div className="flex items-center gap-2 mb-6">
        <div className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
          DocuMentor
        </div>
      </div>

      <button
        type="button"
        onClick={goSwitchLibrary}
        title="Index another library (current URL prefilled on home)"
        className="flex items-center gap-2 px-3 py-2 bg-indigo-500/10 text-indigo-400 rounded-lg w-full text-sm font-medium border border-indigo-500/20 mb-2 hover:bg-indigo-500/15 transition-colors"
      >
        <div className="w-2 h-2 rounded-full bg-indigo-400 shrink-0" />
        <span className="truncate flex-1 text-left">{domainName}</span>
      </button>
      <button
        type="button"
        onClick={goSwitchLibrary}
        className="flex items-center gap-2 w-full px-2 py-1.5 mb-6 text-xs text-[#888888] hover:text-[#CCCCCC] transition-colors rounded-lg hover:bg-[#1A1A1A]"
      >
        <Library className="w-3.5 h-3.5 shrink-0" />
        Switch library
      </button>

      <div className="text-[10px] font-mono uppercase tracking-wider text-[#555555] mb-2 px-1">
        Recent
      </div>
      <div className="flex-1 overflow-y-auto min-h-0 space-y-1 pr-1">
        {pastSessions.length === 0 ? (
          <p className="text-xs text-[#666666] px-1 leading-relaxed">
            Indexed sessions appear here after you chat.
          </p>
        ) : (
          pastSessions.map((s) => {
            const active = s.url === url;
            return (
              <button
                key={s.url}
                type="button"
                onClick={() => restoreSession(s.url)}
                className={`w-full text-left rounded-lg px-2 py-2 text-xs border transition-colors ${
                  active
                    ? "bg-[#1A1A1A] border-indigo-500/40 text-[#EEEEEE]"
                    : "border-transparent text-[#AAAAAA] hover:bg-[#1A1A1A] hover:border-[#333333]"
                }`}
              >
                <div className="truncate font-medium text-[#DDDDDD] mb-0.5">
                  {shortUrlLabel(s.url)}
                </div>
                <div className="truncate text-[#777777] leading-snug">
                  {s.preview}
                </div>
              </button>
            );
          })
        )}
      </div>

      <button
        onClick={startNewConversation}
        className="flex items-center justify-center gap-2 w-full py-3 mt-4 text-sm font-medium text-[#EEEEEE] border border-[#333333] hover:bg-[#222222] rounded-xl transition-colors"
      >
        <Plus className="w-4 h-4" />
        New conversation
      </button>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                    */
/* ------------------------------------------------------------------ */

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const url = searchParams.get("url") || "";
  const ready = searchParams.get("ready") === "1";

  const [status, setStatus] = useState<string>(ready ? "done" : "crawling");
  const [pagesIndexed, setPagesIndexed] = useState<number>(0);
  const [functionsIndexed, setFunctionsIndexed] = useState<number>(0);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [pastSessions, setPastSessions] = useState<
    { url: string; preview: string }[]
  >([]);
  const [useReranker, setUseReranker] = useState(true); // Issue #10
  const [mobileOpen, setMobileOpen] = useState(false); // Issue #14
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* --- IndexedDB persistence (Issue #1) --- */

  const refreshPastSessions = useCallback(async () => {
    const sessions = await idbGetAllSessions();
    const rows = sessions
      .map(({ url: u, messages: msgs }) => ({
        url: u,
        preview: formatLastMessagePreview(msgs),
      }))
      .sort((a, b) => a.url.localeCompare(b.url));
    setPastSessions(rows);
  }, []);

  // Migrate localStorage → IndexedDB on first load
  useEffect(() => {
    migrateFromLocalStorage();
  }, []);

  // Load history from IndexedDB
  useEffect(() => {
    if (!url) return;
    (async () => {
      const saved = await idbGetSession(url);
      if (saved && saved.length > 0) {
        setMessages(saved);
      } else {
        setMessages([
          {
            role: "assistant",
            content: `I'm ready to answer questions about ${url}.`,
          },
        ]);
      }
    })();
  }, [url]);

  // Save history to IndexedDB
  useEffect(() => {
    if (!url || messages.length === 0) return;
    idbSaveSession(url, messages);
  }, [messages, url]);

  useEffect(() => {
    refreshPastSessions();
  }, [url, messages, refreshPastSessions]);

  /* --- Crawl status polling --- */

  useEffect(() => {
    if (!url) return;

    let intervalId: ReturnType<typeof setInterval> | undefined;

    const checkStatus = async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/crawl/status?url=${encodeURIComponent(url)}`
        );
        const data = await res.json();

        setStatus(data.status || "not_found");
        if (typeof data.pages === "number") setPagesIndexed(data.pages);
        if (typeof data.functions === "number")
          setFunctionsIndexed(data.functions);

        if (data.status === "done" || data.status === "error") {
          if (intervalId) clearInterval(intervalId);
        }
      } catch (e) {
        console.error("Failed to fetch crawl status", e);
      }
    };

    if (ready) {
      setStatus("done");
    }

    void checkStatus();

    if (!ready) {
      intervalId = setInterval(checkStatus, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [url, ready]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing, streamingText]);

  /* --- Send handler with SSE streaming (Issue #2) --- */

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;

    const userText = input;
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setInput("");
    setIsProcessing(true);
    setStreamingText("");

    try {
      // Try streaming endpoint first
      const res = await fetch(`${API_BASE_URL}/api/process/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: userText,
          source_url: url || null,
          use_reranker: useReranker,
        }),
      });

      if (!res.ok) {
        // Fallback to non-streaming endpoint
        const fallbackRes = await fetch(`${API_BASE_URL}/api/process`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: userText,
            source_url: url || null,
            use_reranker: useReranker,
          }),
        });

        if (!fallbackRes.ok) {
          const errorPayload = await fallbackRes.json().catch(() => null);
          throw new Error(errorPayload?.detail || "No content returned.");
        }

        const data: ProcessResponse = await fallbackRes.json();
        setMessages((prev) => [
          ...prev,
          { role: "assistant", response: data, content: data.processed_content },
        ]);
        return;
      }

      // Read SSE stream
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";
      let finalPayload: ProcessResponse | null = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });
          const lines = text.split("\n");

          for (const line of lines) {
            if (line.startsWith("event: done")) {
              // Next data line is the final JSON payload
              continue;
            }
            if (line.startsWith("event: error")) {
              continue;
            }
            if (line.startsWith("data: ")) {
              const payload = line.slice(6);

              // Check if this is the final JSON payload
              try {
                const parsed = JSON.parse(payload);
                if (parsed.status && parsed.intent) {
                  finalPayload = parsed as ProcessResponse;
                  continue;
                }
                if (parsed.error) {
                  throw new Error(parsed.error);
                }
              } catch {
                // It's a text chunk, not JSON
              }

              accumulated += payload;
              setStreamingText(accumulated);
            }
          }
        }
      }

      if (finalPayload) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            response: finalPayload!,
            content: finalPayload!.processed_content,
          },
        ]);
      } else if (accumulated) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: accumulated },
        ]);
      }
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Failed to process query: ${e.message}`,
        },
      ]);
    } finally {
      setIsProcessing(false);
      setStreamingText("");
    }
  };

  const startNewConversation = async () => {
    if (!url) return;
    await idbDeleteSession(url);
    setMessages([
      {
        role: "assistant",
        content: `Conversation reset. I'm ready to answer questions about ${url}.`,
      },
    ]);
  };

  const domainName = url
    ? url.replace(/https?:\/\//, "").split("/")[0]
    : "No source";

  const goSwitchLibrary = () => {
    if (!url) return;
    navigate(`/?prefill=${encodeURIComponent(url)}`);
  };

  const restoreSession = (sessionUrl: string) => {
    setMobileOpen(false);
    navigate(`/chat?url=${encodeURIComponent(sessionUrl)}&ready=1`);
  };

  /* --- Render assistant response --- */

  const renderAssistantResponse = (message: Message) => {
    if (!message.response) {
      return (
        <div className="bg-[#151515] border border-[#2A2A2A] rounded-2xl p-5 text-[15px] text-[#CCCCCC] leading-relaxed">
          {message.content}
        </div>
      );
    }

    const response = message.response;
    const intent = response.intent || "function_search";
    const confidence = Math.round((response.confidence || 0) * 100);

    return (
      <div className="bg-[#151515] border border-[#2A2A2A] rounded-2xl p-5 text-[15px] text-[#CCCCCC] leading-relaxed animate-in fade-in slide-in-from-bottom-2 duration-300 space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span
            className={`px-2 py-1 rounded-full border ${intentBadgeClass[intent]}`}
          >
            {intentLabel[intent]}
          </span>
          <span className="text-[#888888]">confidence {confidence}%</span>
        </div>

        <p>{response.explanation || response.processed_content}</p>

        {response.recommended_functions?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-2">
              Recommended functions
            </div>
            <div className="flex flex-wrap gap-2">
              {response.recommended_functions.map((fn, idx) => (
                <span
                  key={`${fn}-${idx}`}
                  className="px-2 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-xs"
                >
                  {fn}
                </span>
              ))}
            </div>
          </div>
        )}

        {response.use_when?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">
              Use when
            </div>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {response.use_when.map((item, idx) => (
                <li key={`use-${idx}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {response.avoid_when?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">
              Avoid when
            </div>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {response.avoid_when.map((item, idx) => (
                <li key={`avoid-${idx}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {response.fixes?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">
              Fixes
            </div>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {response.fixes.map((item, idx) => (
                <li key={`fix-${idx}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Issue #12 — code snippet with copy button */}
        {response.code_snippet && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">
              Code snippet
            </div>
            <CodeBlock code={response.code_snippet} />
          </div>
        )}

        {response.source_url && (
          <div className="text-xs text-[#888888]">
            Source:{" "}
            <a
              className="text-indigo-300 hover:underline"
              href={response.source_url}
              target="_blank"
              rel="noreferrer"
            >
              {response.source_url}
            </a>
          </div>
        )}

        {/* Issue #13 — retrieved chunks / sources section */}
        <SourcesSection chunks={response.retrieved_chunks} />
      </div>
    );
  };

  /* --- Shared sidebar props --- */
  const sidebarProps = {
    domainName,
    goSwitchLibrary,
    pastSessions,
    url,
    restoreSession,
    startNewConversation,
  };

  return (
    <div className="flex h-screen bg-[#0F0F0F] text-[#EEEEEE] font-sans overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="w-64 flex-col border-r border-[#222222] bg-[#111111] p-4 hidden md:flex">
        <SidebarContent {...sidebarProps} />
      </aside>

      <main className="flex-1 flex flex-col relative bg-[#0F0F0F] min-w-0">
        <header className="px-4 sm:px-6 py-4 border-b border-[#222222] flex items-center justify-between bg-[#111111]/80 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-2">
            {/* Issue #14 — mobile hamburger */}
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger asChild>
                <button
                  type="button"
                  className="md:hidden p-2 rounded-lg hover:bg-[#222222] transition-colors"
                >
                  <Menu className="w-5 h-5" />
                </button>
              </SheetTrigger>
              <SheetContent
                side="left"
                className="w-72 bg-[#111111] border-[#222222] p-4 flex flex-col"
              >
                <SheetHeader className="sr-only">
                  <SheetTitle>Navigation</SheetTitle>
                </SheetHeader>
                <SidebarContent {...sidebarProps} />
              </SheetContent>
            </Sheet>

            <div className="flex items-center gap-2 text-sm text-[#888888] font-medium">
              <div
                className={`w-2 h-2 rounded-full ${
                  status === "done"
                    ? "bg-emerald-400"
                    : status === "error"
                    ? "bg-red-400"
                    : "bg-yellow-400 animate-pulse"
                }`}
              />
              <span className="truncate max-w-[200px] sm:max-w-none">
                {domainName} —
                {status === "crawling" && " indexing..."}
                {status === "parsing" &&
                  ` parsing (${pagesIndexed} pages)...`}
                {status === "indexing" && " building retrieval indexes..."}
                {status === "done" &&
                  ` indexed ${pagesIndexed} pages, ${functionsIndexed} functions`}
                {status === "error" && " indexing failed"}
                {status === "not_found" && " status not found"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Issue #10 — reranker toggle */}
            <div className="hidden sm:flex items-center gap-2">
              <label
                htmlFor="reranker-toggle"
                className="text-xs text-[#666666] cursor-pointer"
              >
                Reranker
              </label>
              <Switch
                id="reranker-toggle"
                checked={useReranker}
                onCheckedChange={setUseReranker}
                className="data-[state=checked]:bg-indigo-500 data-[state=unchecked]:bg-[#333333]"
              />
            </div>

            <button
              onClick={() => navigate("/")}
              className="flex items-center gap-2 px-3 sm:px-4 py-2 text-sm font-medium bg-[#222222] rounded-full hover:bg-[#333333] transition-colors"
            >
              <Home className="w-4 h-4" />
              <span className="hidden sm:inline">Home</span>
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex flex-col items-center">
          <div className="w-full max-w-4xl flex flex-col gap-8 pb-20">
            {messages.map((message, i) => (
              <div
                key={i}
                className={
                  message.role === "user"
                    ? "self-end max-w-[80%]"
                    : "self-start w-full max-w-[95%]"
                }
              >
                {message.role === "user" ? (
                  <div className="bg-[#2A2A2A] text-[#EEEEEE] px-5 py-3.5 rounded-2xl rounded-tr-sm text-[15px] border border-[#333333]">
                    {message.content}
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
                        <Search className="w-3.5 h-3.5" />
                      </div>
                      <span className="text-xs font-medium text-[#888888]">
                        DocuMentor
                      </span>
                    </div>
                    {renderAssistantResponse(message)}
                  </div>
                )}
              </div>
            ))}

            {/* Issue #2 — streaming text preview */}
            {isProcessing && streamingText && (
              <div className="self-start w-full max-w-[95%]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
                    <Search className="w-3.5 h-3.5" />
                  </div>
                  <span className="text-xs font-medium text-[#888888]">
                    DocuMentor
                  </span>
                </div>
                <div className="bg-[#151515] border border-[#2A2A2A] rounded-2xl p-5 text-[15px] text-[#CCCCCC] leading-relaxed">
                  <pre className="whitespace-pre-wrap font-sans text-[15px]">
                    {streamingText}
                    <span className="animate-pulse">▊</span>
                  </pre>
                </div>
              </div>
            )}

            {/* Issue #11 — skeleton when no streaming text yet */}
            {isProcessing && !streamingText && <ResponseSkeleton />}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="p-4 bg-gradient-to-t from-[#0F0F0F] via-[#0F0F0F] to-transparent shrink-0">
          <div className="max-w-4xl mx-auto relative">
            <input
              type="text"
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask anything about the library..."
              className="w-full bg-[#1A1A1A] border border-[#333333] border-glow text-[#EEEEEE] placeholder:text-[#666666] text-sm rounded-xl py-3.5 pl-4 pr-12 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all shadow-lg shadow-black/20"
            />
            <button
              id="send-button"
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg bg-[#333333] hover:bg-[#444444] text-[#EEEEEE] flex items-center justify-center transition-colors disabled:opacity-50"
              onClick={handleSend}
              disabled={isProcessing || !input.trim()}
            >
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
