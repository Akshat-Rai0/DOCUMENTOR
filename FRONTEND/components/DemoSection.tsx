import { useState } from "react";
import { Zap, AlertTriangle, Bug, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const presetQueries: Record<string, string[]> = {
  recommend: ["How do I normalize data?", "Read a CSV file in Python", "Sort a list of dictionaries"],
  antipattern: ["When should I avoid pandas apply?", "Is iterrows() efficient?", "Should I use global variables?"],
  errorfix: ["ModuleNotFoundError: No module named 'sklearn'", "KeyError: 'column_name'", "TypeError: unsupported operand type(s)"],
};

type Mode = "recommend" | "antipattern" | "errorfix";

interface SimulatedResponse {
  mode: Mode;
  query: string;
  content: React.ReactNode;
}

const simulateResponse = (mode: Mode, query: string): SimulatedResponse => {
  const responses: Record<Mode, Record<string, React.ReactNode>> = {
    recommend: {
      default: (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary">Recommended</span>
            <span className="text-xs text-muted-foreground">2 candidates found</span>
          </div>
          <div className="space-y-3">
            <div className="border border-border rounded-lg p-4 bg-background/50">
              <div className="flex items-center justify-between mb-2">
                <code className="text-primary font-mono text-sm font-semibold">sklearn.preprocessing.StandardScaler</code>
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">★ Best match</span>
              </div>
              <p className="text-sm text-muted-foreground mb-2">Zero mean, unit variance. Use when your model assumes normally distributed features (SVM, logistic regression).</p>
              <div className="code-block p-3 text-xs">
                <span className="text-muted-foreground">from</span> <span className="text-primary">sklearn.preprocessing</span> <span className="text-muted-foreground">import</span> StandardScaler{"\n"}
                scaler = StandardScaler().fit_transform(X)
              </div>
            </div>
            <div className="border border-border rounded-lg p-4 bg-background/50">
              <div className="flex items-center justify-between mb-2">
                <code className="text-accent font-mono text-sm font-semibold">sklearn.preprocessing.MinMaxScaler</code>
                <span className="text-xs px-2 py-0.5 rounded-full bg-accent/10 text-accent">Alternative</span>
              </div>
              <p className="text-sm text-muted-foreground mb-2">Scales to [0, 1]. Use when you need bounded values (neural networks, image pixels).</p>
              <div className="code-block p-3 text-xs">
                <span className="text-muted-foreground">from</span> <span className="text-primary">sklearn.preprocessing</span> <span className="text-muted-foreground">import</span> MinMaxScaler{"\n"}
                scaler = MinMaxScaler().fit_transform(X)
              </div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground border-t border-border pt-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            Trade-off: StandardScaler preserves outlier distances; MinMaxScaler compresses them.
          </div>
        </div>
      ),
    },
    antipattern: {
      default: (
        <div className="space-y-4">
          <div className="border border-border rounded-lg p-4 bg-background/50">
            <div className="flex items-center gap-2 mb-3">
              <code className="text-primary font-mono text-sm font-semibold">pandas.DataFrame.apply()</code>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-2">✓ Use when</span>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Row-wise custom logic with multiple columns</li>
                  <li>• Complex string transformations</li>
                  <li>• Applying non-vectorizable functions</li>
                </ul>
              </div>
              <div>
                <span className="text-xs font-mono uppercase tracking-wider text-destructive block mb-2">✗ Avoid when</span>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Vectorized alternatives exist (10–100× slower)</li>
                  <li>• Simple arithmetic or comparisons</li>
                  <li>• Operations on a single column</li>
                </ul>
              </div>
            </div>
            <div className="code-block p-3 text-xs space-y-2">
              <div><span className="text-destructive">✗</span> <span className="text-muted-foreground">df['c'] = df.apply(lambda r: r['a'] + r['b'], axis=1)</span></div>
              <div><span className="text-primary">✓</span> <span className="text-muted-foreground">df['c'] = df['a'] + df['b']  </span><span className="text-primary"># 50× faster</span></div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground border-t border-border pt-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-destructive" />
            pandas.apply() with axis=1 is essentially a Python for-loop in disguise.
          </div>
        </div>
      ),
    },
    errorfix: {
      default: (
        <div className="space-y-4">
          <div className="border border-destructive/30 rounded-lg p-4 bg-destructive/5">
            <div className="flex items-center gap-2 mb-2">
              <Bug className="w-4 h-4 text-destructive" />
              <span className="text-xs font-mono text-destructive">ModuleNotFoundError</span>
            </div>
            <code className="text-sm text-muted-foreground">No module named 'sklearn'</code>
          </div>
          <div className="border border-border rounded-lg p-4 bg-background/50">
            <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-3">Root Cause</span>
            <p className="text-sm text-muted-foreground mb-4">
              The package name is <code className="text-primary font-mono">scikit-learn</code>, not <code className="text-destructive font-mono">sklearn</code>. The import name differs from the pip package name.
            </p>
            <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-2">Fix</span>
            <div className="code-block p-3 text-xs space-y-1">
              <div className="text-muted-foreground">pip install scikit-learn</div>
            </div>
          </div>
          <div className="border border-primary/20 rounded-lg p-4 bg-primary/5">
            <span className="text-xs font-mono uppercase tracking-wider text-primary block mb-2">Verified Setup</span>
            <div className="code-block p-3 text-xs space-y-1">
              <div><span className="text-muted-foreground">pip install scikit-learn</span></div>
              <div><span className="text-muted-foreground">python -c "import sklearn; print(sklearn.__version__)"</span></div>
              <div><span className="text-primary"># → 1.3.2</span></div>
            </div>
          </div>
        </div>
      ),
    },
  };
  return { mode, query, content: responses[mode].default };
};

const modes: { key: Mode; label: string; icon: typeof Zap; desc: string }[] = [
  { key: "recommend", label: "Recommend", icon: Zap, desc: "Function recommendations" },
  { key: "antipattern", label: "Anti-Pattern", icon: AlertTriangle, desc: "When NOT to use" },
  { key: "errorfix", label: "Error Fix", icon: Bug, desc: "Error → root cause → fix" },
];

const DemoSection = () => {
  const [activeMode, setActiveMode] = useState<Mode>("recommend");
  const [query, setQuery] = useState(presetQueries.recommend[0]);
  const [response, setResponse] = useState<SimulatedResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsLoading(true);
    setResponse(null);
    setTimeout(() => {
      setResponse(simulateResponse(activeMode, query));
      setIsLoading(false);
    }, 800);
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
          {!isLoading && !response && (
            <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
              Hit <span className="font-mono text-primary mx-1">Run</span> to see the response
            </div>
          )}
          {!isLoading && response && (
            <div className="animate-fade-in">{response.content}</div>
          )}
        </div>
      </div>
    </section>
  );
};

export default DemoSection;
