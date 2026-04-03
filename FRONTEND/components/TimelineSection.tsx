const weeks = [
  {
    week: "Week 1",
    label: "Core",
    tasks: "Scraper + JSON schema extraction + ChromaDB storage. One library fully indexed.",
  },
  {
    week: "Week 2",
    label: "Retrieval",
    tasks: "BM25 + embeddings + RRF merge. Streamlit chat UI. Test with 20 real questions.",
  },
  {
    week: "Week 3",
    label: "Intelligence",
    tasks: "Intent classifier + three LLM prompt templates. Add avoid_when to all answers.",
  },
  {
    week: "Week 4",
    label: "Polish",
    tasks: "Reranker + source citations + version caching. Deploy on Railway or Render.",
  },
];

const TimelineSection = () => {
  return (
    <section className="py-24 px-6">
      <div className="container max-w-4xl">
        <div className="text-center mb-16">
          <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">07 — Feasibility</span>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">4-Week Build Plan</h2>
          <p className="text-muted-foreground">Buildable in &lt;1 month at intermediate level. Prioritize ruthlessly.</p>
        </div>
        <div className="relative">
          <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-px bg-border" />
          <div className="space-y-8">
            {weeks.map((w, i) => (
              <div key={w.week} className={`relative flex items-start gap-6 ${i % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'}`}>
                <div className="absolute left-4 md:left-1/2 w-3 h-3 rounded-full bg-primary -translate-x-1.5 mt-2 animate-glow-pulse" />
                <div className={`ml-10 md:ml-0 md:w-1/2 ${i % 2 === 0 ? 'md:pr-12 md:text-right' : 'md:pl-12'}`}>
                  <div className="surface-glass rounded-xl p-5 hover:border-glow transition-all duration-300">
                    <div className="flex items-center gap-2 mb-2" style={{ justifyContent: i % 2 === 0 ? 'flex-end' : 'flex-start' }}>
                      <span className="font-mono text-primary text-sm font-medium">{w.week}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">{w.label}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{w.tasks}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default TimelineSection;
