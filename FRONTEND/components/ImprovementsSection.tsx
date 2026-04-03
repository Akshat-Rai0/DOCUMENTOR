import { Lightbulb, GitBranch, Shield, Play } from "lucide-react";

const improvements = [
  {
    icon: Lightbulb,
    title: "Query Intent Classifier",
    description: "Pre-retrieval classification into function search, error fix, or concept explanation. Each intent uses a different retrieval strategy and prompt template.",
  },
  {
    icon: GitBranch,
    title: "Version-Aware Ingestion",
    description: 'Store library version tags alongside every chunk. Warn users: "This answer is based on v2.1 — you\'re on v1.5, this function may not exist."',
  },
  {
    icon: Shield,
    title: "Confidence + Citations",
    description: "Show retrieval confidence and link to exact documentation pages. Below-threshold results trigger honest uncertainty signals.",
  },
  {
    icon: Play,
    title: "Sandboxed Snippet Runner",
    description: "Verify generated code actually runs before showing it. A snippet that executes is worth 10× one that might.",
  },
];

const ImprovementsSection = () => {
  return (
    <section className="py-24 px-6 bg-card/40">
      <div className="container max-w-6xl">
        <div className="text-center mb-16">
          <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">06 — Improvements</span>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Further Recommendations</h2>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {improvements.map((item) => (
            <div key={item.title} className="surface-glass rounded-xl p-6 hover:border-glow transition-all duration-300">
              <item.icon className="w-6 h-6 text-accent mb-3" />
              <h3 className="font-semibold mb-2">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ImprovementsSection;
