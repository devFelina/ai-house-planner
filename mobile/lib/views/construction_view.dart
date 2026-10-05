import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/network/api_client.dart';
import '../core/theme/app_tokens.dart';
import '../models/cost_summary.dart';
import '../widgets/app_card.dart';
import '../widgets/cost_breakdown_card.dart';
import '../widgets/app_buttons.dart';
import '../widgets/status_pill.dart';
import '../widgets/section_header.dart';

class ConstructionView extends ConsumerStatefulWidget {
  const ConstructionView({super.key});

  @override
  ConsumerState<ConstructionView> createState() => _ConstructionViewState();
}

class _ConstructionViewState extends ConsumerState<ConstructionView> {
  bool _isLoading = true;
  String _error = '';
  Map<String, dynamic>? _overview;
  List<dynamic> _designs = [];
  List<dynamic> _constructors = [];
  String? _selectedDesign;
  String? _message;
  String? _requestingConstructor;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = '';
    });
    try {
      final overviewRes = await ApiClient.instance.get('/customer/construction');
      final designsRes = await ApiClient.instance.get('/customer/construction/approved-designs');
      
      final overview = overviewRes.data;
      final designs = designsRes.data as List<dynamic>;
      
      setState(() {
        _overview = overview;
        _designs = designs;
        if (_selectedDesign == null && designs.isNotEmpty) {
          _selectedDesign = designs[0]['designId'];
        }
      });

      ApiClient.instance.get('/customer/construction/constructors').then((res) {
        if (mounted) {
          setState(() {
            _constructors = res.data as List<dynamic>;
          });
        }
      }).catchError((_) {});
    } catch (e) {
      if (mounted) setState(() => _error = 'Failed to load construction data.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _requestConstructor(String constructorId) async {
    if (_selectedDesign == null || _requestingConstructor != null) return;
    setState(() => _requestingConstructor = constructorId);
    try {
      await ApiClient.instance.post('/customer/construction/requests', data: {
        'houseDesignId': _selectedDesign,
        'constructorId': constructorId,
      });
      setState(() => _message = 'Construction request sent successfully.');
      await _loadData();
    } catch (e) {
      setState(() => _message = 'Could not send construction request.');
    } finally {
      if (mounted) setState(() => _requestingConstructor = null);
    }
  }

  Future<void> _cancelProject(String projectId) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Cancel Construction'),
        content: const Text('Cancel this construction project?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('No')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Yes')),
        ],
      )
    );
    if (confirm != true) return;

    try {
      await ApiClient.instance.patch('/customer/construction/projects/$projectId/cancel');
      setState(() => _message = 'Construction project cancelled.');
      await _loadData();
    } catch (e) {
      setState(() => _message = 'Could not cancel project.');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    
    if (_error.isNotEmpty) {
      return Scaffold(body: Center(child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(_error, style: const TextStyle(color: Colors.red)),
          PrimaryButton(label: 'Retry', onPressed: _loadData)
        ],
      )));
    }

    final activeProjects = _overview?['activeProjects'] as List<dynamic>? ?? [];
    final pendingRequests = _overview?['pendingRequests'] as List<dynamic>? ?? [];
    final selectedDesignData = _designs.firstWhere((d) => d['designId'] == _selectedDesign, orElse: () => null);

    return Scaffold(
      backgroundColor: AppTokens.bg,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 24.0),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  // Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Construction', style: Theme.of(context).textTheme.headlineSmall),
                            const SizedBox(height: 4),
                            const Text('Choose a constructor and track construction.', style: TextStyle(fontSize: 14, color: AppTokens.textSecondary)),
                          ],
                        ),
                      ),
                      Container(
                        decoration: BoxDecoration(color: Colors.white, border: Border.all(color: AppTokens.line), borderRadius: BorderRadius.circular(12)),
                        child: IconButton(icon: const Icon(Icons.refresh, size: 20, color: AppTokens.textPrimary), onPressed: _loadData),
                      )
                    ],
                  ),
                  const SizedBox(height: 24),

                  if (_message != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      margin: const EdgeInsets.only(bottom: 24),
                      decoration: BoxDecoration(color: AppTokens.statusApprovedBg, borderRadius: BorderRadius.circular(8)),
                      child: Text(_message!, style: const TextStyle(color: AppTokens.statusApprovedText, fontWeight: FontWeight.w600)),
                    ),

                  // Active Construction
                  if (activeProjects.isNotEmpty) ...[
                    const SectionHeader(title: 'Active Construction'),
                    ...activeProjects.map((p) => _buildActiveProject(p)),
                    const SizedBox(height: 32),
                  ],

                  // Pending Requests
                  if (pendingRequests.isNotEmpty) ...[
                    const SectionHeader(title: 'Pending Requests'),
                    ...pendingRequests.map((r) => AppCard(
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(color: AppTokens.statusPendingBg, borderRadius: BorderRadius.circular(AppTokens.radiusIconTile)),
                            child: const Icon(Icons.access_time, color: AppTokens.statusPendingText, size: 20),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Waiting for ${r['constructorName']}', style: Theme.of(context).textTheme.titleSmall),
                                Text('Requested on ${r['requestedAt'].toString().substring(0, 10)}', style: const TextStyle(color: AppTokens.textSecondary, fontSize: 13)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    )),
                    const SizedBox(height: 32),
                  ],

                  // Start Construction section
                  const SectionHeader(title: 'Start Construction'),
                  AppCard(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (_designs.isEmpty)
                          const Text('No approved designs are available yet.', style: TextStyle(color: AppTokens.textSecondary))
                        else ...[
                          // Design selection
                          if (_selectedDesign != null && selectedDesignData != null)
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(color: AppTokens.bg, borderRadius: BorderRadius.circular(AppTokens.radiusContainer)),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('SELECTED DESIGN', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTokens.textSecondary, letterSpacing: 0.5)),
                                  const SizedBox(height: 8),
                                  Text(selectedDesignData['title'] ?? 'Design', style: Theme.of(context).textTheme.titleMedium),
                                  Text('${selectedDesignData['bedrooms']} Bedrooms • ${selectedDesignData['bathrooms']} Bathrooms', style: const TextStyle(color: AppTokens.textSecondary, fontSize: 13)),
                                  const SizedBox(height: 16),
                                  SizedBox(
                                    width: double.infinity,
                                    child: SecondaryButton(label: 'Change design', onPressed: () => setState(() => _selectedDesign = null)),
                                  ),
                                ],
                              ),
                            )
                          else
                            Column(
                              children: _designs.map((d) => Padding(
                                padding: const EdgeInsets.only(bottom: 8.0),
                                child: InkWell(
                                  onTap: () => setState(() => _selectedDesign = d['designId']),
                                  child: Container(
                                    padding: const EdgeInsets.all(16),
                                    decoration: BoxDecoration(border: Border.all(color: AppTokens.line), borderRadius: BorderRadius.circular(12)),
                                    child: Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(d['title'], style: const TextStyle(fontWeight: FontWeight.w600)),
                                            Text('${d['bedrooms']} Beds • ${d['bathrooms']} Baths', style: const TextStyle(color: AppTokens.textSecondary, fontSize: 13)),
                                          ],
                                        ),
                                        const Icon(Icons.chevron_right, color: AppTokens.textSecondary),
                                      ],
                                    ),
                                  ),
                                ),
                              )).toList(),
                            ),

                          if (_selectedDesign != null && selectedDesignData != null) ...[
                            const SizedBox(height: 24),
                            const Text('2. Review estimate', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: AppTokens.textPrimary)),
                            const SizedBox(height: 8),
                            CostBreakdownCard(
                              key: ValueKey('cost-$_selectedDesign'),
                              cost: CostSummary.tryParse(selectedDesignData['cost']),
                            ),

                            const SizedBox(height: 24),
                            const Text('3. Choose a constructor', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: AppTokens.textPrimary)),
                            const SizedBox(height: 12),
                            ..._constructors.map((c) => Padding(
                              padding: const EdgeInsets.only(bottom: 12.0),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(c['name'], style: const TextStyle(fontWeight: FontWeight.w600)),
                                  ),
                                  PrimaryButton(
                                    label: _requestingConstructor == c['id'] ? 'Sending...' : 'Send request',
                                    onPressed: _requestingConstructor != null ? null : () => _requestConstructor(c['id']),
                                  ),
                                ],
                              ),
                            )),
                          ],
                        ],
                      ],
                    ),
                  ),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveProject(dynamic p) {
    final design = _designs.firstWhere((d) => d['designId'] == p['houseDesignId'], orElse: () => null);
    final title = design != null ? design['title'] : 'Design v${p['designVersion']}';

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: AppCard(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                StatusPill.active('In Progress'),
              ],
            ),
            const SizedBox(height: 4),
            Text(p['constructorName'], style: const TextStyle(color: AppTokens.textSecondary, fontWeight: FontWeight.w500)),
            const Padding(padding: EdgeInsets.symmetric(vertical: 16), child: Divider(height: 1)),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('CURRENT PHASE', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppTokens.textSecondary, letterSpacing: 0.5)),
                const SizedBox(height: 4),
                Text(p['currentPhase'] ?? 'Awaiting update', style: Theme.of(context).textTheme.titleSmall),
              ],
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(child: SecondaryButton(label: 'View Progress', onPressed: () => context.go('/dashboard/construction/${p['id']}'))),
                const SizedBox(width: 12),
                TextButton(
                  onPressed: () => _cancelProject(p['id']),
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                  child: const Text('Cancel', style: TextStyle(fontWeight: FontWeight.w600)),
                ),
              ],
            )
          ],
        ),
      ),
    );
  }
}
