import 'package:flutter/material.dart';
import '../services/workflow_service.dart';
import '../widgets/floor_plan_painter.dart';

class DesignPreviewView extends StatefulWidget {
  final String workflowId;

  const DesignPreviewView({Key? key, required this.workflowId}) : super(key: key);

  @override
  _DesignPreviewViewState createState() => _DesignPreviewViewState();
}

class _DesignPreviewViewState extends State<DesignPreviewView> {
  final WorkflowService _service = WorkflowService();
  bool _isLoading = true;
  String? _error;
  Map<String, dynamic>? _workflowData;
  List<RoomLayout> _rooms = [];
  int _selectedFloor = 1;
  int _floorCount = 1;

  @override
  void initState() {
    super.initState();
    _fetchStatus();
  }

  Future<void> _fetchStatus() async {
    try {
      final data = await _service.getWorkflowStatus(widget.workflowId);

      setState(() {
        _workflowData = data;
        if (data['status'] == 'failed') {
          _error = data['terrainType'] == 'unknown'
              ? 'Provide a manual terrain classification and submit again.'
              : 'No valid layout was saved. Review plot dimensions and room requirements, then submit again.';
        }
        if (data['design'] != null && data['design']['rooms'] != null) {
          // Convert the API DTO format to the UI's RoomLayout model
          _rooms = (data['design']['rooms'] as List).map((r) {
            final entrances = (data['design']['entrances'] as List? ?? []).where((e) => e['room_id'] == r['roomId']);
            return RoomLayout(
              entrance: entrances.isEmpty ? null : Opening.fromJson(entrances.first),
              roomId: r['roomId'] ?? '',
              roomType: r['roomType'] ?? 'unknown',
              name: r['name'],
              floor: r['floorNumber'] ?? 1,
              x: (r['x'] as num).toDouble(),
              y: (r['y'] as num).toDouble(),
              width: (r['width'] as num).toDouble(),
              length: (r['length'] as num).toDouble(),
              doors: (r['doors'] as List?)
                      ?.map((d) => Opening(
                            wall: d['wall'],
                            offset: (d['offset'] as num).toDouble(),
                            width: (d['width'] as num).toDouble(),
                          ))
                      .toList() ??
                  [],
              windows: (r['windows'] as List?)
                      ?.map((w) => Opening(
                            wall: w['wall'],
                            offset: (w['offset'] as num).toDouble(),
                            width: (w['width'] as num).toDouble(),
                          ))
                      .toList() ??
                  [],
            );
          }).toList();

          _floorCount = data['design']['floorCount'] ?? 1;
        }
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _handleApproval(String decision) async {
    try {
      await _service.approveWorkflow(widget.workflowId, decision);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Design $decision submitted successfully')),
      );
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(color: Colors.indigo),
              SizedBox(height: 16),
              Text('Loading design...', style: TextStyle(color: Colors.grey)),
            ],
          ),
        ),
      );
    }

    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Error')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(_error!, style: const TextStyle(color: Colors.red), textAlign: TextAlign.center),
          ),
        ),
      );
    }

    if (_workflowData == null || _workflowData!['design'] == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Design Pending')),
        body: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.construction, size: 48, color: Colors.grey),
              SizedBox(height: 16),
              Text('AI is currently generating your house design...'),
              SizedBox(height: 8),
              Text('This page will update when ready.', style: TextStyle(color: Colors.grey, fontSize: 12)),
            ],
          ),
        ),
      );
    }

    final design = _workflowData!['design'];
    final version = design['version'] ?? 1;
    final terrainType = _workflowData!['terrainType'] ?? 'N/A';

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: Text('Your Home Design (v$version)', style: const TextStyle(color: Colors.black87, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black87),
      ),
      body: Column(
        children: [
          // Specs Card
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: Colors.grey[50],
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildSpecItem('Floors', design['floorCount'].toString()),
                _buildSpecItem('Area', '${design['totalBuiltUpAreaSqft']} sqft'),
                _buildSpecItem('Foundation', (design['foundationType'] ?? '').toString().toUpperCase()),
                _buildSpecItem('Terrain', terrainType.toString().toUpperCase()),
              ],
            ),
          ),

          // Floor Tabs (only show for multi-floor)
          if (_floorCount > 1)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: Colors.white,
              child: Row(
                children: List.generate(_floorCount, (i) {
                  final floor = i + 1;
                  final isSelected = _selectedFloor == floor;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text('Floor $floor'),
                      selected: isSelected,
                      selectedColor: Colors.indigo,
                      labelStyle: TextStyle(
                        color: isSelected ? Colors.white : Colors.black87,
                        fontWeight: FontWeight.w600,
                      ),
                      onSelected: (_) => setState(() => _selectedFloor = floor),
                    ),
                  );
                }),
              ),
            ),

          // Floor Plan Interactive View
          Expanded(
            child: InteractiveViewer(
              minScale: 0.5,
              maxScale: 3.0,
              child: FloorPlanViewer(rooms: _rooms, floorFilter: _selectedFloor),
            ),
          ),

          // Action Buttons
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, -5))
              ],
            ),
            child: Column(
              children: [
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.indigo,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: () => _handleApproval('approve'),
                    child: const Text('Approve & Proceed to Costing', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: () => _handleApproval('reject'),
                    child: const Text('Reject Design'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSpecItem(String label, String value) {
    return Column(
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(color: Colors.black87, fontSize: 14, fontWeight: FontWeight.bold)),
      ],
    );
  }
}
