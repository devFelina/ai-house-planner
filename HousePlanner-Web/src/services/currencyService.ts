import apiClient from './apiClient';

export interface ExchangeRateResponse {
    baseCurrency: string;
    targetCurrency: string;
    rate: number;
    source: string;
    fetchedAt: string;
}

export const currencyService = {
    getExchangeRate: async (from = 'LKR', to = 'USD'): Promise<ExchangeRateResponse> => {
        const response = await apiClient.get<ExchangeRateResponse>(`/currency/rate?from=${from}&to=${to}`);
        return response.data;
    }
};
