class ApprovalRequestModel {
  final String decision;
  final String? revisionNotes;

  ApprovalRequestModel({
    required this.decision,
    this.revisionNotes,
  });

  Map<String, dynamic> toJson() => {
    'decision': decision,
    if (revisionNotes != null && revisionNotes!.isNotEmpty) 'revisionNotes': revisionNotes,
  };
}

class ApprovalResponseModel {
  final String workflowId;
  final String decision;
  final String status;
  final String? projectId;
  final String message;
  final String timestamp;

  ApprovalResponseModel({
    required this.workflowId,
    required this.decision,
    required this.status,
    this.projectId,
    required this.message,
    required this.timestamp,
  });

  factory ApprovalResponseModel.fromJson(Map<String, dynamic> json) {
    return ApprovalResponseModel(
      workflowId: json['workflowId']?.toString() ?? '',
      decision: json['decision']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      projectId: json['projectId']?.toString(),
      message: json['message']?.toString() ?? '',
      timestamp: json['timestamp']?.toString() ?? '',
    );
  }
}

class WorkflowStatusModel {
  final String workflowId;
  final String status;
  final String approvalStatus;
  final bool validationPassed;
  final int retryCount;
  final String? revisionNotes;
  final String? projectId;
  final String createdAt;
  final String updatedAt;

  WorkflowStatusModel({
    required this.workflowId,
    required this.status,
    required this.approvalStatus,
    required this.validationPassed,
    required this.retryCount,
    this.revisionNotes,
    this.projectId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory WorkflowStatusModel.fromJson(Map<String, dynamic> json) {
    return WorkflowStatusModel(
      workflowId: json['workflowId']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      approvalStatus: json['approvalStatus']?.toString() ?? '',
      validationPassed: json['validationPassed'] == true,
      retryCount: json['retryCount'] is int ? json['retryCount'] : 0,
      revisionNotes: json['revisionNotes']?.toString(),
      projectId: json['projectId']?.toString(),
      createdAt: json['createdAt']?.toString() ?? '',
      updatedAt: json['updatedAt']?.toString() ?? '',
    );
  }
}

class PhaseTrackingModel {
  final String phaseName;
  final String status;
  final String? startedAtUtc;
  final String? completedAtUtc;
  final int sequenceOrder;

  PhaseTrackingModel({
    required this.phaseName,
    required this.status,
    this.startedAtUtc,
    this.completedAtUtc,
    required this.sequenceOrder,
  });

  factory PhaseTrackingModel.fromJson(Map<String, dynamic> json) {
    return PhaseTrackingModel(
      phaseName: json['phaseName']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      startedAtUtc: json['startedAtUtc']?.toString(),
      completedAtUtc: json['completedAtUtc']?.toString(),
      sequenceOrder: json['sequenceOrder'] is int ? json['sequenceOrder'] : 0,
    );
  }
}

class ProjectTrackingModel {
  final String projectId;
  final String status;
  final String? contractorName;
  final List<PhaseTrackingModel> phases;

  ProjectTrackingModel({
    required this.projectId,
    required this.status,
    this.contractorName,
    required this.phases,
  });

  factory ProjectTrackingModel.fromJson(Map<String, dynamic> json) {
    var rawPhases = json['phases'] as List<dynamic>? ?? [];
    var parsedPhases = rawPhases
        .map((p) => PhaseTrackingModel.fromJson(p as Map<String, dynamic>))
        .toList();

    return ProjectTrackingModel(
      projectId: json['projectId']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      contractorName: json['contractorName']?.toString(),
      phases: parsedPhases,
    );
  }
}
