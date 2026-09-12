/**
 * Matches the backend TerrainMultiplierData owned type.
 * Properties use camelCase as serialised by ASP.NET Core's default JSON policy.
 */
export interface TerrainMultiplier {
  flat: number;
  hillside: number;
  coastal: number;
}

/**
 * Matches the backend PricingData entity returned by GET /pricing.
 */
export interface PricingItem {
  id: number;
  itemName: string;
  category: string;
  unitCostLkr: number;
  unit: string;
  terrainMultiplier: TerrainMultiplier;
  updatedAt: string; // ISO-8601 DateTimeOffset
}

/**
 * Request body sent to PUT /pricing/{id}.
 * Mirrors PricingUpdateDto on the backend.
 */
export interface UpdatePricingItemRequest {
  unitCostLkr: number;
  terrainMultiplier: TerrainMultiplier;
}
