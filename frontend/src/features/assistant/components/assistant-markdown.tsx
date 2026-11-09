import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "cn";

/**
 * Hand-mapped to DESIGN.md's type tokens rather than a generic `prose` class,
 * so assistant replies stay visually consistent with the rest of Orbiz.
 */
const components: Components = {
  p: ({ className, ...props }) => (
    <p className={cn("leading-6 text-foreground [&:not(:first-child)]:mt-3", className)} {...props} />
  ),
  strong: ({ className, ...props }) => (
    <strong className={cn("font-semibold text-foreground", className)} {...props} />
  ),
  ul: ({ className, ...props }) => (
    <ul className={cn("my-2 list-disc space-y-1 pl-5 marker:text-muted-foreground", className)} {...props} />
  ),
  ol: ({ className, ...props }) => (
    <ol className={cn("my-2 list-decimal space-y-1 pl-5 marker:text-muted-foreground", className)} {...props} />
  ),
  li: ({ className, ...props }) => <li className={cn("leading-6", className)} {...props} />,
  a: ({ className, ...props }) => (
    <a className={cn("text-primary underline-offset-4 hover:underline", className)} target="_blank" rel="noreferrer" {...props} />
  ),
  h1: ({ className, ...props }) => (
    <h1 className={cn("mt-4 text-lg font-semibold text-foreground first:mt-0", className)} {...props} />
  ),
  h2: ({ className, ...props }) => (
    <h2 className={cn("mt-4 text-base font-semibold text-foreground first:mt-0", className)} {...props} />
  ),
  h3: ({ className, ...props }) => (
    <h3 className={cn("mt-3 text-sm font-semibold text-foreground first:mt-0", className)} {...props} />
  ),
  blockquote: ({ className, ...props }) => (
    <blockquote className={cn("my-2 border-l-2 border-border pl-3 text-muted-foreground", className)} {...props} />
  ),
  hr: ({ className, ...props }) => <hr className={cn("my-3 border-border", className)} {...props} />,
  code: ({ className, children, ...props }) => (
    <code
      className={cn("rounded bg-muted px-1 py-0.5 font-mono text-[0.85em] text-foreground", className)}
      {...props}
    >
      {children}
    </code>
  ),
  pre: ({ className, ...props }) => (
    <pre
      className={cn(
        "my-2 overflow-x-auto rounded-lg bg-muted p-3 font-mono text-sm [&_code]:bg-transparent [&_code]:p-0",
        className,
      )}
      {...props}
    />
  ),
  table: ({ className, ...props }) => (
    <div className="my-2 overflow-x-auto">
      <table className={cn("w-full border-collapse text-left text-sm", className)} {...props} />
    </div>
  ),
  th: ({ className, ...props }) => (
    <th className={cn("border-b border-border px-2 py-1 font-semibold text-foreground", className)} {...props} />
  ),
  td: ({ className, ...props }) => (
    <td className={cn("border-b border-border px-2 py-1 text-foreground", className)} {...props} />
  ),
};

export function AssistantMarkdown({ content }: { content: string }) {
  return (
    <div className="text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
