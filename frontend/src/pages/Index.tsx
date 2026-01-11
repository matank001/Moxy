import { AppTabs } from "@/components/AppTabs";
import { ResenderProvider } from "@/contexts/ResenderContext";

const Index = () => {
  return (
    <ResenderProvider>
      <div className="h-screen flex flex-col bg-background">
        <AppTabs />
      </div>
    </ResenderProvider>
  );
};

export default Index;
