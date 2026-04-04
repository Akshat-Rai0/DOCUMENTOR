import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { Link } from "react-router-dom";

const QueryPage = () => {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content: query }),
      });

      if (!res.ok) {
        throw new Error("Failed to connect to the backend API");
      }

      const data = await res.json();
      setResponse(data.processed_content);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6 md:p-12">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="flex justify-between items-center mb-12">
          <Link to="/" className="text-muted-foreground hover:text-primary transition-colors font-mono">
            &larr; Back to Landing
          </Link>
          <h1 className="text-2xl font-bold tracking-tight">Query the Architecture</h1>
        </header>

        <Card className="border-border bg-card/60 backdrop-blur-sm">
          <CardHeader>
            <CardTitle>Submit your query</CardTitle>
            <CardDescription>
              Ask questions about the architecture or provide context. It interacts with the FastAPI backend.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Textarea
                placeholder="Type your question here..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="min-h-[150px] resize-none bg-background placeholder:text-muted-foreground/50 border-input"
                disabled={isLoading}
              />
              <Button type="submit" disabled={isLoading || !query.trim()} className="w-full sm:w-auto glow-primary">
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  "Submit Query"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {error && (
          <div className="p-4 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-sm font-mono">
            Error: {error}
          </div>
        )}

        {response && (
          <Card className="border-border bg-card/60 backdrop-blur-sm mt-8">
            <CardHeader>
              <CardTitle>Response</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="p-6 rounded-md bg-secondary/50 font-mono text-sm whitespace-pre-wrap">
                {response}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default QueryPage;
