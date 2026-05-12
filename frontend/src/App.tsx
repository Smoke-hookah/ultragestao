import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import Layout from "./components/Layout";
import ProcessarLote from "./pages/ProcessarLote";
import Historico from "./pages/Historico";

const App = () => (
  <BrowserRouter>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <Layout>
        <Routes>
          <Route path="/" element={<ProcessarLote />} />
          <Route path="/historico" element={<Historico />} />
        </Routes>
      </Layout>
    </TooltipProvider>
  </BrowserRouter>
);

export default App;
