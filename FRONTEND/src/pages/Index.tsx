import { Link, useNavigate } from "react-router-dom";
import { Link as LinkIcon, FunctionSquare, Wrench, ArrowLeftRight } from "lucide-react";

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#111111] text-[#EEEEEE] font-sans flex flex-col">
      {/* Header */}
      <header className="flex justify-between items-center py-6 px-10 border-b border-[#222222]">
        <div className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
          DocuMentor
        </div>
        <nav className="flex gap-4">
          <button className="px-4 py-2 text-sm font-medium bg-[#222222] rounded-full hover:bg-[#333333] transition-colors">Home</button>
          <button className="px-4 py-2 text-sm font-medium text-[#888888] hover:text-[#DDDDDD] transition-colors">History</button>
          <button className="px-4 py-2 text-sm font-medium text-[#888888] hover:text-[#DDDDDD] transition-colors">Settings</button>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center -mt-20 px-6">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
          Ask anything about any library
        </h1>
        <p className="text-[#888888] text-center max-w-xl text-sm sm:text-base leading-relaxed mb-10">
          Paste a documentation URL. We'll read the whole thing, then answer your questions — with the right function, when to use it, and working code.
        </p>

        {/* Input Bar */}
        <div className="w-full max-w-3xl relative mb-4">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[#555555]">
            <LinkIcon className="w-5 h-5" />
          </div>
          <input
            type="text"
            placeholder="https://pandas.pydata.org/docs/"
            className="w-full bg-[#1A1A1A] border border-[#333333] rounded-2xl py-4 pl-12 pr-32 text-sm text-[#DDDDDD] placeholder:text-[#555555] focus:outline-none focus:border-[#555555] focus:ring-1 focus:ring-[#555555] transition-all"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                navigate("/chat");
              }
            }}
          />
          <button 
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-[#333333] hover:bg-[#444444] text-[#EEEEEE] text-sm font-medium px-6 py-2 rounded-xl transition-colors"
            onClick={() => navigate("/chat")}
          >
            Index docs
          </button>
        </div>

        {/* Try links */}
        <div className="text-xs text-[#555555] flex flex-wrap justify-center gap-1 mb-8">
          Try:
          <button className="text-indigo-400 hover:text-indigo-300 hover:underline">https://docs.python-requests.org</button>
          <span>or</span>
          <button className="text-indigo-400 hover:text-indigo-300 hover:underline">https://threejs.org/docs</button>
        </div>

        {/* Pills */}
        <div className="flex flex-wrap justify-center gap-3 mb-16">
          {['Pandas', 'FastAPI', 'Three.js', 'Scikit-learn', 'SQLAlchemy'].map(tag => (
            <button key={tag} className="px-4 py-2 rounded-full border border-[#333333] text-sm text-[#888888] hover:bg-[#222222] hover:text-[#DDDDDD] transition-all">
              {tag}
            </button>
          ))}
        </div>

        {/* Feature Cards */}
        <div className="w-full max-w-4xl text-center">
          <div className="text-xs font-mono text-[#555555] mb-6 tracking-widest uppercase">what you can ask</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left">
            
            <div className="bg-[#151515] hover:bg-[#1A1A1A] border border-[#222222] rounded-2xl p-5 transition-colors cursor-pointer group">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-110 transition-transform">
                <FunctionSquare className="w-4 h-4" />
              </div>
              <h3 className="text-[#EEEEEE] font-medium text-sm mb-1">Function finder</h3>
              <p className="text-[#888888] text-xs">"How do I group and aggregate rows?"</p>
            </div>

            <div className="bg-[#151515] hover:bg-[#1A1A1A] border border-[#222222] rounded-2xl p-5 transition-colors cursor-pointer group">
              <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center text-green-400 mb-4 group-hover:scale-110 transition-transform">
                <Wrench className="w-4 h-4" />
              </div>
              <h3 className="text-[#EEEEEE] font-medium text-sm mb-1">Error fixar</h3>
              <p className="text-[#888888] text-xs">"Paste a traceback, get the fix"</p>
            </div>

            <div className="bg-[#151515] hover:bg-[#1A1A1A] border border-[#222222] rounded-2xl p-5 transition-colors cursor-pointer group">
              <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-400 mb-4 group-hover:scale-110 transition-transform">
                <ArrowLeftRight className="w-4 h-4" />
              </div>
              <h3 className="text-[#EEEEEE] font-medium text-sm mb-1">Trade-offs</h3>
              <p className="text-[#888888] text-xs">"When should I avoid apply()?"</p>
            </div>

          </div>
        </div>

      </main>
    </div>
  );
};

export default Index;
