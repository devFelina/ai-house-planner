import React, { useState, useMemo } from 'react';
import {
  Search,
  Pencil,
  X,
  Save,
  Tag,
  Box,
  Layers,
  PackageCheck,
  AlertCircle,
  TrendingUp,
  CalendarDays,
  DollarSign,
} from 'lucide-react';

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

type PricingCategory =
  | 'Structural'
  | 'Finishing'
  | 'Labour'
  | 'MEP'
  | 'Landscaping';

interface PricingItem {
  id: string;
  name: string;
  category: PricingCategory;
  unit: string;
  unitCost: number;
  flatMultiplier: number;
  hillsideMultiplier: number;
  coastalMultiplier: number;
  lastUpdated: string;
}

interface EditFormState {
  unitCost: string;
  flatMultiplier: string;
  hillsideMultiplier: string;
  coastalMultiplier: string;
}

interface ValidationErrors {
  unitCost?: string;
  flatMultiplier?: string;
  hillsideMultiplier?: string;
  coastalMultiplier?: string;
}

// ─────────────────────────────────────────────
// Mock Data
// ─────────────────────────────────────────────

const INITIAL_PRICING_ITEMS: PricingItem[] = [
  {
    id: 'p-001',
    name: 'Portland Cement (50 kg)',
    category: 'Structural',
    unit: 'Bag',
    unitCost: 2150,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.18,
    coastalMultiplier: 1.12,
    lastUpdated: '2026-08-20',
  },
  {
    id: 'p-002',
    name: 'Tor Steel — 16mm Rebar',
    category: 'Structural',
    unit: 'MT',
    unitCost: 185000,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.22,
    coastalMultiplier: 1.15,
    lastUpdated: '2026-08-15',
  },
  {
    id: 'p-003',
    name: 'Ceramic Floor Tile (600x600)',
    category: 'Finishing',
    unit: 'sqft',
    unitCost: 320,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.10,
    coastalMultiplier: 1.08,
    lastUpdated: '2026-09-01',
  },
  {
    id: 'p-004',
    name: 'Granite Flooring',
    category: 'Finishing',
    unit: 'sqft',
    unitCost: 650,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.12,
    coastalMultiplier: 1.09,
    lastUpdated: '2026-09-01',
  },
  {
    id: 'p-005',
    name: 'Skilled Construction Labour',
    category: 'Labour',
    unit: 'Day',
    unitCost: 4500,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.30,
    coastalMultiplier: 1.20,
    lastUpdated: '2026-09-05',
  },
  {
    id: 'p-006',
    name: 'Unskilled Construction Labour',
    category: 'Labour',
    unit: 'Day',
    unitCost: 2800,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.25,
    coastalMultiplier: 1.15,
    lastUpdated: '2026-09-05',
  },
  {
    id: 'p-007',
    name: 'River Sand',
    category: 'Structural',
    unit: 'Cube',
    unitCost: 14500,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.20,
    coastalMultiplier: 1.10,
    lastUpdated: '2026-08-25',
  },
  {
    id: 'p-008',
    name: 'Electrical Wiring (PVC)',
    category: 'MEP',
    unit: 'm',
    unitCost: 285,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.08,
    coastalMultiplier: 1.14,
    lastUpdated: '2026-08-10',
  },
  {
    id: 'p-009',
    name: 'Plumbing — CPVC Pipe (20mm)',
    category: 'MEP',
    unit: 'm',
    unitCost: 420,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.10,
    coastalMultiplier: 1.18,
    lastUpdated: '2026-08-10',
  },
  {
    id: 'p-010',
    name: 'Interior Wall Paint (Dulux)',
    category: 'Finishing',
    unit: 'Litre',
    unitCost: 1650,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.05,
    coastalMultiplier: 1.07,
    lastUpdated: '2026-09-03',
  },
  {
    id: 'p-011',
    name: 'Lawn Turf Grass',
    category: 'Landscaping',
    unit: 'sqft',
    unitCost: 95,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.35,
    coastalMultiplier: 1.12,
    lastUpdated: '2026-08-30',
  },
  {
    id: 'p-012',
    name: 'Roof Sheet (Zinc Alum)',
    category: 'Structural',
    unit: 'Sheet',
    unitCost: 3200,
    flatMultiplier: 1.0,
    hillsideMultiplier: 1.15,
    coastalMultiplier: 1.22,
    lastUpdated: '2026-08-18',
  },
];

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

const CATEGORY_COLORS: Record<PricingCategory, string> = {
  Structural: 'bg-blue-50 text-blue-700 ring-1 ring-blue-100',
  Finishing: 'bg-violet-50 text-violet-700 ring-1 ring-violet-100',
  Labour: 'bg-amber-50 text-amber-700 ring-1 ring-amber-100',
  MEP: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100',
  Landscaping: 'bg-teal-50 text-teal-700 ring-1 ring-teal-100',
};

function formatCurrency(value: number): string {
  return `LKR ${value.toLocaleString('en-LK')}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function getLatestUpdate(items: PricingItem[]): string {
  const sorted = [...items].sort(
    (a, b) => new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime()
  );
  return sorted[0] ? formatDate(sorted[0].lastUpdated) : '-';
}

function parsePositiveFloat(value: string): number | null {
  const n = parseFloat(value);
  return isNaN(n) || n <= 0 ? null : n;
}

function validateEditForm(form: EditFormState): ValidationErrors {
  const errors: ValidationErrors = {};
  if (parsePositiveFloat(form.unitCost) === null)
    errors.unitCost = 'Must be a positive number.';
  if (parsePositiveFloat(form.flatMultiplier) === null)
    errors.flatMultiplier = 'Must be a positive number.';
  if (parsePositiveFloat(form.hillsideMultiplier) === null)
    errors.hillsideMultiplier = 'Must be a positive number.';
  if (parsePositiveFloat(form.coastalMultiplier) === null)
    errors.coastalMultiplier = 'Must be a positive number.';
  return errors;
}

// ─────────────────────────────────────────────
// SummaryCard sub-component
// ─────────────────────────────────────────────

interface SummaryCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ icon, label, value, sub }) => (
  <div className="bg-white rounded-2xl border border-slate-100 custom-shadow-sm px-6 py-5 flex items-center gap-4">
    <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-500">
      {icon}
    </div>
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-0.5">{label}</p>
      <p className="text-2xl font-bold text-slate-900 leading-tight">{value}</p>
      {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  </div>
);

// ─────────────────────────────────────────────
// MultiplierBadge sub-component
// ─────────────────────────────────────────────

interface MultiplierBadgeProps {
  value: number;
}

const MultiplierBadge: React.FC<MultiplierBadgeProps> = ({ value }) => {
  const isBase = value === 1.0;
  const isHigh = value >= 1.2;
  const cls = isBase
    ? 'text-slate-400 bg-slate-50 ring-1 ring-slate-100'
    : isHigh
    ? 'text-rose-600 bg-rose-50 ring-1 ring-rose-100'
    : 'text-indigo-600 bg-indigo-50 ring-1 ring-indigo-100';

  return (
    <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-bold font-mono ${cls}`}>
      x{value.toFixed(2)}
    </span>
  );
};

// ─────────────────────────────────────────────
// EditModal sub-component
// ─────────────────────────────────────────────

interface EditModalProps {
  item: PricingItem;
  onClose: () => void;
  onSave: (updated: PricingItem) => void;
}

const EditModal: React.FC<EditModalProps> = ({ item, onClose, onSave }) => {
  const [form, setForm] = useState<EditFormState>({
    unitCost: String(item.unitCost),
    flatMultiplier: String(item.flatMultiplier),
    hillsideMultiplier: String(item.hillsideMultiplier),
    coastalMultiplier: String(item.coastalMultiplier),
  });
  const [errors, setErrors] = useState<ValidationErrors>({});

  const handleChange = (field: keyof EditFormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSave = () => {
    const validationErrors = validateEditForm(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    onSave({
      ...item,
      unitCost: parseFloat(form.unitCost),
      flatMultiplier: parseFloat(form.flatMultiplier),
      hillsideMultiplier: parseFloat(form.hillsideMultiplier),
      coastalMultiplier: parseFloat(form.coastalMultiplier),
      lastUpdated: new Date().toISOString().slice(0, 10),
    });
  };

  const fields: { key: keyof EditFormState; label: string; help: string }[] = [
    {
      key: 'unitCost',
      label: 'Unit Cost (LKR)',
      help: 'Base cost per unit on flat terrain.',
    },
    {
      key: 'flatMultiplier',
      label: 'Flat Terrain Multiplier',
      help: 'Applied on standard flat-land projects. Usually 1.00.',
    },
    {
      key: 'hillsideMultiplier',
      label: 'Hillside Multiplier',
      help: 'Accounts for slope access, extra labour and material transport.',
    },
    {
      key: 'coastalMultiplier',
      label: 'Coastal Multiplier',
      help: 'Factors in corrosion-resistant materials and coastal logistics.',
    },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative bg-white rounded-3xl border border-slate-100 custom-shadow-lg w-full max-w-lg mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-8 pt-8 pb-6 border-b border-slate-100">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-bold tracking-[0.18em] text-indigo-500 uppercase mb-1">
                Edit Pricing
              </p>
              <h2 className="text-xl font-bold text-slate-900 leading-snug">{item.name}</h2>
              <div className="flex items-center gap-2 mt-2">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${CATEGORY_COLORS[item.category]}`}>
                  {item.category}
                </span>
                <span className="text-xs text-slate-400">per {item.unit}</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-50 transition-colors"
              aria-label="Close modal"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="px-8 py-6 space-y-5">
          {fields.map(({ key, label, help }) => (
            <div key={key}>
              <label
                className="block text-xs font-semibold text-slate-700 mb-1.5"
                htmlFor={`modal-${key}`}
              >
                {label}
              </label>
              <input
                id={`modal-${key}`}
                type="number"
                step="0.01"
                min="0"
                value={form[key]}
                onChange={handleChange(key)}
                className={`w-full bg-slate-50 border rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition-all focus:bg-white focus:ring-2 focus:ring-indigo-400/40 ${
                  errors[key]
                    ? 'border-red-300 ring-1 ring-red-200'
                    : 'border-slate-200 focus:border-indigo-300'
                }`}
              />
              {errors[key] ? (
                <p className="mt-1 flex items-center gap-1 text-[11px] text-red-500 font-medium">
                  <AlertCircle size={11} /> {errors[key]}
                </p>
              ) : (
                <p className="mt-1 text-[11px] text-slate-400">{help}</p>
              )}
            </div>
          ))}
        </div>

        {/* Modal Footer */}
        <div className="px-8 pb-7 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-600 border border-slate-200 bg-white hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 active:scale-[0.98] text-white transition-all custom-shadow-sm"
          >
            <Save size={14} />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────
// Main Page Component
// ─────────────────────────────────────────────

const TABLE_COLUMNS = [
  'Item Name',
  'Category',
  'Unit',
  'Unit Cost (LKR)',
  'Flat x',
  'Hillside x',
  'Coastal x',
  'Last Updated',
  '',
];

const PricingManagementPage: React.FC = () => {
  const [items, setItems] = useState<PricingItem[]>(INITIAL_PRICING_ITEMS);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<PricingCategory | 'All'>('All');
  const [editingItem, setEditingItem] = useState<PricingItem | null>(null);
  const [savedItemId, setSavedItemId] = useState<string | null>(null);

  const categories: Array<PricingCategory | 'All'> = [
    'All',
    'Structural',
    'Finishing',
    'Labour',
    'MEP',
    'Landscaping',
  ];

  const filteredItems = useMemo(() => {
    const q = search.toLowerCase().trim();
    return items.filter((item) => {
      const matchSearch =
        !q ||
        item.name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        item.unit.toLowerCase().includes(q);
      const matchCategory =
        selectedCategory === 'All' || item.category === selectedCategory;
      return matchSearch && matchCategory;
    });
  }, [items, search, selectedCategory]);

  const uniqueCategories = useMemo(
    () => [...new Set(items.map((i) => i.category))].length,
    [items]
  );

  const handleSave = (updated: PricingItem) => {
    setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
    setSavedItemId(updated.id);
    setEditingItem(null);
    setTimeout(() => setSavedItemId(null), 2500);
  };

  return (
    <div className="space-y-8">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold tracking-[0.2em] text-indigo-500 uppercase mb-2">
            Cost Estimator
          </p>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight mb-2">
            Pricing Management
          </h1>
          <p className="text-sm text-slate-400 font-light max-w-lg leading-relaxed">
            Manage the base unit costs and terrain multipliers used by the HousePlanner AI cost
            estimation system. Changes here are reflected in all future project cost calculations.
          </p>
        </div>
        <div className="flex-shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 text-xs font-semibold">
          <DollarSign size={14} />
          <span>LKR Pricing Table</span>
        </div>
      </div>

      {/* ── Summary Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <SummaryCard
          icon={<PackageCheck size={18} />}
          label="Pricing Items"
          value={String(items.length)}
          sub="Across all categories"
        />
        <SummaryCard
          icon={<Layers size={18} />}
          label="Categories"
          value={String(uniqueCategories)}
          sub="Structural, Labour, MEP..."
        />
        <SummaryCard
          icon={<CalendarDays size={18} />}
          label="Last Updated"
          value={getLatestUpdate(items)}
          sub="Most recent price change"
        />
      </div>

      {/* ── Filters & Table Card ── */}
      <div className="bg-white rounded-2xl border border-slate-100 custom-shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="px-6 py-4 border-b border-slate-50 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          {/* Search */}
          <div className="relative w-full sm:max-w-xs">
            <Search
              size={15}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              id="pricing-search"
              type="text"
              placeholder="Search items, categories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 outline-none focus:bg-white focus:border-indigo-300 focus:ring-2 focus:ring-indigo-400/30 transition-all"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                aria-label="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Category pill filters */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedCategory === cat
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-50 text-slate-500 border border-slate-200 hover:bg-slate-100 hover:text-slate-700'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px]">
            <thead>
              <tr className="border-b border-slate-100">
                {TABLE_COLUMNS.map((col, i) => (
                  <th
                    key={i}
                    className={`px-5 py-3.5 text-left text-[11px] font-bold tracking-wider text-slate-400 uppercase ${
                      i === 0 ? 'pl-6' : ''
                    } ${i === TABLE_COLUMNS.length - 1 ? 'pr-6 text-right' : ''}`}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-50">
              {filteredItems.length === 0 ? (
                /* Empty state */
                <tr>
                  <td colSpan={TABLE_COLUMNS.length} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center gap-3 text-slate-400">
                      <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center">
                        <Box size={20} className="text-slate-300" />
                      </div>
                      <p className="text-sm font-medium text-slate-500">No pricing items found</p>
                      <p className="text-xs text-slate-400">
                        Try adjusting your search or category filter.
                      </p>
                      <button
                        onClick={() => {
                          setSearch('');
                          setSelectedCategory('All');
                        }}
                        className="mt-1 text-xs font-semibold text-indigo-500 hover:text-indigo-700 transition-colors"
                      >
                        Clear filters
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredItems.map((item) => (
                  <tr
                    key={item.id}
                    className={`group transition-colors hover:bg-slate-50/70 ${
                      savedItemId === item.id ? 'bg-emerald-50/60' : ''
                    }`}
                  >
                    {/* Item Name */}
                    <td className="pl-6 pr-4 py-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center flex-shrink-0">
                          <Tag size={13} className="text-slate-400" />
                        </div>
                        <span className="text-sm font-semibold text-slate-800 group-hover:text-slate-950 transition-colors">
                          {item.name}
                        </span>
                        {savedItemId === item.id && (
                          <span className="ml-1 inline-flex items-center gap-1 text-[10px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded-full">
                            Saved
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Category */}
                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${CATEGORY_COLORS[item.category]}`}
                      >
                        {item.category}
                      </span>
                    </td>

                    {/* Unit */}
                    <td className="px-4 py-4">
                      <span className="text-xs text-slate-500 font-medium bg-slate-100 px-2 py-0.5 rounded-md">
                        {item.unit}
                      </span>
                    </td>

                    {/* Unit Cost */}
                    <td className="px-4 py-4">
                      <span className="text-sm font-bold text-slate-900">
                        {formatCurrency(item.unitCost)}
                      </span>
                    </td>

                    {/* Flat Multiplier */}
                    <td className="px-4 py-4">
                      <MultiplierBadge value={item.flatMultiplier} />
                    </td>

                    {/* Hillside Multiplier */}
                    <td className="px-4 py-4">
                      <MultiplierBadge value={item.hillsideMultiplier} />
                    </td>

                    {/* Coastal Multiplier */}
                    <td className="px-4 py-4">
                      <MultiplierBadge value={item.coastalMultiplier} />
                    </td>

                    {/* Last Updated */}
                    <td className="px-4 py-4">
                      <span className="text-xs text-slate-400 font-medium">
                        {formatDate(item.lastUpdated)}
                      </span>
                    </td>

                    {/* Edit Action */}
                    <td className="px-4 pr-6 py-4 text-right">
                      <button
                        onClick={() => setEditingItem(item)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-500 border border-slate-200 bg-white hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200 transition-all opacity-0 group-hover:opacity-100"
                        aria-label={`Edit ${item.name}`}
                      >
                        <Pencil size={11} />
                        Edit
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer */}
        {filteredItems.length > 0 && (
          <div className="px-6 py-3 border-t border-slate-50 flex items-center justify-between">
            <p className="text-xs text-slate-400">
              Showing{' '}
              <span className="font-semibold text-slate-600">{filteredItems.length}</span>
              {' '}of{' '}
              <span className="font-semibold text-slate-600">{items.length}</span>{' '}
              pricing items
            </p>
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <TrendingUp size={12} />
              <span>All prices in Sri Lankan Rupees (LKR)</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Edit Modal ── */}
      {editingItem && (
        <EditModal
          item={editingItem}
          onClose={() => setEditingItem(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
};

export default PricingManagementPage;
