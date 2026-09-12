import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/approval_provider.dart';
import '../models/approval_models.dart';

class ApprovalView extends ConsumerStatefulWidget {
  final String workflowId;

  const ApprovalView({
    super.key,
    this.workflowId = '3fa85f64-5717-4562-b3fc-2c963f66afa6',
  });

  @override
  ConsumerState<ApprovalView> createState() => _ApprovalViewState();
}

class _ApprovalViewState extends ConsumerState<ApprovalView> {
  final _revisionController = TextEditingController();
  bool _isSubmitting = false;
  String? _errorMessage;
  String? _successMessage;
  String? _createdProjectId;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(approvalProvider.notifier).fetchWorkflowStatus(widget.workflowId));
  }

  @override
  void dispose() {
    _revisionController.dispose();
    super.dispose();
  }

  Future<void> _handleDecision(String decision) async {
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final response = await ref.read(approvalProvider.notifier).submitDecision(
            widget.workflowId,
            decision,
            revisionNotes: _revisionController.text.trim().isNotEmpty
                ? _revisionController.text.trim()
                : null,
          );

      if (mounted) {
        setState(() {
          _successMessage = response.message;
          _createdProjectId = response.projectId;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncWorkflow = ref.watch(approvalProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Project Approval'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: asyncWorkflow.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error: $err')),
        data: (workflow) {
          final status = workflow?.approvalStatus ?? 'pending';
          final validationPassed = workflow?.validationPassed ?? true;
          final isApproved = status == 'approved';
          final isRejected = status == 'rejected';

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header Status Card
                Card(
                  elevation: 2,
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Approval Status',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.grey),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              status.toUpperCase().replaceAll('_', ' '),
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                                color: isApproved
                                    ? Colors.green
                                    : isRejected
                                        ? Colors.red
                                        : Colors.indigo,
                              ),
                            ),
                          ],
                        ),
                        Chip(
                          avatar: Icon(
                            validationPassed ? Icons.check_circle : Icons.warning,
                            color: validationPassed ? Colors.green : Colors.red,
                            size: 18,
                          ),
                          label: Text(
                            validationPassed ? 'Validation PASSED' : 'Validation FAILED',
                            style: TextStyle(
                              fontSize: 12,
                              color: validationPassed ? Colors.green.shade800 : Colors.red.shade800,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          backgroundColor: validationPassed ? Colors.green.shade50 : Colors.red.shade50,
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // Notifications
                if (_errorMessage != null)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      border: Border.all(color: Colors.red.shade200),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(_errorMessage!, style: TextStyle(color: Colors.red.shade900)),
                  ),

                if (_successMessage != null)
                  Container(
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: Colors.green.shade50,
                      border: Border.all(color: Colors.green.shade200),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_successMessage!, style: TextStyle(color: Colors.green.shade900, fontWeight: FontWeight.bold)),
                        if (_createdProjectId != null) ...[
                          const SizedBox(height: 8),
                          Text('Project ID: $_createdProjectId', style: const TextStyle(fontSize: 12)),
                          const SizedBox(height: 8),
                          ElevatedButton.icon(
                            onPressed: () {
                              Navigator.pushNamed(
                                context,
                                '/project_status',
                                arguments: _createdProjectId,
                              );
                            },
                            icon: const Icon(Icons.arrow_forward),
                            label: const Text('View Project Status'),
                          ),
                        ],
                      ],
                    ),
                  ),

                const SizedBox(height: 8),

                // Plan & Cost Summary Card
                Card(
                  elevation: 1,
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'House Plan & Safety Summary',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        const Divider(height: 24),
                        const ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text('Project Concept'),
                          subtitle: Text('Modern Minimalist Eco-Villa'),
                          trailing: Icon(Icons.home, color: Colors.indigo),
                        ),
                        const ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text('Estimated Total Cost'),
                          subtitle: Text('LKR 12,500,000 (Within 10% budget tolerance)'),
                          trailing: Icon(Icons.attach_money, color: Colors.green),
                        ),
                        const ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text('Design Specifications'),
                          subtitle: Text('4 Bedrooms, 3 Bathrooms • 2,450 sq ft • Ground coverage compliant'),
                          trailing: Icon(Icons.rule, color: Colors.indigo),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                // Actions Card
                Card(
                  elevation: 1,
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Approval Decision',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _revisionController,
                          maxLines: 3,
                          enabled: !isApproved && !isRejected && !_isSubmitting,
                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                            labelText: 'Revision / Rejection Notes (Optional)',
                            hintText: 'Enter feedback for architect/design revisions...',
                          ),
                        ),
                        const SizedBox(height: 16),
                        if (_isSubmitting)
                          const Center(child: CircularProgressIndicator())
                        else ...[
                          ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.green.shade600,
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                            onPressed: (isApproved || !validationPassed)
                                ? null
                                : () => _handleDecision('approve'),
                            icon: const Icon(Icons.check),
                            label: const Text('Approve & Create Project'),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton.icon(
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.red.shade700,
                                    side: BorderSide(color: Colors.red.shade300),
                                  ),
                                  onPressed: isRejected ? null : () => _handleDecision('reject'),
                                  icon: const Icon(Icons.close),
                                  label: const Text('Reject'),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: isApproved ? null : () => _handleDecision('request_revision'),
                                  icon: const Icon(Icons.replay),
                                  label: const Text('Request Revision'),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
