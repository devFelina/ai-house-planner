
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/workflow_provider.dart';
import '../widgets/floor_plan_painter.dart';
import '../core/theme/app_tokens.dart';

class WorkflowStatusView extends ConsumerStatefulWidget {
  final String workflowId;
  const WorkflowStatusView({super.key, required this.workflowId});

  @override
  ConsumerState<WorkflowStatusView> createState() => _WorkflowStatusViewState();
}

class _WorkflowStatusViewState extends ConsumerState<WorkflowStatusView> {
  int _selectedTab = 0; // 0 = Floor Plan, 1 = Construction Plan
  int _selectedFloor = 1;
  bool _actionLoading = false;

  @override
  Widget build(BuildContext context) {
    final workflowState = ref.watch(workflowProvider(widget.workflowId));

    return Scaffold(
      backgroundColor: AppTokens.bg,
      appBar: AppBar(
        backgroundColor: AppTokens.bg,
        elevation: 0,
        leading: Padding(
          padding: const EdgeInsets.only(left: 16.0),
          child: IconButton(
            icon: const Icon(Icons.arrow_back, color: AppTokens.ink),
            onPressed: () {
              if (GoRouter.of(context).canPop()) {
                context.pop();
              } else {
                context.go('/dashboard');
              }
            },
            style: IconButton.styleFrom(
              backgroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: const BorderSide(color: AppTokens.line),
              ),
            ),
          ),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Design Review', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: AppTokens.ink)),
            Text('WF-${widget.workflowId.toUpperCase().take(8)}', style: const TextStyle(fontSize: 12, color: AppTokens.inkMute, fontFamily: 'monospace')),
          ],
        ),
        actions: [
          Center(
            child: Container(
              margin: const EdgeInsets.only(right: 16),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppTokens.amberSoft,
                borderRadius: BorderRadius.circular(AppTokens.radiusPill),
              ),
              child: const Text(
                'AWAITING APPROVAL',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5, color: AppTokens.amber),
              ),
            ),
          ),
        ],
      ),
      body: workflowState.when(
        loading: () => const Center(child: CircularProgressIndicator(color: AppTokens.ink)),
        error: (err, stack) => Center(child: Text('Error: $err', style: const TextStyle(color: AppTokens.red))),
        data: (data) {
          if (data.status == 'failed' || data.status == 'rejected') {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, color: AppTokens.red, size: 64),
                    const SizedBox(height: 16),
                    Text('Status: ${data.status.toUpperCase()}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTokens.ink)),
                    const SizedBox(height: 8),
                    Text(data.failureReason ?? 'The AI was unable to generate a plan that met all constraints.', 
                      style: const TextStyle(fontSize: 15, color: AppTokens.inkSoft), textAlign: TextAlign.center),
                    const SizedBox(height: 32),
                    ElevatedButton(
                      onPressed: () => context.pop(),
                      style: ElevatedButton.styleFrom(backgroundColor: AppTokens.ink, foregroundColor: Colors.white, minimumSize: const Size(double.infinity, 50), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      child: const Text('Try Again', style: TextStyle(fontWeight: FontWeight.w700)),
                    )
                  ],
                ),
              ),
            );
          }

          if (data.status == 'failed' || data.status == 'rejected') {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, color: AppTokens.red, size: 64),
                    const SizedBox(height: 16),
                    Text('Status: ${data.status.toUpperCase()}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTokens.ink)),
                    const SizedBox(height: 8),
                    Text(data.failureReason ?? 'The AI was unable to generate a plan that met all constraints.', 
                      style: const TextStyle(fontSize: 15, color: AppTokens.inkSoft), textAlign: TextAlign.center),
                    const SizedBox(height: 32),
                    ElevatedButton(
                      onPressed: () => context.pop(),
                      style: ElevatedButton.styleFrom(backgroundColor: AppTokens.ink, foregroundColor: Colors.white, minimumSize: const Size(double.infinity, 50), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      child: const Text('Try Again', style: TextStyle(fontWeight: FontWeight.w700)),
                    )
                  ],
                ),
              ),
            );
          }

          if (data.status == 'failed' || data.status == 'rejected') {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, color: AppTokens.red, size: 64),
                    const SizedBox(height: 16),
                    Text('Status: ${data.status.toUpperCase()}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTokens.ink)),
                    const SizedBox(height: 8),
                    Text(data.failureReason ?? 'The AI was unable to generate a plan that met all constraints.', 
                      style: const TextStyle(fontSize: 15, color: AppTokens.inkSoft), textAlign: TextAlign.center),
                    const SizedBox(height: 32),
                    ElevatedButton(
                      onPressed: () => context.pop(),
                      style: ElevatedButton.styleFrom(backgroundColor: AppTokens.ink, foregroundColor: Colors.white, minimumSize: const Size(double.infinity, 50), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      child: const Text('Try Again', style: TextStyle(fontWeight: FontWeight.w700)),
                    )
                  ],
                ),
              ),
            );
          }

          if (data.status == 'failed' || data.status == 'rejected') {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, color: AppTokens.red, size: 64),
                    const SizedBox(height: 16),
                    Text('Status: ${data.status.toUpperCase()}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTokens.ink)),
                    const SizedBox(height: 8),
                    Text(data.failureReason ?? 'The AI was unable to generate a plan that met all constraints.', 
                      style: const TextStyle(fontSize: 15, color: AppTokens.inkSoft), textAlign: TextAlign.center),
                    const SizedBox(height: 32),
                    ElevatedButton(
                      onPressed: () => context.pop(),
                      style: ElevatedButton.styleFrom(backgroundColor: AppTokens.ink, foregroundColor: Colors.white, minimumSize: const Size(double.infinity, 50), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      child: const Text('Try Again', style: TextStyle(fontWeight: FontWeight.w700)),
                    )
                  ],
                ),
              ),
            );
          }

          final isCompleted = data.status == 'completed' || data.status == 'awaiting_approval' || data.status == 'design_generated' || data.status == 'awaiting_architect_review';
          if (!isCompleted) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const CircularProgressIndicator(color: AppTokens.accent),
                  const SizedBox(height: 24),
                  const Text('AI is orchestrating your design...', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTokens.ink)),
                  const SizedBox(height: 8),
                  Text('Status: ${data.status.toUpperCase()}', style: const TextStyle(color: AppTokens.inkMute)),
                ],
              ),
            );
          }

          final design = data.design;
          if (design == null) return const Center(child: Text('Design data missing'));

          // Normalize rooms
          final List<RoomLayout> rooms = (design['rooms'] as List<dynamic>?)?.map((r) => RoomLayout.fromJson(r as Map<String, dynamic>)).toList() ?? [];

          return Column(
            children: [
              // Segmented Tabs
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFEFEF),
                    borderRadius: BorderRadius.circular(AppTokens.radiusPill),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _selectedTab = 0),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: _selectedTab == 0 ? Colors.white : Colors.transparent,
                              borderRadius: BorderRadius.circular(AppTokens.radiusPill),
                              boxShadow: _selectedTab == 0 ? [const BoxShadow(color: Color(0x11000000), blurRadius: 4, offset: Offset(0, 2))] : [],
                            ),
                            child: Center(
                              child: Text('Floor Plan', style: TextStyle(
                                fontSize: 13,
                                fontWeight: _selectedTab == 0 ? FontWeight.w700 : FontWeight.w600,
                                color: _selectedTab == 0 ? AppTokens.ink : AppTokens.inkMute,
                              )),
                            ),
                          ),
                        ),
                      ),
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _selectedTab = 1),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: _selectedTab == 1 ? Colors.white : Colors.transparent,
                              borderRadius: BorderRadius.circular(AppTokens.radiusPill),
                              boxShadow: _selectedTab == 1 ? [const BoxShadow(color: Color(0x11000000), blurRadius: 4, offset: Offset(0, 2))] : [],
                            ),
                            child: Center(
                              child: Text('Construction Plan', style: TextStyle(
                                fontSize: 13,
                                fontWeight: _selectedTab == 1 ? FontWeight.w700 : FontWeight.w600,
                                color: _selectedTab == 1 ? AppTokens.ink : AppTokens.inkMute,
                              )),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              Expanded(
                child: _selectedTab == 0
                    ? _buildFloorPlanTab(design, rooms)
                    : _buildConstructionTab(data.constructionPlan),
              ),

              // Bottom Sticky Action Bar
              if (data.status == 'awaiting_architect_review')
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: const BoxDecoration(
                    color: AppTokens.bg,
                    border: Border(top: BorderSide(color: AppTokens.line)),
                  ),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: AppTokens.emeraldSoft,
                      borderRadius: BorderRadius.circular(AppTokens.radiusButton),
                      border: Border.all(color: AppTokens.emerald.withValues(alpha: 0.3)),
                    ),
                    child: const Center(
                      child: Text('Request sent to architecture successfully', style: TextStyle(color: AppTokens.emerald, fontWeight: FontWeight.bold)),
                    ),
                  ),
                )
              else
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: const BoxDecoration(
                    color: AppTokens.bg,
                    border: Border(top: BorderSide(color: AppTokens.line)),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ElevatedButton(
                        onPressed: _actionLoading ? null : () async {
                          setState(() => _actionLoading = true);
                          try {
                            await ref.read(workflowProvider(widget.workflowId).notifier).submitArchitectReview(design['designId']);
                            // Success message handled by UI state change now
                          } catch (e) {
                            if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()), backgroundColor: AppTokens.red));
                          } finally {
                            if (mounted) setState(() => _actionLoading = false);
                          }
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTokens.emerald,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTokens.radiusButton)),
                          minimumSize: const Size(double.infinity, 0),
                          elevation: 0,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            if (_actionLoading) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) else const Icon(Icons.send, size: 18),
                            const SizedBox(width: 8),
                            Text(_actionLoading ? 'Sending...' : 'Send Architecture Request', style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: _actionLoading ? null : () async {
                          setState(() => _actionLoading = true);
                          try {
                            await ref.read(workflowProvider(widget.workflowId).notifier).regenerateDesign(design['designId']);
                            if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Regenerating design...')));
                          } catch (e) {
                            if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()), backgroundColor: AppTokens.red));
                          } finally {
                            if (mounted) setState(() => _actionLoading = false);
                          }
                        },
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTokens.ink,
                          backgroundColor: Colors.white,
                          side: const BorderSide(color: AppTokens.line, width: 1.4),
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTokens.radiusButton)),
                          minimumSize: const Size(double.infinity, 0),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            if (_actionLoading) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: AppTokens.ink, strokeWidth: 2)) else const Icon(Icons.refresh, size: 18),
                            const SizedBox(width: 8),
                            Text(_actionLoading ? 'Generating...' : 'Generate Another Design', style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildFloorPlanTab(dynamic design, List<RoomLayout> rooms) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Column(
        children: [
          // Floor selector
          if (design['floorCount'] != null && design['floorCount'] > 1)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              child: Row(
                children: List.generate(design['floorCount'] as int, (index) {
                  final floor = index + 1;
                  final isSel = _selectedFloor == floor;
                  return GestureDetector(
                    onTap: () => setState(() => _selectedFloor = floor),
                    child: Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: isSel ? AppTokens.ink : Colors.white,
                        borderRadius: BorderRadius.circular(AppTokens.radiusPill),
                        border: Border.all(color: isSel ? AppTokens.ink : AppTokens.line),
                      ),
                      child: Text('Floor $floor', style: TextStyle(color: isSel ? Colors.white : AppTokens.ink, fontWeight: FontWeight.w600, fontSize: 12.5)),
                    ),
                  );
                }),
              ),
            ),
          
          // Canvas
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: Container(
              height: 320,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(AppTokens.radiusCardSolid),
                border: Border.all(color: AppTokens.line),
                boxShadow: const [
                  BoxShadow(color: Color(0x140B0B14), blurRadius: 16, offset: Offset(0, 8), spreadRadius: -8)
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(AppTokens.radiusCardSolid),
                child: InteractiveViewer(
                  minScale: 0.5,
                  maxScale: 4.0,
                  child: FloorPlanViewer(
                    rooms: rooms,
                    floorFilter: _selectedFloor,
                  ),
                ),
              ),
            ),
          ),

          // Specs Grid
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Row(
              children: [
                Expanded(child: _buildSpecTile('Terrain', design['terrainType']?.toString() ?? 'Flat / Urban')),
                const SizedBox(width: 12),
                Expanded(child: _buildSpecTile('Foundation', design['foundationType']?.toString() ?? 'Strip footing')),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Row(
              children: [
                Expanded(child: _buildSpecTile('Floors', '${design['floorCount'] ?? 1}')),
                const SizedBox(width: 12),
                Expanded(child: _buildSpecTile('Area', '${design['totalBuiltUpAreaSqft']?.toStringAsFixed(0) ?? 0} sqft')),
              ],
            ),
          ),
          
          // Rooms List
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: rooms.map((r) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    Container(width: 4, height: 24, decoration: BoxDecoration(color: AppTokens.accent, borderRadius: BorderRadius.circular(2))),
                    const SizedBox(width: 12),
                    Expanded(child: Text(r.name ?? r.roomType, style: const TextStyle(fontWeight: FontWeight.w600, color: AppTokens.ink, fontSize: 14))),
                    Text("${r.width.toStringAsFixed(0)}'×${r.length.toStringAsFixed(0)}' (F${r.floor})", style: const TextStyle(color: AppTokens.inkMute, fontSize: 12.5)),
                  ],
                ),
              )).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSpecTile(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      decoration: BoxDecoration(
        color: AppTokens.card,
        borderRadius: BorderRadius.circular(AppTokens.radiusSection),
        border: Border.all(color: AppTokens.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1.0, color: AppTokens.inkMute)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTokens.ink)),
        ],
      ),
    );
  }

  Widget _buildConstructionTab(dynamic plan) {
    if (plan == null) return const Center(child: Text('No timeline available.', style: TextStyle(color: AppTokens.inkMute)));

    final phases = plan['phases'] as List<dynamic>? ?? [];
    final summary = plan['project_summary'] as Map<String, dynamic>?;
    final totalDays = summary?['estimated_duration_days'] ?? 0;
    final months = (totalDays / 30).toStringAsFixed(1);
    final targetDuration = summary?['target_duration_days'];
    final terrainType = summary?['terrain_type'] ?? 'flat';
    final optimizationNotes = summary?['optimization_notes'] as String?;

    return ListView(
      padding: const EdgeInsets.all(24),
      physics: const BouncingScrollPhysics(),
      children: [
        // ── Header Card ──
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(AppTokens.radiusCardSolid),
            border: Border.all(color: AppTokens.line),
            boxShadow: const [BoxShadow(color: Color(0x0A000000), blurRadius: 12, offset: Offset(0, 4))],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Project Timeline Estimate',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTokens.ink),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'AI-generated construction roadmap based on architectural design',
                          style: TextStyle(fontSize: 12.5, color: AppTokens.inkMute),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '$totalDays',
                        style: const TextStyle(
                          fontSize: 36,
                          fontWeight: FontWeight.w900,
                          color: AppTokens.emerald,
                          height: 1,
                        ),
                      ),
                      Text(
                        'days',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppTokens.emerald.withValues(alpha: 0.7),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '(~$months months)',
                        style: const TextStyle(fontSize: 11, color: AppTokens.inkMute, fontStyle: FontStyle.italic),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 20),
              // Target Duration & Schedule Status
              Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTokens.line),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('TARGET DURATION', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 1.0, color: AppTokens.inkMute)),
                          const SizedBox(height: 6),
                          Text(targetDuration != null ? '$targetDuration days' : 'Not Provided', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTokens.ink)),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF0FDF4),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFBBF7D0)),
                      ),
                      child: const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('SCHEDULE STATUS', style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 1.0, color: AppTokens.inkMute)),
                          SizedBox(height: 6),
                          Text('ON SCHEDULE', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTokens.emerald)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 28),

        // ── Construction Phases Header ──
        const Text('Construction Phases', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppTokens.ink)),
        const SizedBox(height: 16),

        // ── Phase Cards ──
        ...phases.map((phase) {
          final phaseId = phase['id'] ?? 0;
          final phaseName = phase['name'] ?? '';
          final durationDays = phase['duration_days'] ?? 0;
          final startDay = phase['start_day'] ?? 0;
          final endDay = phase['end_day'] ?? 0;
          final dependencies = phase['dependencies'] as List<dynamic>? ?? [];

          String dependencyText;
          if (dependencies.isEmpty) {
            dependencyText = 'No dependencies';
          } else {
            dependencyText = 'Depends on: ${dependencies.join(', ')}';
          }

          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppTokens.radiusCardSolid),
              border: Border.all(color: AppTokens.line),
              boxShadow: const [BoxShadow(color: Color(0x08000000), blurRadius: 8, offset: Offset(0, 3))],
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // Phase Number
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6366F1), Color(0xFF818CF8)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    '$phaseId',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14),
                  ),
                ),
                const SizedBox(width: 16),
                // Phase Info
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        phaseName,
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5, color: AppTokens.ink),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        dependencyText,
                        style: TextStyle(
                          color: dependencies.isEmpty ? AppTokens.inkSoft : AppTokens.accent,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                // Duration & Day Range
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '$durationDays days',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: AppTokens.ink),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Day $startDay – $endDay',
                      style: const TextStyle(fontSize: 11.5, color: AppTokens.accent, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ],
            ),
          );
        }),
        const SizedBox(height: 28),

        // ── Critical Path ──
        const Text('Critical Path', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: AppTokens.ink)),
        const SizedBox(height: 14),
        SizedBox(
          height: 42,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            itemCount: phases.length,
            separatorBuilder: (_, _) => const Padding(
              padding: EdgeInsets.symmetric(horizontal: 4),
              child: Icon(Icons.arrow_forward_ios, size: 10, color: AppTokens.inkSoft),
            ),
            itemBuilder: (context, index) {
              final phase = phases[index];
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFEEF2FF), Color(0xFFE0E7FF)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(AppTokens.radiusPill),
                  border: Border.all(color: const Color(0xFFC7D2FE)),
                ),
                child: Text(
                  phase['name'] ?? '',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF4338CA)),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 28),

        // ── Optimization Notes ──
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: const Color(0xFFFEFCE8),
            borderRadius: BorderRadius.circular(AppTokens.radiusCardSolid),
            border: Border.all(color: const Color(0xFFFDE68A)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.lightbulb_outline, size: 16, color: AppTokens.amber),
                  SizedBox(width: 8),
                  Text('Optimization Notes', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AppTokens.ink)),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                optimizationNotes ?? 'Optimized schedule duration: $totalDays days by parallelizing finishing work.',
                style: const TextStyle(fontSize: 12.5, color: Color(0xFF78716C), height: 1.5),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // ── AI Assumptions ──
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: const Color(0xFFF8FAFC),
            borderRadius: BorderRadius.circular(AppTokens.radiusCardSolid),
            border: Border.all(color: AppTokens.line),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.smart_toy_outlined, size: 16, color: AppTokens.inkMute),
                  SizedBox(width: 8),
                  Text('AI Assumptions', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AppTokens.ink)),
                ],
              ),
              const SizedBox(height: 10),
              _buildAssumptionRow('Duration estimates are AI generated approximate planning estimates.'),
              const SizedBox(height: 6),
              _buildAssumptionRow('Normal working conditions assumed.'),
              const SizedBox(height: 6),
              _buildAssumptionRow('Terrain factored as: $terrainType.'),
            ],
          ),
        ),
        const SizedBox(height: 24),
      ],
    );
  }

  Widget _buildAssumptionRow(String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(top: 4),
          child: Icon(Icons.circle, size: 5, color: AppTokens.inkSoft),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontSize: 12, color: Color(0xFF78716C), height: 1.45),
          ),
        ),
      ],
    );
  }
}

extension StringExtension on String {
  String take(int count) {
    if (length <= count) return this;
    return substring(0, count);
  }
}
