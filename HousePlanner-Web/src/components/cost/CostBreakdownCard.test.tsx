import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CostBreakdownCard } from './CostBreakdownCard';
import { currencyService } from '../../services/currencyService';
import '@testing-library/jest-dom';

vi.mock('../../services/currencyService', () => ({
    currencyService: {
        getExchangeRate: vi.fn()
    }
}));

const mockCost = {
    materialCostLkr: 1000000,
    labourCostLkr: 500000,
    totalCostLkr: 1500000,
    budgetDeltaPercent: 95,
    formulaVersion: 'v1',
    appliedAreaSqft: 1000,
    terrainType: 'flat',
    estimatedAt: '2023-10-01T00:00:00Z',
    breakdown: [
        {
            category: 'material',
            costHead: 'Foundation',
            itemName: 'Concrete',
            unitCostLkr: 1000,
            appliedQuantity: 1000,
            terrainMultiplier: 1,
            sharePercent: 66.67,
            amountLkr: 1000000
        }
    ]
};

describe('CostBreakdownCard Currency Feature', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('defaults to LKR and shows original values', async () => {
        (currencyService.getExchangeRate as any).mockResolvedValue({ rate: 0.003 });
        
        render(<CostBreakdownCard cost={mockCost as any} />);
        
        expect(screen.getByText('LKR')).toHaveClass('bg-white');
        expect(screen.getAllByText('LKR 1,500,000').length).toBeGreaterThan(0);
        expect(screen.getAllByText('LKR 1,000,000').length).toBeGreaterThan(0);
    });

    it('converts to USD when USD is selected', async () => {
        (currencyService.getExchangeRate as any).mockResolvedValue({ rate: 0.003 });
        
        render(<CostBreakdownCard cost={mockCost as any} />);
        
        const usdButton = await screen.findByRole('button', { name: 'USD' });
        await waitFor(() => expect(usdButton).not.toBeDisabled());
        
        fireEvent.click(usdButton);
        
        expect(usdButton).toHaveClass('bg-white');
        expect(screen.getAllByText('USD $4,500').length).toBeGreaterThan(0); // 1,500,000 * 0.003
        expect(screen.getAllByText('USD $3,000').length).toBeGreaterThan(0); // 1,000,000 * 0.003
    });

    it('disables USD button if currency API fails', async () => {
        (currencyService.getExchangeRate as any).mockRejectedValue(new Error('Network error'));
        
        render(<CostBreakdownCard cost={mockCost as any} />);
        
        const usdButton = await screen.findByRole('button', { name: 'USD' });
        expect(usdButton).toBeDisabled();
        
        await waitFor(() => {
            expect(screen.getByText('USD conversion temporarily unavailable.')).toBeInTheDocument();
        });
        
        // Still shows LKR
        expect(screen.getAllByText('LKR 1,500,000').length).toBeGreaterThan(0);
    });
});
