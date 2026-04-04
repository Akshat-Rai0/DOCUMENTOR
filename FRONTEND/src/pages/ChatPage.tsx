import { useState } from "react";
import { Copy, Plus, ArrowRight, XCircle, Search } from "lucide-react";

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

export default function ChatPage() {
  const [mode, setMode] = useState<"function" | "error">("function");

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
          pandas
          <span className="ml-auto text-xs opacity-70">2.1.0</span>
        </button>

        <div className="flex-1 overflow-y-auto">
          <div className="mb-6">
            <h4 className="text-xs font-medium text-[#555555] uppercase tracking-wider mb-3 px-2">Past 7 days</h4>
            <ul className="space-y-1">
              <li>
                <button className={`w-full flex items-center gap-3 px-2 py-2 text-sm rounded-lg transition-colors ${mode === 'function' ? 'bg-[#222222] text-[#DDDDDD]' : 'text-[#888888] hover:bg-[#1A1A1A]'}`} onClick={() => setMode("function")}>
                  <ArrowRight className="w-4 h-4 opacity-50" />
                  <span className="truncate">Normalize data</span>
                </button>
              </li>
              <li>
                <button className="w-full flex items-center gap-3 px-2 py-2 text-sm text-[#888888] hover:bg-[#1A1A1A] rounded-lg transition-colors">
                  <ArrowRight className="w-4 h-4 opacity-50" />
                  <span className="truncate">Group by + aggregate</span>
                </button>
              </li>
              <li>
                <button className="w-full flex items-center gap-3 px-2 py-2 text-sm text-[#888888] hover:bg-[#1A1A1A] rounded-lg transition-colors">
                  <ArrowRight className="w-4 h-4 opacity-50" />
                  <span className="truncate">Merge two dataframes</span>
                </button>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-medium text-[#555555] uppercase tracking-wider mb-3 px-2">Error fixes</h4>
            <ul className="space-y-1">
              <li>
                <button className={`w-full flex items-center gap-3 px-2 py-2 text-sm rounded-lg transition-colors ${mode === 'error' ? 'bg-[#222222] text-[#DDDDDD]' : 'text-[#888888] hover:bg-[#1A1A1A]'}`} onClick={() => setMode("error")}>
                  <XCircle className="w-4 h-4 opacity-50" />
                  <span className="truncate">KeyError: 'col_name'</span>
                </button>
              </li>
            </ul>
          </div>
        </div>

        <button className="flex items-center justify-center gap-2 w-full py-3 mt-4 text-sm font-medium text-[#EEEEEE] border border-[#333333] hover:bg-[#222222] rounded-xl transition-colors">
          <Plus className="w-4 h-4" />
          New conversation
        </button>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col relative bg-[#0F0F0F] min-w-0">
        
        {/* Toggle View For Demonstration Purposes */}
        <div className="absolute top-4 right-4 z-10 flex gap-2">
          <button onClick={() => setMode("function")} className={`px-3 py-1.5 text-xs font-medium rounded-lg border leading-none transition-colors ${mode === 'function' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' : 'bg-[#1A1A1A] text-[#888888] border-[#333333]'}`}>
            Show Function Fix
          </button>
          <button onClick={() => setMode("error")} className={`px-3 py-1.5 text-xs font-medium rounded-lg border leading-none transition-colors ${mode === 'error' ? 'bg-red-500/20 text-red-300 border-red-500/30' : 'bg-[#1A1A1A] text-[#888888] border-[#333333]'}`}>
            Show Error Fix
          </button>
        </div>

        {/* Chat Header */}
        <header className="px-6 py-4 border-b border-[#222222] flex items-center justify-between bg-[#111111]/80 backdrop-blur-sm sticky top-0 z-0">
          <div className="flex items-center gap-2 text-sm text-[#888888] font-medium">
            <div className={`w-2 h-2 rounded-full ${mode === 'function' ? 'bg-emerald-400' : 'bg-red-400'}`} />
             pandas 2.1.0 {mode === 'function' ? 'indexed - 847 functions' : '- error fix mode'}
          </div>
          {mode === 'error' && (
             <div className="px-3 py-1 bg-indigo-500/10 text-indigo-400 rounded-full text-xs font-medium border border-indigo-500/20">
               pandas
             </div>
          )}
        </header>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex justify-center">
          <div className="w-full max-w-4xl flex flex-col gap-8 pb-20">
            {mode === 'function' ? (
              <>
                {/* User Message */}
                <div className="self-end bg-[#2A2A2A] text-[#EEEEEE] px-5 py-3.5 rounded-2xl rounded-tr-sm text-[15px] max-w-[80%] border border-[#333333]">
                  How do I normalize data in pandas?
                </div>

                {/* Assistant Message */}
                <div className="flex flex-col gap-2 max-w-[95%]">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow-[0_0_10px_rgba(99,102,241,0.5)]">
                      <Search className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs font-medium text-[#888888]">DocuMentor - function recommendation</span>
                  </div>

                  {/* Main Answer Card */}
                  <div className="bg-[#151515] border border-[#2A2A2A] rounded-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
                    
                    {/* Header */}
                    <div className="px-5 py-4 border-b border-[#2A2A2A] flex flex-wrap items-center gap-3">
                      <span className="bg-indigo-500/20 text-indigo-300 text-[11px] font-bold px-2 py-1 rounded-md uppercase tracking-wider border border-indigo-500/20">
                        recommended
                      </span>
                      <h3 className="text-lg font-bold text-[#EEEEEE] tracking-tight truncate">
                        sklearn.preprocessing.StandardScaler
                      </h3>
                      <div className="ml-auto flex items-center gap-2">
                        <div className="h-1.5 w-16 bg-[#222] rounded-full overflow-hidden">
                          <div className="h-full bg-emerald-400 w-[95%]" />
                        </div>
                      </div>
                    </div>

                    <div className="p-5">
                      <p className="text-[#CCCCCC] text-[15px] leading-relaxed mb-5">
                        Standardizes features by removing mean and scaling to unit variance (z-score normalization). Best default choice when the distribution of your data matters.
                      </p>

                      {/* Tags */}
                      <div className="flex flex-wrap gap-2 mb-6">
                        <span className="px-3 py-1 bg-[#222222] text-[#AAAAAA] text-xs font-mono rounded-lg border border-[#333333]">sklearn.preprocessing</span>
                        <span className="px-3 py-1 bg-[#222222] text-[#AAAAAA] text-xs font-mono rounded-lg border border-[#333333]">#normalization</span>
                        <span className="px-3 py-1 bg-[#222222] text-[#AAAAAA] text-xs font-mono rounded-lg border border-[#333333]">#z-score</span>
                      </div>

                      {/* Pros / Cons grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <div className="bg-emerald-950/20 border border-emerald-900/30 rounded-xl p-4 relative overflow-hidden">
                          <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500/50" />
                          <h4 className="text-emerald-400 text-xs font-bold uppercase tracking-wider mb-3">Use when</h4>
                          <ul className="space-y-2 text-[13px] text-[#DDDDDD]">
                            <li className="flex gap-2"><span className="text-emerald-500 mt-0.5">•</span> Features have different scales</li>
                            <li className="flex gap-2"><span className="text-emerald-500 mt-0.5">•</span> Algorithm needs normal dist.</li>
                            <li className="flex gap-2"><span className="text-emerald-500 mt-0.5">•</span> Training ML models</li>
                          </ul>
                        </div>
                        <div className="bg-red-950/20 border border-red-900/30 rounded-xl p-4 relative overflow-hidden">
                          <div className="absolute top-0 left-0 w-1 h-full bg-red-500/50" />
                          <h4 className="text-red-400 text-xs font-bold uppercase tracking-wider mb-3">Avoid when</h4>
                          <ul className="space-y-2 text-[13px] text-[#DDDDDD]">
                            <li className="flex gap-2"><span className="text-red-500 mt-0.5">•</span> Data has many outliers (skews mean)</li>
                            <li className="flex gap-2"><span className="text-red-500 mt-0.5">•</span> You need values in [0, 1] range</li>
                            <li className="flex gap-2"><span className="text-red-500 mt-0.5">•</span> Data isn't roughly Gaussian</li>
                          </ul>
                        </div>
                      </div>

                      {/* Code Block */}
                      <div className="bg-[#0A0A0A] border border-[#222222] rounded-xl overflow-hidden mt-2">
                        <div className="flex items-center justify-between px-4 py-2 bg-[#1A1A1A] border-b border-[#222222]">
                          <span className="text-[#888888] text-xs font-mono">python</span>
                          <button className="flex items-center gap-1.5 text-[#888888] hover:text-[#EEEEEE] text-xs font-medium transition-colors bg-[#222222] px-2.5 py-1 rounded-md">
                            <Copy className="w-3 h-3" /> copy
                          </button>
                        </div>
                        <div className="p-4 overflow-x-auto">
                          <pre className="text-[13px] font-mono leading-relaxed text-[#DDDDDD]">
<span className="text-purple-400">from</span> sklearn.preprocessing <span className="text-purple-400">import</span> StandardScaler{'\n\n'}
scaler = <span className="text-blue-400">StandardScaler</span>(){'\n'}
df[<span className="text-green-400">'normalized'</span>] = scaler.<span className="text-yellow-200">fit_transform</span>(df[[<span className="text-green-400">'col'</span>]]){'\n'}
<span className="text-[#666666]"># fit_transform on train, transform only on test</span>
                          </pre>
                        </div>
                      </div>
                    </div>

                    {/* Footer / Links */}
                    <div className="px-5 py-3 border-t border-[#2A2A2A] bg-[#1A1A1A]/50 flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center text-[13px]">
                      <div className="text-[#888888]">
                        Source: <a href="#" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 decoration-indigo-400/50">sklearn.org/stable/modules/preprocessing.html</a>
                      </div>
                    </div>
                    <div className="px-5 py-3 border-t border-[#2A2A2A] bg-[#1A1A1A]/80 text-[13px] flex items-center gap-2">
                      <span className="text-[#888888]">Alternatives:</span>
                      <a href="#" className="text-indigo-400 font-medium hover:underline">MinMaxScaler</a>
                      <span className="text-[#666666] hidden sm:inline">- use when you need values strictly in [0, 1]</span>
                    </div>

                  </div>
                </div>
              </>
            ) : (
              <>
                {/* User Message (Error) */}
                <div className="self-end bg-red-950/20 text-[#EEEEEE] px-5 py-4 rounded-2xl rounded-tr-sm text-[14px] max-w-[85%] border border-red-900/30">
                  <pre className="font-mono text-xs text-red-300 leading-relaxed whitespace-pre-wrap break-all">
<span className="font-bold text-red-400">ValueError: cannot convert float NaN to integer</span> 
  File "process.py", Line 14, in clean_data
    df['age'] = df['age'].astype(int)
pandas.errors.IntCastingNaError
                  </pre>
                </div>

                {/* Assistant Message (Error Fix) */}
                <div className="flex flex-col gap-2 max-w-[95%]">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded bg-red-500/20 border border-red-500/40 flex items-center justify-center text-xs font-bold text-red-500">
                      <Wrench className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-xs font-medium text-[#888888]">DocuMentor - error fix</span>
                  </div>

                  {/* Error Answer Card */}
                  <div className="bg-[#181111] border border-red-900/40 rounded-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500 shadow-[0_4px_20px_rgba(220,38,38,0.05)]">
                    
                    {/* Header */}
                    <div className="px-5 py-4 border-b border-red-900/20 flex flex-wrap items-center gap-3 bg-red-950/10">
                      <span className="bg-red-500/20 text-red-400 text-[11px] font-bold px-2 py-1 rounded-md uppercase tracking-wider border border-red-500/20">
                        error fix
                      </span>
                      <h3 className="text-lg font-mono font-bold text-[#EEEEEE] tracking-tight truncate">
                        IntCastingNaError
                      </h3>
                    </div>

                    <div className="p-5">
                      
                      {/* Root Cause */}
                      <div className="mb-6">
                        <h4 className="text-[#888888] text-xs font-bold uppercase tracking-wider mb-2">ROOT CAUSE</h4>
                        <div className="bg-[#1A1515] p-4 rounded-xl border border-red-900/20">
                          <p className="text-[#DDDDDD] text-[14px] leading-relaxed">
                            Your column <code className="bg-[#2A2020] text-red-300 px-1.5 py-0.5 rounded font-mono border border-red-900/30">df['age']</code> contains <code className="bg-[#2A2020] text-red-300 px-1.5 py-0.5 rounded font-mono border border-red-900/30">NaN</code> values. Python's <code className="bg-[#222] px-1.5 py-0.5 rounded font-mono">int</code> type cannot represent NaN — the cast fails before it starts. This often happens after a merge or read from CSV with missing rows.
                          </p>
                        </div>
                      </div>

                      {/* Fix Options */}
                      <div className="mb-6">
                        <h4 className="text-[#888888] text-xs font-bold uppercase tracking-wider mb-3">FIX → OPTIONS</h4>
                        <ul className="space-y-3">
                          <li className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#222] border border-[#333] flex items-center justify-center text-xs font-medium text-[#888]">1</span>
                            <span className="text-[14px] text-[#CCCCCC] pt-0.5">Drop NaNs first if missing rows are acceptable: <code className="bg-[#222] px-1.5 py-0.5 rounded font-mono text-indigo-300">dropna()</code> before casting</span>
                          </li>
                          <li className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#222] border border-[#333] flex items-center justify-center text-xs font-medium text-[#888]">2</span>
                            <span className="text-[14px] text-[#CCCCCC] pt-0.5">Fill NaNs with a sensible default: <code className="bg-[#222] px-1.5 py-0.5 rounded font-mono text-indigo-300">fillna(0)</code> or <code className="bg-[#222] px-1.5 py-0.5 rounded font-mono text-indigo-300">fillna(df['age'].median())</code></span>
                          </li>
                          <li className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-xs font-medium text-indigo-400">3</span>
                            <span className="text-[14px] text-[#EEEEEE] pt-0.5">Use pandas nullable integer type <code className="bg-[#222] px-1.5 py-0.5 rounded font-mono text-indigo-300 border border-indigo-500/20">Int64</code> — keeps NaN, no crash</span>
                          </li>
                        </ul>
                      </div>

                      {/* Working Code Block */}
                      <div>
                        <h4 className="text-[#888888] text-xs font-bold uppercase tracking-wider mb-2">WORKING CODE</h4>
                        <div className="bg-[#0A0A0A] border border-[#222222] rounded-xl overflow-hidden">
                          <div className="flex items-center justify-between px-4 py-2 bg-[#1A1A1A] border-b border-[#222222]">
                            <span className="text-[#888888] text-xs font-mono">python - diff</span>
                            <button className="flex items-center gap-1.5 text-[#888888] hover:text-[#EEEEEE] text-xs font-medium transition-colors bg-[#222222] hover:bg-[#333] px-2.5 py-1 rounded-md">
                              <Copy className="w-3 h-3" /> copy fix
                            </button>
                          </div>
                          <div className="p-4 overflow-x-auto bg-[#0F0A0A]">
                            <pre className="text-[13px] font-mono leading-relaxed text-[#DDDDDD] flex flex-col">
<span className="text-[#666] mb-1"># option 1 - drop NaN rows</span>
<span>df = df.<span className="text-indigo-300">dropna</span>(subset=[<span className="text-green-400">'age'</span>])</span>
<span>df[<span className="text-green-400">'age'</span>] = df[<span className="text-green-400">'age'</span>].<span className="text-indigo-300">astype</span>(<span className="text-purple-400">int</span>)</span>
<span className="my-1"></span>
<span className="text-[#666] mb-1"># option 2 - fill with median</span>
<span>df[<span className="text-green-400">'age'</span>] = df[<span className="text-green-400">'age'</span>].<span className="text-indigo-300">fillna</span>(df[<span className="text-green-400">'age'</span>].<span className="text-yellow-200">median</span>()).<span className="text-indigo-300">astype</span>(<span className="text-purple-400">int</span>)</span>
<span className="my-1"></span>
<span className="text-[#666] mb-1"># option 3 - nullable Int64 (keeps NaN)</span>
<span className="bg-emerald-900/30 px-2 -mx-2 py-0.5 border-l-2 border-emerald-500">df[<span className="text-green-400">'age'</span>] = df[<span className="text-green-400">'age'</span>].<span className="text-indigo-300">astype</span>(<span className="text-green-400">'Int64'</span>)</span>
                            </pre>
                          </div>
                        </div>
                      </div>

                    </div>

                    {/* Footer / Links */}
                    <div className="px-5 py-3 border-t border-red-900/20 bg-red-950/20 flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center text-[13px]">
                      <div className="text-[#888888]">
                        Source: <a href="#" className="text-red-400/80 hover:text-red-400 underline underline-offset-2 decoration-red-400/30">pandas.pydata.org/docs/reference/api/pandas.DataFrame.astype</a>
                      </div>
                    </div>
                  </div>
                  
                  {/* Follow up chips */}
                  <div className="flex flex-wrap gap-2 mt-2">
                    <button className="px-3 py-1.5 bg-[#151515] hover:bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg text-xs text-[#AAAAAA] hover:text-[#EEEEEE] transition-colors">
                      How do I check for NaNs first?
                    </button>
                    <button className="px-3 py-1.5 bg-[#151515] hover:bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg text-xs text-[#AAAAAA] hover:text-[#EEEEEE] transition-colors">
                      What is Int64 vs int?
                    </button>
                    <button className="px-3 py-1.5 bg-[#151515] hover:bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg text-xs text-[#AAAAAA] hover:text-[#EEEEEE] transition-colors">
                      Why did a merge cause NaNs?
                    </button>
                  </div>

                </div>
              </>
            )}

          </div>
        </div>

        {/* Input Footer */}
        <div className="p-4 bg-gradient-to-t from-[#0F0F0F] via-[#0F0F0F] to-transparent shrink-0">
          <div className="max-w-4xl mx-auto relative">
            <input 
              type="text" 
              placeholder={mode === 'function' ? "When would I use MinMaxScaler instead?" : "Ask a follow-up..."}
              className="w-full bg-[#1A1A1A] border border-[#333333] border-glow text-[#EEEEEE] placeholder:text-[#666666] text-sm rounded-xl py-3.5 pl-4 pr-12 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all shadow-lg shadow-black/20"
            />
            <button className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg bg-[#333333] hover:bg-[#444444] text-[#EEEEEE] flex items-center justify-center transition-colors">
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

