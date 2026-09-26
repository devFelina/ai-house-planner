import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/land_submission.dart';
import '../core/network/api_client.dart';
import 'package:dio/dio.dart';

final intakeProvider = StateNotifierProvider<IntakeNotifier, AsyncValue<LandSubmission>>((ref) {
  return IntakeNotifier();
});

class IntakeNotifier extends StateNotifier<AsyncValue<LandSubmission>> {
  IntakeNotifier() : super(AsyncValue.data(LandSubmission(
    landSizePerches: 15.0,
    preferredBedrooms: 3,
    preferredBathrooms: 1,
    preferredFloors: 1,
    stylePreference: 'modern',
    spacePriority: 'balanced',
    manualTerrainType: 'flat',
  )));

  void updateField({
    double? budgetLkr,
    double? landSizePerches,
    String? manualTerrainType,
    
    double? plotWidth,
    double? plotLength,
    String? roadSide,
    String? northOrientation,
    String? entranceSide,
    String? plotSetbacks,

    int? preferredBedrooms,
    int? preferredBathrooms,
    int? preferredFloors,
    String? stylePreference,
    String? spacePriority,
    String? targetCompletionDate,
  }) {
    final currentData = state.value ?? LandSubmission();
    state = AsyncValue.data(currentData.copyWith(
      budgetLkr: budgetLkr,
      landSizePerches: landSizePerches,
      manualTerrainType: manualTerrainType,
      
      plotWidth: plotWidth,
      plotLength: plotLength,
      roadSide: roadSide,
      northOrientation: northOrientation,
      entranceSide: entranceSide,
      plotSetbacks: plotSetbacks,

      preferredBedrooms: preferredBedrooms,
      preferredBathrooms: preferredBathrooms,
      preferredFloors: preferredFloors,
      stylePreference: stylePreference,
      spacePriority: spacePriority,
      targetCompletionDate: targetCompletionDate,
      
      clearManualTerrain: manualTerrainType != null ? false : currentData.landPhoto != null,
    ));
  }

  void setPhoto(File photo) {
    final currentData = state.value ?? LandSubmission();
    state = AsyncValue.data(currentData.copyWith(
      landPhoto: photo,
      clearManualTerrain: true,
    ));
  }

  void clearPhoto() {
    final currentData = state.value ?? LandSubmission();
    state = AsyncValue.data(currentData.copyWith(clearPhoto: true));
  }

  void togglePreference(String preference) {
    final currentData = state.value ?? LandSubmission();
    
    switch (preference) {
      case 'openPlan':
        state = AsyncValue.data(currentData.copyWith(openPlan: !currentData.openPlan));
        break;
      case 'masterEnsuite':
        state = AsyncValue.data(currentData.copyWith(masterEnsuite: !currentData.masterEnsuite));
        break;
      case 'separateDining':
        state = AsyncValue.data(currentData.copyWith(separateDining: !currentData.separateDining));
        break;
      case 'homeOffice':
        state = AsyncValue.data(currentData.copyWith(homeOffice: !currentData.homeOffice));
        break;
      case 'balcony':
        state = AsyncValue.data(currentData.copyWith(balcony: !currentData.balcony));
        break;
      case 'veranda':
        state = AsyncValue.data(currentData.copyWith(veranda: !currentData.veranda));
        break;
      case 'utilityLaundry':
        state = AsyncValue.data(currentData.copyWith(utilityLaundry: !currentData.utilityLaundry));
        break;
      case 'parkingRequired':
        state = AsyncValue.data(currentData.copyWith(parkingRequired: !currentData.parkingRequired));
        break;
      case 'accessibility':
        state = AsyncValue.data(currentData.copyWith(accessibility: !currentData.accessibility));
        break;
    }
  }

  void setPreDesignedPlan(String planId, String mode) {
    final currentData = state.value ?? LandSubmission();
    state = AsyncValue.data(currentData.copyWith(
      basePreDesignedPlanId: planId,
      planSelectionMode: mode,
    ));
  }

  Future<String?> submitIntake({String? basePlanId, String? mode}) async {
    final data = state.value;
    if (data == null || !data.isValid) return null;

    state = const AsyncValue.loading();
    
    try {
      final payload = <String, dynamic>{
        'landSizePerches': data.landSizePerches,
        'manualTerrainType': data.manualTerrainType == 'flat' ? 'Flat' : data.manualTerrainType == 'hillside' ? 'Hillside' : data.manualTerrainType == 'coastal' ? 'Coastal' : data.manualTerrainType == 'forested' ? 'Forested' : 'Flat',
        'preferences': {
          'bedrooms': data.preferredBedrooms ?? 3,
          'bathrooms': data.preferredBathrooms ?? 1,
          'floors': data.preferredFloors ?? 1,
          'architecturalStyle': data.stylePreference == 'modern' ? 'Modern Minimalist' : data.stylePreference == 'traditional' ? 'Traditional' : data.stylePreference == 'contemporary' ? 'Contemporary' : 'Modern Minimalist',
          'open_plan': data.openPlan,
          'master_ensuite': data.masterEnsuite,
          'separate_dining': data.separateDining,
          'home_office': data.homeOffice,
          'balcony': data.balcony,
          'veranda': data.veranda,
          'utility_room': data.utilityLaundry,
          'parking_required': data.parkingRequired,
          'accessibility': data.accessibility,
          'space_priority': data.spacePriority ?? 'balanced',
          'circulation_preference': 'space_efficient'
        },
        'designSeed': DateTime.now().millisecondsSinceEpoch % 100000,
      };

      if (data.targetCompletionDate != null && data.targetCompletionDate!.isNotEmpty) {
        (payload['preferences'] as Map<String, dynamic>)['targetCompletionDate'] = data.targetCompletionDate;
      }

      // Conditionally add base plan fields (same as web)
      final effectiveBasePlanId = basePlanId ?? data.basePreDesignedPlanId;
      if (effectiveBasePlanId != null && effectiveBasePlanId.isNotEmpty) {
        payload['basePreDesignedPlanId'] = effectiveBasePlanId;
        payload['planSelectionMode'] = mode ?? data.planSelectionMode ?? 'use';
      }

      // Conditionally add budget
      if (data.budgetLkr != null) {
        payload['budgetLkr'] = data.budgetLkr;
      }

      // Build plotConstraints matching backend field names
      final plotConstraints = <String, dynamic>{
        'road_side': data.roadSide ?? 'south',
        'north_direction': data.northOrientation ?? 'north',
        'entrance_side': (data.entranceSide == 'road side') ? (data.roadSide ?? 'south') : (data.entranceSide ?? 'south'),
      };

      // Only include dimensions when provided (same as web)
      if (data.plotWidth != null) {
        plotConstraints['plot_width_ft'] = data.plotWidth;
      }
      if (data.plotLength != null) {
        plotConstraints['plot_length_ft'] = data.plotLength;
      }

      // Parse setbacks string into object if provided
      if (data.plotSetbacks != null && data.plotSetbacks!.isNotEmpty) {
        final setbacks = _parseSetbacks(data.plotSetbacks!);
        if (setbacks.isNotEmpty) {
          plotConstraints['setbacks'] = setbacks;
        }
      }

      payload['plotConstraints'] = plotConstraints;

      final response = await ApiClient.instance.post('/ai-generation/generate', data: payload);
      
      state = AsyncValue.data(data); 
      return response.data['workflowId'] as String? ?? response.data['WorkflowId'] as String?;
    } catch (e) {
      state = AsyncValue.data(data);
      if (e is DioException && e.response?.data != null) {
        final errorData = e.response!.data;
        final message = errorData['message'] ?? errorData['Message'] ?? e.message;
        throw Exception(message);
      }
      rethrow;
    }
  }

  /// Parses a free-text setbacks string like "Front 10ft, Rear 5ft" into a
  /// structured map e.g. { "front": 10, "rear": 5 }.
  Map<String, dynamic> _parseSetbacks(String input) {
    final result = <String, dynamic>{};
    final lower = input.toLowerCase();
    final pattern = RegExp(r'(front|rear|left|right)\s*[:=]?\s*(\d+)');
    for (final match in pattern.allMatches(lower)) {
      result[match.group(1)!] = int.parse(match.group(2)!);
    }
    return result;
  }
}