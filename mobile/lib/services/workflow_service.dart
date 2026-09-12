import 'dart:convert';
import 'package:http/http.dart' as http;
import '../widgets/floor_plan_painter.dart'; // To access RoomLayout

class WorkflowService {
  // Update to match your local or cloud backend API URL
  static const String baseUrl = 'http://10.0.2.2:5265/api/v1'; // 10.0.2.2 is localhost for Android emulator

  Future<Map<String, dynamic>> getWorkflowStatus(String id) async {
    final response = await http.get(Uri.parse('$baseUrl/workflows/$id/status'));

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load workflow status');
    }
  }

  Future<void> approveWorkflow(String id, String decision) async {
    final response = await http.post(
      Uri.parse('$baseUrl/workflows/$id/approve'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'decision': decision,
        'revisionNotes': decision == 'reject' ? 'Client rejected design.' : null
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to submit approval decision');
    }
  }
}
