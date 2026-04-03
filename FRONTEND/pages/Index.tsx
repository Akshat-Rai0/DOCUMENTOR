import Hero from "@/components/Hero";
import ModesSection from "@/components/ModesSection";
import PipelineSection from "@/components/PipelineSection";
import DataModelSection from "@/components/DataModelSection";
import RetrievalSection from "@/components/RetrievalSection";
import StackSection from "@/components/StackSection";
import ImprovementsSection from "@/components/ImprovementsSection";
import TimelineSection from "@/components/TimelineSection";
import DemoSection from "@/components/DemoSection";

const Index = () => {
  return (
    <div className="min-h-screen">
      <Hero />
      <DemoSection />
      <ModesSection />
      <PipelineSection />
      <DataModelSection />
      <RetrievalSection />
      <StackSection />
      <ImprovementsSection />
      <TimelineSection />
      <footer className="py-12 px-6 border-t border-border text-center">
        <p className="text-sm text-muted-foreground font-mono">Built with a 7-stage RAG pipeline · No hallucinations by design</p>
      </footer>
    </div>
  );
};

export default Index;
