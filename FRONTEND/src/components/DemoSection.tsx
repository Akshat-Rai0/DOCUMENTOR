import { useState } from "react";
import { Zap, AlertTriangle, Bug, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
 
const presetQueries: Record<string, string[]> = {
  recommend: ["How do I normalize data?", "Read a CSV file in Python", "Sort a list of dictionaries"],
  antipattern: ["When should I avoid pandas apply?", "Is iterrows() efficient?", "Should I use global variables?"],
  errorfix: ["ModuleNotFoundError: No module named 'sklearn'", "KeyError: 'column_name'", "TypeError: unsupported operand type(s)"],
};
 
type Mode = "recommend" | "antipattern" | "errorfix";
 
// Map frontend modes to backend intents
const modeToIntent: Record<Mode, string> = {
  recommend: "function_search",
  antipattern: "concept_explain",
  errorfix: "error_fix",
};
 
interface BackendResponse {
  status: string;
  intent: string;
  processed_content: string;
  recommended_functions: string[];
  use_when: string[];
  avoid_when: string[];
  code_snippet: string;
  source_url: string;
  confidence: number;
  explanation: string;
  fixes: string[];
  retrieved_chunks: Array<{
    chunk_id: string;
    score: number;
    text: string;
    source_url: string;
    function_name: string;
    rank: number;
  }>;
}
 
interface SimulatedResponse {
  mode: Mode;
  query: string;
  content: React.ReactNode;
}
 
const callBackend = async (query: string, mode: Mode): Promise<BackendResponse> => {
  const response = await fetch('http://localhost:8000/api/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: query,
      intent: modeToIntent[mode],
      use_reranker: true,
    }),
  });
 
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Backend error: ${response.statusText}`);
  }
 
  return response.json();
};
 
const ConfidenceBadge = ({ confidence }: { confidence: number }) => {
  const pct = Math.round(confidence * 100);
  const tier =
    confidence >= 0.7 ? "high" : confidence >= 0.4 ? "medium" : "low";
 
  const styles: Record<string, string> = {
    high: "bg-emerald-500/10 text-emerald-500",
    medium: "bg-amber-500/10 text-amber-500",
    low: "bg-destructive/10 text-destructive",
  };
 
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${styles[tier]}`}>
      Confidence: {pct}%
    </span>
  );
};
 
const renderBackendResponse = (mode: Mode, data: BackendResponse): React.ReactNode => {
  if (mode === "recommend") {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary">Recommended</span>
          <span className="text-xs text-muted-foreground">{data.recommended_functions.length} candidates found</span>
          <ConfidenceBadge confidence={data.confidence} />
        </div>
        <div className="space-y-3">
          {data.recommended_functions.map((func, idx) => (
            <div key={idx} className="border border-border rounded-lg p-4 bg-background/50">
              <div className="flex items-center justify-between mb-2">
                <code className="text-primary font-mono text-sm font-semibold">{func}</code>
                {idx === 0 && <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">★ Best match</span>}
              </div>
              <p className="text-sm text-muted-foreground mb-2">{data.explanation}</p>
              {data.code_snippet && (
                <div className="code-block p-3 text-xs whitespace-pre-wrap">
                  {data.code_snippet}
                </div>
              )}
              {data.use_when.length > 0 && (
                <div className="mt-3">
                  <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-1">Use when</span>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {data.use_when.map((item, i) => <li key={i}>• {item}</li>)}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
        {data.source_url && (
          <div className="text-xs text-muted-foreground border-t border-border pt-3">
            Source: <a href={data.source_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{data.source_url}</a>
          </div>
        )}
      </div>
    );
  }
 
  if (mode === "antipattern") {
    return (
      <div className="space-y-4">
        <div className="border border-border rounded-lg p-4 bg-background/50">
          <div className="flex items-center gap-2 mb-3">
            <code className="text-primary font-mono text-sm font-semibold">{data.recommended_functions[0] || "Function"}</code>
            <ConfidenceBadge confidence={data.confidence} />
          </div>
          {(data.use_when.length > 0 || data.avoid_when.length > 0) && (
            <div className="grid grid-cols-2 gap-4 mb-4">
              {data.use_when.length > 0 && (
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-2">✓ Use when</span>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {data.use_when.map((item, i) => <li key={i}>• {item}</li>)}
                  </ul>
                </div>
              )}
              {data.avoid_when.length > 0 && (
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-destructive block mb-2">✗ Avoid when</span>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {data.avoid_when.map((item, i) => <li key={i}>• {item}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
          {data.code_snippet && (
            <div className="code-block p-3 text-xs whitespace-pre-wrap">
              {data.code_snippet}
            </div>
          )}
        </div>
        <div className="text-xs text-muted-foreground border-t border-border pt-3 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-destructive" />
          {data.explanation}
        </div>
      </div>
    );
  }
 
  if (mode === "errorfix") {
    return (
      <div className="space-y-4">
        <div className="border border-destructive/30 rounded-lg p-4 bg-destructive/5">
          <div className="flex items-center gap-2 mb-2">
            <Bug className="w-4 h-4 text-destructive" />
            <span className="text-xs font-mono text-destructive">Error Analysis</span>
            <ConfidenceBadge confidence={data.confidence} />
          </div>
          <p className="text-sm text-muted-foreground">{data.explanation}</p>
        </div>
        {data.fixes.length > 0 && (
          <div className="border border-border rounded-lg p-4 bg-background/50">
            <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-3">Fixes</span>
            <ul className="text-sm text-muted-foreground space-y-2">
              {data.fixes.map((fix, i) => <li key={i}>• {fix}</li>)}
            </ul>
          </div>
        )}
        {data.code_snippet && (
          <div className="border border-primary/20 rounded-lg p-4 bg-primary/5">
            <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-2">Code Example</span>
            <div className="code-block p-3 text-xs whitespace-pre-wrap">
              {data.code_snippet}
            </div>
          </div>
        )}
        {data.source_url && (
          <div className="text-xs text-muted-foreground border-t border-border pt-3">
            Source: <a href={data.source_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{data.source_url}</a>
          </div>
        )}
      </div>
    );
  }
 
  return <div className="text-sm text-muted-foreground">{data.processed_content}</div>;
};
 
const modes: { key: Mode; label: string; icon: typeof Zap; desc: string }[] = [
  { key: "recommend", label: "Recommend", icon: Zap, desc: "Function recommendations" },
  { key: "antipattern", label: "Anti-Pattern", icon: AlertTriangle, desc: "When NOT to use" },
  { key: "errorfix", label: "Error Fix", icon: Bug, desc: "Error → root cause → fix" },
];
 
const DemoSection = () => {
  const [activeMode, setActiveMode] = useState<Mode>("recommend");
  const [query, setQuery] = useState(presetQueries.recommend[0]);
  const [response, setResponse] = useState<BackendResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
 
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsLoading(true);
    setResponse(null);
    setError(null);
    try {
      const data = await callBackend(query, activeMode);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch response");
    } finally {
      setIsLoading(false);
    }
  };
 
  const switchMode = (mode: Mode) => {
    setActiveMode(mode);
    setQuery(presetQueries[mode][0]);
    setResponse(null);
  };
 
  return (
    <section className="py-24 px-6 bg-card/40">
      <div className="container max-w-4xl">
        <div className="text-center mb-12">
          <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">Interactive Demo</span>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Try It Yourself</h2>
          <p className="text-muted-foreground max-w-xl mx-auto">Pick a mode, type a query (or use a preset), and see how the system responds.</p>
        </div>
 
        {/* Mode tabs */}
        <div className="flex gap-2 mb-6 justify-center flex-wrap">
          {modes.map((m) => (
            <button
              key={m.key}
              onClick={() => switchMode(m.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeMode === m.key
                  ? "bg-primary text-primary-foreground glow-primary"
                  : "surface-glass text-muted-foreground hover:text-foreground hover:border-glow"
              }`}
            >
              <m.icon className="w-4 h-4" />
              {m.label}
            </button>
          ))}
        </div>
 
        {/* Preset chips */}
        <div className="flex gap-2 mb-4 flex-wrap justify-center">
          {presetQueries[activeMode].map((q) => (
            <button
              key={q}
              onClick={() => { setQuery(q); setResponse(null); }}
              className={`text-xs px-3 py-1.5 rounded-full border transition-all duration-200 font-mono ${
                query === q ? "border-primary text-primary bg-primary/10" : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {q.length > 40 ? q.slice(0, 40) + "…" : q}
            </button>
          ))}
        </div>
 
        {/* Input */}
        <form onSubmit={handleSubmit} className="mb-6">
          <div className="surface-glass rounded-xl p-1.5 flex items-center gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Try: "${presetQueries[activeMode][0]}"`}
              className="flex-1 bg-transparent border-none outline-none px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground font-mono"
            />
            <Button type="submit" size="sm" disabled={isLoading || !query.trim()} className="gap-2 px-5">
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Run
            </Button>
          </div>
        </form>
 
        {/* Response area */}
        <div className="surface-glass rounded-xl p-6 min-h-[200px]">
          {isLoading && (
            <div className="flex items-center justify-center h-[200px]">
              <div className="flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-5 h-5 animate-spin text-primary" />
                <span className="text-sm font-mono">Retrieving from pipeline…</span>
              </div>
            </div>
          )}
          {!isLoading && !response && !error && (
            <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
              Hit <span className="font-mono text-primary mx-1">Run</span> to see the response
            </div>
          )}
          {!isLoading && error && (
            <div className="flex items-center justify-center h-[200px] text-destructive text-sm">
              {error}
            </div>
          )}
          {!isLoading && response && (
            <div className="animate-fade-in">{renderBackendResponse(activeMode, response)}</div>
          )}
        </div>
      </div>
    </section>
  );
};
 
export default DemoSection;