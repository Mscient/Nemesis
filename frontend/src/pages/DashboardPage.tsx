import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import { formatDate } from "@/lib/utils";
import type { Item } from "@/types/api";

export function DashboardPage() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ["items"],
    queryFn: api.items.list,
  });

  const createMutation = useMutation({
    mutationFn: api.items.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["items"] });
      setTitle("");
      setDescription("");
      toast({ title: "Item created ✅" });
    },
    onError: (err: Error) => toast({ title: "Error", description: err.message, variant: "destructive" }),
  });

  const deleteMutation = useMutation({
    mutationFn: api.items.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["items"] });
      toast({ title: "Item deleted" });
    },
    onError: (err: Error) => toast({ title: "Error", description: err.message, variant: "destructive" }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    createMutation.mutate({ title: title.trim(), description: description.trim() });
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Example CRUD – copy{" "}
          <code className="text-xs bg-muted px-1 py-0.5 rounded">items.py</code> to add new features.
        </p>
      </div>

      {/* Create form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">New Item</CardTitle>
          <CardDescription>Reference pattern for adding data</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-3">
            <Input
              id="item-title-input"
              placeholder="Title *"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Input
              id="item-description-input"
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <Button
              id="create-item-btn"
              type="submit"
              disabled={!title.trim() || createMutation.isPending}
              className="w-full"
            >
              {createMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Create Item
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Item list */}
      {isLoading && (
        <div className="flex items-center justify-center py-12 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading items…</span>
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-2 text-destructive bg-destructive/10 rounded-lg p-4">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span className="text-sm">Failed to load items. Is the backend running?</span>
        </div>
      )}

      {!isLoading && items.length === 0 && !isError && (
        <div className="text-center py-12 text-muted-foreground">
          <CheckCircle2 className="h-8 w-8 mx-auto mb-3 opacity-20" />
          <p className="text-sm">No items yet. Create one above or run <code className="text-xs bg-muted px-1 rounded">make seed</code>.</p>
        </div>
      )}

      <div className="space-y-2">
        {items.map((item: Item) => (
          <div
            key={item.id}
            className="flex items-start gap-3 p-4 rounded-lg border border-border bg-card hover:border-border/80 transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm text-foreground truncate">{item.title}</p>
              {item.description && (
                <p className="text-xs text-muted-foreground mt-0.5 truncate">{item.description}</p>
              )}
              <p className="text-xs text-muted-foreground/60 mt-1">{formatDate(item.created_at)}</p>
            </div>
            <Button
              id={`delete-item-${item.id}-btn`}
              size="icon"
              variant="ghost"
              className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 text-muted-foreground hover:text-destructive"
              onClick={() => deleteMutation.mutate(item.id)}
              disabled={deleteMutation.isPending}
              aria-label={`Delete ${item.title}`}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
