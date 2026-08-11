import React from 'react';
import useAuth from '../features/auth/useAuth';
import Card from '../components/common/Card';
import { 
  Compass, 
  Layers, 
  Map, 
  DollarSign, 
  Briefcase, 
  Activity, 
  TrendingUp, 
  ArrowRight 
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  const isArchitect = user.role === 'Architect';

  // Mock dashboard data
  const stats = isArchitect 
    ? [
        { label: 'Active Projects', value: '12', icon: Briefcase, color: 'text-indigo-600 bg-indigo-50' },
        { label: 'Blueprints Drafted', value: '48', icon: Layers, color: 'text-sky-600 bg-sky-50' },
        { label: 'Render Quality Index', value: '98%', icon: Activity, color: 'text-emerald-600 bg-emerald-50' },
      ]
    : [
        { label: 'Active Bids', value: '7', icon: Briefcase, color: 'text-indigo-600 bg-indigo-50' },
        { label: 'Total Value Managed', value: '$2.4M', icon: DollarSign, color: 'text-emerald-600 bg-emerald-50' },
        { label: 'Active Crew Members', value: '34', icon: Activity, color: 'text-amber-600 bg-amber-50' },
      ];

  const recentItems = isArchitect
    ? [
        { title: 'Villa Paradiso - Phase 2', date: 'Updated 2 hours ago', status: 'In Review' },
        { title: 'Oakwood Residence - Concept', date: 'Updated 1 day ago', status: 'Draft' },
        { title: 'Urban Loft Renovations', date: 'Updated 3 days ago', status: 'Approved' },
      ]
    : [
        { title: 'Material Supply: Steel Girders', date: 'Due tomorrow', status: 'Pending Delivery' },
        { title: 'Villa Paradiso - Cost Audit', date: 'Updated 4 hours ago', status: 'Submitted' },
        { title: 'Bridge Street Excavation Bid', date: 'Updated 2 days ago', status: 'Under Review' },
      ];

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-950 tracking-tight">
          Welcome back, {isArchitect ? 'Architect' : 'Contractor'}
        </h1>
        <p className="text-sm text-zinc-500">
          Here is an overview of your design workspace and active projects.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className="flex items-center gap-4">
              <div className={`p-3.5 rounded-xl ${stat.color}`}>
                <Icon size={20} />
              </div>
              <div>
                <p className="text-xs text-zinc-500 font-semibold tracking-wide uppercase">{stat.label}</p>
                <h4 className="text-2xl font-bold text-zinc-950 mt-1 leading-none">{stat.value}</h4>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Main Grid content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2/3 width) - Workspaces & Tools */}
        <div className="lg:col-span-2 space-y-6">
          <Card title="Quick Actions" subtitle="Frequently used design tools & estimators">
            {isArchitect ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="group border border-zinc-100 hover:border-indigo-100 hover:bg-indigo-50/10 rounded-xl p-4 transition-all duration-200 cursor-pointer flex gap-4">
                  <div className="bg-indigo-50 p-2.5 rounded-lg text-indigo-600 shrink-0">
                    <Compass size={20} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-zinc-900 group-hover:text-indigo-600 flex items-center gap-1.5">
                      New 3D Sketch <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </h4>
                    <p className="text-xs text-zinc-500 mt-1">Start sketching custom layouts with AI placement assistants.</p>
                  </div>
                </div>

                <div className="group border border-zinc-100 hover:border-indigo-100 hover:bg-indigo-50/10 rounded-xl p-4 transition-all duration-200 cursor-pointer flex gap-4">
                  <div className="bg-sky-50 p-2.5 rounded-lg text-sky-600 shrink-0">
                    <Map size={20} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-zinc-900 group-hover:text-indigo-600 flex items-center gap-1.5">
                      Blueprint Editor <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </h4>
                    <p className="text-xs text-zinc-500 mt-1">Refine schematic blueprint vector lines and specify walls.</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="group border border-zinc-100 hover:border-indigo-100 hover:bg-indigo-50/10 rounded-xl p-4 transition-all duration-200 cursor-pointer flex gap-4">
                  <div className="bg-indigo-50 p-2.5 rounded-lg text-indigo-600 shrink-0">
                    <DollarSign size={20} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-zinc-900 group-hover:text-indigo-600 flex items-center gap-1.5">
                      Calculate Bill of Materials <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </h4>
                    <p className="text-xs text-zinc-500 mt-1">Estimate total material volumes and current market costs.</p>
                  </div>
                </div>

                <div className="group border border-zinc-100 hover:border-indigo-100 hover:bg-indigo-50/10 rounded-xl p-4 transition-all duration-200 cursor-pointer flex gap-4">
                  <div className="bg-emerald-50 p-2.5 rounded-lg text-emerald-600 shrink-0">
                    <TrendingUp size={20} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-zinc-900 group-hover:text-indigo-600 flex items-center gap-1.5">
                      Procurement Log <ArrowRight size={14} className="opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </h4>
                    <p className="text-xs text-zinc-500 mt-1">Track supplier deliveries, timelines, and payment stages.</p>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Right Column (1/3 width) - Recent Activity */}
        <div>
          <Card title="Recent Activity" subtitle="Updates on your local workspace">
            <ul className="space-y-4">
              {recentItems.map((item, index) => (
                <li key={index} className="flex flex-col gap-1 text-sm border-b border-zinc-100 pb-3 last:border-0 last:pb-0">
                  <span className="font-medium text-zinc-800">{item.title}</span>
                  <div className="flex items-center justify-between text-xs text-zinc-400 mt-0.5">
                    <span>{item.date}</span>
                    <span className="bg-zinc-100 text-zinc-600 font-semibold px-2 py-0.5 rounded text-[10px] uppercase">
                      {item.status}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
