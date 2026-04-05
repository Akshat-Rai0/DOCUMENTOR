import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Link as LinkIcon, FunctionSquare, Wrench, ArrowLeftRight, Loader2, X } from "lucide-react";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

type CrawlStatus = "idle" | "starting" | "crawling" | "parsing" | "indexing" | "done" | "error";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const statusToProgress = (status: CrawlStatus): number => {
  if (status === "starting") return 5;
  if (status === "crawling") return 35;
  if (status === "parsing") return 65;
  if (status === "indexing") return 85;
  if (status === "done") return 100;
  return 0;
};

/** Official doc roots used when a quick-start pill is clicked */
const LIBRARY_DOC_URLS: Record<string, string> = {
  Pandas: "https://pandas.pydata.org/docs/",
  FastAPI: "https://fastapi.tiangolo.com/",
  "Three.js": "https://threejs.org/docs/",
  "Scikit-learn": "https://scikit-learn.org/stable/",
  SQLAlchemy: "https://docs.sqlalchemy.org/en/20/",
};

type FeaturePreviewId = "function-finder" | "error-fixer" | "trade-offs";

const FEATURE_PREVIEW: Record<
  FeaturePreviewId,
  {
    title: string;
    tagline: string;
    paragraphs: string[];
    accent: "indigo" | "green" | "orange";
  }
> = {
  "function-finder": {
    title: "Function finder",
    tagline: "How do I group and aggregate rows?",
    accent: "indigo",
    paragraphs: [
      "Describe what you want to do in everyday language—grouping, aggregating, merging, reshaping, reading files, or configuring behavior. You do not need to remember exact API names.",
      "After your docs are indexed, DocuMentor retrieves the most relevant pages and functions, then explains which calls match your intent, what arguments matter, and how they fit together.",
      "Best for exploration and glue code: turning a vague task into a short list of concrete functions with enough context to use them correctly in your project.",
    ],
  },
  "error-fixer": {
    title: "Error fixer",
    tagline: "Paste a traceback, get the fix",
    accent: "green",
    paragraphs: [
      "Paste an error message or full traceback from your run. The system aligns what went wrong with patterns and explanations in the documentation you indexed—not generic web guesses.",
      "You get grounded suggestions: likely causes, the API or usage that typically fixes it, and steps or code shaped to the library version you are actually using.",
      "Best when you are blocked on a failure you partially understand and want a fix tied to official behavior and wording from the docs.",
    ],
  },
  "trade-offs": {
    title: "Trade-offs",
    tagline: "When should I avoid apply()?",
    accent: "orange",
    paragraphs: [
      "Ask when a pattern is appropriate versus when it becomes a footgun: performance, readability, thread safety, or compatibility with future versions.",
      "Answers compare alternatives (for example vectorized versus row-wise work, eager versus lazy evaluation, or different abstraction layers) so you can choose with intent instead of habit.",
      "Best for design questions—picking between idioms, understanding costs, and knowing when the docs recommend a different approach.",
    ],
  },
};

const accentRing: Record<FeaturePreviewId, string> = {
  "function-finder": "ring-indigo-500/30",
  "error-fixer": "ring-green-500/30",
  "trade-offs": "ring-orange-500/30",
};

const featureIcon = (id: FeaturePreviewId) => {
  if (id === "function-finder") return FunctionSquare;
  if (id === "error-fixer") return Wrench;
  return ArrowLeftRight;
};

const featureIconWrap = (accent: "indigo" | "green" | "orange") => {
  if (accent === "indigo") return "bg-indigo-500/10 text-indigo-400";
  if (accent === "green") return "bg-green-500/10 text-green-400";
  return "bg-orange-500/10 text-orange-400";
};

function FeaturePreviewCard({ id, onClose }: { id: FeaturePreviewId; onClose: () => void }) {
  const f = FEATURE_PREVIEW[id];
  const Icon = featureIcon(id);
  return (
    <>
      <button
        type="button"
        onClick={onClose}
        className="absolute right-4 top-4 rounded-lg p-1.5 text-[#888888] hover:bg-[#222222] hover:text-[#EEEEEE] transition-colors"
        aria-label="Close"
      >
        <X className="w-5 h-5" />
      </button>
      <div className={`mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl ${featureIconWrap(f.accent)}`}>
        <Icon className="h-6 w-6" />
      </div>
      <h2 id="feature-preview-title" className="text-xl font-semibold text-[#EEEEEE] pr-10">
        {f.title}
      </h2>
      <p className="mt-1 text-sm text-[#888888] italic">&quot;{f.tagline}&quot;</p>
      <div className="mt-6 space-y-4 text-sm leading-relaxed text-[#BBBBBB] text-left">
        {f.paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </>
  );
}

const Index = () => {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [crawlStatus, setCrawlStatus] = useState<CrawlStatus>("idle");
  const [pagesIndexed, setPagesIndexed] = useState(0);
  const [functionsIndexed, setFunctionsIndexed] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState<FeaturePreviewId | null>(null);

  useEffect(() => {
    if (!previewOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPreviewOpen(null);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [previewOpen]);

  const pollStatusUntilDone = async (targetUrl: string): Promise<CrawlStatus> => {
    for (let attempt = 0; attempt < 180; attempt++) {
      const res = await fetch(`${API_BASE_URL}/api/crawl/status?url=${encodeURIComponent(targetUrl)}`);
      const data = await res.json();

      const status = (data.status || "idle") as CrawlStatus;
      if (typeof data.pages === "number") setPagesIndexed(data.pages);
      if (typeof data.functions === "number") setFunctionsIndexed(data.functions);

      if (status === "done") {
        setCrawlStatus("done");
        return "done";
      }
      if (status === "error") {
        setCrawlStatus("error");
        setErrorMessage(data.error || "Indexing failed.");
        return "error";
      }

      if (status === "crawling" || status === "parsing" || status === "indexing") {
        setCrawlStatus(status);
      }

      await sleep(2000);
    }
    setCrawlStatus("error");
    setErrorMessage("Indexing timed out. Please try again.");
    return "error";
  };

  const handleIndex = async (overrideUrl?: string) => {
    const targetUrl = (overrideUrl ?? url).trim();
    if (!targetUrl) return;
    if (overrideUrl !== undefined) {
      setUrl(overrideUrl);
    }
    setIsLoading(true);
    setErrorMessage(null);
    setPagesIndexed(0);
    setFunctionsIndexed(0);
    setCrawlStatus("starting");
    try {
      const startRes = await fetch(`${API_BASE_URL}/api/crawl`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: targetUrl })
      });

      if (!startRes.ok) {
        throw new Error("Failed to start crawl.");
      }

      const finalStatus = await pollStatusUntilDone(targetUrl);
      if (finalStatus === "done") {
        navigate(`/chat?url=${encodeURIComponent(targetUrl)}&ready=1`);
      }
    } catch (e) {
      console.error(e);
      setCrawlStatus("error");
      setErrorMessage("Could not reach backend. Check if API is running.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#111111] text-[#EEEEEE] font-sans flex flex-col relative">
      {/* Header */}
      <header className="flex justify-between items-center py-6 px-10 border-b border-[#222222]">
        <div className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
          DocuMentor
        </div>
        <nav className="flex items-center gap-2">
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center -mt-20 px-6">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
          Ask anything about any library
        </h1>
        <p className="text-[#888888] text-center max-w-xl text-sm sm:text-base leading-relaxed mb-10">
          Paste a documentation URL. We'll read the whole thing, then answer your questions — with the right function, when to use it, and working code.
        </p>

        {/* Input Bar */}
        <div className="w-full max-w-3xl relative mb-4">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[#555555]">
            <LinkIcon className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://pandas.pydata.org/docs/"
            className="w-full bg-[#1A1A1A] border border-[#333333] rounded-2xl py-4 pl-12 pr-32 text-sm text-[#DDDDDD] placeholder:text-[#555555] focus:outline-none focus:border-[#555555] focus:ring-1 focus:ring-[#555555] transition-all"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleIndex();
              }
            }}
          />
          <button 
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-[#333333] hover:bg-[#444444] text-[#EEEEEE] text-sm font-medium px-6 py-2 rounded-xl transition-colors disabled:opacity-50"
            onClick={handleIndex}
            disabled={isLoading || !url}
          >
            {isLoading ? "Indexing..." : "Index docs"}
          </button>
        </div>

        {(isLoading || crawlStatus === "error" || crawlStatus === "done") && (
          <div className="w-full max-w-3xl mb-8">
            <div className="w-full h-2 rounded-full bg-[#1E1E1E] overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${crawlStatus === "error" ? "bg-red-500" : "bg-indigo-500"}`}
                style={{ width: `${statusToProgress(crawlStatus)}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-[#888888] flex items-center gap-2">
              {isLoading && crawlStatus !== "done" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              <span>
                {crawlStatus === "starting" && "Starting crawl job..."}
                {crawlStatus === "crawling" && "Crawling documentation pages..."}
                {crawlStatus === "parsing" && `Parsing pages (${pagesIndexed} crawled)...`}
                {crawlStatus === "indexing" && `Building retrieval index (${functionsIndexed} functions parsed)...`}
                {crawlStatus === "done" && `Done — ${pagesIndexed} pages and ${functionsIndexed} functions indexed.`}
                {crawlStatus === "error" && (errorMessage || "Indexing failed.")}
              </span>
            </div>
          </div>
        )}


        {/* Pills */}
        <div className="flex flex-wrap justify-center gap-3 mb-16">
          {(Object.keys(LIBRARY_DOC_URLS) as Array<keyof typeof LIBRARY_DOC_URLS>).map((tag) => (
            <button
              key={tag}
              type="button"
              className="px-4 py-2 rounded-full border border-[#333333] text-sm text-[#888888] hover:bg-[#222222] hover:text-[#DDDDDD] transition-all disabled:opacity-50"
              disabled={isLoading}
              onClick={() => handleIndex(LIBRARY_DOC_URLS[tag])}
            >
              {tag}
            </button>
          ))}
        </div>

        {/* Feature Cards */}
        <div className="w-full max-w-4xl text-center">
          <div className="text-xs font-mono text-[#555555] mb-6 tracking-widest uppercase">what you can ask</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
            <button
              type="button"
              onClick={() => setPreviewOpen("function-finder")}
              className="text-left bg-[#151515] hover:bg-[#1A1A1A] border border-[#222222] rounded-2xl p-5 transition-colors cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-110 transition-transform">
                <FunctionSquare className="w-4 h-4" />
              </div>
              <h3 className="text-[#EEEEEE] font-medium text-sm mb-1">Function finder</h3>
              <p className="text-[#888888] text-xs">&quot;How do I group and aggregate rows?&quot;</p>
            </button>

            <button
              type="button"
              onClick={() => setPreviewOpen("error-fixer")}
              className="text-left bg-[#151515] hover:bg-[#1A1A1A] border border-[#222222] rounded-2xl p-5 transition-colors cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center text-green-400 mb-4 group-hover:scale-110 transition-transform">
                <Wrench className="w-4 h-4" />
              </div>
              <h3 className="text-[#EEEEEE] font-medium text-sm mb-1">Error fixer</h3>
              <p className="text-[#888888] text-xs">&quot;Paste a traceback, get the fix&quot;</p>
            </button>

            <button
              type="button"
              onClick={() => setPreviewOpen("trade-offs")}
              className="text-left bg-[#151515] hover:bg-[#1A1A1A] border border-[#222222] rounded-2xl p-5 transition-colors cursor-pointer group"
            >
              <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-400 mb-4 group-hover:scale-110 transition-transform">
                <ArrowLeftRight className="w-4 h-4" />
              </div>
              <h3 className="text-[#EEEEEE] font-medium text-sm mb-1">Trade-offs</h3>
              <p className="text-[#888888] text-xs">&quot;When should I avoid apply()?&quot;</p>
            </button>
          </div>
        </div>

      </main>

      {previewOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
          role="presentation"
          onClick={() => setPreviewOpen(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="feature-preview-title"
            className={`relative w-full max-w-lg rounded-2xl border border-[#333333] bg-[#151515] p-6 sm:p-8 shadow-2xl ring-2 ${accentRing[previewOpen]} animate-in zoom-in-95 duration-200`}
            onClick={(e) => e.stopPropagation()}
          >
            <FeaturePreviewCard id={previewOpen} onClose={() => setPreviewOpen(null)} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Index;
