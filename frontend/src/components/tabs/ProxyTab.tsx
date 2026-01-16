import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Settings, Play, Square, RefreshCw, Copy, Check, Globe, Download } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export const ProxyTab = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [proxyPort, setProxyPort] = useState<number>(8081);
  const [proxyHost, setProxyHost] = useState<string>("localhost");
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isBrowserLoading, setIsBrowserLoading] = useState(false);
  const [isDocker, setIsDocker] = useState(false);

  // Fetch proxy settings on mount and set up polling
  useEffect(() => {
    fetchProxySettings();
    checkDockerEnvironment();
    
    // Poll every 2 seconds to keep status up to date
    const interval = setInterval(() => {
      fetchProxySettings(true); // Silent refresh (no loading indicator)
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const checkDockerEnvironment = async () => {
    try {
      const health = await api.healthCheck();
      setIsDocker(health.docker === true);
    } catch (error) {
      console.error("Failed to check Docker environment:", error);
    }
  };

  const fetchProxySettings = async (silent = false) => {
    if (!silent) {
      setIsRefreshing(true);
    }
    try {
      const settings = await api.getProxySettings();
      setIsRunning(settings.running);
      setProxyPort(settings.port);
      setProxyHost(settings.host);
    } catch (error) {
      console.error("Failed to fetch proxy settings:", error);
      if (!silent) {
        toast.error("Failed to fetch proxy settings", {
          description: error instanceof Error ? error.message : "Unknown error",
        });
      }
    } finally {
      if (!silent) {
        setIsRefreshing(false);
      }
    }
  };

  const handleStartProxy = async () => {
    setIsLoading(true);
    try {
      const response = await api.startProxy();
      setIsRunning(response.running);
      toast.success("Proxy started", {
        description: `Proxy server is now running on port ${response.port}`,
      });
    } catch (error) {
      console.error("Failed to start proxy:", error);
      toast.error("Failed to start proxy", {
        description: error instanceof Error ? error.message : "",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopProxy = async () => {
    setIsLoading(true);
    try {
      const response = await api.stopProxy();
      setIsRunning(response.running);
      toast.success("Proxy stopped", {
        description: "Proxy server has been stopped",
      });
    } catch (error) {
      console.error("Failed to stop proxy:", error);
      toast.error("Failed to stop proxy", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const proxyUrl = `http://${proxyHost}:${proxyPort}`;

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(proxyUrl);
    setCopied(true);
    toast.success("Copied to clipboard", {
      description: proxyUrl,
    });
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenBrowser = async () => {
    setIsBrowserLoading(true);
    try {
      // Check if proxy is running, start it if not
      const proxyStatus = await api.getProxyStatus();
      if (!proxyStatus.running) {
        await api.startProxy();
        setIsRunning(true);
      }
      
      // Start browser
      await api.startBrowser();
      toast.success("Browser opened", {
        description: "Browser is now running with proxy settings",
      });
    } catch (error) {
      console.error("Failed to open browser:", error);
      toast.error("Failed to open browser", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsBrowserLoading(false);
    }
  };

  const handleDownloadCertificateScript = () => {
    const scriptContent = `#!/bin/bash
# Install mitmproxy certificate on macOS and Linux
CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

# Check if certificate exists
if [ ! -f "$CERT_PATH" ]; then
    echo "Error: Certificate not found at $CERT_PATH"
    echo "Please run mitmproxy at least once to generate the certificate."
    exit 1
fi

# Detect OS
OS="$(uname -s)"

case "$OS" in
    Darwin*)
        echo "Detected macOS. Installing certificate to system keychain..."
        echo "You may be prompted for your password."
        echo ""
        
        # Add certificate to system keychain
        sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$CERT_PATH"
        
        if [ $? -eq 0 ]; then
            echo "✅ Certificate installed successfully on macOS!"
        else
            echo "❌ Failed to install certificate."
            exit 1
        fi
        ;;
    Linux*)
        echo "Detected Linux. Installing certificate to system trust store..."
        echo "You may be prompted for your password."
        echo ""
        
        # Determine certificate store location
        if [ -d /etc/pki/ca-trust/source/anchors/ ]; then
            # RHEL/CentOS/Fedora
            CERT_STORE="/etc/pki/ca-trust/source/anchors/mitmproxy-ca-cert.crt"
            sudo cp "$CERT_PATH" "$CERT_STORE"
            sudo update-ca-trust
        elif [ -d /usr/local/share/ca-certificates/ ]; then
            # Debian/Ubuntu
            CERT_STORE="/usr/local/share/ca-certificates/mitmproxy-ca-cert.crt"
            sudo cp "$CERT_PATH" "$CERT_STORE"
            sudo update-ca-certificates
        else
            echo "Error: Could not determine certificate store location."
            echo "Please install the certificate manually."
            exit 1
        fi
        
        if [ $? -eq 0 ]; then
            echo "✅ Certificate installed successfully on Linux!"
        else
            echo "❌ Failed to install certificate."
            exit 1
        fi
        ;;
    *)
        echo "Error: Unsupported operating system: $OS"
        echo "Please install the certificate manually."
        exit 1
        ;;
esac

echo ""
echo "Certificate installation complete!"
`;

    // Create blob and download
    const blob = new Blob([scriptContent], { type: 'text/x-shellscript' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'install-mitmproxy-cert.sh';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    toast.success("Script downloaded", {
      description: "Run the script to install the certificate",
    });
  };

  return (
    <div className="h-full p-4 overflow-auto">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Proxy Control Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-muted-foreground" />
                  Proxy Server
                </CardTitle>
                <CardDescription>
                  Control the mitmproxy server
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => fetchProxySettings()}
                disabled={isRefreshing}
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Status */}
            <div className="flex items-center justify-between p-4 rounded-lg border">
              <div className="space-y-1">
                <p className="text-sm font-medium">Status</p>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      isRunning ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    }`}
                  />
                  <p className="text-sm text-muted-foreground">
                    {isRunning ? "Running" : "Stopped"}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                {!isRunning ? (
                  <Button
                    onClick={handleStartProxy}
                    disabled={isLoading}
                    className="gap-2"
                  >
                    <Play className="w-4 h-4" />
                    Start Proxy
                  </Button>
                ) : (
                  <Button
                    onClick={handleStopProxy}
                    disabled={isLoading}
                    variant="destructive"
                    className="gap-2"
                  >
                    <Square className="w-4 h-4" />
                    Stop Proxy
                  </Button>
                )}
              </div>
            </div>

            {/* Proxy URL */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Proxy URL</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 p-3 rounded-lg border bg-muted font-mono text-sm">
                  {proxyUrl}
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleCopyUrl}
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Configuration Instructions */}
            <div className="space-y-3 p-4 rounded-lg border border-dashed">
              <p className="text-sm font-medium">How to use:</p>
              <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
                <li>Start the proxy server using the button above</li>
                <li>Select a project to capture requests for</li>
                <li>Configure your application to use the proxy:
                  <ul className="ml-6 mt-1 space-y-1 list-disc list-inside">
                    <li>HTTP Proxy: <code className="px-1 py-0.5 rounded bg-muted font-mono text-xs">{proxyUrl}</code></li>
                    <li>HTTPS Proxy: <code className="px-1 py-0.5 rounded bg-muted font-mono text-xs">{proxyUrl}</code></li>
                  </ul>
                </li>
                <li>Make requests through your application</li>
                <li>View captured requests in the Project tab</li>
              </ol>
            </div>

            {/* Browser Control */}
            {!isDocker && (
              <div className="flex items-center justify-between p-4 rounded-lg border">
                <div className="space-y-1">
                  <p className="text-sm font-medium">Browser</p>
                  <p className="text-sm text-muted-foreground">
                    Open a browser instance with proxy settings
                  </p>
                </div>
                <Button
                  onClick={handleOpenBrowser}
                  disabled={isBrowserLoading}
                  className="gap-2"
                >
                  <Globe className="w-4 h-4" />
                  {isBrowserLoading ? "Opening..." : "Open Browser"}
                </Button>
              </div>
            )}
            {isDocker && (
              <div className="p-4 rounded-lg border border-dashed bg-muted/50">
                <p className="text-sm font-medium mb-1">Browser Control</p>
                <p className="text-xs text-muted-foreground">
                  Browser automation is not available in Docker. Please configure your browser manually to use the proxy at <code className="px-1 py-0.5 rounded bg-background font-mono text-xs">{proxyUrl}</code>
                </p>
              </div>
            )}

            {/* HTTPS Certificate Notice */}
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-start justify-between mb-2">
                <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
                  📋 HTTPS Certificate
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleDownloadCertificateScript}
                  className="gap-2"
                >
                  <Download className="w-3 h-3" />
                  Download Install Script
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                For HTTPS interception, you need to install the mitmproxy CA certificate.
                Download the installation script above, or visit{" "}
                <a
                  href="http://mitm.it"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-foreground"
                >
                  mitm.it
                </a>{" "}
                while connected to the proxy to download and install it.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
