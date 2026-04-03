const stack = [
  { category: "Scraping", tool: "Crawl4AI", note: "JS rendering, markdown extraction" },
  { category: "Keyword Search", tool: "rank_bm25", note: "Python, lightweight" },
  { category: "Embeddings", tool: "text-embedding-3-small", note: "OpenAI or sentence-transformers" },
  { category: "Vector DB", tool: "ChromaDB → Pinecone", note: "Local MVP → production" },
  { category: "Reranker", tool: "ms-marco-MiniLM", note: "cross-encoder via sentence-transformers" },
  { category: "LLM", tool: "Claude Sonnet", note: "Strict system prompt" },
  { category: "Backend", tool: "FastAPI + Python", note: "" },
  { category: "Frontend", tool: "Streamlit → React", note: "MVP → v2" },
];

const StackSection = () => {
  return (
    <section className="py-24 px-6">
      <div className="container max-w-5xl">
        <div className="text-center mb-16">
          <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">05 — Stack</span>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Technology Stack</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stack.map((item) => (
            <div key={item.category} className="surface-glass rounded-xl p-4 hover:border-glow transition-all duration-300 text-center">
              <span className="text-xs font-mono text-primary block mb-2">{item.category}</span>
              <p className="font-semibold text-sm">{item.tool}</p>
              {item.note && <p className="text-xs text-muted-foreground mt-1">{item.note}</p>}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default StackSection;
