import Hero from "@/components/Hero";

const Index = () => {
  return (
    <div className="min-h-screen">
      <Hero />
      <footer className="py-12 px-6 border-t border-border text-center absolute bottom-0 w-full">
        <p className="text-sm text-muted-foreground font-mono">JUST DROP THE URL AND ASK</p>
      </footer>
    </div>
  );
};

export default Index;
