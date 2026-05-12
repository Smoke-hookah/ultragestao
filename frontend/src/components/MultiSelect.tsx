import { useMemo, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { ScrollArea } from "@/components/ui/scroll-area";

export type MultiSelectOption = {
  value: string;
  label?: string;
};

type Props = {
  placeholder: string;
  options: MultiSelectOption[];
  value: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
  minSearchChars?: number;
  maxInitialOptions?: number;
  className?: string;
};

export function MultiSelect({
  placeholder,
  options,
  value,
  onChange,
  disabled,
  minSearchChars = 3,
  maxInitialOptions = 80,
  className,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const selectedSet = useMemo(() => new Set(value), [value]);

  const optionMap = useMemo(() => {
    const m = new Map<string, MultiSelectOption>();
    for (const o of options) m.set(o.value, o);
    return m;
  }, [options]);

  const selectedBadges = useMemo(() => {
    return value
      .map((v) => optionMap.get(v))
      .filter(Boolean) as MultiSelectOption[];
  }, [value, optionMap]);

  const qTrim = query.trim();
  const isEmptyQuery = qTrim.length === 0;
  const canSearch = qTrim.length >= minSearchChars;
  const filtered = useMemo(() => {
    if (isEmptyQuery) return options.slice(0, maxInitialOptions);
    if (!canSearch) return [];
    const q = qTrim.toLowerCase();
    return options.filter((o) => (o.label || o.value).toLowerCase().includes(q));
  }, [options, qTrim, canSearch, isEmptyQuery, maxInitialOptions]);

  const toggleValue = (v: string) => {
    if (selectedSet.has(v)) {
      onChange(value.filter((x) => x !== v));
    } else {
      onChange([...value, v]);
    }
  };

  const clearAll = () => {
    onChange([]);
  };

  return (
    <div className={cn("w-full", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            disabled={disabled}
            className={cn(
              "h-auto min-h-10 w-full justify-between bg-background px-3 py-2 text-left",
              disabled && "opacity-60"
            )}
          >
            <div className="flex flex-1 flex-wrap items-center gap-2">
              {selectedBadges.length === 0 ? (
                <span className="text-sm text-muted-foreground">{placeholder}</span>
              ) : (
                selectedBadges.slice(0, 3).map((o) => (
                  <Badge key={o.value} variant="secondary" className="max-w-[220px] truncate">
                    {o.label || o.value}
                  </Badge>
                ))
              )}
              {selectedBadges.length > 3 && (
                <Badge variant="secondary">+{selectedBadges.length - 3}</Badge>
              )}
            </div>
            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-60" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder={`Digite para buscar (min ${minSearchChars})...`}
              value={query}
              onValueChange={setQuery}
            />
            <ScrollArea className="h-[min(320px,60vh)]">
              <CommandList className="max-h-none overflow-hidden">
                {!isEmptyQuery && !canSearch ? (
                  <CommandEmpty>Digite ao menos {minSearchChars} caracteres</CommandEmpty>
                ) : filtered.length === 0 ? (
                  <CommandEmpty>{isEmptyQuery ? "Sem opções" : "Nenhum resultado"}</CommandEmpty>
                ) : (
                  <CommandGroup>
                    <div className="p-1 pr-2">
                      {filtered.map((o) => {
                        const isSelected = selectedSet.has(o.value);
                        return (
                          <CommandItem
                            key={o.value}
                            value={o.value}
                            onSelect={() => toggleValue(o.value)}
                            className="flex items-center justify-between"
                          >
                            <span className="truncate">{o.label || o.value}</span>
                            {isSelected && <Check className="h-4 w-4 text-primary" />}
                          </CommandItem>
                        );
                      })}
                    </div>
                  </CommandGroup>
                )}
              </CommandList>
            </ScrollArea>

            <div className="flex items-center justify-between border-t p-2">
              <span className="text-xs text-muted-foreground">Selecionados: {value.length}</span>
              <Button type="button" variant="ghost" size="sm" onClick={clearAll} disabled={value.length === 0}>
                Limpar
              </Button>
            </div>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}
