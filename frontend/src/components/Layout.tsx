import React from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, History, Settings, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

const Layout = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();

  const menuItems = [
    { icon: LayoutDashboard, label: "Processar Lote", path: "/" },
    { icon: History, label: "Histórico", path: "/historico" },
  ];

  return (
    <div className="flex h-screen bg-[#121212] text-[#e0e0e0] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-[#1a1a1a] border-r border-[#2a2a2a] flex flex-col shrink-0">
        <div className="p-6 border-b border-[#2a2a2a]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center font-bold text-white italic">
              U
            </div>
            <span className="font-bold text-lg tracking-tight">UltraDanfe<span className="text-blue-500">XML</span></span>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-md transition-all group",
                location.pathname === item.path
                  ? "bg-blue-600/10 text-blue-400 border border-blue-600/20"
                  : "text-muted-foreground hover:bg-[#222] hover:text-[#e0e0e0]"
              )}
            >
              <item.icon className={cn("w-5 h-5", location.pathname === item.path ? "text-blue-400" : "group-hover:text-blue-400")} />
              <span className="font-medium text-sm">{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-[#2a2a2a]">
          <div className="bg-[#222] rounded-lg p-3 border border-[#333]">
            <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest mb-2">Servidor</p>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-green-500 flex items-center gap-1.5">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                Online
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">v1.2.0</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {children}
      </main>
    </div>
  );
};

export default Layout;
