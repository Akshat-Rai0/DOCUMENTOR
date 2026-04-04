import { BookOpen, Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const Hero = () => {
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center px-6 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px]" />

      <div className="relative z-10 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border bg-card/60 backdrop-blur-sm mb-8">
          <span className="w-2 h-2 rounded-full bg-primary animate-glow-pulse" />
          <span className="text-xs font-mono text-muted-foreground">RAG-powered documentation intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-7xl font-extrabold tracking-tight mb-6 leading-[1.1]">
          Docs that <span className="text-gradient-primary">understand</span> your questions
        </h1>

        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
          A RAG POWERED documentation experience that delivers precise answers and insights about any functions in the DOCUmentation
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/explore">
            <Button size="lg" className="gap-2 glow-primary px-8">
              <BookOpen className="w-4 h-4" />
              Explore DOCUMENTOR
            </Button>
          </Link>
          <Button variant="outline" size="lg" className="gap-2 px-8">
            <Github className="w-4 h-4" />
            View Source
          </Button>
        </div>
      </div>
    </section>
  );
};

export default Hero;
