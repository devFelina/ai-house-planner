import apiClient from './apiClient';
import type { PricingItem, UpdatePricingItemRequest } from '../types/pricing.types';

/**
 * Pricing Service
 * Wraps the HousePlanner.API pricing endpoints.
 * Uses the shared apiClient (baseURL already includes /api/v1).
 */
const pricingService = {
  /**
   * GET /pricing
   * Fetches all pricing items from the database.
   * This endpoint is public (no [Authorize] required).
   */
  getAll: async (): Promise<PricingItem[]> => {
    const response = await apiClient.get<PricingItem[]>('/pricing');
    return response.data;
  },

  /**
   * PUT /pricing/{id}
   * Updates a single pricing item's unit cost and terrain multipliers.
   *
   * ⚠ INTEGRATION DEPENDENCY: This endpoint requires [Authorize(Roles = "Contractor")].
   * The shared ASP.NET JWT authentication scheme has not yet been implemented by Member 1.
   * Until that token exchange is wired end-to-end, this call will return 401 Unauthorized.
   * Do NOT remove the [Authorize] attribute on the backend.
   */
  update: async (id: number, body: UpdatePricingItemRequest): Promise<PricingItem> => {
    const response = await apiClient.put<PricingItem>(`/pricing/${id}`, body);
    return response.data;
  },
};

export default pricingService;
