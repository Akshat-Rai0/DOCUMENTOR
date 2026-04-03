import { Zap, AlertTriangle, Bug } from "lucide-react";

const modes = [
  {
    icon: Zap,
    title: "Function Recommendation",
    description: "Describe a goal in plain English. Get ranked function candidates, trade-offs, and code snippets.",
    example: '"How do I normalize data?" → StandardScaler vs MinMaxScaler with trade-offs',
    color: "text-primary",
  },
  {
    icon: AlertTriangle,
    title: "Anti-Pattern Detection",
    description: 'Every answer includes a structured "avoid when" section. Learn the right patterns from day one.',
    example: "pandas.apply() — Avoid when: vectorized alternatives exist (10–100× slower)",
    color: "text-accent",
  },
  {
    icon: Bug,
    title: "Error → Fix Mode",
    description: "Paste a traceback. Get root cause, fix, and a verified working snippet.",
    example: "ModuleNotFoundError: No module named 'xyz' → install docs + fix + setup snippet",
    color: "text-primary",
  },
];

const ModesSection = () => {
  return (
    <section className="py-24 px-6">
      <div className="container max-w-6xl">
        <div className="text-center mb-16">
          <span className="text-xs font-mono font-medium tracking-widest uppercase text-primary mb-4 block">01 — Core Modes</span>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Three Intelligent Response Modes</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">The system adapts its output format based on what you're actually asking — function search, anti-patterns, or error debugging.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {modes.map((mode, i) => (
            <div
              key={mode.title}
              className="surface-glass rounded-xl p-6 hover:border-glow transition-all duration-300 group"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <mode.icon className={`w-8 h-8 ${mode.color} mb-4`} />
              <h3 className="text-lg font-semibold mb-2">{mode.title}</h3>
              <p className="text-sm text-muted-foreground mb-4">{mode.description}</p>
              <div className="code-block p-3 text-xs text-muted-foreground">
                {mode.example}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ModesSection;
