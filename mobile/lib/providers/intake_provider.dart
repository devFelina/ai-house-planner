import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/land_submission.dart';

// Provides the current state of the intake form
final intakeProvider = StateNotifierProvider<IntakeNotifier, AsyncValue<LandSubmission>>((ref) {
  return IntakeNotifier();
});

class IntakeNotifier extends StateNotifier<AsyncValue<LandSubmission>> {
  IntakeNotifier() : super(AsyncValue.data(LandSubmission()));

  void updateField({
    double? budgetLkr,
    double? landSizePerches,
    String? manualTerrainType,
    int? preferredBedrooms,
    int? preferredFloors,
    String? stylePreference,
  }) {
    final currentData = state.value ?? LandSubmission();
    state = AsyncValue.data(currentData.copyWith(
      budgetLkr: budgetLkr,
      landSizePerches: landSizePerches,
      manualTerrainType: manualTerrainType,
      preferredBedrooms: preferredBedrooms,
      preferredFloors: preferredFloors,
      stylePreference: stylePreference,
      clearManualTerrain: manualTerrainType != null ? false : currentData.landPhoto != null,
    ));
  }

  void setPhoto(File photo) {
    final currentData = state.value ?? LandSubmission();
    // If a photo is provided, clear the manual terrain fallback
    state = AsyncValue.data(currentData.copyWith(
      landPhoto: photo,
      clearManualTerrain: true,
    ));
  }

  void clearPhoto() {
    final currentData = state.value ?? LandSubmission();
    state = AsyncValue.data(currentData.copyWith(clearPhoto: true));
  }

  Future<bool> submitIntake() async {
    final data = state.value;
    if (data == null || !data.isValid) return false;

    state = const AsyncValue.loading();
    
    try {
      // TODO: Connect this to your API client (e.g., using Dio)
      // Example implementation:
      // final formData = FormData.fromMap({
      //   'BudgetLkr': data.budgetLkr,
      //   'LandSizePerches': data.landSizePerches,
      //   'PreferredBedrooms': data.preferredBedrooms,
      //   'PreferredFloors': data.preferredFloors,
      //   'StylePreference': data.stylePreference,
      //   if (data.manualTerrainType != null) 'ManualTerrainType': data.manualTerrainType,
      //   if (data.landPhoto != null)
      //     'LandPhoto': await MultipartFile.fromFile(data.landPhoto!.path),
      // });
      // await apiClient.post('/api/v1/intake', data: formData);
      
      // Simulating a network delay for the AI orchestration
      await Future.delayed(const Duration(seconds: 3));
      
      state = AsyncValue.data(data); // Revert to data state on success
      return true;
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      return false;
    }
  }
}
