import apiClient from '../../services/apiClient';

export interface ApprovalRequestDto {
  decision: 'approve' | 'reject' | 'request_revision';
  revisionNotes?: string;
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
  getWorkflowStatus: async (workflowId: string) => {
    // Note: Do not call this automatically if backend is not implemented yet.
    const response = await apiClient.get(`/api/v1/workflows/${workflowId}/status`);
    return response.data;
  },

  /**
   * Submits an approval decision for a workflow.
   * POST /api/v1/workflows/{id}/approve
   */
  approveWorkflow: async (workflowId: string, data: ApprovalRequestDto) => {
    // Note: Do not call this automatically if backend is not implemented yet.
    const response = await apiClient.post(`/api/v1/workflows/${workflowId}/approve`, data);
    return response.data;
  },

  /**
   * Retrieves the tracking details for a project.
   * GET /api/v1/projects/{id}/tracking
   */
  getProjectTracking: async (projectId: string): Promise<ProjectTrackingResponseDto> => {
    // Note: Do not call this automatically if backend is not implemented yet.
    const response = await apiClient.get<ProjectTrackingResponseDto>(`/api/v1/projects/${projectId}/tracking`);
    return response.data;
  }
};

export default projectService;
