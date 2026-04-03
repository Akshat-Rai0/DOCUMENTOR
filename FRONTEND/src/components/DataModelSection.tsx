const codeSnippet = `{
  "type": "function",
  "name": "pandas.read_csv",
  "library": "pandas",
  "version": "2.1.0",
  "params": [
    { "name": "filepath_or_buffer", "type": "str", "required": true },
    { "name": "sep", "type": "str", "default": "," },
    { "name": "dtype", "type": "dict", "default": null }
  ],
  "use_when": ["loading tabular data from disk"],
  "avoid_when": ["file > available RAM — use chunksize or Dask"],
  "example": "df = pd.read_csv('data.csv', dtype={'id': str})",
  "related": ["pandas.read_parquet", "pandas.read_json"],
  "notes": "Use engine='pyarrow' for 3–5× faster parse"
}`;

const DataModelSection = () => {
  return (
    <section className="py-24 px-6">
      <div className="container max-w-6xl">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">03 — Data Model</span>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Structured Function Storage</h2>
            <p className="text-muted-foreground mb-6">
              Each function is stored as a typed JSON object — not raw text. Metadata like <code className="text-primary font-mono text-sm">use_when</code> and <code className="text-primary font-mono text-sm">avoid_when</code> are pre-populated from docs during ingestion.
            </p>
            <p className="text-muted-foreground">
              The LLM doesn't generate anti-pattern advice at query time. It's already in the data. This makes answers <span className="text-foreground font-medium">reliable, not hallucinated</span>.
            </p>
          </div>
          <div className="code-block p-4 overflow-auto max-h-[450px] glow-primary">
            <pre className="text-xs leading-relaxed">
              <code className="text-muted-foreground">
                {codeSnippet.split('\n').map((line, i) => (
                  <span key={i} className="block">
                    <span className="text-border select-none mr-4 inline-block w-5 text-right">{i + 1}</span>
                    {line.includes('"name"') || line.includes('"type"') ? (
                      <span>
                        {line.replace(/(\"[^"]+\")/, '').split(/(\"[^"]+\")/g).map((part, j) =>
                          part.startsWith('"') ? <span key={j} className="text-primary">{part}</span> : part
                        )}
                      </span>
                    ) : (
                      line
                    )}
                  </span>
                ))}
              </code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DataModelSection;
