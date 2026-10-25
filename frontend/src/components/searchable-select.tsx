import { Check, ChevronDown } from "lucide-react";
import {
  useId,
  useMemo,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import {
  Controller,
  type Control,
  type FieldPath,
  type FieldValues,
} from "react-hook-form";
import { cn } from "cn";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from "@/components/ui/popover";

export type SearchableSelectOption = {
  value: string;
  /** Compact closed-field text (usually the name). */
  label: string;
  /** Prominent first line in the list. Defaults to `label`. */
  primary?: string;
  /** Muted second line in the list (email, SKU · stock, …). */
  secondary?: string;
  /** Extra tokens for local filtering beyond label/primary/secondary. */
  keywords?: string;
};

type SearchableSelectProps<T extends FieldValues> = {
  id: string;
  label: string;
  name: FieldPath<T>;
  control: Control<T>;
  options: SearchableSelectOption[];
  placeholder?: string;
  error?: string;
  className?: string;
  triggerClassName?: string;
  parseValue?: (value: string) => T[FieldPath<T>];
  isEmpty?: (value: T[FieldPath<T>]) => boolean;
  disabled?: boolean;
  /** Remote search term (controlled by parent for API filtering). */
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  footer?: ReactNode;
};

function optionMatches(option: SearchableSelectOption, q: string): boolean {
  const haystack = [
    option.label,
    option.primary,
    option.secondary,
    option.keywords,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

/**
 * Editable combobox: compact selected value; richer two-line options in the list.
 * Parent should defer remote queries with useDeferredValue.
 */
export function SearchableSelect<T extends FieldValues>({
  id,
  label,
  name,
  control,
  options,
  placeholder = "Select…",
  error,
  className,
  triggerClassName,
  parseValue,
  isEmpty,
  disabled,
  searchValue,
  onSearchChange,
  footer,
}: SearchableSelectProps<T>) {
  const errorId = `${id}-error`;
  const listboxId = useId();
  const [open, setOpen] = useState(false);
  const [localSearch, setLocalSearch] = useState("");
  /** null = show committed selection; string = active query in the field. */
  const [draft, setDraft] = useState<string | null>(null);
  const [committedLabel, setCommittedLabel] = useState("");

  const search = searchValue ?? localSearch;
  const setSearch = onSearchChange ?? setLocalSearch;

  const filtered = useMemo(() => {
    if (onSearchChange || !search.trim()) return options;
    const q = search.trim().toLowerCase();
    return options.filter((option) => optionMatches(option, q));
  }, [onSearchChange, options, search]);

  const clearQuery = () => {
    setDraft(null);
    setSearch("");
    if (!onSearchChange) setLocalSearch("");
  };

  const close = () => {
    setOpen(false);
    clearQuery();
  };

  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor={id} className="text-sm font-semibold">
        {label}
      </Label>
      <Controller
        control={control}
        name={name}
        render={({ field }) => {
          const empty = isEmpty
            ? isEmpty(field.value)
            : field.value == null || field.value === "" || field.value === 0;
          const fromOptions = empty
            ? null
            : options.find((option) => option.value === String(field.value));
          const displayLabel = empty
            ? ""
            : (fromOptions?.label ?? committedLabel);

          const inputValue = draft !== null ? draft : displayLabel;

          const selectOption = (option: SearchableSelectOption) => {
            field.onChange(
              parseValue
                ? parseValue(option.value)
                : (option.value as T[FieldPath<T>]),
            );
            setCommittedLabel(option.label);
            close();
          };

          const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setOpen(true);
              return;
            }
            if (event.key === "Escape") {
              event.preventDefault();
              close();
              return;
            }
            if (event.key === "Enter" && open && filtered.length > 0) {
              event.preventDefault();
              selectOption(filtered[0]);
            }
          };

          return (
            <Popover
              open={open}
              onOpenChange={(next) => {
                if (next) {
                  setOpen(true);
                } else {
                  close();
                }
              }}
            >
              <PopoverAnchor asChild>
                <div className="relative">
                  <Input
                    id={id}
                    role="combobox"
                    aria-expanded={open}
                    aria-controls={listboxId}
                    aria-autocomplete="list"
                    aria-invalid={Boolean(error) || undefined}
                    aria-describedby={error ? errorId : undefined}
                    disabled={disabled}
                    autoComplete="off"
                    placeholder={placeholder}
                    value={inputValue}
                    onFocus={(event) => {
                      // Stay closed until the user types or opens via chevron / ↓.
                      event.currentTarget.select();
                    }}
                    onChange={(event) => {
                      const next = event.target.value;
                      setDraft(next);
                      setSearch(next);
                      setOpen(true);
                    }}
                    onKeyDown={onKeyDown}
                    className={cn(
                      "h-12 rounded-xl border-foreground bg-card pr-10 text-base md:text-base",
                      !displayLabel && draft === null && "text-muted-foreground",
                      triggerClassName,
                    )}
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    disabled={disabled}
                    aria-label={open ? "Close options" : "Open options"}
                    className="absolute top-1/2 right-3 -translate-y-1/2 text-muted-foreground"
                    onClick={() => {
                      if (open) {
                        close();
                      } else {
                        setOpen(true);
                      }
                    }}
                  >
                    <ChevronDown className="size-4" />
                  </button>
                </div>
              </PopoverAnchor>
              <PopoverContent
                align="start"
                onOpenAutoFocus={(event) => event.preventDefault()}
                className="w-(--radix-popover-trigger-width) max-w-[min(100vw-2rem,36rem)] p-2"
              >
                <ul
                  id={listboxId}
                  className="max-h-56 overflow-y-auto"
                  role="listbox"
                  aria-labelledby={id}
                >
                  {filtered.length === 0 ? (
                    <li className="px-2 py-3 text-sm text-muted-foreground">
                      No matches.
                    </li>
                  ) : (
                    filtered.map((option) => {
                      const isSelected = option.value === String(field.value);
                      const primary = option.primary ?? option.label;
                      return (
                        <li key={option.value}>
                          <button
                            type="button"
                            role="option"
                            aria-selected={isSelected}
                            className={cn(
                              "flex w-full items-start gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-muted",
                              isSelected && "bg-muted",
                            )}
                            onMouseDown={(event) => {
                              event.preventDefault();
                            }}
                            onClick={() => selectOption(option)}
                          >
                            <Check
                              className={cn(
                                "mt-0.5 size-4 shrink-0",
                                isSelected ? "opacity-100" : "opacity-0",
                              )}
                            />
                            <span className="min-w-0 flex-1">
                              <span className="block truncate font-semibold text-foreground">
                                {primary}
                              </span>
                              {option.secondary ? (
                                <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                                  {option.secondary}
                                </span>
                              ) : null}
                            </span>
                          </button>
                        </li>
                      );
                    })
                  )}
                </ul>
              </PopoverContent>
            </Popover>
          );
        }}
      />
      {error ? (
        <p id={errorId} className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      {footer}
    </div>
  );
}
