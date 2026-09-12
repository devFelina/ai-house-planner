import apiClient from '../../services/apiClient';

export interface ApprovalRequestDto {
  decision: 'approve' | 'reject' | 'request_revision';
  revisionNotes?: string;
}

export interface ApprovalResponseDto {
  workflowId: string;
  decision: string;
  status: string;
  projectId: string | null;
  message: string;
  timestamp: string;
}

export interface WorkflowStatusResponseDto {
  workflowId: string;
  status: string;
  approvalStatus: string;
  validationPassed: boolean;
  retryCount: number;
  revisionNotes: string | null;
  validationResult: Record<string, unknown> | null;
  projectId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PhaseTrackingDto {
  phaseName: string;
  status: string;
  startedAtUtc: string | null;
  completedAtUtc: string | null;
  sequenceOrder: number;
}

export interface ProjectTrackingResponseDto {
  projectId: string;
  status: string;
  contractorName: string | null;
  phases: PhaseTrackingDto[];
}

export const projectService = {
  /**
   * Retrieves the current status of a workflow.
   * GET /api/v1/workflows/{id}/status
   */
  getWorkflowStatus: async (workflowId: string): Promise<WorkflowStatusResponseDto> => {
    const response = await apiClient.get<WorkflowStatusResponseDto>(`/workflows/${workflowId}/status`);
    return response.data;
  },

  /**
   * Submits an approval decision for a workflow.
   * POST /api/v1/workflows/{id}/approve
   */
  approveWorkflow: async (workflowId: string, data: ApprovalRequestDto): Promise<ApprovalResponseDto> => {
    const response = await apiClient.post<ApprovalResponseDto>(`/workflows/${workflowId}/approve`, data);
    return response.data;
  },

  /**
   * Retrieves the tracking details for a project.
   * GET /api/v1/projects/{id}/tracking
   */
  getProjectTracking: async (projectId: string): Promise<ProjectTrackingResponseDto> => {
    const response = await apiClient.get<ProjectTrackingResponseDto>(`/projects/${projectId}/tracking`);
    return response.data;
  },

  /**
   * Retrieves the tracking details for a project by workflow ID.
   * GET /api/v1/projects/by-workflow/{workflowId}
   */
  getProjectByWorkflow: async (workflowId: string): Promise<ProjectTrackingResponseDto> => {
    const response = await apiClient.get<ProjectTrackingResponseDto>(`/projects/by-workflow/${workflowId}`);
    return response.data;
  }
};

export default projectService;
