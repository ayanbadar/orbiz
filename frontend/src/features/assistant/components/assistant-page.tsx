import { Sparkles } from "lucide-react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AssistantActivityList } from "@/features/assistant/components/assistant-activity-list";
import { AssistantDigestPanel } from "@/features/assistant/components/assistant-digest-panel";
import { ChatTab } from "@/features/assistant/components/chat-tab";

export function AssistantPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <span className="flex size-10 items-center justify-center rounded-full bg-muted text-foreground">
          <Sparkles className="size-5" aria-hidden />
        </span>
        <div>
          <h1 className="font-heading text-xl font-semibold text-foreground">Orbiz AI</h1>
          <p className="text-sm text-muted-foreground">
            Draft orders, answer questions, and propose PayPal actions — grounded in your store.
          </p>
        </div>
      </div>

      <Tabs defaultValue="chat" className="gap-4">
        <TabsList>
          <TabsTrigger value="chat">Chat</TabsTrigger>
          <TabsTrigger value="attention">Needs attention</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="chat">
          <ChatTab />
        </TabsContent>
        <TabsContent value="attention">
          <AssistantDigestPanel />
        </TabsContent>
        <TabsContent value="activity">
          <AssistantActivityList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
