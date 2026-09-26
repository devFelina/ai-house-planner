import '../widgets/floor_plan_painter.dart';

class Plan {
  final String id;
  final String name;
  final String slug;
  final String description;
  final String style;
  final double estimatedCost;
  final int squareFootage;
  final int bedrooms;
  final int bathrooms;
  final List<String> imageUrls;
  final String designCode;
  final String category;
  final String suitableTerrain;
  final int floorCount;
  final double totalBuiltUpAreaSqft;
  final int minimumLandSizePerches;
  final int parkingSpaces;
  final bool hasBalcony;
  final bool hasVeranda;
  final bool hasOffice;
  final bool isAccessibleFriendly;
  final List<String> tags;
  final String thumbnailUrl;
  final bool isActive;
  final double? minimumPlotWidthFt;
  final double? minimumPlotLengthFt;
  final bool hasUtilityRoom;
  final String? conceptualDisclaimer;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final List<RoomLayout>? layout;

  Plan({
    required this.id,
    required this.name,
    this.slug = '',
    required this.description,
    required this.style,
    required this.estimatedCost,
    required this.squareFootage,
    required this.bedrooms,
    required this.bathrooms,
    required this.imageUrls,
    this.designCode = 'P-001',
    this.category = 'Standard',
    this.suitableTerrain = 'Flat',
    this.floorCount = 1,
    this.totalBuiltUpAreaSqft = 0.0,
    this.minimumLandSizePerches = 10,
    this.parkingSpaces = 0,
    this.hasBalcony = false,
    this.hasVeranda = false,
    this.hasOffice = false,
    this.isAccessibleFriendly = false,
    this.tags = const [],
    this.thumbnailUrl = '',
    this.isActive = true,
    this.minimumPlotWidthFt,
    this.minimumPlotLengthFt,
    this.hasUtilityRoom = false,
    this.conceptualDisclaimer,
    required this.createdAt,
    this.updatedAt,
    this.layout,
  });

  factory Plan.fromJson(Map<String, dynamic> json) {
    String? thumb = json['thumbnailUrl'] as String?;
    List<String> images = thumb != null && thumb.isNotEmpty ? [thumb] : [];
    
    List<RoomLayout>? parsedLayout;
    if (json['layout'] != null && json['layout']['rooms'] != null) {
      final entrancesJson = json['layout']['entrances'] as List?;
      parsedLayout = (json['layout']['rooms'] as List).map((r) {
        Map<String, dynamic> roomData = Map<String, dynamic>.from(r);
        if (entrancesJson != null) {
          final entrance = entrancesJson.firstWhere(
            (e) => e['room_id'] == roomData['room_id'] || e['roomId'] == roomData['roomId'], 
            orElse: () => null
          );
          if (entrance != null) {
            roomData['entrance'] = entrance;
          }
        }
        return RoomLayout.fromJson(roomData);
      }).toList();
    }
    
    return Plan(
      id: json['id']?.toString() ?? '',
      name: json['name'] ?? '',
      slug: json['slug'] ?? '',
      description: json['description'] ?? '',
      style: json['style'] ?? '',
      estimatedCost: _parseDouble(json['estimatedCost']),
      squareFootage: (json['squareFootage'] as num?)?.toInt() ?? 0,
      bedrooms: (json['bedrooms'] as num?)?.toInt() ?? 0,
      bathrooms: (json['bathrooms'] as num?)?.toInt() ?? 0,
      imageUrls: images,
      designCode: json['designCode'] ?? json['id']?.toString().substring(0, 5) ?? 'P-001',
      category: json['category'] ?? 'Standard',
      suitableTerrain: json['suitableTerrain'] ?? 'Flat',
      floorCount: (json['floorCount'] as num?)?.toInt() ?? 1,
      totalBuiltUpAreaSqft: _parseDouble(json['totalBuiltUpAreaSqft'] ?? json['squareFootage']),
      minimumLandSizePerches: (json['minimumLandSizePerches'] as num?)?.toInt() ?? 10,
      parkingSpaces: (json['parkingSpaces'] as num?)?.toInt() ?? 0,
      hasBalcony: json['hasBalcony'] ?? false,
      hasVeranda: json['hasVeranda'] ?? false,
      hasOffice: json['hasOffice'] ?? false,
      isAccessibleFriendly: json['isAccessibleFriendly'] ?? false,
      tags: (json['tags'] as List?)?.map((t) => t.toString()).toList() ?? [],
      thumbnailUrl: thumb ?? '',
      isActive: json['isActive'] ?? true,
      minimumPlotWidthFt: _parseDoubleOrNull(json['minimumPlotWidthFt']),
      minimumPlotLengthFt: _parseDoubleOrNull(json['minimumPlotLengthFt']),
      hasUtilityRoom: json['hasUtilityRoom'] ?? false,
      conceptualDisclaimer: json['conceptualDisclaimer'],
      createdAt: json['createdAt'] != null ? DateTime.parse(json['createdAt']) : DateTime.now(),
      updatedAt: json['updatedAt'] != null ? DateTime.parse(json['updatedAt']) : null,
      layout: parsedLayout,
    );
  }

  static double _parseDouble(dynamic value, [double defaultValue = 0.0]) {
    if (value == null) return defaultValue;
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? defaultValue;
    return defaultValue; // Return default if it's a map or other type
  }

  static double? _parseDoubleOrNull(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }
}

