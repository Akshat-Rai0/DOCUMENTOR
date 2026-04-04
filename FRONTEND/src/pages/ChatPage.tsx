import { useState, useEffect, useRef } from "react";
import { Copy, Plus, ArrowRight, Search, Loader2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";

// Icon for Error Fix Mode Wrench
function Wrench(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const url = searchParams.get("url") || "Unknown Source";
  
  const [status, setStatus] = useState<string>("crawling");
  const [pagesIndexed, setPagesIndexed] = useState<number>(0);
  const [functionsIndexed, setFunctionsIndexed] = useState<number>(0);
  
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: `I'm ready to answer questions about ${url}.` }
  ]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Poll for crawl status
  useEffect(() => {
    if (url === "Unknown Source") return;
    
    let intervalId: NodeJS.Timeout;
    
    const checkStatus = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/crawl/status?url=${encodeURIComponent(url)}`);
        const data = await res.json();
        
        setStatus(data.status || "not_found");
        if (data.pages) setPagesIndexed(data.pages);
        if (data.functions) setFunctionsIndexed(data.functions);
        
        if (data.status === "done" || data.status === "error") {
          clearInterval(intervalId);
        }
      } catch (e) {
        console.error("Failed to fetch crawl status", e);
      }
    };
    
    checkStatus(); // Initial check
    intervalId = setInterval(checkStatus, 2000); // Poll every 2 seconds
    
    return () => clearInterval(intervalId);
  }, [url]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return;
    
    const userText = input;
    setMessages(prev => [...prev, { role: "user", content: userText }]);
    setInput("");
    setIsProcessing(true);
    
    try {
      const res = await fetch("http://localhost:8000/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: userText })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.processed_content || "Error: No content returned." }]);
    } catch (e: any) {
      setMessages(prev => [...prev, { role: "assistant", content: `Failed to contact API: ${e.message}` }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const domainName = url.replace(/https?:\/\//, '').split('/')[0];

  return (
    <div className="flex h-screen bg-[#0F0F0F] text-[#EEEEEE] font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col border-r border-[#222222] bg-[#111111] p-4 hidden md:flex">
        <div className="flex items-center gap-2 mb-6">
          <div className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
            DocuMentor
          </div>
        </div>

        <button className="flex items-center gap-2 px-3 py-2 bg-indigo-500/10 text-indigo-400 rounded-lg w-full text-sm font-medium border border-indigo-500/20 mb-6">
          <div className="w-2 h-2 rounded-full bg-indigo-400" />
          <span className="truncate flex-1 text-left">{domainName}</span>
        </button>

        <div className="flex-1 overflow-y-auto">
          {/* History goes here later */}
        </div>

        <button className="flex items-center justify-center gap-2 w-full py-3 mt-4 text-sm font-medium text-[#EEEEEE] border border-[#333333] hover:bg-[#222222] rounded-xl transition-colors">
          <Plus className="w-4 h-4" />
          New conversation
        </button>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col relative bg-[#0F0F0F] min-w-0">
        
        {/* Chat Header */}
        <header className="px-6 py-4 border-b border-[#222222] flex items-center justify-between bg-[#111111]/80 backdrop-blur-sm sticky top-0 z-0">
          <div className="flex items-center gap-2 text-sm text-[#888888] font-medium">
            <div className={`w-2 h-2 rounded-full ${status === 'done' ? 'bg-emerald-400' : status === 'error' ? 'bg-red-400' : 'bg-yellow-400 animate-pulse'}`} />
             {domainName} — 
             {status === 'crawling' && ` indexing...`}
             {status === 'parsing' && ` parsing (${pagesIndexed} pages)...`}
             {status === 'done' && ` indexed ${pagesIndexed} pages, ${functionsIndexed} functions`}
             {status === 'error' && ` indexing failed`}
             {status === 'not_found' && ` status not found`}
          </div>
        </header>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex flex-col items-center">
          <div className="w-full max-w-4xl flex flex-col gap-8 pb-20">
            
            {messages.map((msg, i) => (
              <div key={i} className={msg.role === "user" ? "self-end max-w-[80%]" : "self-start w-full max-w-[95%]"}>
                {msg.role === "user" ? (
                  <div className="bg-[#2A2A2A] text-[#EEEEEE] px-5 py-3.5 rounded-2xl rounded-tr-sm text-[15px] border border-[#333333]">
                    {msg.content}
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
                        <Search className="w-3.5 h-3.5" />
                      </div>
                      <span className="text-xs font-medium text-[#888888]">DocuMentor</span>
                    </div>
                    <div className="bg-[#151515] border border-[#2A2A2A] rounded-2xl p-5 text-[15px] text-[#CCCCCC] leading-relaxed animate-in fade-in slide-in-from-bottom-2 duration-300">
                      {msg.content}
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {isProcessing && (
              <div className="self-start w-full max-w-[95%]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  </div>
                  <span className="text-xs font-medium text-[#888888]">DocuMentor is thinking...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Footer */}
        <div className="p-4 bg-gradient-to-t from-[#0F0F0F] via-[#0F0F0F] to-transparent shrink-0">
          <div className="max-w-4xl mx-auto relative">
            <input 
              type="text" 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSend()}
              placeholder="Ask anything about the library..."
              className="w-full bg-[#1A1A1A] border border-[#333333] border-glow text-[#EEEEEE] placeholder:text-[#666666] text-sm rounded-xl py-3.5 pl-4 pr-12 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all shadow-lg shadow-black/20"
            />
            <button 
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg bg-[#333333] hover:bg-[#444444] text-[#EEEEEE] flex items-center justify-center transition-colors disabled:opacity-50"
              onClick={handleSend}
              disabled={isProcessing || !input.trim()}
            >
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
