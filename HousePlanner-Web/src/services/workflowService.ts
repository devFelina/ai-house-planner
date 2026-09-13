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
  templateFamily?: string | null;
  designSeed?: number | null;
  designScore?: number | null;
  geometryFingerprint?: string | null;
  groundFootprintSqft?: number | null;
  entrances?: { room_id: string; wall: OpeningDto['wall']; offset: number; width: number }[];
  plotConstraints?: { dimensions_estimated?: boolean };
  candidateSummary?: { 
    notes?: string[],
    valid_count?: number,
    rejected_count?: number,
    generated_count?: number,
    unique_valid_count?: number,
    generation_mode?: string,
    selection_method?: string
  };

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

export interface GenerateDesignRequest {
  budgetLkr?: number;
  landSizePerches: number;
  manualTerrainType?: string;
  designSeed?: number;
  preferences: {
    bedrooms: number; bathrooms: number; floors: number; architecturalStyle?: string;
    openPlan?: boolean; masterEnsuite?: boolean; separateDining?: boolean;
    homeOffice?: boolean; balcony?: boolean; veranda?: boolean; utilityRoom?: boolean;
    parkingRequired?: boolean; accessibility?: boolean; spacePriority?: string;
    circulationPreference?: 'space_efficient';
  };
  plotConstraints?: {
    road_side: string; plot_width_ft?: number; plot_length_ft?: number;
    north_direction?: string; entrance_side?: string;
    setbacks?: { front?: number; rear?: number; left?: number; right?: number };
  };
}

// ──────────────────────────────────────────────────
// API calls
// ──────────────────────────────────────────────────

export const workflowService = {
  startDesign: async (request: GenerateDesignRequest): Promise<{ workflowId: string }> => {
    const response = await apiClient.post('/ai-generation/generate', request);
    return response.data;
  },
  getWorkflowStatus: async (id: string): Promise<WorkflowStatusResponseDto> => {
    const response = await apiClient.get<WorkflowStatusResponseDto>(`/workflows/${id}/status`);
    return response.data;
  },

  approveWorkflow: async (id: string, decision: 'approve' | 'reject' | 'request_revision', notes?: string) => {
    const response = await apiClient.post(`/workflows/${id}/approve`, { decision, revisionNotes: notes });
    return response.data;
  }
};
