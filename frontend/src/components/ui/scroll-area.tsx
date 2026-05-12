import * as React from "react";
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";

import { cn } from "@/lib/utils";

const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root ref={ref} className={cn("relative overflow-hidden flex flex-col min-h-0", className)} {...props}>
    <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit] flex-1 overflow-auto">
      {children}
    </ScrollAreaPrimitive.Viewport>
    <ScrollBar />
    <ScrollAreaPrimitive.Corner />
  </ScrollAreaPrimitive.Root>
));
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName;

const ScrollBar = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>
>(({ className, orientation = "vertical", ...props }, ref) => (
  <ScrollAreaPrimitive.ScrollAreaScrollbar
    ref={ref}
    orientation={orientation}
    className={cn(
      "flex touch-none select-none transition-colors rounded-full",
      orientation === "vertical" && "h-full w-2 p-0.5",
      orientation === "horizontal" && "h-2 flex-col p-0.5",
      // Track minimalista: levemente mais escuro que o fundo e com transparência
      "bg-muted/10 hover:bg-muted/20",
      className,
    )}
    {...props}
  >
    <ScrollAreaPrimitive.ScrollAreaThumb
      className={cn(
        "relative flex-1 rounded-full",
        // Thumb minimalista: tom sutil, com transparência
        "bg-muted-foreground/25 hover:bg-muted-foreground/35 active:bg-muted-foreground/45",
      )}
    />
  </ScrollAreaPrimitive.ScrollAreaScrollbar>
));
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName;

export { ScrollArea, ScrollBar };
