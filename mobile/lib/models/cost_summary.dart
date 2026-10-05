/// Cost estimate returned by the shared ASP.NET Core API (`CostSummaryDto`).
///
/// The estimate is calculated by the Cost Estimation Agent and stored with the
/// design; the app only displays it and never recalculates it.
class CostSummary {
  final double materialCostLkr;
  final double labourCostLkr;
  final double totalCostLkr;
  final double? budgetDeltaPercent;
  final List<CostBreakdownLine> breakdown;
  final String? formulaVersion;
  final double? appliedAreaSqft;
  final String? terrainType;
  final DateTime? estimatedAt;

  const CostSummary({
    required this.materialCostLkr,
    required this.labourCostLkr,
    required this.totalCostLkr,
    this.budgetDeltaPercent,
    this.breakdown = const [],
    this.formulaVersion,
    this.appliedAreaSqft,
    this.terrainType,
    this.estimatedAt,
  });

  /// Returns null when the API sent no estimate or one without a usable total.
  static CostSummary? tryParse(dynamic json) {
    if (json is! Map) return null;
    final total = _toDouble(json['totalCostLkr']);
    if (total == null) return null;

    final rawBreakdown = json['breakdown'];
    final lines = rawBreakdown is List
        ? rawBreakdown.map(CostBreakdownLine.tryParse).whereType<CostBreakdownLine>().toList()
        : <CostBreakdownLine>[];

    return CostSummary(
      materialCostLkr: _toDouble(json['materialCostLkr']) ?? 0,
      labourCostLkr: _toDouble(json['labourCostLkr']) ?? 0,
      totalCostLkr: total,
      budgetDeltaPercent: _toDouble(json['budgetDeltaPercent']),
      breakdown: lines,
      formulaVersion: _toText(json['formulaVersion']),
      appliedAreaSqft: _toDouble(json['appliedAreaSqft']),
      terrainType: _toText(json['terrainType']),
      estimatedAt: _toDate(json['estimatedAt']),
    );
  }
}

/// One cost-head line of the saved estimate (`CostBreakdownItemDto`).
class CostBreakdownLine {
  final String itemName;
  final String costHead;
  final String category;
  final double unitCostLkr;
  final String unit;
  final double appliedQuantity;
  final String quantityUnit;
  final double terrainMultiplier;
  final double amountLkr;
  final double sharePercent;
  final String? provider;
  final String? sourceReference;
  final DateTime? pricingUpdatedAt;

  const CostBreakdownLine({
    required this.itemName,
    required this.costHead,
    required this.category,
    required this.unitCostLkr,
    required this.unit,
    required this.appliedQuantity,
    required this.quantityUnit,
    required this.terrainMultiplier,
    required this.amountLkr,
    required this.sharePercent,
    this.provider,
    this.sourceReference,
    this.pricingUpdatedAt,
  });

  bool get isLabour => category.toLowerCase() == 'labour';

  static CostBreakdownLine? tryParse(dynamic json) {
    if (json is! Map) return null;
    final amount = _toDouble(json['amountLkr']);
    if (amount == null) return null;
    final itemName = _toText(json['itemName']) ?? '';
    return CostBreakdownLine(
      itemName: itemName,
      costHead: _toText(json['costHead']) ?? itemName,
      category: _toText(json['category']) ?? 'material',
      unitCostLkr: _toDouble(json['unitCostLkr']) ?? 0,
      unit: _toText(json['unit']) ?? '',
      appliedQuantity: _toDouble(json['appliedQuantity']) ?? 0,
      quantityUnit: _toText(json['quantityUnit']) ?? '',
      terrainMultiplier: _toDouble(json['terrainMultiplier']) ?? 1,
      amountLkr: amount,
      sharePercent: _toDouble(json['sharePercent']) ?? 0,
      provider: _toText(json['provider']),
      sourceReference: _toText(json['sourceReference']),
      pricingUpdatedAt: _toDate(json['pricingUpdatedAt']),
    );
  }
}

double? _toDouble(dynamic value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

String? _toText(dynamic value) {
  if (value == null) return null;
  final text = value.toString().trim();
  return text.isEmpty ? null : text;
}

DateTime? _toDate(dynamic value) => value is String ? DateTime.tryParse(value) : null;
