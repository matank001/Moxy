import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FolderPlus, FolderOpen, Download, Trash2, Plus, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";
import { api, Project, HttpRequest } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { MethodBadge } from "@/components/MethodBadge";
import { StatusCode } from "@/components/StatusCode";

export const ProjectTab = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [requests, setRequests] = useState<HttpRequest[]>([]);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isAddRequestDialogOpen, setIsAddRequestDialogOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");
  const [newRequestMethod, setNewRequestMethod] = useState("GET");
  const [newRequestUrl, setNewRequestUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  // Load projects on mount
  useEffect(() => {
    loadProjects();
    loadCurrentProject();
  }, []);

  // Load requests when project changes
  useEffect(() => {
    if (currentProject) {
      loadProjectRequests(currentProject.id);
      // Sync with backend
      api.setCurrentProject(currentProject.id).catch(console.error);
    } else {
      setRequests([]);
    }
  }, [currentProject]);

  const loadProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to load projects: ${error}`,
        variant: "destructive",
      });
    }
  };

  const loadCurrentProject = async () => {
    try {
      const data = await api.getCurrentProject();
      if (data.current_project_id && data.project) {
        setCurrentProject(data.project);
      } else {
        // If no current project, try to get the first project
        const projects = await api.getProjects();
        if (projects.length > 0) {
          const firstProject = projects[0];
          setCurrentProject(firstProject);
          await api.setCurrentProject(firstProject.id);
        }
      }
    } catch (error) {
      console.error("Failed to load current project:", error);
    }
  };

  const loadProjectRequests = async (projectId: number) => {
    try {
      const data = await api.getProjectRequests(projectId);
      setRequests(data);
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to load requests: ${error}`,
        variant: "destructive",
      });
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      toast({
        title: "Error",
        description: "Project name is required",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const project = await api.createProject({
        name: newProjectName,
        description: newProjectDescription,
      });
      
      setProjects([project, ...projects]);
      setCurrentProject(project);
      setIsCreateDialogOpen(false);
      setNewProjectName("");
      setNewProjectDescription("");
      
      toast({
        title: "Success",
        description: `Project "${project.name}" created successfully`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to create project: ${error}`,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteProject = async (projectId: number, projectName: string) => {
    if (!confirm(`Are you sure you want to delete "${projectName}"?`)) {
      return;
    }

    try {
      await api.deleteProject(projectId);
      setProjects(projects.filter(p => p.id !== projectId));
      if (currentProject?.id === projectId) {
        setCurrentProject(null);
        await api.setCurrentProject(null);
      }
      
      toast({
        title: "Success",
        description: `Project "${projectName}" deleted successfully`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to delete project: ${error}`,
        variant: "destructive",
      });
    }
  };

  const handleAddRequest = async () => {
    if (!currentProject) return;
    
    if (!newRequestUrl.trim()) {
      toast({
        title: "Error",
        description: "URL is required",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const request = await api.addProjectRequest(currentProject.id, {
        method: newRequestMethod,
        url: newRequestUrl,
      });
      
      setRequests([request, ...requests]);
      setIsAddRequestDialogOpen(false);
      setNewRequestMethod("GET");
      setNewRequestUrl("");
      
      toast({
        title: "Success",
        description: "Request added successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to add request: ${error}`,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteRequest = async (requestId: number) => {
    if (!currentProject) return;

    try {
      await api.deleteProjectRequest(currentProject.id, requestId);
      setRequests(requests.filter(r => r.id !== requestId));
      
      toast({
        title: "Success",
        description: "Request deleted successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to delete request: ${error}`,
        variant: "destructive",
      });
    }
  };

  const handleClearRequests = async () => {
    if (!currentProject) return;
    
    if (!confirm("Are you sure you want to clear all requests?")) {
      return;
    }

    try {
      await api.clearProjectRequests(currentProject.id);
      setRequests([]);
      
      toast({
        title: "Success",
        description: "All requests cleared successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to clear requests: ${error}`,
        variant: "destructive",
      });
    }
  };

  const handleOpenFolder = async (projectId: number) => {
    try {
      const result = await api.openProjectFolder(projectId);
      
      toast({
        title: "Success",
        description: `Opened folder: ${result.path}`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to open folder: ${error}`,
        variant: "destructive",
      });
    }
  };

  const handleExportProject = async () => {
    if (!currentProject) return;

    try {
      const blob = await api.exportProjectDatabase(currentProject.id);
      
      // Create a download link and trigger download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentProject.name.replace(/[^a-zA-Z0-9-_]/g, '_').toLowerCase()}.db`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: "Success",
        description: `Project database exported successfully`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to export project: ${error}`,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="h-full p-4 overflow-auto">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Project Actions Card */}
        <Card>
          <CardHeader>
            <CardTitle>Project Management</CardTitle>
            <CardDescription>
              Create, load, and manage your security testing projects
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              <Button 
                variant="outline" 
                className="h-24 flex-col gap-2 hover:bg-primary/10 hover:border-primary/50 hover:text-foreground transition-colors"
                onClick={() => setIsCreateDialogOpen(true)}
              >
                <FolderPlus className="w-6 h-6 text-primary hover:text-primary" />
                <span>New Project</span>
              </Button>
              <Button 
                variant="outline" 
                className="h-24 flex-col gap-2 hover:bg-primary/10 hover:border-primary/50 hover:text-foreground transition-colors disabled:hover:bg-transparent disabled:hover:border-border"
                onClick={handleExportProject}
                disabled={!currentProject}
              >
                <Download className={`w-6 h-6 ${currentProject ? 'text-primary' : 'text-muted-foreground'}`} />
                <span>Export Data</span>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Current Project Info */}
        <Card className={currentProject ? "border-primary" : "border-dashed"}>
          <CardContent className="pt-6">
            <div className="text-center">
              {currentProject ? (
                <>
                  <p className="text-sm text-muted-foreground">
                    Current project: <span className="font-mono text-foreground font-semibold">{currentProject.name}</span>
                  </p>
                  {currentProject.description && (
                    <p className="text-xs mt-1 text-muted-foreground">
                      {currentProject.description}
                    </p>
                  )}
                  <p className="text-xs mt-2 text-muted-foreground">
                    Created: {new Date(currentProject.created_at).toLocaleString()}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No project selected • Create or select a project to get started
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Projects List */}
        <Card>
          <CardHeader>
            <CardTitle>Your Projects ({projects.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {projects.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No projects yet. Create your first project to get started!</p>
              </div>
            ) : (
              <div className="space-y-2">
                {projects.map((project) => (
                  <div
                    key={project.id}
                    className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${
                      currentProject?.id === project.id
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-accent"
                    }`}
                  >
                    <div 
                      className="flex-1 cursor-pointer"
                      onClick={() => setCurrentProject(project)}
                    >
                      <h3 className="font-semibold">{project.name}</h3>
                      {project.description && (
                        <p className="text-sm text-muted-foreground">{project.description}</p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        Created {new Date(project.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenFolder(project.id)}
                        title="Open database folder"
                      >
                        <FolderOpen className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteProject(project.id, project.name)}
                        title="Delete project"
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create Project Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
            <DialogDescription>
              Create a new project to organize your security testing sessions
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Project Name *</Label>
              <Input
                id="name"
                placeholder="My Security Test"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Optional description for this project"
                value={newProjectDescription}
                onChange={(e) => setNewProjectDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button onClick={handleCreateProject} disabled={isLoading}>
              {isLoading ? "Creating..." : "Create Project"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};