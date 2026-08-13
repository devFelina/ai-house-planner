import 'dart:io';

class LandSubmission {
  final double? budgetLkr;
  final double? landSizePerches;
  final File? landPhoto;
  final String? manualTerrainType;
  final int? preferredBedrooms;
  final int? preferredFloors;
  final String? stylePreference;

  //The value given to the constructor is put into the property of this object.
  LandSubmission({
    this.budgetLkr,
    this.landSizePerches,
    this.landPhoto,
    this.manualTerrainType,
    this.preferredBedrooms,
    this.preferredFloors,
    this.stylePreference,
  });

  //A new LandSubmission object based on current object is created, but only the values that are wanted are changed.
  LandSubmission copyWith({
    double? budgetLkr,
    double? landSizePerches,
    File? landPhoto,
    String? manualTerrainType,
    int? preferredBedrooms,
    int? preferredFloors,
    String? stylePreference,
    bool clearPhoto=false,
    bool clearManualTerrain=false
  }){
    return LandSubmission(
      budgetLkr: budgetLkr??this.budgetLkr,
      landSizePerches: landSizePerches??this.landSizePerches,
      landPhoto: clearPhoto ? null:(landPhoto ?? this.landPhoto),
      manualTerrainType: clearManualTerrain ? null :(manualTerrainType ?? this.manualTerrainType),
      preferredBedrooms: preferredBedrooms ?? this.preferredBedrooms,
      preferredFloors: preferredFloors ?? this.preferredFloors,
      stylePreference: stylePreference ?? this.stylePreference,
    );
  }

  //To check form is valid submission 
  bool get isValid{
    return(budgetLkr ?? 0)>0 &&
      (landSizePerches ?? 0)>0 &&
      (preferredBedrooms ?? 0)>0 &&
      (preferredFloors ?? 0)>0 &&
      (landPhoto!=null || (manualTerrainType !=null && manualTerrainType!.isNotEmpty));
  }

}