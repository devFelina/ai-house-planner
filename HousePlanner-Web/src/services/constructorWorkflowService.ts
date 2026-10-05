import axios from 'axios';
import { supabase } from '../lib/supabase';
import type { CostSummaryDto } from './workflowService';

const API_URL = `${import.meta.env.VITE_API_BASE_URL}/constructor/workflow`;

// Add the auth token to requests
const getAuthHeaders = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) return {};
  return {
    Authorization: `Bearer ${session.access_token}`
  };
};

export interface ConstructionPhase {
  id: string;
  projectId: string;
  phaseName: string;
  sequenceOrder: number;
  aiEstimatedDurationDays: number;
  plannedDurationDays: number;
  plannedStartDate?: string;
  plannedEndDate?: string;
  status: string;
  startedAt?: string;
  completedAt?: string;
}

export interface ConstructorWorkflowProject {
  id: string;
  workflowStateId: string;
  contractorId?: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  aiEstimatedTotalDurationDays: number;
  plannedTotalDurationDays: number;
  constructionPhases: ConstructionPhase[];
  design: {
    designId: string;
    version: number;
    floorCount: number;
    totalBuiltUpAreaSqft: number;
    foundationType: string;
    layoutJson: string;
  } | null;
  cost: CostSummaryDto | null;
}

export interface ConstructorWorkflowLog {
  id: string;
  projectId: string;
  constructorId: string;
  constructionPhaseId?: string;
  dayNumber: number;
  date: string;
  completedWork: string;
  progressPercentage: number;
  challenges?: string;
  issues?: string;
  resolution?: string;
  tomorrowPlan?: string;
  additionalNotes?: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  constructionPhase?: ConstructionPhase;
}

export interface ProjectProgress {
  totalEstimatedDays: number;
  daysCompleted: number;
  daysRemaining: number;
  overallProgress: number;
  delayStatus: string;
  latestLog?: ConstructorWorkflowLog;
}

export const constructorWorkflowService = {
  getProjects: async (): Promise<ConstructorWorkflowProject[]> => {
    const response = await axios.get(`${API_URL}/projects`, { headers: await getAuthHeaders() });
    return response.data;
  },

  getProjectDetails: async (projectId: string): Promise<ConstructorWorkflowProject> => {
    const response = await axios.get(`${API_URL}/projects/${projectId}`, { headers: await getAuthHeaders() });
    return response.data;
  },

  getWorkflowLogs: async (projectId: string): Promise<ConstructorWorkflowLog[]> => {
    const response = await axios.get(`${API_URL}/projects/${projectId}/logs`, { headers: await getAuthHeaders() });
    return response.data;
  },

  getProjectProgress: async (projectId: string): Promise<ProjectProgress> => {
    const response = await axios.get(`${API_URL}/projects/${projectId}/progress`, { headers: await getAuthHeaders() });
    return response.data;
  },

  createLog: async (log: Partial<ConstructorWorkflowLog>): Promise<ConstructorWorkflowLog> => {
    const response = await axios.post(`${API_URL}/logs`, log, { headers: await getAuthHeaders() });
    return response.data;
  },

  updateLog: async (logId: string, log: Partial<ConstructorWorkflowLog>): Promise<ConstructorWorkflowLog> => {
    const response = await axios.put(`${API_URL}/logs/${logId}`, log, { headers: await getAuthHeaders() });
    return response.data;
  },

  searchProject: async (projectId: string) => {
    const response = await axios.get(`${API_URL}/search/${projectId}`, { headers: await getAuthHeaders() });
    return response.data;
  },

  requestProject: async (projectId: string) => {
    const response = await axios.post(`${API_URL}/request/${projectId}`, {}, { headers: await getAuthHeaders() });
    return response.data;
  },

  approveRequest: async (requestId: string) => {
    const response = await axios.post(`${API_URL}/approve/${requestId}`, {}, { headers: await getAuthHeaders() });
    return response.data;
  },

  getProjectRequests: async (projectId: string) => {
    const response = await axios.get(`${API_URL}/requests/project/${projectId}`, { headers: await getAuthHeaders() });
    return response.data;
  },

  getConstructorRequests: async () => {
    const response = await axios.get(`${API_URL}/requests/constructor`, { headers: await getAuthHeaders() });
    return response.data;
  },

  getConstructorRequest: async (requestId: string) => {
    const response = await axios.get(`${API_URL}/requests/${requestId}`, { headers: await getAuthHeaders() });
    return response.data;
  },

  acceptRequest: async (requestId: string) => {
    const response = await axios.post(`${API_URL}/requests/${requestId}/accept`, {}, { headers: await getAuthHeaders() });
    return response.data;
  },

  declineRequest: async (requestId: string, reason?: string) => {
    const response = await axios.post(`${API_URL}/requests/${requestId}/decline`, { reason }, { headers: await getAuthHeaders() });
    return response.data;
  },

  setEstimatedDuration: async (projectId: string, estimatedDays: number) => {
    const response = await axios.post(`${API_URL}/projects/${projectId}/duration`, estimatedDays, {
      headers: {
        ...await getAuthHeaders(),
        'Content-Type': 'application/json'
      }
    });
    return response.data;
  },

  updatePhaseSchedule: async (projectId: string, phaseId: string, plannedDurationDays: number): Promise<ConstructionPhase> => {
    const response = await axios.put(`${API_URL}/projects/${projectId}/phases/${phaseId}/schedule`, { plannedDurationDays }, { headers: await getAuthHeaders() });
    return response.data;
  },

  updatePhaseStatus: async (projectId: string, phaseId: string, status: string): Promise<ConstructionPhase> => {
    const response = await axios.patch(`${API_URL}/projects/${projectId}/phases/${phaseId}/status`, { status }, { headers: await getAuthHeaders() });
    return response.data;
  }
};

export interface DailyConstructionLogDto {
  id: string;
  projectId: string;
  logDate: string;
  constructionPhaseId?: string;
  phaseName?: string;
  workCompleted: string;
  challenges?: string;
  materialsUsed?: string;
  workforceCount?: number;
  weatherCondition?: string;
  safetyIssues?: string;
  progressPercentage?: number;
  tomorrowPlan?: string;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDailyConstructionLogRequest {
  logDate: string;
  constructionPhaseId?: string;
  workCompleted: string;
  challenges?: string;
  materialsUsed?: string;
  workforceCount?: number;
  weatherCondition?: string;
  safetyIssues?: string;
  progressPercentage?: number;
  tomorrowPlan?: string;
  notes?: string;
}

export interface UpdateDailyConstructionLogRequest extends CreateDailyConstructionLogRequest {}

export const dailyConstructionLogService = {
  getLogs: async (projectId: string): Promise<DailyConstructionLogDto[]> => {
    const response = await axios.get(`${API_URL}/projects/${projectId}/logs`, { headers: await getAuthHeaders() });
    return response.data;
  },
  getLog: async (projectId: string, logId: string): Promise<DailyConstructionLogDto> => {
    const response = await axios.get(`${API_URL}/projects/${projectId}/logs/${logId}`, { headers: await getAuthHeaders() });
    return response.data;
  },
  createLog: async (projectId: string, request: CreateDailyConstructionLogRequest): Promise<DailyConstructionLogDto> => {
    const response = await axios.post(`${API_URL}/projects/${projectId}/logs`, request, { headers: await getAuthHeaders() });
    return response.data;
  },
  updateLog: async (projectId: string, logId: string, request: UpdateDailyConstructionLogRequest): Promise<DailyConstructionLogDto> => {
    const response = await axios.put(`${API_URL}/projects/${projectId}/logs/${logId}`, request, { headers: await getAuthHeaders() });
    return response.data;
  },
  deleteLog: async (projectId: string, logId: string): Promise<void> => {
    await axios.delete(`${API_URL}/projects/${projectId}/logs/${logId}`, { headers: await getAuthHeaders() });
  },
  getProjectCalendar: async (projectId: string): Promise<CalendarEventDto[]> => {
    const response = await axios.get(`${API_URL}/projects/${projectId}/calendar`, { headers: await getAuthHeaders() });
    return response.data;
  }
};

export interface CalendarEventDto {
  id: string;
  date: string;
  title: string;
  type: string;
  status: string;
  description: string;
  projectId: string;
  dailyLogId?: string;
  phaseId?: string;
}
