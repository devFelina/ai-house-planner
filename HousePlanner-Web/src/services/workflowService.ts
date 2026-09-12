import apiClient from './apiClient';

// ──────────────────────────────────────────────────
// Shared TypeScript interfaces matching the backend DTOs
// ──────────────────────────────────────────────────

export interface OpeningDto {
  wall: 'north' | 'south' | 'east' | 'west';
  offset: number;
  width: number;
}

export interface RoomSummaryDto {
  roomId: string;
  roomType: string;
  name: string | null;
  floorNumber: number;
  x: number;
  y: number;
  width: number;
  length: number;
  areaSqft: number;
  wallHeight: number;
  doors: OpeningDto[] | null;
  windows: OpeningDto[] | null;
}

export interface HouseDesignSummaryDto {
  designId: string;
  version: number;
  floorCount: number;
  totalBuiltUpAreaSqft: number;
  foundationType: string;
  templateId: string | null;
  terrainType: string | null;
  isCurrent: boolean;
  rooms: RoomSummaryDto[];
}

export interface WorkflowStatusResponseDto {
  workflowId: string;
  status: string;
  terrainType: string | null;
  slopeEstimate: string | null;
  design: HouseDesignSummaryDto | null;
  cost: any | null; // Expand when Component C is integrated
  approvalStatus: string;
}

// ──────────────────────────────────────────────────
// API calls
// ──────────────────────────────────────────────────

export const workflowService = {
  getWorkflowStatus: async (id: string): Promise<WorkflowStatusResponseDto> => {
    const response = await apiClient.get<WorkflowStatusResponseDto>(`/workflows/${id}/status`);
    return response.data;
  },

  approveWorkflow: async (id: string, decision: 'approve' | 'reject' | 'request_revision', notes?: string) => {
    const response = await apiClient.post(`/workflows/${id}/approve`, { decision, revisionNotes: notes });
    return response.data;
  }
};
