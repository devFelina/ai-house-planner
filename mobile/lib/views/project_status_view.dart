import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/approval_provider.dart';
import '../models/approval_models.dart';

class ProjectStatusView extends ConsumerStatefulWidget {
  final String? projectId;

  const ProjectStatusView({
    super.key,
    this.projectId,
  });

  @override
  ConsumerState<ProjectStatusView> createState() => _ProjectStatusViewState();
}

class _ProjectStatusViewState extends ConsumerState<ProjectStatusView> {
  final _projectIdController = TextEditingController();
  ProjectTrackingModel? _project;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    if (widget.projectId != null && widget.projectId!.isNotEmpty) {
      _projectIdController.text = widget.projectId!;
      _loadProjectTracking(widget.projectId!);
    }
  }

  @override
  void dispose() {
    _projectIdController.dispose();
    super.dispose();
  }

  Future<void> _loadProjectTracking(String id) async {
    if (id.trim().isEmpty) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final data = await ref.read(approvalProvider.notifier).fetchProjectTracking(id.trim());
      if (mounted) {
        setState(() {
          _project = data;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _project = null;
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Check if arguments were passed via ModalRoute
    final routeArgs = ModalRoute.of(context)?.settings.arguments;
    if (routeArgs is String && _projectIdController.text.isEmpty) {
      _projectIdController.text = routeArgs;
      _loadProjectTracking(routeArgs);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Project Status & Handoff'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Search / Lookup Field
            Card(
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _projectIdController,
                        decoration: const InputDecoration(
                          hintText: 'Enter Project ID...',
                          border: InputBorder.none,
                          isDense: true,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.search),
                      onPressed: () => _loadProjectTracking(_projectIdController.text),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            if (_isLoading)
              const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator()))
            else if (_errorMessage != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  border: Border.all(color: Colors.red.shade200),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text('Notice: $_errorMessage', style: TextStyle(color: Colors.red.shade900)),
              )
            else if (_project != null) ...[
              Card(
                elevation: 2,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Approved Project Status',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      const Divider(height: 24),
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Project ID'),
                        subtitle: Text(_project!.projectId, style: const TextStyle(fontFamily: 'monospace')),
                      ),
                      ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Registration Status'),
                        subtitle: Text(
                          _project!.status.toUpperCase().replaceAll('_', ' '),
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: _project!.status == 'not_started' ? Colors.amber.shade800 : Colors.green,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.green.shade50,
                          border: Border.all(color: Colors.green.shade200),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.check_circle, color: Colors.green.shade700, size: 20),
                            const SizedBox(width: 8),
                            const Expanded(
                              child: Text(
                                'Project successfully approved and registered in database.',
                                style: TextStyle(fontSize: 12, color: Colors.green, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ] else
              const Card(
                elevation: 1,
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: Center(
                    child: Text(
                      'Enter a Project ID above to inspect approved project status.',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
