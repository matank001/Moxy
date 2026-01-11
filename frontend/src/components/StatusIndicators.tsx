import { useEffect, useState } from "react";
import { api, Project } from "@/lib/api";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface StatusIndicatorsProps {
  onProxyClick?: () => void;
}

export const StatusIndicators = ({ onProxyClick }: StatusIndicatorsProps) => {
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [proxyStatus, setProxyStatus] = useState<'running' | 'stopped' | 'checking'>('checking');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);

  useEffect(() => {
    // Initial check
    checkStatus();
    loadCurrentProject();

    // Poll every 2 seconds
    const interval = setInterval(() => {
      checkStatus();
      loadCurrentProject();
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const loadCurrentProject = async () => {
    try {
      const data = await api.getCurrentProject();
      if (data.current_project_id && data.project) {
        setCurrentProject(data.project);
      } else {
        setCurrentProject(null);
      }
    } catch (error) {
      console.error("Failed to load current project:", error);
    }
  };

  const checkStatus = async () => {
    // Check backend health
    try {
      await api.healthCheck();
      setBackendStatus('online');
    } catch (error) {
      setBackendStatus('offline');
    }

    // Check proxy status
    try {
      const proxySettings = await api.getProxyStatus();
      setProxyStatus(proxySettings.running ? 'running' : 'stopped');
    } catch (error) {
      setProxyStatus('stopped');
    }
  };

  return (
    <TooltipProvider>
      <div className="flex items-center gap-3">
        {/* Backend Status */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer">
              <div
                className={`w-2 h-2 rounded-full ${
                  backendStatus === 'online'
                    ? 'bg-green-500 animate-pulse'
                    : backendStatus === 'offline'
                    ? 'bg-red-500'
                    : 'bg-gray-400 animate-pulse'
                }`}
              />
              <span className="text-xs font-medium text-muted-foreground">Backend</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>
              Backend:{' '}
              {backendStatus === 'online' ? (
                <span className="text-green-500">Online</span>
              ) : backendStatus === 'offline' ? (
                <span className="text-red-500">Offline</span>
              ) : (
                <span className="text-gray-500">Checking...</span>
              )}
            </p>
          </TooltipContent>
        </Tooltip>

        {/* Proxy Status */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div 
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer"
              onClick={onProxyClick}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  proxyStatus === 'running'
                    ? 'bg-green-500 animate-pulse'
                    : proxyStatus === 'stopped'
                    ? 'bg-gray-400'
                    : 'bg-gray-400 animate-pulse'
                }`}
              />
              <span className="text-xs font-medium text-muted-foreground">Proxy</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>
              Proxy:{' '}
              {proxyStatus === 'running' ? (
                <span className="text-green-500">Running</span>
              ) : proxyStatus === 'stopped' ? (
                <span className="text-muted-foreground">Stopped</span>
              ) : (
                <span className="text-gray-500">Checking...</span>
              )}
            </p>
          </TooltipContent>
        </Tooltip>

        {/* Project Name Tag */}
        {currentProject && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-card">
            <span className="text-xs font-medium text-foreground/70">{currentProject.name}</span>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};
