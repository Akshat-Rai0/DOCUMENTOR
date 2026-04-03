import { Search, Brain, Filter } from "lucide-react";

const layers = [
  {
    icon: Search,
    name: "BM25 (Keyword)",
    catches: 'Exact function names. "read_csv" → finds pandas.read_csv directly.',
    fails: "Concept queries with no matching keywords.",
  },
  {
    icon: Brain,
    name: "Dense Embeddings",
    catches: '"load tabular file" → finds read_csv semantically.',
    fails: "Exact rare tokens like function names with underscores.",
  },
  {
    icon: Filter,
    name: "Cross-Encoder Reranker",
    catches: "Re-reads query + each candidate together. Eliminates false positives.",
    fails: "N/A — final precision layer.",
  },
];

const RetrievalSection = () => {
  return (
    <section className="py-24 px-6 bg-card/40">
      <div className="container max-w-6xl">
        <div className="text-center mb-16">
          <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">04 — Retrieval</span>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Hybrid Search Architecture</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            BM25 + embeddings + reranker. Merged via Reciprocal Rank Fusion: <code className="font-mono text-primary text-sm">score = Σ 1/(k + rank_i)</code>
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {layers.map((layer) => (
            <div key={layer.name} className="surface-glass rounded-xl p-6 hover:border-glow transition-all duration-300">
              <layer.icon className="w-8 h-8 text-primary mb-4" />
              <h3 className="font-semibold mb-3">{layer.name}</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-primary">Catches</span>
                  <p className="text-muted-foreground mt-1">{layer.catches}</p>
                </div>
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-accent">Fails on</span>
                  <p className="text-muted-foreground mt-1">{layer.fails}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default RetrievalSection;
