import { Link } from "react-router-dom";
import { ArrowRight, Zap, Database, Bot, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    icon: <Zap className="h-6 w-6 text-yellow-400" />,
    title: "Instant Setup",
    description: "Clone and run make dev. No Node, Python, or uv installs on the host.",
  },
  {
    icon: <Bot className="h-6 w-6 text-blue-400" />,
    title: "Streaming AI",
    description: "Anthropic Claude with Server-Sent Events. Real-time token streaming out of the box.",
  },
  {
    icon: <Database className="h-6 w-6 text-green-400" />,
    title: "SQLite + ORM",
    description: "SQLAlchemy 2.0 with automatic table creation. Add a model and you're done.",
  },
  {
    icon: <Layers className="h-6 w-6 text-purple-400" />,
    title: "Production Patterns",
    description: "Typed API client, React Query, CRUD reference, hot reload, CI workflow.",
  },
];

export function HomePage() {
  return (
    <div className="container mx-auto px-4 py-16 max-w-5xl">
      {/* Hero */}
      <div className="text-center space-y-6 mb-16">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-4 py-1.5 text-sm text-muted-foreground">
          <Zap className="h-3.5 w-3.5 text-yellow-400" />
          12-hour hackathon starter
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-foreground">
          Ship faster.
          <br />
          <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
            Win the hackathon.
          </span>
        </h1>

        <p className="text-lg text-muted-foreground max-w-xl mx-auto">
          A full-stack React + FastAPI starter with streaming AI, SQLite, hot reload, and
          everything wired up. Docker only — zero host installs.
        </p>

        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Button asChild size="lg" id="hero-dashboard-btn">
            <Link to="/dashboard">
              View Dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" id="hero-chat-btn">
            <Link to="/chat">Try the AI Chat</Link>
          </Button>
        </div>

        {/* Code snippet */}
        <div className="inline-block rounded-lg bg-muted border border-border px-5 py-3 text-left font-mono text-sm text-muted-foreground mt-4">
          <span className="text-green-400">$</span> git clone repo &amp;&amp; cp .env.example .env &amp;&amp;{" "}
          <span className="text-yellow-400">make dev</span>
        </div>
      </div>

      {/* Feature grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {features.map((f) => (
          <Card key={f.title} className="border-border/50 hover:border-border transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                {f.icon}
                <CardTitle className="text-base">{f.title}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>{f.description}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
