import { useEffect, useRef, useState } from "react";
import { Plus, ArrowRight, Search, Loader2, Home } from "lucide-react";
import { useSearchParams, useNavigate } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load history from localStorage
  useEffect(() => {
    if (!url) return;
    const history = JSON.parse(localStorage.getItem("documentor_history") || "{}");
    if (history[url]) {
      setMessages(history[url]);
    } else {
      setMessages([
        {
          role: "assistant",
          content: `I'm ready to answer questions about ${url}.`,
        },
      ]);
    }
  }, [url]);

  // Save history to localStorage
  useEffect(() => {
    if (!url || messages.length === 0) return;
    const history = JSON.parse(localStorage.getItem("documentor_history") || "{}");
    history[url] = messages;
    localStorage.setItem("documentor_history", JSON.stringify(history));
  }, [messages, url]);

  useEffect(() => {
    if (!url) return;
    if (ready) {
      setStatus("done");
      return;
    }

    let intervalId: ReturnType<typeof setInterval>;

    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/crawl/status?url=${encodeURIComponent(url)}`);
        const data = await res.json();

        setStatus(data.status || "not_found");
        if (typeof data.pages === "number") setPagesIndexed(data.pages);
        if (typeof data.functions === "number") setFunctionsIndexed(data.functions);

        if (data.status === "done" || data.status === "error") {
          clearInterval(intervalId);
        }
      } catch (e) {
        console.error("Failed to fetch crawl status", e);
      }
    };

    checkStatus();
    intervalId = setInterval(checkStatus, 2000);
    return () => clearInterval(intervalId);
  }, [url, ready]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;

    const userText = input;
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setInput("");
    setIsProcessing(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: userText,
          source_url: url || null,
          use_reranker: true,
        }),
      });

      if (!res.ok) {
        const errorPayload = await res.json().catch(() => null);
        throw new Error(errorPayload?.detail || "No content returned.");
      }

      const data: ProcessResponse = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          response: data,
          content: data.processed_content,
        },
      ]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Failed to process query: ${e.message}` },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const startNewConversation = () => {
    if (!url) return;
    const history = JSON.parse(localStorage.getItem("documentor_history") || "{}");
    delete history[url];
    localStorage.setItem("documentor_history", JSON.stringify(history));
    setMessages([
      {
        role: "assistant",
        content: `Conversation reset. I'm ready to answer questions about ${url}.`,
      },
    ]);
  };

  const domainName = url ? url.replace(/https?:\/\//, "").split("/")[0] : "No source";

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
          <span className={`px-2 py-1 rounded-full border ${intentBadgeClass[intent]}`}>
            {intentLabel[intent]}
          </span>
          <span className="text-[#888888]">confidence {confidence}%</span>
        </div>

        <p>{response.explanation || response.processed_content}</p>

        {response.recommended_functions?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-2">Recommended functions</div>
            <div className="flex flex-wrap gap-2">
              {response.recommended_functions.map((fn, idx) => (
                <span key={`${fn}-${idx}`} className="px-2 py-1 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-xs">
                  {fn}
                </span>
              ))}
            </div>
          </div>
        )}

        {response.use_when?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">Use when</div>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {response.use_when.map((item, idx) => (
                <li key={`use-${idx}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {response.avoid_when?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">Avoid when</div>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {response.avoid_when.map((item, idx) => (
                <li key={`avoid-${idx}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {response.fixes?.length > 0 && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">Fixes</div>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {response.fixes.map((item, idx) => (
                <li key={`fix-${idx}`}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {response.code_snippet && (
          <div>
            <div className="text-xs uppercase tracking-wide text-[#888888] mb-1">Code snippet</div>
            <pre className="bg-[#111111] border border-[#2A2A2A] rounded-xl p-3 text-xs overflow-x-auto whitespace-pre-wrap">
              {response.code_snippet}
            </pre>
          </div>
        )}

        {response.source_url && (
          <div className="text-xs text-[#888888]">
            Source:{" "}
            <a className="text-indigo-300 hover:underline" href={response.source_url} target="_blank" rel="noreferrer">
              {response.source_url}
            </a>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-[#0F0F0F] text-[#EEEEEE] font-sans overflow-hidden">
      <aside className="w-64 flex flex-col border-r border-[#222222] bg-[#111111] p-4 hidden md:flex">
        <div className="flex items-center gap-2 mb-6">
          <div className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
            DocuMentor
          </div>
        </div>

        <button className="flex items-center gap-2 px-3 py-2 bg-indigo-500/10 text-indigo-400 rounded-lg w-full text-sm font-medium border border-indigo-500/20 mb-6">
          <div className="w-2 h-2 rounded-full bg-indigo-400" />
          <span className="truncate flex-1 text-left">{domainName}</span>
        </button>

        <div className="flex-1 overflow-y-auto" />

        <button 
          onClick={startNewConversation}
          className="flex items-center justify-center gap-2 w-full py-3 mt-4 text-sm font-medium text-[#EEEEEE] border border-[#333333] hover:bg-[#222222] rounded-xl transition-colors"
        >
          <Plus className="w-4 h-4" />
          New conversation
        </button>
      </aside>

      <main className="flex-1 flex flex-col relative bg-[#0F0F0F] min-w-0">
        <header className="px-6 py-4 border-b border-[#222222] flex items-center justify-between bg-[#111111]/80 backdrop-blur-sm sticky top-0 z-0">
          <div className="flex items-center gap-2 text-sm text-[#888888] font-medium">
            <div className={`w-2 h-2 rounded-full ${status === "done" ? "bg-emerald-400" : status === "error" ? "bg-red-400" : "bg-yellow-400 animate-pulse"}`} />
            {domainName} —
            {status === "crawling" && " indexing..."}
            {status === "parsing" && ` parsing (${pagesIndexed} pages)...`}
            {status === "indexing" && " building retrieval indexes..."}
            {status === "done" && ` indexed ${pagesIndexed} pages, ${functionsIndexed} functions`}
            {status === "error" && " indexing failed"}
            {status === "not_found" && " status not found"}
          </div>
          <button 
            onClick={() => navigate("/")}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-[#222222] rounded-full hover:bg-[#333333] transition-colors"
          >
            <Home className="w-4 h-4" />
            Home
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex flex-col items-center">
          <div className="w-full max-w-4xl flex flex-col gap-8 pb-20">
            {messages.map((message, i) => (
              <div key={i} className={message.role === "user" ? "self-end max-w-[80%]" : "self-start w-full max-w-[95%]"}>
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
                      <span className="text-xs font-medium text-[#888888]">DocuMentor</span>
                    </div>
                    {renderAssistantResponse(message)}
                  </div>
                )}
              </div>
            ))}

            {isProcessing && (
              <div className="self-start w-full max-w-[95%]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  </div>
                  <span className="text-xs font-medium text-[#888888]">DocuMentor is thinking...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="p-4 bg-gradient-to-t from-[#0F0F0F] via-[#0F0F0F] to-transparent shrink-0">
          <div className="max-w-4xl mx-auto relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask anything about the library..."
              className="w-full bg-[#1A1A1A] border border-[#333333] border-glow text-[#EEEEEE] placeholder:text-[#666666] text-sm rounded-xl py-3.5 pl-4 pr-12 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all shadow-lg shadow-black/20"
            />
            <button
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
