import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Bot, Loader2, Database, CheckCircle2, ChevronDown, Eye, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant" | "step";
  content: string;
  stepType?: "tool_call" | "tool_result" | "message";
  toolName?: string;
  toolInput?: any;
  toolOutput?: any;
  id?: string;
}

interface Chat {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export const AgentTab = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChatId, setCurrentChatId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load chats on mount
  useEffect(() => {
    loadChats();
  }, []);

  const loadChats = async () => {
    try {
      const chatsList = await api.getAgentChats();
      setChats(chatsList);
      // Load the most recent chat if available
      if (chatsList.length > 0 && !currentChatId) {
        loadChat(chatsList[0].id);
      }
    } catch (error) {
      console.error("Error loading chats:", error);
    }
  };

  const loadChat = async (chatId: number) => {
    try {
      setCurrentChatId(chatId);
      setIsLoading(true);
      const { chat, messages: chatMessages } = await api.getAgentChat(chatId);
      
      // Convert database messages to UI format
      const uiMessages: Message[] = chatMessages.map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        stepType: msg.step_type || undefined,
        toolName: msg.tool_name || undefined,
        toolInput: msg.tool_input || undefined,
        toolOutput: msg.tool_output || undefined,
        id: `msg-${msg.id}`,
      }));
      
      setMessages(uiMessages);
      // Don't refresh chat list here to avoid infinite loop - it's updated elsewhere
    } catch (error) {
      console.error("Error loading chat:", error);
      toast.error("Failed to load chat", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const createNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
    setInput("");
  };

  const deleteChat = async (chatId: number, e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    try {
      await api.deleteAgentChat(chatId);
      if (currentChatId === chatId) {
        createNewChat();
      }
      loadChats();
      toast.success("Chat deleted");
    } catch (error) {
      console.error("Error deleting chat:", error);
      toast.error("Failed to delete chat", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const toggleResultExpansion = (index: string) => {
    setExpandedResults((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const messageText = input.trim();
    setInput("");
    setIsLoading(true);

    let pollInterval: NodeJS.Timeout | null = null;
    let pollTimeout: NodeJS.Timeout | null = null;

    const startPolling = (chatId: number) => {
      let lastMessageCount = messages.length + 1; // +1 for the user message we just added
      
      pollInterval = setInterval(async () => {
        try {
          const { chat, messages: chatMessages } = await api.getAgentChat(chatId);
          
          // Always update to get latest messages
          const uiMessages: Message[] = chatMessages.map((msg: any) => ({
            role: msg.role,
            content: msg.content,
            stepType: msg.step_type || undefined,
            toolName: msg.tool_name || undefined,
            toolInput: msg.tool_input || undefined,
            toolOutput: msg.tool_output || undefined,
            id: `msg-${msg.id}`,
          }));
          
          setMessages(uiMessages);
          
          // Check if we're done (last message is from assistant)
          const lastMessage = chatMessages[chatMessages.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            if (pollInterval) clearInterval(pollInterval);
            if (pollTimeout) clearTimeout(pollTimeout);
            setIsLoading(false);
          }
        } catch (error) {
          console.error("Error polling for updates:", error);
          if (pollInterval) clearInterval(pollInterval);
          if (pollTimeout) clearTimeout(pollTimeout);
          setIsLoading(false);
        }
      }, 500); // Poll every 500ms
      
      // Stop polling after 60 seconds max
      pollTimeout = setTimeout(() => {
        if (pollInterval) clearInterval(pollInterval);
        setIsLoading(false);
      }, 60000);
    };

    // Start polling immediately if we have an existing chat
    if (currentChatId) {
      startPolling(currentChatId);
    }

    try {
      // Send message and get chat_id (processing happens synchronously on backend)
      const chatId = await api.chatWithAgent(messageText, currentChatId || undefined);
      
      // Update current chat ID if a new chat was created
      if (chatId && chatId !== currentChatId) {
        setCurrentChatId(chatId);
        loadChats(); // Refresh chat list
        // Start polling for new chat
        if (pollInterval) clearInterval(pollInterval);
        if (pollTimeout) clearTimeout(pollTimeout);
        startPolling(chatId);
      } else if (!currentChatId) {
        // New chat created, start polling now
        setCurrentChatId(chatId);
        if (pollInterval) clearInterval(pollInterval);
        if (pollTimeout) clearTimeout(pollTimeout);
        startPolling(chatId);
      }
      
      // Also fetch immediately in case processing is already done
      try {
        const { chat, messages: chatMessages } = await api.getAgentChat(chatId);
        
        const uiMessages: Message[] = chatMessages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          stepType: msg.step_type || undefined,
          toolName: msg.tool_name || undefined,
          toolInput: msg.tool_input || undefined,
          toolOutput: msg.tool_output || undefined,
          id: `msg-${msg.id}`,
        }));
        
        setMessages(uiMessages);
        
        // Check if already complete
        const lastMessage = chatMessages[chatMessages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant') {
          if (pollInterval) clearInterval(pollInterval);
          if (pollTimeout) clearTimeout(pollTimeout);
          setIsLoading(false);
        }
      } catch (error) {
        console.error("Error fetching initial messages:", error);
      }
      
    } catch (error) {
      console.error("Error chatting with agent:", error);
      if (pollInterval) clearInterval(pollInterval);
      if (pollTimeout) clearTimeout(pollTimeout);
      toast.error("Failed to get response", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full bg-background">
      {/* Sidebar with chat list */}
      <div className="w-64 border-r border-border flex flex-col">
        <div className="p-4 border-b border-border">
          <Button
            onClick={createNewChat}
            className="w-full"
            variant="default"
            size="sm"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {chats.map((chat) => (
              <ContextMenu key={chat.id}>
                <ContextMenuTrigger asChild>
                  <div
                    onClick={() => loadChat(chat.id)}
                    className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                      currentChatId === chat.id 
                        ? "bg-primary/10 border border-primary/20" 
                        : "hover:bg-accent"
                    }`}
                  >
                    <div className="flex-1 min-w-0 overflow-hidden">
                      <div className="text-sm font-medium truncate">{chat.title}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        {new Date(chat.updated_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </ContextMenuTrigger>
                <ContextMenuContent>
                  <ContextMenuItem
                    onClick={(e) => deleteChat(chat.id, e)}
                    className="gap-2 text-destructive focus:text-destructive focus:bg-destructive/10"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete chat
                  </ContextMenuItem>
                </ContextMenuContent>
              </ContextMenu>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <div className="relative mb-6">
                <Bot className="w-20 h-20 opacity-30" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Database className="w-8 h-8 opacity-50" />
                </div>
              </div>
              <p className="text-xl font-semibold mb-2 font-logo">Agent Chat</p>
              <p className="text-sm text-center max-w-md">
                Ask me anyhting, I can browse the requests, send requests, and navigate using the browser.
              </p>
            </div>
          )}
          {messages.map((message, index) => {
            const messageKey = `${index}-${message.id || message.role}`;
            const isExpanded = expandedResults.has(messageKey);
            
            return (
              <div
                key={messageKey}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {message.role === "step" ? (
                  <Card className={`max-w-[80%] border px-4 py-3 ${
                    message.stepType === "tool_result" 
                      ? "bg-success/10 border-success" 
                      : "bg-muted/50 border-muted"
                  }`}>
                    <div className="flex items-start gap-3">
                      {message.stepType === "tool_result" && (
                        <CheckCircle2 className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className={`text-sm font-medium mb-1 ${
                          message.stepType === "tool_result" ? "text-foreground" : ""
                        }`}>
                          {message.content}
                        </div>
                        {message.stepType === "tool_call" && message.toolInput && (
                          <Collapsible open={isExpanded} onOpenChange={() => toggleResultExpansion(messageKey)}>
                            <CollapsibleTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                              >
                                <Eye className="w-3 h-3 mr-1.5" />
                                View input
                                <ChevronDown className={`w-3 h-3 ml-1.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                              </Button>
                            </CollapsibleTrigger>
                            <CollapsibleContent className="mt-2">
                              <div className="bg-background border rounded-md p-3 max-h-96 overflow-auto">
                                <pre className="text-xs font-mono text-foreground whitespace-pre-wrap break-words">
                                  {JSON.stringify(message.toolInput, null, 2)}
                                </pre>
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}
                        {message.stepType === "tool_result" && message.toolOutput && (
                          <Collapsible open={isExpanded} onOpenChange={() => toggleResultExpansion(messageKey)}>
                            <CollapsibleTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                              >
                                <Eye className="w-3 h-3 mr-1.5" />
                                View results
                                <ChevronDown className={`w-3 h-3 ml-1.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                              </Button>
                            </CollapsibleTrigger>
                            <CollapsibleContent className="mt-2">
                              <div className="bg-background border rounded-md p-3 max-h-96 overflow-auto">
                                <pre className="text-xs font-mono text-foreground whitespace-pre-wrap break-words">
                                  {JSON.stringify(message.toolOutput, null, 2)}
                                </pre>
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}
                      </div>
                    </div>
                  </Card>
                ) : (
                  <div
                    className={`max-w-[80%] rounded-lg px-5 py-3 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-card border border-border shadow-sm"
                    }`}
                  >
                    {message.role === "assistant" ? (
                      <div
                        className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-muted prose-pre:border prose-pre:rounded-md prose-code:text-foreground prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-pre:code:bg-transparent prose-pre:code:p-0 prose-headings:text-foreground prose-p:text-foreground prose-li:text-foreground"
                        style={{
                          fontFamily: "var(--sans-font)",
                        }}
                      >
                        <ReactMarkdown
                          components={{
                            code: ({ node, inline, className, children, ...props }: any) => {
                              return inline ? (
                                <code className="text-xs bg-muted px-1 py-0.5 rounded text-foreground" {...props}>
                                  {children}
                                </code>
                              ) : (
                                <code className="block" {...props}>
                                  {children}
                                </code>
                              );
                            },
                            pre: ({ children }: any) => {
                              return (
                                <pre className="bg-muted border rounded-md p-3 overflow-x-auto">
                                  {children}
                                </pre>
                              );
                            },
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div
                        className={`whitespace-pre-wrap break-words text-sm`}
                      >
                        {message.content}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {isLoading && messages.length > 0 && messages[messages.length - 1].role !== "assistant" && (
            <div className="flex justify-start">
              <Card className="bg-muted/50 border-muted px-4 py-3">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">Thinking...</span>
                </div>
              </Card>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-border p-4">
          <div className="flex gap-2">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
              className="resize-none min-h-[44px] max-h-[200px]"
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="h-11 w-11 flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
