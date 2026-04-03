import { ArrowRight } from "lucide-react";

const stages = [
  { num: "1", name: "Scrape", desc: "Crawl4AI / Playwright for JS-heavy docs" },
  { num: "2", name: "Clean", desc: "Strip boilerplate, extract typed JSON" },
  { num: "3", name: "Chunk", desc: "By function boundary, not token count" },
  { num: "4", name: "Embed", desc: "text-embedding-3-small → ChromaDB" },
  { num: "5", name: "Retrieve", desc: "BM25 + dense embeddings via RRF" },
  { num: "6", name: "Rerank", desc: "Cross-encoder re-scores top-k" },
  { num: "7", name: "Answer", desc: "Strict-format LLM, no hallucinations" },
];

const PipelineSection = () => {
  return (
    <section className="py-24 px-6 bg-card/40">
      <div className="container max-w-6xl">
        <div className="text-center mb-16">
          <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">02 — Pipeline</span>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">7-Stage Architecture</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">Every stage has a clear job — from URL to verified answer.</p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2 md:gap-0">
          {stages.map((stage, i) => (
            <div key={stage.num} className="flex items-center">
              <div className="surface-glass rounded-xl p-4 min-w-[140px] text-center hover:border-glow transition-all duration-300 group">
                <span className="text-xs font-mono text-primary block mb-1">Stage {stage.num}</span>
                <h4 className="font-semibold text-sm mb-1">{stage.name}</h4>
                <p className="text-xs text-muted-foreground">{stage.desc}</p>
              </div>
              {i < stages.length - 1 && (
                <ArrowRight className="w-4 h-4 text-primary mx-2 hidden md:block flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default PipelineSection;
