import { Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";

/** Development only: the API returns the link because the console is the only inbox. */
export function DevInviteLink({
  url,
  onDone,
}: {
  url: string;
  onDone: () => void;
}) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-body">
        Development mode: copy the invite link directly.
      </p>
      <div className="flex gap-2">
        <Input readOnly value={url} className="h-10 rounded-lg text-xs" />
        <Button
          type="button"
          variant="secondary"
          size="icon-lg"
          aria-label="Copy invite link"
          onClick={() => {
            void navigator.clipboard.writeText(url);
            toast.success("Link copied.");
          }}
        >
          <Copy />
        </Button>
      </div>
      <Button type="button" className="rounded-[24px]" onClick={onDone}>
        Done
      </Button>
    </div>
  );
}
