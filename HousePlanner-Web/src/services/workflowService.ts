import type { AxiosRequestConfig } from 'axios';
import apiClient from './apiClient';

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
  notes?: string[];
  valid_count?: number;
  rejected_count?: number;
  generated_count?: number;
  unique_valid_count?: number;
  generation_mode?: string;
  selection_method?: string;
 };
}

export interface CostSummaryDto {
 materialCostLkr: number;
 labourCostLkr: number;
 totalCostLkr: number;
 budgetDeltaPercent: number | null;
 breakdown?: CostBreakdownItemDto[] | null;
 formulaVersion?: string | null;
 appliedAreaSqft?: number | null;
 terrainType?: string | null;
 estimatedAt?: string | null;
}

export interface CostBreakdownItemDto {
 itemName: string;
 costHead: string;
 category: 'material' | 'labour';
 unitCostLkr: number;
 unit: string;
 appliedQuantity: number;
 quantityUnit: string;
 terrainMultiplier: number;
 amountLkr: number;
 sharePercent: number;
 provider?: string | null;
 sourceReference?: string | null;
 pricingUpdatedAt?: string | null;
}

export interface ConstructionPhaseDto {
 id: number;
 name: string;
 description: string;
 duration_days: number;
 depends_on: number[];
 start_day: number;
 end_day: number;
 status: string;
}

export interface ConstructionPlanSummaryDto {
 project_summary: {
  estimated_duration_days: number;
  estimated_duration_months: number;
  target_duration_days: number | null;
  schedule_status: string;
 };
 phases: ConstructionPhaseDto[];
 critical_path: string[];
 assumptions: string[];
 optimization_notes: string[];
}

export interface AgentExecutionLogEntry {
  agent: string;
  status: 'completed' | 'failed' | string;
  message: string;
  toolCalled?: string | null;
  durationMs?: number | null;
  createdAt?: string | null;
}

export interface CostEstimationRunSummaryDto {
  status: 'success' | 'failed';
  formulaVersion: string;
  pricingRecordCount: number;
  appliedAreaSqft: number | null;
  terrainType: string | null;
  failureReason: string | null;
  startedAt: string;
  completedAt: string;
}

export interface WorkflowRequirementsDto {
 landSizeCategory?: string;
 landSizePerches?: number;
 bedrooms?: number;
 bathrooms?: number;
 houseType?: string;
 floors?: number;
}

export interface WorkflowStatusResponseDto {
 workflowId: string;
 status: string;
 terrainType: string | null;
 slopeEstimate: string | null;
 design: HouseDesignSummaryDto | null;
 cost: CostSummaryDto | null;
 approvalStatus: string;
 failureReason?: string | null;
 preferredHouseDesignId?: string | null;
 architectReviewStatus?: string | null;
 architectFeedback?: string | null;
 constructionPlan?: ConstructionPlanSummaryDto | null;
 agentExecutionLog?: AgentExecutionLogEntry[] | null;
 costEstimationRun?: CostEstimationRunSummaryDto | null;
 landSizeCategory?: string;
 landSizePerches?: number;
 bedrooms?: number;
 bathrooms?: number;
 houseType?: string;
 requirements?: WorkflowRequirementsDto;
 validationResultJson?: string | null;
 architectDecisionDate?: string | null;
}

export interface DesignHistoryDto {
 designId: string;
 version: number;
 isCurrent: boolean;
 isPreferred: boolean;
 isArchived: boolean;
 isArchitectApproved?: boolean;
 topology: string | null;
 bedrooms: number;
 bathrooms: number;
 floorCount: number;
 totalBuiltUpAreaSqft: number;
 foundationType: string;
 generationMode: string | null;
 selectedBasePlan: string | null;
 geometryFingerprint: string | null;
 createdAt: string;
 suitabilityScore: number | null;
 architecturalQualityScore: number | null;
 previewRooms: { roomType: string; floor: number; x: number; y: number; width: number; length: number }[];
}

export interface WorkflowDesignHistoryDto {
 workflowId: string;
 status: string;
 preferredHouseDesignId: string | null;
 createdAt: string;
 designs: DesignHistoryDto[];
 projectId?: string;
 architectReviewStatus?: string | null;
 architectFeedback?: string | null;
}

export interface StartDesignRequest {
 landSizeCategory: 'small' | 'medium';
 landSizePerches: number;
 bedrooms: number;
 bathrooms: number;
 houseType: 'simple' | 'modern';
 targetDurationDays?: number;
}

export const workflowService = {
 startDesign: async (request: StartDesignRequest): Promise<{ workflowId: string }> => {
  const response = await apiClient.post('/ai-generation/generate', request);
  return response.data;
 },
 getWorkflowStatus: async (id: string, designId?: string): Promise<WorkflowStatusResponseDto> => {
  const response = await apiClient.get<WorkflowStatusResponseDto>(`/workflows/${id}/status`, {
   params: designId ? { designId } : undefined,
  });
  return response.data;
 },
 checkCompatibility: async (payload: any) =>
  (await apiClient.post('/design-compatibility/options', payload)).data,
 getMyDesigns: async (config?: AxiosRequestConfig): Promise<WorkflowDesignHistoryDto[]> =>
  (await apiClient.get<WorkflowDesignHistoryDto[]>('/workflows/designs', config)).data,
 getDesigns: async (id: string): Promise<WorkflowDesignHistoryDto> =>
  (await apiClient.get<WorkflowDesignHistoryDto>(`/workflows/${id}/designs`)).data,
 selectDesign: async (workflowId: string, designId: string) =>
  (await apiClient.post(`/workflows/${workflowId}/designs/${designId}/select`)).data,
 clearDesignSelection: async (workflowId: string) =>
  (await apiClient.delete(`/workflows/${workflowId}/design-selection`)).data,
 removeDesign: async (workflowId: string, designId: string) =>
  (await apiClient.delete(`/workflows/${workflowId}/designs/${designId}`)).data,
 submitArchitectReview: async (workflowId: string, designId: string) =>
  (await apiClient.post(`/workflows/${workflowId}/submit-architect-review/${designId}`)).data,
 regenerateDesign: async (workflowId: string, designId: string) =>
  (await apiClient.post(`/workflows/${workflowId}/regenerate/${designId}`)).data,
 approveWorkflow: async (
  id: string,
  decision: 'approve' | 'reject' | 'request_revision',
  notes?: string,
 ) => {
  const response = await apiClient.post(`/workflows/${id}/approve`, {
   decision,
   revisionNotes: notes,
  });
  return response.data;
 },
 updateConstructionPlan: async (workflowId: string, planData: any) => {
  const response = await apiClient.put(`/workflows/${workflowId}/construction-plan`, planData);
  return response.data;
 },
 getDesignVisualization: async (designId: string, signal?: AbortSignal) => {
  const response = await apiClient.get(`/design/${designId}/visualization`, { signal });
  return response.data;
 },
};
