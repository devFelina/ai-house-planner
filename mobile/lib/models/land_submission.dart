import 'dart:io';

class LandSubmission {
  final double? budgetLkr;
  final double? landSizePerches;
  final File? landPhoto;
  final String? manualTerrainType;
  
  // Plot constraints
  final double? plotWidth;
  final double? plotLength;
  final String? roadSide;
  final String? northOrientation;
  final String? entranceSide;
  final String? plotSetbacks;
  final String? targetCompletionDate;

  // Preferences
  final int? preferredBedrooms;
  final int? preferredBathrooms;
  final int? preferredFloors;
  final String? stylePreference;
  final String? spacePriority;
  
  // Chips
  final bool openPlan;
  final bool masterEnsuite;
  final bool separateDining;
  final bool homeOffice;
  final bool balcony;
  final bool veranda;
  final bool utilityLaundry;
  final bool parkingRequired;
  final bool accessibility;
  
  final String? basePreDesignedPlanId;
  final String? planSelectionMode;

  LandSubmission({
    this.budgetLkr,
    this.landSizePerches,
    this.landPhoto,
    this.manualTerrainType,
    
    this.plotWidth,
    this.plotLength,
    this.roadSide = 'south',
    this.northOrientation = 'north',
    this.entranceSide = 'south',
    this.plotSetbacks,
    this.targetCompletionDate,

    this.preferredBedrooms,
    this.preferredBathrooms = 1,
    this.preferredFloors,
    this.stylePreference = 'modern',
    this.spacePriority = 'balanced',

    this.openPlan = false,
    this.masterEnsuite = false,
    this.separateDining = false,
    this.homeOffice = false,
    this.balcony = false,
    this.veranda = false,
    this.utilityLaundry = false,
    this.parkingRequired = false,
    this.accessibility = false,
    
    this.basePreDesignedPlanId,
    this.planSelectionMode,
  });

  LandSubmission copyWith({
    double? budgetLkr,
    double? landSizePerches,
    File? landPhoto,
    String? manualTerrainType,
    
    double? plotWidth,
    double? plotLength,
    String? roadSide,
    String? northOrientation,
    String? entranceSide,
    String? plotSetbacks,
    String? targetCompletionDate,

    int? preferredBedrooms,
    int? preferredBathrooms,
    int? preferredFloors,
    String? stylePreference,
    String? spacePriority,

    bool? openPlan,
    bool? masterEnsuite,
    bool? separateDining,
    bool? homeOffice,
    bool? balcony,
    bool? veranda,
    bool? utilityLaundry,
    bool? parkingRequired,
    bool? accessibility,
    
    String? basePreDesignedPlanId,
    String? planSelectionMode,
    bool clearPhoto = false,
    bool clearManualTerrain = false,
  }) {
    return LandSubmission(
      budgetLkr: budgetLkr ?? this.budgetLkr,
      landSizePerches: landSizePerches ?? this.landSizePerches,
      landPhoto: clearPhoto ? null : (landPhoto ?? this.landPhoto),
      manualTerrainType: clearManualTerrain ? null : (manualTerrainType ?? this.manualTerrainType),
      
      plotWidth: plotWidth ?? this.plotWidth,
      plotLength: plotLength ?? this.plotLength,
      roadSide: roadSide ?? this.roadSide,
      northOrientation: northOrientation ?? this.northOrientation,
      entranceSide: entranceSide ?? this.entranceSide,
      plotSetbacks: plotSetbacks ?? this.plotSetbacks,
      targetCompletionDate: targetCompletionDate ?? this.targetCompletionDate,

      preferredBedrooms: preferredBedrooms ?? this.preferredBedrooms,
      preferredBathrooms: preferredBathrooms ?? this.preferredBathrooms,
      preferredFloors: preferredFloors ?? this.preferredFloors,
      stylePreference: stylePreference ?? this.stylePreference,
      spacePriority: spacePriority ?? this.spacePriority,

      openPlan: openPlan ?? this.openPlan,
      masterEnsuite: masterEnsuite ?? this.masterEnsuite,
      separateDining: separateDining ?? this.separateDining,
      homeOffice: homeOffice ?? this.homeOffice,
      balcony: balcony ?? this.balcony,
      veranda: veranda ?? this.veranda,
      utilityLaundry: utilityLaundry ?? this.utilityLaundry,
      parkingRequired: parkingRequired ?? this.parkingRequired,
      accessibility: accessibility ?? this.accessibility,
      
      basePreDesignedPlanId: basePreDesignedPlanId ?? this.basePreDesignedPlanId,
      planSelectionMode: planSelectionMode ?? this.planSelectionMode,
    );
  }

  bool get isValid {
    return (landSizePerches ?? 0) > 0 &&
           (preferredBedrooms ?? 0) > 0 &&
           (preferredFloors ?? 0) > 0;
  }
}