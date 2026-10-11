import { ChatBox } from "@/components/ai/ChatBox";

export function ChatPage() {
  return (
    <div className="container mx-auto px-4 py-6 max-w-3xl h-[calc(100vh-3.5rem-1px)] flex flex-col">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-foreground">AI Chat</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Streaming responses via Server-Sent Events. Set{" "}
          <code className="text-xs bg-muted px-1 py-0.5 rounded">USE_MOCK_AI=false</code> to use real Claude.
        </p>
      </div>

      <div className="flex-1 rounded-lg border border-border bg-card overflow-hidden">
        <ChatBox />
      </div>
    </div>
  );
}
